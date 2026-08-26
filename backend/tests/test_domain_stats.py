"""The statistics.

The first test here is the other half of the untouchable promise: `balances`
proves a transfer cannot move a total, this proves it cannot appear in one. Both
have to hold, because they fail in different places — the first would break the
net worth, the second would break every chart.
"""

from datetime import date

from app.domain import stats
from app.domain.balances import AccountRow, MovementRow
from app.domain.period import Period, month_of
from app.domain.vocabulary import TransactionKind

MARCH = month_of(date(2026, 3, 1))
FEBRUARY = month_of(date(2026, 2, 1))

CORRENTE = AccountRow(id=1, opening_balance_cents=100_000)
DEPOSITO = AccountRow(id=2, opening_balance_cents=500_000)
ACCOUNTS = [CORRENTE, DEPOSITO]


def expense(amount, *, when=date(2026, 3, 12), category=10, account=1, row_id=None):
    return MovementRow(
        kind=TransactionKind.EXPENSE,
        amount_cents=amount,
        account_id=account,
        date=when,
        category_id=category,
        id=row_id,
    )


def income(amount, *, when=date(2026, 3, 12), category=90, account=1):
    return MovementRow(
        kind=TransactionKind.INCOME,
        amount_cents=amount,
        account_id=account,
        date=when,
        category_id=category,
    )


def transfer(amount, *, when=date(2026, 3, 12), source=1, target=2):
    return MovementRow(
        kind=TransactionKind.TRANSFER,
        amount_cents=amount,
        account_id=source,
        counter_account_id=target,
        date=when,
    )


def adjustment(amount, *, kind=TransactionKind.EXPENSE, when=date(2026, 3, 12)):
    """What reconciling a balance writes: no category, and not a spend."""
    return MovementRow(
        kind=kind,
        amount_cents=amount,
        account_id=1,
        date=when,
        category_id=None,
        is_adjustment=True,
    )


# --------------------------------------------------------------------------
# ⚠️ The one that does not get touched
# --------------------------------------------------------------------------


def test_a_transfer_never_appears_in_income_or_spending():
    """In no period, under no grouping, in neither direction.

    A salary moved onto the savings account is not an 1.800 € income, and the
    current account it left is not down 1.800 € of spending. If this breaks,
    every figure on the dashboard is inflated by an arbitrary amount and nothing
    on screen can be trusted.
    """
    movements = [
        transfer(180_000, source=1, target=2),
        transfer(20_000, source=2, target=1),  # and back the other way
    ]

    summed = stats.totals(movements, MARCH)
    assert summed.income_cents == 0
    assert summed.expense_cents == 0
    assert summed.savings_cents == 0
    assert summed.movement_count == 0

    assert stats.by_category(movements, MARCH) == []
    assert stats.by_category(movements, MARCH, kind=TransactionKind.INCOME) == []
    assert stats.top_expenses(movements, MARCH) == []

    for month in stats.monthly_series(movements, [date(2026, 2, 1), date(2026, 3, 1)]):
        assert (month.income_cents, month.expense_cents, month.savings_cents) == (0, 0, 0)

    # And the money is still all there, which is the point of the whole model.
    series = stats.net_worth_series(ACCOUNTS, movements, [date(2026, 3, 1)])
    assert series[0].value_cents == 600_000


# --------------------------------------------------------------------------
# Adjustments
# --------------------------------------------------------------------------


def test_an_adjustment_moves_the_balance_and_not_the_spending():
    """It is not consumption, it is the measure of what you forgot to record.

    Putting it in "spending by category" would invent a spend you cannot account
    for, and a skewed pie is worse than an admitted gap.
    """
    movements = [adjustment(3_000)]

    summed = stats.totals(movements, MARCH)
    assert summed.expense_cents == 0
    assert summed.movement_count == 0
    assert stats.by_category(movements, MARCH) == []
    assert stats.top_expenses(movements, MARCH) == []
    assert stats.pace(movements, MARCH, on=date(2026, 3, 31)).spent_cents == 0

    # But the money really is gone, so the net worth has to say so.
    series = stats.net_worth_series(ACCOUNTS, movements, [date(2026, 3, 1)])
    assert series[0].value_cents == 600_000 - 3_000


# --------------------------------------------------------------------------
# Totals and period edges
# --------------------------------------------------------------------------


def test_both_ends_of_the_period_belong_to_it():
    """A spend on the 1st and one on the 31st are both March."""
    movements = [
        expense(1_000, when=date(2026, 3, 1)),
        expense(2_000, when=date(2026, 3, 31)),
        expense(9_999, when=date(2026, 2, 28)),
        expense(8_888, when=date(2026, 4, 1)),
    ]

    assert stats.totals(movements, MARCH).expense_cents == 3_000


def test_savings_is_income_minus_spending_and_can_be_negative():
    movements = [income(150_000), expense(180_000)]

    summed = stats.totals(movements, MARCH)
    assert summed.savings_cents == -30_000
    assert summed.movement_count == 2


def test_an_empty_period_is_zeros_and_a_count_of_zero():
    """⚠️ The count is what lets the screen say "you recorded nothing" instead of
    drawing "you spent nothing". They are different statements."""
    summed = stats.totals([expense(5_000, when=date(2026, 1, 4))], MARCH)

    assert (summed.income_cents, summed.expense_cents) == (0, 0)
    assert summed.movement_count == 0


# --------------------------------------------------------------------------
# By category
# --------------------------------------------------------------------------


def test_categories_come_back_biggest_first_with_shares_that_add_up():
    """⚠️ Shares are integers and the remainder lands on the last slice.

    Three equal thirds rounded separately add up to 999, and next to a chart
    that is visible.
    """
    movements = [expense(1_000, category=1), expense(1_000, category=2), expense(1_000, category=3)]

    rows = stats.by_category(movements, MARCH)

    assert [row.total_cents for row in rows] == [1_000, 1_000, 1_000]
    assert sum(row.share_permille for row in rows) == stats.WHOLE
    # The leftover goes on the last, which is the smallest slice on screen.
    assert [row.share_permille for row in rows] == [333, 333, 334]


def test_a_category_that_stopped_costing_anything_is_kept_with_a_negative_delta():
    """"You stopped spending there" is information; dropping the row hides it."""
    movements = [
        expense(5_000, category=1, when=date(2026, 3, 3)),
        expense(9_000, category=2, when=date(2026, 2, 3)),
    ]

    rows = stats.by_category(movements, MARCH, previous=FEBRUARY)
    gone = next(row for row in rows if row.category_id == 2)

    assert gone.total_cents == 0
    assert gone.previous_cents == 9_000
    assert gone.delta_cents == -9_000
    # ⚠️ And it must not receive the remainder of the shares.
    assert gone.share_permille == 0
    assert sum(row.share_permille for row in rows) == stats.WHOLE


def test_uncategorised_spending_groups_under_none_instead_of_vanishing():
    """The category is optional at the till on purpose, so this bucket is real."""
    movements = [expense(4_000, category=None), expense(6_000, category=7)]

    rows = stats.by_category(movements, MARCH)

    assert {row.category_id: row.total_cents for row in rows} == {7: 6_000, None: 4_000}


def test_the_two_lists_never_mix():
    """Asking for spending must not return "Stipendio"."""
    movements = [expense(1_000, category=1), income(200_000, category=90)]

    assert [row.category_id for row in stats.by_category(movements, MARCH)] == [1]
    assert [
        row.category_id
        for row in stats.by_category(movements, MARCH, kind=TransactionKind.INCOME)
    ] == [90]


# --------------------------------------------------------------------------
# Series
# --------------------------------------------------------------------------


def test_a_month_with_nothing_in_it_is_a_zero_and_not_a_gap():
    """A line that skips it would draw straight across, claiming the money did
    something it did not."""
    movements = [expense(5_000, when=date(2026, 1, 10)), expense(7_000, when=date(2026, 3, 10))]

    series = stats.monthly_series(
        movements, [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]
    )

    assert [point.expense_cents for point in series] == [5_000, 0, 7_000]
    assert series[1].movement_count == 0


def test_the_net_worth_of_a_month_is_what_it_was_at_the_end_of_it():
    """⚠️ Not "the latest number, repeated". Each point is the net worth as of
    the last day of its month, so the curve is a history and not a smear."""
    movements = [expense(10_000, when=date(2026, 2, 15)), expense(25_000, when=date(2026, 3, 20))]

    series = stats.net_worth_series(
        ACCOUNTS, movements, [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]
    )

    assert [point.value_cents for point in series] == [600_000, 590_000, 565_000]


def test_an_account_left_out_of_the_net_worth_stays_out_of_the_series():
    shared = AccountRow(id=3, opening_balance_cents=80_000, include_in_net_worth=False)

    series = stats.net_worth_series([*ACCOUNTS, shared], [], [date(2026, 3, 1)])

    assert series[0].value_cents == 600_000


# --------------------------------------------------------------------------
# Top spends and pace
# --------------------------------------------------------------------------


def test_the_biggest_spends_come_back_in_order_with_their_identity():
    movements = [
        expense(1_000, row_id=1),
        expense(90_000, row_id=2),
        expense(30_000, row_id=3),
        income(500_000),
        transfer(400_000),
    ]

    top = stats.top_expenses(movements, MARCH, limit=2)

    assert [row.id for row in top] == [2, 3]


def test_the_projection_of_a_finished_month_is_simply_the_total():
    """There is nothing left to project once the month is over."""
    movements = [expense(31_000, when=date(2026, 3, 5))]

    pace = stats.pace(movements, MARCH, on=date(2026, 4, 2))

    assert pace.elapsed_days == 31
    assert pace.total_days == 31
    assert pace.projection_cents == 31_000
    assert pace.daily_average_cents == 1_000


def test_halfway_through_the_month_the_projection_is_the_rate_carried_forward():
    """⚠️ A linear projection and nothing else — it knows nothing about the rent
    due on the 28th, and the label on screen has to say so."""
    movements = [expense(10_000, when=date(2026, 3, 2)), expense(20_000, when=date(2026, 3, 9))]

    pace = stats.pace(movements, MARCH, on=date(2026, 3, 10))

    assert pace.elapsed_days == 10  # today counts: part of it is already spent
    assert pace.spent_cents == 30_000
    assert pace.daily_average_cents == 3_000
    assert pace.projection_cents == 3_000 * 31


def test_the_projection_is_computed_from_the_total_not_from_the_rounded_average():
    """Multiplying a rounded number by thirty multiplies its error by thirty."""
    movements = [expense(1_001, when=date(2026, 3, 1))]

    pace = stats.pace(movements, MARCH, on=date(2026, 3, 3))

    assert pace.daily_average_cents == 334  # 1001 / 3, half up
    assert pace.projection_cents == 10_344  # 1001 * 31 / 3, not 334 * 31 = 10_354


def test_a_month_that_has_not_started_projects_nothing():
    """Dividing by zero elapsed days would be a crash; guessing would be worse."""
    pace = stats.pace([], MARCH, on=date(2026, 2, 20))

    assert pace.elapsed_days == 0
    assert pace.daily_average_cents == 0
    assert pace.projection_cents == 0


def test_a_free_range_is_a_period_like_any_other():
    """The charts accept any interval, not only calendar months."""
    week = Period(start=date(2026, 3, 9), end=date(2026, 3, 15))
    movements = [expense(2_000, when=date(2026, 3, 9)), expense(3_000, when=date(2026, 3, 16))]

    assert stats.totals(movements, week).expense_cents == 2_000
    assert stats.pace(movements, week, on=date(2026, 3, 15)).total_days == 7


# --------------------------------------------------------------------------
# The savings goal: a calendar month funded by the month before
# --------------------------------------------------------------------------

SALARY = 42


def salary(amount, *, when):
    return income(amount, when=when, category=SALARY)


def september(movements, on=date(2026, 9, 30)):
    return stats.savings_month(
        movements, date(2026, 9, 15), salary_category_id=SALARY, on=on
    )


def test_the_salary_of_the_month_before_is_what_this_month_lives_on():
    """⚠️ The shift is the whole rule.

    Pay lands on the 27th. September is lived on August's salary, and the one
    arriving on 27 September belongs to October — otherwise the month looks
    broke for twenty-six days and rich on the twenty-seventh, and a verdict on
    it says nothing about how the month went.
    """
    movements = [
        salary(200_000, when=date(2026, 8, 27)),
        salary(210_000, when=date(2026, 9, 27)),
    ]

    month = september(movements)

    assert month.salary_cents == 200_000
    assert month.budget_cents == 200_000


def test_everything_that_is_not_a_salary_counts_where_it_lands():
    """A refund or a gift is spent in the month it arrives, so it stays there."""
    movements = [
        salary(200_000, when=date(2026, 8, 27)),
        income(15_000, when=date(2026, 9, 4), category=7),   # a refund, in September
        income(90_000, when=date(2026, 8, 4), category=7),   # one in August: not ours
    ]

    month = september(movements)

    assert month.other_income_cents == 15_000
    assert month.budget_cents == 215_000


def test_the_spending_is_the_month_s_own():
    movements = [
        salary(200_000, when=date(2026, 8, 27)),
        expense(30_000, when=date(2026, 9, 3)),
        expense(50_000, when=date(2026, 8, 31)),   # August's problem
        expense(70_000, when=date(2026, 10, 1)),   # October's
    ]

    month = september(movements)

    assert month.spent_cents == 30_000
    assert month.saved_cents == 170_000


def test_spending_dated_later_in_the_month_counts_now():
    """⚠️ A rent already recorded for the 28th is money that is going to go. An
    allowance that ignored it would say you can spend it twice."""
    movements = [
        salary(200_000, when=date(2026, 8, 27)),
        expense(80_000, when=date(2026, 9, 28)),
    ]

    month = september(movements, on=date(2026, 9, 10))

    assert month.spent_cents == 80_000
    assert month.is_open is True


def test_transfers_and_rectifications_are_in_none_of_it():
    """The untouchable rule, inside the goal too."""
    movements = [
        salary(200_000, when=date(2026, 8, 27)),
        transfer(150_000, when=date(2026, 9, 2)),
        adjustment(5_000, when=date(2026, 9, 3)),
        expense(20_000, when=date(2026, 9, 4)),
    ]

    month = september(movements)

    assert month.budget_cents == 200_000
    assert month.spent_cents == 20_000


def test_the_allowance_is_what_is_left_after_the_target():
    """"Quanto posso ancora spendere": budget, minus what has gone, minus what
    has to survive the month."""
    movements = [
        salary(200_000, when=date(2026, 8, 27)),
        expense(60_000, when=date(2026, 9, 2)),
    ]

    month = september(movements, on=date(2026, 9, 10))

    assert month.allowance_cents(30_000) == 110_000
    # Past it the number goes negative rather than stopping at zero: how far
    # past is the part you can act on.
    assert month.allowance_cents(200_000) == -60_000


def test_two_salaries_in_one_month_both_fund_the_next():
    """⚠️ The thirteenth month arrives in December and is what January lives on,
    together with December's pay. Summing them is what stops a windfall from
    inventing a second, five-day month."""
    movements = [
        salary(200_000, when=date(2026, 8, 27)),
        salary(180_000, when=date(2026, 8, 15)),
    ]

    assert september(movements).salary_cents == 380_000


def test_without_a_salary_category_there_is_no_shift():
    """Nothing is a salary, so nothing moves forward: the month is just what
    came in and what went out. Honest, and the screen asks for the category
    rather than pretending this is the answer."""
    movements = [income(200_000, when=date(2026, 9, 5), category=7)]

    month = stats.savings_month(
        movements, date(2026, 9, 15), salary_category_id=None, on=date(2026, 9, 30)
    )

    assert month.salary_cents == 0
    assert month.other_income_cents == 200_000


def test_a_month_being_lived_is_marked_open():
    movements = [salary(200_000, when=date(2026, 8, 27))]

    assert september(movements, on=date(2026, 9, 10)).is_open is True
    assert september(movements, on=date(2026, 10, 3)).is_open is False
