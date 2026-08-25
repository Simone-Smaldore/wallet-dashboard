"""Movements over HTTP: the three kinds, the filters, the cursor, the rectifier."""

from datetime import date, timedelta

import pytest

TODAY = date.today()


@pytest.fixture
def setup(signed_in):
    """Two accounts and two categories to point at."""
    corrente = signed_in.post(
        "/api/accounts",
        json={
            "name": "Corrente",
            "kind": "corrente",
            "opening_balance_cents": 100_000,
            "opening_date": "2026-01-01",
        },
    ).json()
    deposito = signed_in.post(
        "/api/accounts",
        json={
            "name": "Deposito",
            "kind": "deposito",
            "opening_balance_cents": 500_000,
            "opening_date": "2026-01-01",
        },
    ).json()
    spesa = signed_in.post(
        "/api/categories",
        json={"name": "Spesa", "kind": "expense", "color": "chart-1", "icon": "ShoppingCart"},
    ).json()
    stipendio = signed_in.post(
        "/api/categories",
        json={"name": "Stipendio", "kind": "income", "color": "chart-2", "icon": "Banknote"},
    ).json()
    return {
        "client": signed_in,
        "corrente": corrente,
        "deposito": deposito,
        "spesa": spesa,
        "stipendio": stipendio,
    }


def expense(setup, **overrides):
    body = {
        "kind": "expense",
        "date": TODAY.isoformat(),
        "amount_cents": 2_500,
        "account_id": setup["corrente"]["id"],
        "category_id": setup["spesa"]["id"],
    }
    return setup["client"].post("/api/transactions", json={**body, **overrides})


def balance_of(setup, account_key: str) -> int:
    listed = setup["client"].get("/api/accounts").json()
    target = setup[account_key]["id"]
    return next(a["balance_cents"] for a in listed["accounts"] if a["id"] == target)


def test_movements_need_a_session(client):
    assert client.get("/api/transactions").status_code == 401


def test_an_expense_leaves_the_account(setup):
    created = expense(setup)
    assert created.status_code == 201
    body = created.json()
    # The row carries what it needs to draw itself.
    assert body["account_name"] == "Corrente"
    assert body["category_name"] == "Spesa"
    assert body["category_color"] == "chart-1"

    assert balance_of(setup, "corrente") == 100_000 - 2_500


def test_income_arrives(setup):
    expense(
        setup,
        kind="income",
        amount_cents=180_000,
        category_id=setup["stipendio"]["id"],
    )
    assert balance_of(setup, "corrente") == 100_000 + 180_000


def test_a_transfer_moves_both_and_no_total(setup):
    """⚠️ The rule the whole model rests on, checked end to end this time."""
    before = setup["client"].get("/api/accounts").json()["net_worth_cents"]

    created = expense(
        setup,
        kind="transfer",
        amount_cents=50_000,
        counter_account_id=setup["deposito"]["id"],
        category_id=None,
    )
    assert created.status_code == 201

    assert balance_of(setup, "corrente") == 100_000 - 50_000
    assert balance_of(setup, "deposito") == 500_000 + 50_000
    assert setup["client"].get("/api/accounts").json()["net_worth_cents"] == before


def test_a_transfer_appears_in_neither_expenses_nor_income(setup):
    """⚠️ The untouchable one, at the level the screens actually read."""
    expense(setup)
    expense(
        setup,
        kind="transfer",
        amount_cents=50_000,
        counter_account_id=setup["deposito"]["id"],
        category_id=None,
    )

    expenses = setup["client"].get("/api/transactions?kind=expense").json()["transactions"]
    incomes = setup["client"].get("/api/transactions?kind=income").json()["transactions"]

    assert all(row["kind"] == "expense" for row in expenses)
    assert len(expenses) == 1
    assert incomes == []


def test_a_transfer_with_a_category_is_refused_readably(setup):
    """The database would refuse it anyway; this makes the answer a sentence
    instead of a 500."""
    response = expense(
        setup,
        kind="transfer",
        counter_account_id=setup["deposito"]["id"],
        category_id=setup["spesa"]["id"],
    )
    assert response.status_code == 422
    assert "trasferimento" in str(response.json()["detail"]).lower()


def test_a_transfer_onto_itself_is_refused(setup):
    response = expense(
        setup,
        kind="transfer",
        counter_account_id=setup["corrente"]["id"],
        category_id=None,
    )
    assert response.status_code == 422


def test_a_category_of_the_wrong_sign_is_refused(setup):
    """⚠️ Filing a spend under "Stipendio" would put money on the wrong side of
    every chart, and nothing downstream would notice."""
    response = expense(setup, category_id=setup["stipendio"]["id"])
    assert response.status_code == 422
    assert "entrata" in response.json()["detail"]


def test_an_account_of_someone_else_is_a_404(setup):
    assert expense(setup, account_id=9999).status_code == 404


def test_a_zero_amount_never_reaches_the_database(setup):
    assert expense(setup, amount_cents=0).status_code == 422


def test_the_period_filter_includes_both_ends(setup):
    expense(setup, date="2026-03-01")
    expense(setup, date="2026-03-31")
    expense(setup, date="2026-04-01")

    march = setup["client"].get("/api/transactions?from=2026-03-01&to=2026-03-31").json()
    assert len(march["transactions"]) == 2


def test_filtering_by_account_finds_both_sides_of_a_transfer(setup):
    """Money landing on the savings account has to be visible from the savings
    account, and it arrives there through `counter_account_id`."""
    expense(
        setup,
        kind="transfer",
        amount_cents=50_000,
        counter_account_id=setup["deposito"]["id"],
        category_id=None,
    )

    seen = setup["client"].get(
        f"/api/transactions?account_id={setup['deposito']['id']}"
    ).json()
    assert len(seen["transactions"]) == 1


def test_text_search_ignores_case(setup):
    expense(setup, description="Esselunga di via Roma")
    expense(setup, description="Benzina")

    found = setup["client"].get("/api/transactions?q=ESSELUNGA").json()
    assert len(found["transactions"]) == 1


def test_the_cursor_does_not_repeat_or_skip_when_a_row_is_inserted(setup):
    """⚠️ The test that justifies keyset over OFFSET.

    Recording a spend from last month while someone is scrolling must not slide
    the pages under them. With an offset, inserting a row above the boundary
    pushes one row from page 1 down into page 2 — it gets read twice — or the
    other way round and one is never seen at all.
    """
    for day in range(1, 11):
        expense(setup, date=f"2026-03-{day:02d}", amount_cents=day * 100)

    first = setup["client"].get("/api/transactions?limit=5").json()
    assert len(first["transactions"]) == 5
    assert first["next_cursor"]

    # Someone records an older spend, right in the middle of the ordering.
    expense(setup, date="2026-03-06", amount_cents=9_999)

    second = setup["client"].get(
        f"/api/transactions?limit=5&cursor={first['next_cursor']}"
    ).json()

    seen = [row["id"] for row in first["transactions"]] + [
        row["id"] for row in second["transactions"]
    ]
    assert len(seen) == len(set(seen)), "una riga è stata letta due volte"


def test_editing_moves_the_balance(setup):
    created = expense(setup).json()

    setup["client"].patch(
        f"/api/transactions/{created['id']}", json={"amount_cents": 10_000}
    )
    assert balance_of(setup, "corrente") == 100_000 - 10_000


def test_deleting_gives_the_money_back(setup):
    """⚠️ A real delete: a mistyped movement is not history, it is a typo."""
    created = expense(setup).json()
    assert balance_of(setup, "corrente") == 97_500

    assert setup["client"].delete(f"/api/transactions/{created['id']}").status_code == 204
    assert balance_of(setup, "corrente") == 100_000
    assert setup["client"].get("/api/transactions").json()["transactions"] == []


def test_turning_an_expense_into_a_transfer_revalidates_the_whole_row(setup):
    """Changing `kind` alone can make an otherwise fine row impossible: the
    category has to go at the same time."""
    created = expense(setup).json()

    broken = setup["client"].patch(
        f"/api/transactions/{created['id']}",
        json={"kind": "transfer", "counter_account_id": setup["deposito"]["id"]},
    )
    assert broken.status_code == 422

    fixed = setup["client"].patch(
        f"/api/transactions/{created['id']}",
        json={
            "kind": "transfer",
            "counter_account_id": setup["deposito"]["id"],
            "category_id": None,
        },
    )
    assert fixed.status_code == 200


def test_the_last_account_used_is_remembered(setup):
    """So the next quick entry starts where the previous one left off."""
    expense(setup, account_id=setup["deposito"]["id"], category_id=setup["spesa"]["id"])

    me = setup["client"].get("/api/auth/me").json()
    assert me["preferences"]["last_account_id"] == setup["deposito"]["id"]


# --------------------------------------------------------------------------
# Reconciliation
# --------------------------------------------------------------------------


def test_reconciling_writes_the_difference(setup):
    expense(setup)  # 100.000 - 2.500 = 97.500

    result = setup["client"].post(
        f"/api/accounts/{setup['corrente']['id']}/reconcile",
        json={"balance_cents": 95_000},
    ).json()

    assert result["difference_cents"] == -2_500
    assert result["transaction"]["kind"] == "expense"
    assert result["transaction"]["is_adjustment"] is True
    # ⚠️ No category: a rectification is not consumption.
    assert result["transaction"]["category_id"] is None
    assert result["new_balance_cents"] == 95_000
    assert balance_of(setup, "corrente") == 95_000


def test_reconciling_upwards_writes_income(setup):
    result = setup["client"].post(
        f"/api/accounts/{setup['corrente']['id']}/reconcile",
        json={"balance_cents": 120_000},
    ).json()

    assert result["difference_cents"] == 20_000
    assert result["transaction"]["kind"] == "income"


def test_reconciling_an_already_correct_balance_writes_nothing(setup):
    """A zero movement would clutter the list without meaning anything."""
    result = setup["client"].post(
        f"/api/accounts/{setup['corrente']['id']}/reconcile",
        json={"balance_cents": 100_000},
    ).json()

    assert result["difference_cents"] == 0
    assert result["transaction"] is None
    assert setup["client"].get("/api/transactions").json()["transactions"] == []


def test_reconciling_ignores_future_movements(setup):
    """⚠️ The safeguard behind the "future movements count" decision.

    Tomorrow's rent belongs in the balance on screen — that number answers "how
    much will be left". It does not belong in the comparison with a bank
    statement, because a statement cannot contain tomorrow. Without this, the
    difference would include the rent and the adjustment would invent a movement
    that never happened.
    """
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    expense(setup, date=tomorrow, amount_cents=80_000)

    # On screen the balance already reflects it.
    assert balance_of(setup, "corrente") == 100_000 - 80_000

    # The bank still says 100.000, and that is not a discrepancy.
    result = setup["client"].post(
        f"/api/accounts/{setup['corrente']['id']}/reconcile",
        json={"balance_cents": 100_000},
    ).json()

    assert result["difference_cents"] == 0
    assert result["transaction"] is None


def test_an_adjustment_stays_out_of_the_expense_totals_but_in_the_balance(setup):
    setup["client"].post(
        f"/api/accounts/{setup['corrente']['id']}/reconcile",
        json={"balance_cents": 90_000},
    )

    assert balance_of(setup, "corrente") == 90_000

    rows = setup["client"].get("/api/transactions").json()["transactions"]
    assert len(rows) == 1
    assert rows[0]["is_adjustment"] is True
    # It is visible in the list — hiding it would make the balance unexplainable
    # — but it carries no category, so no chart can count it as spending.
    assert rows[0]["category_id"] is None


# --------------------------------------------------------------------------
# Creating a category from inside the sheet
# --------------------------------------------------------------------------


def test_a_category_created_on_the_fly_gets_a_colour_and_an_icon(setup):
    created = setup["client"].post(
        "/api/categories", json={"name": "Parrucchiere", "kind": "expense"}
    )
    assert created.status_code == 201

    body = created.json()
    assert body["color"].startswith("chart-")
    assert body["icon"] == "Ellipsis"

    # And it can be used immediately, which is the whole point.
    assert expense(setup, category_id=body["id"]).status_code == 201


def test_two_categories_in_a_row_do_not_get_the_same_colour(setup):
    first = setup["client"].post(
        "/api/categories", json={"name": "Uno", "kind": "expense"}
    ).json()
    second = setup["client"].post(
        "/api/categories", json={"name": "Due", "kind": "expense"}
    ).json()

    assert first["color"] != second["color"]


def test_a_name_that_already_exists_is_still_refused(setup):
    """The duplicate check doubles as the alarm: if it says the category exists,
    you did not need to create it."""
    response = setup["client"].post(
        "/api/categories", json={"name": "spesa", "kind": "expense"}
    )
    assert response.status_code == 409
