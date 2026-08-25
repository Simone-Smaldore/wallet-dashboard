"""The CHECK constraints on `transaction`.

No screen writes this table yet — the movements arrive with M3 — but its shape
*is* the model, and these are the rules that stop a wrong row from ever existing
rather than hoping every future caller remembers them.

⚠️ These test the **database**, not Python. SQLite does enforce CHECK
constraints (it does not enforce foreign keys unless asked, which is a different
thing and not what is being checked here), so the same constraint text is
exercised locally and in Postgres.
"""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Account, Category, Household, Transaction


@pytest.fixture
def fixtures(db_factory):
    """A household with two accounts and a category to point at."""
    with db_factory() as db:
        household = db.query(Household).first()
        first = Account(
            household_id=household.id,
            name="Corrente",
            kind="corrente",
            opening_balance_cents=0,
            opening_date=date(2026, 1, 1),
        )
        second = Account(
            household_id=household.id,
            name="Deposito",
            kind="deposito",
            opening_balance_cents=0,
            opening_date=date(2026, 1, 1),
        )
        category = Category(
            household_id=household.id,
            name="Spesa",
            kind="expense",
            color="chart-1",
            icon="ShoppingCart",
        )
        db.add_all([first, second, category])
        db.commit()
        yield {
            "household_id": household.id,
            "account_id": first.id,
            "other_account_id": second.id,
            "category_id": category.id,
        }


def movement(fixtures, **overrides) -> Transaction:
    fields = {
        "household_id": fixtures["household_id"],
        "date": date(2026, 3, 12),
        "kind": "expense",
        "amount_cents": 1250,
        "account_id": fixtures["account_id"],
        "category_id": fixtures["category_id"],
    }
    return Transaction(**{**fields, **overrides})


def insert(db_factory, row) -> None:
    with db_factory() as db:
        db.add(row)
        db.commit()


def test_a_well_formed_expense_is_accepted(db_factory, fixtures):
    insert(db_factory, movement(fixtures))


def test_a_zero_amount_is_refused(db_factory, fixtures):
    """The sign lives in `kind`, so the amount is always strictly positive. A
    zero movement is not a movement."""
    with pytest.raises(IntegrityError):
        insert(db_factory, movement(fixtures, amount_cents=0))


def test_a_negative_amount_is_refused(db_factory, fixtures):
    with pytest.raises(IntegrityError):
        insert(db_factory, movement(fixtures, amount_cents=-500))


def test_a_transfer_with_a_category_is_refused(db_factory, fixtures):
    """⚠️ The rule the whole model rests on. A transfer is neither income nor an
    expense, so it cannot be filed under one — and the database is what makes
    that true rather than a convention some future endpoint might forget."""
    with pytest.raises(IntegrityError):
        insert(
            db_factory,
            movement(
                fixtures,
                kind="transfer",
                counter_account_id=fixtures["other_account_id"],
            ),
        )


def test_a_transfer_without_a_counter_account_is_refused(db_factory, fixtures):
    with pytest.raises(IntegrityError):
        insert(db_factory, movement(fixtures, kind="transfer", category_id=None))


def test_an_expense_with_a_counter_account_is_refused(db_factory, fixtures):
    """The implication runs both ways: only a transfer has two accounts."""
    with pytest.raises(IntegrityError):
        insert(
            db_factory,
            movement(fixtures, counter_account_id=fixtures["other_account_id"]),
        )


def test_a_transfer_onto_the_same_account_is_refused(db_factory, fixtures):
    """Money that leaves and lands in the same place is a typo, and it would
    quietly do nothing at all to the balance."""
    with pytest.raises(IntegrityError):
        insert(
            db_factory,
            movement(
                fixtures,
                kind="transfer",
                category_id=None,
                counter_account_id=fixtures["account_id"],
            ),
        )


def test_an_adjustment_carries_no_category(db_factory, fixtures):
    """A reconciliation is the measure of what you forgot to record, not a
    spend: filing it under a category would invent an expense you cannot
    account for."""
    with pytest.raises(IntegrityError):
        insert(db_factory, movement(fixtures, is_adjustment=True))

    # Without a category it is fine.
    insert(db_factory, movement(fixtures, is_adjustment=True, category_id=None))
