"""The two dashboard screens over HTTP.

The arithmetic is tested in test_domain_stats.py, where it is pure. What is
tested here is the wiring: that the router asks the domain rather than inventing
its own rules, and that the shapes on the wire are the ones the screens read.
"""

from datetime import date, timedelta

import pytest

TODAY = date.today()
FIRST = TODAY.replace(day=1)


@pytest.fixture
def setup(signed_in):
    """Two accounts and two categories, and nothing else."""
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


def record(setup, **overrides):
    body = {
        "kind": "expense",
        "date": TODAY.isoformat(),
        "amount_cents": 1_000,
        "account_id": setup["corrente"]["id"],
        "category_id": setup["spesa"]["id"],
    }
    body.update(overrides)
    response = setup["client"].post("/api/transactions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_the_dashboard_needs_a_session(client):
    assert client.get("/api/stats/summary").status_code == 401
    assert client.get("/api/stats/analysis").status_code == 401


# --------------------------------------------------------------------------
# Riepilogo
# --------------------------------------------------------------------------


def test_the_summary_answers_the_daily_question_in_one_request(setup):
    record(setup, amount_cents=30_000)
    record(setup, kind="income", amount_cents=200_000, category_id=setup["stipendio"]["id"])

    body = setup["client"].get("/api/stats/summary").json()

    assert body["net_worth_cents"] == 600_000 - 30_000 + 200_000
    assert body["totals"]["expense_cents"] == 30_000
    assert body["totals"]["income_cents"] == 200_000
    assert body["totals"]["savings_cents"] == 170_000
    assert {account["name"] for account in body["accounts"]} == {"Corrente", "Deposito"}
    assert len(body["recent"]) == 2


def test_the_summary_agrees_with_the_accounts_screen(setup):
    """Two screens, one formula. If these ever disagree, one of them is lying
    and there is no way to tell which."""
    record(setup, amount_cents=12_345)

    summary = setup["client"].get("/api/stats/summary").json()
    accounts = setup["client"].get("/api/accounts").json()

    assert summary["net_worth_cents"] == accounts["net_worth_cents"]
    assert [account["balance_cents"] for account in summary["accounts"]] == [
        account["balance_cents"] for account in accounts["accounts"]
    ]


def test_a_transfer_moves_no_number_on_the_dashboard(setup):
    """⚠️ The untouchable rule, seen from the outside.

    Money moved between two of your own accounts is not income, not a spend,
    and not a change in what you own.
    """
    before = setup["client"].get("/api/stats/summary").json()

    record(
        setup,
        kind="transfer",
        amount_cents=180_000,
        category_id=None,
        counter_account_id=setup["deposito"]["id"],
    )

    after = setup["client"].get("/api/stats/summary").json()

    assert after["net_worth_cents"] == before["net_worth_cents"]
    assert after["totals"] == before["totals"]

    analysis = setup["client"].get("/api/stats/analysis").json()
    assert analysis["by_category"] == []
    assert analysis["top_expenses"] == []


def test_a_rectification_moves_the_balance_and_not_the_spending(setup):
    """It is the measure of what you forgot, not a spend you can categorise."""
    setup["client"].post(
        f"/api/accounts/{setup['corrente']['id']}/reconcile", json={"balance_cents": 95_000}
    )

    body = setup["client"].get("/api/stats/summary").json()

    assert body["net_worth_cents"] == 595_000
    assert body["totals"]["expense_cents"] == 0
    assert body["totals"]["movement_count"] == 0
    # It is still a row you can see in the list — hidden from the charts, not
    # hidden from you.
    assert body["recent"][0]["is_adjustment"] is True


def test_an_empty_month_says_so_with_a_count_and_not_only_with_zeros(setup):
    body = setup["client"].get("/api/stats/summary").json()

    assert body["totals"]["movement_count"] == 0
    assert body["recent"] == []


# --------------------------------------------------------------------------
# The savings target
# --------------------------------------------------------------------------


def test_the_target_starts_unset_rather_than_at_zero(setup):
    """⚠️ Null and zero are different statements: one is "I have not decided",
    the other is "I mean to save nothing"."""
    savings = setup["client"].get("/api/stats/summary").json()["savings"]

    assert savings["target_cents"] is None
    assert savings["salary_category_id"] is None
    # ⚠️ And no verdict at all rather than a failed one: with nothing to judge,
    # "you missed it" would be a made-up answer.
    assert savings["met"] is None


def test_the_target_is_set_and_cleared_from_the_household(setup):
    client = setup["client"]

    saved = client.patch("/api/household", json={"monthly_savings_target_cents": 40_000})
    assert saved.status_code == 200
    assert saved.json()["monthly_savings_target_cents"] == 40_000
    assert client.get("/api/stats/summary").json()["savings"]["target_cents"] == 40_000

    # An explicit null means "forget it", which is not the same as omitting it.
    cleared = client.patch("/api/household", json={"monthly_savings_target_cents": None})
    assert cleared.json()["monthly_savings_target_cents"] is None


def test_a_negative_target_is_refused(setup):
    """Saving a negative amount is not a goal, it is a typo."""
    response = setup["client"].patch(
        "/api/household", json={"monthly_savings_target_cents": -1}
    )
    assert response.status_code == 422


def test_the_household_is_not_a_place_to_rename_things(setup):
    """extra="forbid": a field written wrong fails loudly instead of vanishing."""
    assert setup["client"].patch("/api/household", json={"name": "Altro"}).status_code == 422


# --------------------------------------------------------------------------
# Analisi
# --------------------------------------------------------------------------


def test_the_analysis_compares_with_the_month_before(setup):
    """For a whole month the comparison is the month before, not thirty days."""
    last_month = (FIRST - timedelta(days=1)).replace(day=1)

    record(setup, amount_cents=50_000)
    record(setup, amount_cents=30_000, date=last_month.isoformat())

    body = setup["client"].get("/api/stats/analysis").json()

    assert body["period"]["start"] == FIRST.isoformat()
    assert body["previous"]["start"] == last_month.isoformat()
    assert body["totals"]["expense_cents"] == 50_000
    assert body["previous_totals"]["expense_cents"] == 30_000

    slice_ = body["by_category"][0]
    assert slice_["name"] == "Spesa"
    assert slice_["color"] == "chart-1"
    assert slice_["total_cents"] == 50_000
    assert slice_["previous_cents"] == 30_000
    assert slice_["delta_cents"] == 20_000
    assert slice_["share_permille"] == 1000


def test_the_slices_carry_the_name_and_colour_the_chart_draws_with(setup):
    """Denormalised into the response: the chart must not have to wait for the
    category list to have loaded before it can draw itself."""
    altro = setup["client"].post(
        "/api/categories",
        json={"name": "Trasporti", "kind": "expense", "color": "chart-3", "icon": "Car"},
    ).json()
    record(setup, amount_cents=60_000)
    record(setup, amount_cents=40_000, category_id=altro["id"])

    slices = setup["client"].get("/api/stats/analysis").json()["by_category"]

    assert [(s["name"], s["share_permille"]) for s in slices] == [
        ("Spesa", 600),
        ("Trasporti", 400),
    ]


def test_a_spend_with_no_category_is_named_rather_than_dropped(setup):
    """The category is optional at the till on purpose, so this bucket is real
    and the total has to keep adding up."""
    record(setup, amount_cents=7_000, category_id=None)

    slices = setup["client"].get("/api/stats/analysis").json()["by_category"]

    assert [s["name"] for s in slices] == ["Senza categoria"]
    assert slices[0]["color"] is None


def test_the_analysis_is_about_the_period_and_nothing_else(setup):
    """⚠️ The long series lives on /series, not here.

    They answer different questions over different windows — this one breaks
    down a month, that one draws five years — so widening a line must not
    re-fetch a pie, and changing the month must not re-fetch five years of
    history.
    """
    body = setup["client"].get("/api/stats/analysis").json()

    assert "months" not in body
    assert set(body) == {
        "period",
        "previous",
        "totals",
        "previous_totals",
        "by_category",
        "top_expenses",
        "pace",
    }


def test_the_biggest_spends_come_back_whole(setup):
    """An amount with no name attached explains nothing."""
    record(setup, amount_cents=5_000, description="Caffè")
    record(setup, amount_cents=90_000, description="Volo")
    record(setup, amount_cents=20_000, description="Scarpe")

    top = setup["client"].get("/api/stats/analysis").json()["top_expenses"]

    assert [row["description"] for row in top] == ["Volo", "Scarpe", "Caffè"]
    assert top[0]["account_name"] == "Corrente"


def test_a_free_range_is_accepted_and_kept(setup):
    body = setup["client"].get("/api/stats/analysis?from=2026-03-09&to=2026-03-15").json()

    assert body["period"] == {"start": "2026-03-09", "end": "2026-03-15"}
    assert body["pace"]["total_days"] == 7
    # Same length, ending the day before this one starts.
    assert body["previous"] == {"start": "2026-03-02", "end": "2026-03-08"}


def test_the_ends_of_a_range_can_arrive_the_wrong_way_round(setup):
    body = setup["client"].get("/api/stats/analysis?from=2026-03-15&to=2026-03-09").json()

    assert body["period"] == {"start": "2026-03-09", "end": "2026-03-15"}


# --------------------------------------------------------------------------
# The long charts, over a window you pick
# --------------------------------------------------------------------------


def test_the_series_defaults_to_twelve_months_ending_now(setup):
    body = setup["client"].get("/api/stats/series").json()

    assert len(body["months"]) == 12
    assert body["months"][-1]["month"] == FIRST.isoformat()


def test_the_series_window_is_chosen_by_the_caller(setup):
    """Widening a line must not mean re-fetching a pie: that is why this is its
    own endpoint."""
    for months in (6, 36, 60):
        body = setup["client"].get(f"/api/stats/series?months={months}").json()
        assert len(body["months"]) == months


def test_zero_months_means_everything_there_is(setup):
    """⚠️ "Max" is not an arbitrarily large number: it is where the data starts.
    Asking for 600 months would draw fifty years of zeros in front of a life
    that began four months ago."""
    old = (FIRST - timedelta(days=70)).replace(day=1)
    record(setup, amount_cents=5_000, date=old.isoformat())

    body = setup["client"].get("/api/stats/series?months=0").json()

    assert body["months"][0]["month"] == old.isoformat()
    assert body["months"][-1]["month"] == FIRST.isoformat()


def test_with_no_movements_at_all_max_is_this_month_alone(setup):
    """No data means no history to draw, not a crash and not an empty array the
    chart would have to special-case."""
    body = setup["client"].get("/api/stats/series?months=0").json()

    assert [point["month"] for point in body["months"]] == [FIRST.isoformat()]


def test_a_transfer_is_absent_from_the_series_too(setup):
    """⚠️ The untouchable rule, on this endpoint as well."""
    record(
        setup,
        kind="transfer",
        amount_cents=180_000,
        category_id=None,
        counter_account_id=setup["deposito"]["id"],
    )

    body = setup["client"].get("/api/stats/series?months=1").json()
    point = body["months"][-1]

    assert (point["income_cents"], point["expense_cents"]) == (0, 0)
    assert point["net_worth_cents"] == 600_000


def test_the_series_needs_a_session(client):
    assert client.get("/api/stats/series").status_code == 401
