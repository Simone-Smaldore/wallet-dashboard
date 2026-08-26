"""The checks doctor runs.

They are pure functions over rows already loaded, so they are tested here
without a database — the same rule the rest of the project follows: the part
that can be wrong is the part that has to be testable.
"""

from scripts.doctor import Row, World, check, check_migration, check_similar_names

WORLD = World(accounts={1, 2}, categories={10: "expense", 90: "income"})


def movement(**overrides) -> Row:
    row = {
        "id": 1,
        "kind": "expense",
        "amount_cents": 1_000,
        "account_id": 1,
        "counter_account_id": None,
        "category_id": 10,
        "is_adjustment": False,
    }
    row.update(overrides)
    return Row(**row)


def checks(*rows) -> set[str]:
    return {finding.check for finding in check(list(rows), WORLD)}


def test_healthy_data_finds_nothing():
    """The test that keeps the others honest: a clean database has to come back
    silent, or every finding is noise."""
    assert (
        check(
            [
                movement(id=1),
                movement(id=2, kind="income", category_id=90),
                movement(
                    id=3, kind="transfer", counter_account_id=2, category_id=None
                ),
                movement(id=4, category_id=None, is_adjustment=True),
            ],
            WORLD,
        )
        == []
    )


def test_a_movement_pointing_at_an_account_that_is_gone():
    assert "orfano" in checks(movement(account_id=99))


def test_a_movement_pointing_at_a_category_that_is_gone():
    assert "orfano" in checks(movement(category_id=99))


def test_a_transfer_without_its_second_account():
    """⚠️ Reported, never repaired: which account would it be? A guess here
    looks like a fix and moves money in the balances."""
    findings = check([movement(kind="transfer", counter_account_id=None, category_id=None)], WORLD)

    assert findings[0].check == "trasferimento"
    assert findings[0].fixable is False


def test_a_transfer_with_the_same_account_on_both_sides():
    assert "trasferimento" in checks(
        movement(kind="transfer", counter_account_id=1, category_id=None)
    )


def test_a_transfer_with_a_category_is_repairable():
    """The rule the whole model rests on, and the one repair that is not a
    choice: a transfer has no category by definition."""
    findings = check([movement(kind="transfer", counter_account_id=2, category_id=10)], WORLD)

    assert findings[0].fixable is True


def test_a_spend_filed_under_an_income_category():
    """⚠️ Found but not fixed: putting it right means choosing a category, and
    choosing one changes what a chart says."""
    findings = check([movement(kind="expense", category_id=90)], WORLD)

    assert findings[0].check == "categoria"
    assert findings[0].fixable is False
    assert "expense" in findings[0].detail


def test_an_amount_of_zero_or_less():
    """The sign lives in `kind`, so a negative amount is not "money out" — it is
    a number that subtracts where every sum expects it to add."""
    assert "importo" in checks(movement(amount_cents=0))
    assert "importo" in checks(movement(amount_cents=-500))


def test_a_rectification_with_a_category_is_repairable():
    findings = check([movement(is_adjustment=True, category_id=10)], WORLD)

    assert any(f.check == "rettifica" and f.fixable for f in findings)


def test_a_second_account_on_something_that_is_not_a_transfer():
    assert "conto" in checks(movement(kind="expense", counter_account_id=2))


# --------------------------------------------------------------------------
# The check that would have saved two afternoons
# --------------------------------------------------------------------------


def test_a_database_behind_the_repository_is_reported():
    """⚠️ This one earns its place from experience: twice, a column the code
    selected and the database did not have came out as a 500 with a stack trace
    three screens long, and nothing in it said "alembic upgrade head"."""
    findings = check_migration(applied="a5fa7907b274", head="cf58aa978b71")

    assert findings[0].check == "migrazione"
    assert "alembic upgrade head" in findings[0].detail


def test_a_database_that_was_never_migrated_is_reported():
    assert check_migration(applied=None, head="cf58aa978b71")


def test_a_database_in_step_says_nothing():
    assert check_migration(applied="cf58aa978b71", head="cf58aa978b71") == []


# --------------------------------------------------------------------------
# Categories that are probably one category
# --------------------------------------------------------------------------


def test_two_categories_that_look_like_one_are_suggested():
    findings = check_similar_names([("expense", "Bar"), ("expense", "Bar e caffè")])

    assert findings[0].check == "doppioni"


def test_the_same_name_on_the_two_lists_is_not_a_duplicate():
    """⚠️ "Regalo" as a spend is a present you bought; as income it is money
    someone gave you. That is the distinction the two lists exist for."""
    assert check_similar_names([("expense", "Regalo"), ("income", "Regalo")]) == []


def test_two_unrelated_names_are_left_alone():
    assert check_similar_names([("expense", "Spesa"), ("expense", "Trasporti")]) == []
