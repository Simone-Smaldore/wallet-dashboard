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

⚠️ **The savings goal is judged on a calendar month whose salary arrived the
month before.** Pay lands on the 27th; September is lived on August's salary.
`savings_month` is the only place that says so.

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
from datetime import date as Date

from app.domain.balances import AccountRow, MovementRow, balances
from app.domain.period import Period, month_of, shift_month
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
class SavingsMonth:
    """A month, and whether it saved what it was supposed to save.

    ⚠️ **The salary that funds a month arrives in the month before it.** Pay
    lands on the 27th and is what September is lived on, so September's budget
    is August's salary plus whatever else came in during September — and
    September's own salary, arriving on the 27th, belongs to October.

    Without that shift the month you are living looks flush for twenty-six days
    and then rich on the twenty-seventh, and a verdict on it says nothing about
    how the month actually went.

    ⚠️ **Only the salary shifts.** A refund, a gift, a bit of interest are spent
    in the month they arrive, so they count where they land.
    """

    #: First day of the month this is about.
    month: Date
    #: The salary that arrived the month before, and funds this one.
    salary_cents: int
    #: Everything else that came in *during* this month.
    other_income_cents: int
    spent_cents: int
    #: ⚠️ Money moved into an investment account this month, net of anything
    #: taken back out. It is not spending — it is still yours — but it has left
    #: the current account and cannot be spent twice, so the month's budget has
    #: to lose it. See the note on `saved_cents`.
    set_aside_cents: int
    #: True for the month being lived: it gets an allowance, not a verdict.
    is_open: bool

    @property
    def budget_cents(self) -> int:
        """What there was to live on."""
        return self.salary_cents + self.other_income_cents

    @property
    def saved_cents(self) -> int:
        """What is left over. Negative means the month cost more than it had.

        ⚠️ **What you put away counts against the month like spending does.**
        Paying 400 € into an ETF is saving, not consumption — but the money has
        gone, and a goal that ignored it would tell you that you can still spend
        it. So the target measures what you keep **on top of** what you invest,
        which is the stricter reading and the one you asked for.

        The money itself is not lost: it moved to an investment account and the
        net worth does not budge. The two statements live together because they
        are about different things.
        """
        return self.budget_cents - self.spent_cents - self.set_aside_cents

    def allowance_cents(self, target_cents: int) -> int:
        """What can still be spent this month and still hit the target."""
        return self.saved_cents - target_cents


def savings_month(
    movements: Iterable[MovementRow],
    month: Date,
    *,
    salary_category_id: int | None,
    investment_account_ids: frozenset[int] = frozenset(),
    on: Date,
) -> SavingsMonth:
    """How one month is doing against the goal.

    `month` is any day inside the month being asked about; `on` is today, which
    only decides whether that month is still being lived.

    ⚠️ The whole month's spending counts, **including anything dated later in
    it**. A rent you have already recorded for the 28th is money that is going
    to go, and an allowance that ignored it would tell you that you can spend it
    twice. This is the same reading the balances take — the number answers "what
    will be left", not "what is in the account this second".

    ⚠️ Transfers and adjustments are in none of it, here as everywhere.
    """
    this = month_of(month)
    before = month_of(shift_month(this.start, -1))

    salary = 0
    other = 0
    spent = 0
    set_aside = 0

    for movement in movements:
        if this.contains(movement.date) and movement.kind is TransactionKind.TRANSFER:
            # ⚠️ Into an investment account is money put away; out of one is
            # money taken back. Between two of them, or between two ordinary
            # accounts, is nothing at all — which the two ifs say by cancelling.
            if movement.counter_account_id in investment_account_ids:
                set_aside += movement.amount_cents
            if movement.account_id in investment_account_ids:
                set_aside -= movement.amount_cents
            continue

        if is_spend(movement) and this.contains(movement.date):
            spent += movement.amount_cents
            continue
        if not is_income(movement):
            continue

        is_salary = (
            salary_category_id is not None
            and movement.category_id == salary_category_id
        )
        if is_salary:
            # The salary of the month before is what this month lives on.
            if before.contains(movement.date):
                salary += movement.amount_cents
        elif this.contains(movement.date):
            other += movement.amount_cents

    return SavingsMonth(
        month=this.start,
        salary_cents=salary,
        other_income_cents=other,
        spent_cents=spent,
        set_aside_cents=set_aside,
        is_open=this.contains(on),
    )


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
    *,
    valuations: dict[int, Sequence[tuple[Date, int]]] | None = None,
) -> list[NetWorthPoint]:
    """What the given accounts were worth at the end of each month.

    Pass every account for the net worth, one account for its own curve, or the
    non-investment ones for the liquid line: the filtering is the caller's, the
    arithmetic is here.

    ⚠️ **Each month uses the valuation that existed *then*, never the latest
    one.** Applying today's price backwards would redraw last March with August's
    market and the curve would be a retroactive lie — the exact reason valuations
    are dated snapshots instead of a field that gets overwritten.

    ⚠️ A month **before** the first price falls back to the capital paid in.
    That is honest but it is not the same quantity, so the first priced month
    steps up by however much the holding had gained in silence. The screen has
    to say where the prices begin, or that step reads as a very good month.
    """
    rows = list(accounts)
    history = list(movements)
    priced = valuations or {}

    points = []
    for month in months:
        end = month_of(month).end
        total = 0
        for account in rows:
            if not account.include_in_net_worth:
                continue
            balance = balances([account], history, as_of=end).get(
                account.id, account.opening_balance_cents
            )
            total += _valued_at(priced.get(account.id), end, balance)
        points.append(NetWorthPoint(month=month, value_cents=total))
    return points


def _valued_at(
    valuations: Sequence[tuple[Date, int]] | None, on: Date, fallback: int
) -> int:
    """The newest valuation not later than `on`, or the capital paid in."""
    if not valuations:
        return fallback

    best = None
    for when, value in valuations:
        if when <= on and (best is None or when > best[0]):
            best = (when, value)
    return best[1] if best else fallback


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
