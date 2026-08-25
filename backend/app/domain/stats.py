"""The statistics.

⚠️ **This module is the single definition of what counts as what.** Every number
the dashboard shows comes out of here, and the two predicates at the top are the
whole rule:

| Number            | Includes                     | Excludes                  |
|-------------------|------------------------------|---------------------------|
| Spending          | `expense`                    | transfers, adjustments    |
| Income            | `income`                     | transfers, adjustments    |
| Savings           | income − spending            | transfers, adjustments    |
| Balance/net worth | everything, adjustments too  | nothing                   |

The last row lives in `balances.py`, which is why net-worth points here are
computed by *calling* it rather than by summing again: one formula, one place.

⚠️ **A transfer is never income and never a spend.** Moving money between two of
your accounts does not change how much you have; the two sides cancel. Getting
this wrong is what makes a personal-finance dashboard useless — a salary split
across three accounts would read as three incomes and three expenses, and every
figure on the screen would be inflated by an arbitrary amount. The test that
proves it is the one test in this project that does not get touched.

⚠️ **An adjustment is not consumption.** It is the measure of what you forgot to
record. It moves the balance and it stays out of every spending figure: filing it
under a category would invent a spend you cannot account for, and a skewed pie is
worse than an admitted gap.

Pure, like the rest of `domain/`: plain values in, plain values out, no SQLAlchemy
and no FastAPI. The aggregation happens in Python rather than in SQL because a
year of real use is around 1.500 rows and five years 7.500 — summing those in
memory costs milliseconds, and in exchange every rule above is a function that
can be tested without starting a database. `CLAUDE.md` records where that stops
being true.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date as Date, timedelta

from app.domain.balances import AccountRow, MovementRow, net_worth
from app.domain.period import Period, month_of
from app.domain.vocabulary import TransactionKind

#: How many shares add up to a whole. Per mille rather than per cent: one
#: decimal place of precision, still an integer, so no float ever crosses the
#: wire. The formatter turns 342 into "34,2 %".
WHOLE = 1000


def is_spend(movement: MovementRow) -> bool:
    """Money that actually left, for something."""
    return movement.kind is TransactionKind.EXPENSE and not movement.is_adjustment


def is_income(movement: MovementRow) -> bool:
    """Money that actually arrived, from somewhere."""
    return movement.kind is TransactionKind.INCOME and not movement.is_adjustment


@dataclass(frozen=True)
class Totals:
    """What a period did to your money."""

    income_cents: int
    expense_cents: int
    #: ⚠️ How many rows *counted*, so the screen can tell "you spent nothing"
    #: from "you recorded nothing". They are different statements, and drawing a
    #: chart with its axes at zero makes the second one look like the first.
    movement_count: int

    @property
    def savings_cents(self) -> int:
        """What is left. Negative when you spent more than you earned."""
        return self.income_cents - self.expense_cents


@dataclass(frozen=True)
class CategoryTotal:
    """One slice: what a category took, and what it took last time."""

    category_id: int | None
    total_cents: int
    #: Out of `WHOLE`, and only over this period's spending.
    share_permille: int
    previous_cents: int

    @property
    def delta_cents(self) -> int:
        """The number that says something you can act on.

        Not "340 € on transport" but "+120 € against last month": the first is a
        fact about the past, the second is a fact about a change.
        """
        return self.total_cents - self.previous_cents


@dataclass(frozen=True)
class MonthTotals:
    """A point on the month-by-month chart. `month` is the first day of it."""

    month: Date
    income_cents: int
    expense_cents: int
    movement_count: int

    @property
    def savings_cents(self) -> int:
        return self.income_cents - self.expense_cents


@dataclass(frozen=True)
class NetWorthPoint:
    """What everything was worth at the end of a month."""

    month: Date
    value_cents: int


@dataclass(frozen=True)
class Pace:
    """How fast the money is going out, and where that lands.

    ⚠️ `projection_cents` is a **linear projection and nothing else**: today's
    average carried to the end of the period. It is not a forecast, it knows
    nothing about the rent due on the 28th, and the label on screen has to say
    so. The honest wording starts here, in the name of the field.
    """

    elapsed_days: int
    total_days: int
    spent_cents: int
    daily_average_cents: int
    projection_cents: int


@dataclass(frozen=True)
class SalaryCycle:
    """The stretch of time one salary has to last.

    ⚠️ **This, and not the calendar month, is the period a savings goal is
    judged on.** Money arrives on a day of the month that is not the first, and
    what matters is whether the salary that arrived in November was still
    partly there when December's arrived. A calendar month cuts that stretch in
    the middle and answers a question nobody asked.

    `is_open` marks the cycle being lived right now: its end is *unknown* —
    nobody knows when the next salary lands — so it is cut at the day being
    asked about. That is the only honest boundary available for it, and it is
    why an open cycle gets an allowance rather than a verdict.
    """

    start: Date
    end: Date
    salary_cents: int
    spent_cents: int
    is_open: bool

    @property
    def saved_cents(self) -> int:
        """What the salary had left over. Negative means it did not last."""
        return self.salary_cents - self.spent_cents

    def allowance_cents(self, target_cents: int) -> int:
        """What can still be spent and still hit the target."""
        return self.salary_cents - self.spent_cents - target_cents


def salary_cycles(
    movements: Iterable[MovementRow],
    *,
    salary_category_id: int | None,
    on: Date,
) -> list[SalaryCycle]:
    """The salary-to-salary cycles, oldest first.

    A salary is an income movement in the one category you have named as such.
    ⚠️ Not "any income": a 10 € refund would open a cycle and every number after
    it would be measured over five days. And not "the biggest income of the
    month" either — that is a rule that guesses, and the month you sell
    something expensive it would move the boundaries without telling you.

    ⚠️ **A cycle starts at the first salary payment of a calendar month**, and
    any further payment in that same month is added to it. That is what keeps a
    thirteenth month in December from splitting the month into two cycles, one
    of them five days long with a savings verdict attached. It costs an edge:
    a salary paid on the 31st and the next on the 1st are two cycles, one a day
    long — real, rare, and visible rather than silently smoothed away.

    Anything before the first salary is not in any cycle. There is no salary it
    was being spent out of, so there is nothing to judge it against.
    """
    if salary_category_id is None:
        return []

    payments = [
        movement
        for movement in movements
        if is_income(movement)
        and movement.category_id == salary_category_id
        and movement.date <= on
    ]
    if not payments:
        return []

    # First payment of each month opens the cycle; the rest of that month adds
    # to it.
    by_month: dict[tuple[int, int], tuple[Date, int]] = {}
    for payment in payments:
        key = (payment.date.year, payment.date.month)
        start, total = by_month.get(key, (payment.date, 0))
        by_month[key] = (min(start, payment.date), total + payment.amount_cents)

    opened = sorted(by_month.values())
    spends = [movement for movement in movements if is_spend(movement)]

    cycles = []
    for index, (start, salary) in enumerate(opened):
        is_open = index == len(opened) - 1
        end = on if is_open else opened[index + 1][0] - timedelta(days=1)
        if end < start:
            # Two salaries on consecutive days: the earlier cycle has no days in
            # it at all. Dropping it is better than a zero-length verdict.
            continue

        cycles.append(
            SalaryCycle(
                start=start,
                end=end,
                salary_cents=salary,
                spent_cents=sum(
                    movement.amount_cents
                    for movement in spends
                    if start <= movement.date <= end
                ),
                is_open=is_open,
            )
        )
    return cycles


def totals(movements: Iterable[MovementRow], period: Period) -> Totals:
    """Income, spending and savings over a period."""
    income = expense = counted = 0

    for movement in movements:
        if not period.contains(movement.date):
            continue
        if is_income(movement):
            income += movement.amount_cents
            counted += 1
        elif is_spend(movement):
            expense += movement.amount_cents
            counted += 1

    return Totals(income_cents=income, expense_cents=expense, movement_count=counted)


def by_category(
    movements: Iterable[MovementRow],
    period: Period,
    *,
    kind: TransactionKind = TransactionKind.EXPENSE,
    previous: Period | None = None,
) -> list[CategoryTotal]:
    """What each category took, biggest first, with its share and its change.

    `previous` is the period to compare against — the month before, for a month.
    A category that took nothing this time but something last time is kept, with
    a negative delta: "you stopped spending there" is information, and dropping
    the row would hide it.

    ⚠️ `category_id` can legitimately be `None`. The description is optional and
    so is the category — an app that demands one at the till is an app you stop
    using in March. Those rows group together, and the screen calls them what
    they are instead of pretending they do not exist.
    """
    counts = is_income if kind is TransactionKind.INCOME else is_spend

    current: dict[int | None, int] = {}
    before: dict[int | None, int] = {}

    for movement in movements:
        if not counts(movement):
            continue
        if period.contains(movement.date):
            current[movement.category_id] = (
                current.get(movement.category_id, 0) + movement.amount_cents
            )
        elif previous is not None and previous.contains(movement.date):
            before[movement.category_id] = (
                before.get(movement.category_id, 0) + movement.amount_cents
            )

    rows = [
        CategoryTotal(
            category_id=category_id,
            total_cents=current.get(category_id, 0),
            share_permille=0,
            previous_cents=before.get(category_id, 0),
        )
        for category_id in {**before, **current}
    ]

    # Biggest first; ties broken by id so the order does not wobble between two
    # requests that returned the same numbers.
    rows.sort(key=lambda row: (-row.total_cents, -row.previous_cents, row.category_id or 0))
    return _with_shares(rows)


def monthly_series(
    movements: Iterable[MovementRow], months: Sequence[Date]
) -> list[MonthTotals]:
    """One point per month, in the order given, including the empty ones.

    A month where nothing happened has to be a zero on the chart and not a gap:
    a line that skips it would draw a straight segment across it, quietly
    claiming the money did something it did not.
    """
    history = list(movements)
    points = []
    for month in months:
        summed = totals(history, month_of(month))
        points.append(
            MonthTotals(
                month=month,
                income_cents=summed.income_cents,
                expense_cents=summed.expense_cents,
                movement_count=summed.movement_count,
            )
        )
    return points


def net_worth_series(
    accounts: Iterable[AccountRow],
    movements: Iterable[MovementRow],
    months: Sequence[Date],
) -> list[NetWorthPoint]:
    """What everything was worth at the end of each month.

    ⚠️ Computed by calling `balances.net_worth` with `as_of` set to the last day
    of the month, not by accumulating the series as it goes. Accumulating would
    be a second definition of net worth, and the first time the two disagree —
    an account opened mid-history, a movement dated before its own account —
    there would be no way to tell which one is lying.

    The cost is one pass over the movements per month. Twelve passes over a few
    thousand rows is nothing, and it buys a number that is right by construction.
    """
    rows = list(accounts)
    history = list(movements)

    return [
        NetWorthPoint(
            month=month,
            value_cents=net_worth(rows, history, as_of=month_of(month).end),
        )
        for month in months
    ]


def top_expenses(
    movements: Iterable[MovementRow], period: Period, *, limit: int = 5
) -> list[MovementRow]:
    """The biggest spends of the period, biggest first.

    Nearly always the explanation of a bad month is in this list, and finding it
    by scrolling is work. Returns the rows themselves so the caller can show what
    they were — an amount with no name attached explains nothing.
    """
    spends = [
        movement
        for movement in movements
        if is_spend(movement) and period.contains(movement.date)
    ]
    spends.sort(key=lambda movement: (-movement.amount_cents, movement.date))
    return spends[:limit]


def pace(movements: Iterable[MovementRow], period: Period, *, on: Date) -> Pace:
    """Spending so far, per day, and where that lands at this rate.

    `on` is the day being asked about — today, normally. Once the period is over
    the projection is simply the total: there is nothing left to project.
    """
    spent = sum(
        movement.amount_cents
        for movement in movements
        if is_spend(movement) and period.contains(movement.date)
    )

    if on < period.start:
        elapsed = 0
    elif on >= period.end:
        elapsed = period.days
    else:
        # Today counts: you have already spent part of it.
        elapsed = (on - period.start).days + 1

    if elapsed == 0:
        return Pace(
            elapsed_days=0,
            total_days=period.days,
            spent_cents=spent,
            daily_average_cents=0,
            projection_cents=0,
        )

    # ⚠️ Integer arithmetic all the way, half rounded up. And the projection is
    # computed from the total rather than from the rounded average: multiplying
    # a rounded number by thirty multiplies the rounding error by thirty too.
    average = (spent + elapsed // 2) // elapsed
    projection = (spent * period.days + elapsed // 2) // elapsed

    return Pace(
        elapsed_days=elapsed,
        total_days=period.days,
        spent_cents=spent,
        daily_average_cents=average,
        projection_cents=projection,
    )


def _with_shares(rows: list[CategoryTotal]) -> list[CategoryTotal]:
    """Give each row its share of the total, in per mille.

    ⚠️ **The remainder goes on the last slice.** Rounding each share on its own
    leaves the slices adding up to 99,7 % or 100,2 %, and next to a chart that
    is visible. The list is already sorted biggest first, so the leftover lands
    on the smallest slice that has anything in it — where a tenth of a percent
    is least visible.

    Rows with nothing in this period get a share of zero: they are here for
    their delta, and they must not receive the remainder.
    """
    positive = [row for row in rows if row.total_cents > 0]
    total = sum(row.total_cents for row in positive)
    if total == 0:
        return rows

    # `rows` is sorted biggest first, so the ones with something in them are a
    # prefix: the index into `positive` is the index into `rows`.
    shared = []
    running = 0
    for index, row in enumerate(rows):
        if index >= len(positive):
            share = 0
        elif index == len(positive) - 1:
            share = WHOLE - running
        else:
            share = row.total_cents * WHOLE // total
            running += share

        shared.append(
            CategoryTotal(
                category_id=row.category_id,
                total_cents=row.total_cents,
                share_permille=share,
                previous_cents=row.previous_cents,
            )
        )
    return shared
