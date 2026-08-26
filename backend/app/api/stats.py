"""The two dashboard screens.

The router does what routers do here: it loads the movements once, hands them to
`domain/stats.py`, and turns what comes back into JSON. **No rule about what
counts as a spend lives in this file** — that is the whole point of the split,
and the reason those rules can be tested without a database.

One endpoint per screen, not one per chart: see schemas/stats.py.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.accounts import balance_rows, movement_rows
from app.api.deps import CurrentUserDep, DbDep
from app.api.transactions import load_by_ids, load_recent
from app.domain import balances as balances_domain
from app.domain import stats as domain
from app.domain.period import (
    Period,
    month_of,
    months_between,
    previous_period,
    shift_month,
)
from app.models import Account, Category, Household, Transaction
from app.schemas.account import AccountOut
from app.schemas.stats import (
    AnalysisOut,
    CategorySliceOut,
    CycleOut,
    MonthPointOut,
    PaceOut,
    CalendarOut,
    PeriodOut,
    SeriesOut,
    SavingsOut,
    SummaryOut,
    TotalsOut,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])

#: What `/series` looks back by default. A year is the span that makes
#: seasonality visible — the holidays, the insurance premium — and it is only a
#: default: the screen offers 6 months to Max.
DEFAULT_MONTHS = 12

#: What an uncategorised spend is called on screen. Computed here rather than in
#: a component so the two charts that can show it cannot disagree.
UNCATEGORISED = "Senza categoria"


@router.get("/summary", response_model=SummaryOut)
def summary(
    user: CurrentUserDep,
    db: DbDep,
    on: date | None = Query(default=None),
) -> SummaryOut:
    """The opening screen: how much there is, and what happened this month."""
    day = on or date.today()
    period = month_of(day)

    accounts = _accounts(db, user.household_id)
    rows = balance_rows(accounts)
    movements = movement_rows(db, user.household_id)

    totals = balances_domain.balances(rows, movements)
    summed = domain.totals(movements, period)

    household = db.get(Household, user.household_id)

    return SummaryOut(
        on=day,
        period=PeriodOut(start=period.start, end=period.end),
        net_worth_cents=balances_domain.net_worth(rows, movements),
        accounts=[_account_out(account, totals) for account in accounts],
        totals=_totals_out(summed),
        savings=_savings_out(db, household, movements, on=day),
        recent=load_recent(db, user.household_id),
    )


def _savings_out(
    db: DbSession,
    household: Household | None,
    movements: list[balances_domain.MovementRow],
    *,
    on: date,
) -> SavingsOut:
    """The goal, judged salary to salary.

    ⚠️ The verdict belongs to the **closed** cycle — the one a new salary has
    already ended — because that is the only stretch whose spending is finished.
    The cycle being lived gets an allowance instead: what can still be spent and
    still land on the target. A verdict on a month that is half over would be a
    guess dressed as a result.
    """
    target = household.monthly_savings_target_cents if household else None
    category_id = household.salary_category_id if household else None

    cycles = domain.salary_cycles(movements, salary_category_id=category_id, on=on)
    open_cycle = cycles[-1] if cycles else None
    closed = cycles[-2] if len(cycles) > 1 else None

    category = db.get(Category, category_id) if category_id is not None else None

    return SavingsOut(
        target_cents=target,
        salary_category_id=category_id,
        salary_category_name=category.name if category else None,
        closed=_cycle_out(closed),
        open=_cycle_out(open_cycle),
        # Null rather than False when there is nothing to judge: "you missed it"
        # and "I cannot say yet" are different things to show.
        met=None if closed is None or target is None else closed.saved_cents >= target,
        allowance_cents=(
            None if open_cycle is None or target is None else open_cycle.allowance_cents(target)
        ),
    )


def _cycle_out(cycle: domain.SalaryCycle | None) -> CycleOut | None:
    if cycle is None:
        return None
    return CycleOut(
        start=cycle.start,
        end=cycle.end,
        salary_cents=cycle.salary_cents,
        spent_cents=cycle.spent_cents,
        saved_cents=cycle.saved_cents,
        is_open=cycle.is_open,
    )


@router.get("/series", response_model=SeriesOut)
def series(
    user: CurrentUserDep,
    db: DbDep,
    months: int = Query(default=DEFAULT_MONTHS, ge=0, le=600),
    end: date | None = Query(default=None),
) -> SeriesOut:
    """Income, spending and net worth month by month, over a window you choose.

    `months` is how far back to look, counting the month `end` falls in.
    ⚠️ **Zero means "everything"** — from the month of the first movement — which
    is the honest reading of a "Max" button: not an arbitrary large number, but
    the point where the data actually starts.

    Separate from `/analysis` on purpose: widening a line from one year to five
    must not re-fetch a pie, and changing the month must not re-fetch five years
    of history.
    """
    last_month = month_of(end or date.today()).start
    movements = movement_rows(db, user.household_id)

    if months == 0:
        earliest = min((row.date for row in movements), default=last_month)
        first_month = month_of(earliest).start
    else:
        first_month = shift_month(last_month, -(months - 1))

    span = months_between(first_month, month_of(last_month).end)
    accounts = _accounts(db, user.household_id)

    monthly = domain.monthly_series(movements, span)
    worth = domain.net_worth_series(balance_rows(accounts), movements, span)

    return SeriesOut(
        months=[
            MonthPointOut(
                month=point.month,
                income_cents=point.income_cents,
                expense_cents=point.expense_cents,
                savings_cents=point.savings_cents,
                net_worth_cents=value.value_cents,
                movement_count=point.movement_count,
            )
            for point, value in zip(monthly, worth, strict=True)
        ]
    )


@router.get("/calendar", response_model=CalendarOut)
def calendar(user: CurrentUserDep, db: DbDep) -> CalendarOut:
    """Which months actually have something in them.

    ⚠️ It exists so the Analisi screen can refuse to offer a period there is
    nothing to say about. Showing seven empty charts for March 2019 and
    explaining each time that there is no data is worse than not letting you go
    there: the screen looks broken, and the honest message repeated seven times
    reads as an error rather than as an answer.

    Distinct dates rather than a `date_trunc`: the tests run on SQLite and the
    production database is Postgres, and a query that only works on one of them
    is a query nobody tests.
    """
    days = db.scalars(
        select(Transaction.date).where(Transaction.household_id == user.household_id).distinct()
    ).all()

    months = sorted({day.replace(day=1) for day in days})
    return CalendarOut(months=months)


@router.get("/analysis", response_model=AnalysisOut)
def analysis(
    user: CurrentUserDep,
    db: DbDep,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> AnalysisOut:
    """Where the money went, against where it went last time.

    The period is free — a month, a quarter, a year, any two dates — and the
    comparison is always the previous stretch of the same length, which for a
    whole calendar month means *the month before* rather than thirty days
    earlier. `domain/period.previous_period` is the only place that decides that.
    """
    period = _requested_period(date_from, date_to)
    previous = previous_period(period)

    movements = movement_rows(db, user.household_id)

    slices = domain.by_category(movements, period, previous=previous)
    names = _category_labels(db, user.household_id)

    biggest = domain.top_expenses(movements, period)

    return AnalysisOut(
        period=PeriodOut(start=period.start, end=period.end),
        previous=PeriodOut(start=previous.start, end=previous.end),
        totals=_totals_out(domain.totals(movements, period)),
        previous_totals=_totals_out(domain.totals(movements, previous)),
        by_category=[_slice_out(row, names) for row in slices],
        # ⚠️ The domain chose *which* rows; this only fetches them whole. A
        # WHERE clause repeating "expense and not an adjustment" would be a
        # second definition of spending, living where nobody would test it.
        top_expenses=load_by_ids(
            db, user.household_id, [row.id for row in biggest if row.id is not None]
        ),
        pace=_pace_out(domain.pace(movements, period, on=date.today())),
    )


def _requested_period(date_from: date | None, date_to: date | None) -> Period:
    """Default to the calendar month, and tolerate the ends arriving swapped."""
    if date_from is None and date_to is None:
        return month_of(date.today())
    if date_from is None:
        return month_of(date_to)  # type: ignore[arg-type]
    if date_to is None:
        return month_of(date_from)
    return Period(start=min(date_from, date_to), end=max(date_from, date_to))


def _accounts(db: DbSession, household_id: int) -> list[Account]:
    return list(
        db.scalars(
            select(Account)
            .where(Account.household_id == household_id)
            .order_by(Account.is_archived, Account.position, func.lower(Account.name))
        ).all()
    )


def _account_out(account: Account, totals: dict[int, int]) -> AccountOut:
    return AccountOut(
        id=account.id,
        name=account.name,
        kind=account.kind,
        opening_balance_cents=account.opening_balance_cents,
        opening_date=account.opening_date,
        include_in_net_worth=account.include_in_net_worth,
        position=account.position,
        is_archived=account.is_archived,
        balance_cents=totals.get(account.id, account.opening_balance_cents),
    )


def _category_labels(db: DbSession, household_id: int) -> dict[int, Category]:
    return {
        category.id: category
        for category in db.scalars(
            select(Category).where(Category.household_id == household_id)
        ).all()
    }


def _slice_out(row: domain.CategoryTotal, names: dict[int, Category]) -> CategorySliceOut:
    category = names.get(row.category_id) if row.category_id is not None else None
    return CategorySliceOut(
        category_id=row.category_id,
        name=category.name if category else UNCATEGORISED,
        color=category.color if category else None,
        icon=category.icon if category else None,
        total_cents=row.total_cents,
        share_permille=row.share_permille,
        previous_cents=row.previous_cents,
        delta_cents=row.delta_cents,
    )


def _totals_out(summed: domain.Totals) -> TotalsOut:
    return TotalsOut(
        income_cents=summed.income_cents,
        expense_cents=summed.expense_cents,
        savings_cents=summed.savings_cents,
        movement_count=summed.movement_count,
    )


def _pace_out(pace: domain.Pace) -> PaceOut:
    return PaceOut(
        elapsed_days=pace.elapsed_days,
        total_days=pace.total_days,
        spent_cents=pace.spent_cents,
        daily_average_cents=pace.daily_average_cents,
        projection_cents=pace.projection_cents,
    )
