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

from app.api.accounts import account_values, balance_rows, movement_rows
from app.api.deps import CurrentUserDep, DbDep
from app.api.transactions import load_by_ids, load_recent
from app.domain import balances as balances_domain
from app.domain import stats as domain
from app.domain.vocabulary import AccountKind
from app.domain.period import (
    Period,
    month_of,
    months_between,
    previous_period,
    shift_month,
)
from app.models import Account, Asset, AssetValuation, Category, Household, Transaction
from app.schemas.account import AccountOut
from app.schemas.stats import (
    AnalysisOut,
    CategorySliceOut,
    MonthPointOut,
    NetWorthOut,
    PaceOut,
    CalendarOut,
    PeriodOut,
    SavingsMonthOut,
    SavingsOut,
    SeriesOut,
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
    valued, valued_on = account_values(db, user.household_id)
    worth = balances_domain.net_worth_parts(rows, movements, valuations=valued)

    return SummaryOut(
        on=day,
        period=PeriodOut(start=period.start, end=period.end),
        net_worth_cents=worth.total_cents,
        net_worth=NetWorthOut(
            total_cents=worth.total_cents,
            liquid_cents=worth.liquid_cents,
            invested_cents=worth.invested_cents,
            valued_on=valued_on,
        ),
        accounts=[_account_out(account, totals, valued, valued_on) for account in accounts],
        totals=_totals_out(summed),
        savings=_savings_out(db, household, accounts, movements, on=day),
        recent=load_recent(db, user.household_id),
    )


def _savings_out(
    db: DbSession,
    household: Household | None,
    accounts: list[Account],
    movements: list[balances_domain.MovementRow],
    *,
    on: date,
) -> SavingsOut:
    """The goal, month by month.

    ⚠️ The verdict belongs to **last month**, because that is the only one whose
    spending is finished. This month gets an allowance instead: what can still
    be spent and still land on the target. A verdict on a month that is half
    over would be a guess dressed as a result.
    """
    target = household.monthly_savings_target_cents if household else None
    category_id = household.salary_category_id if household else None

    invested = frozenset(
        account.id
        for account in accounts
        if account.kind == AccountKind.INVESTIMENTO.value
    )

    this_month = domain.savings_month(
        movements,
        on,
        salary_category_id=category_id,
        investment_account_ids=invested,
        on=on,
    )
    last_month = domain.savings_month(
        movements,
        shift_month(month_of(on).start, -1),
        salary_category_id=category_id,
        investment_account_ids=invested,
        on=on,
    )

    # Nothing came in and nothing went out: there is no month to judge, which is
    # a different thing from a month that missed its target.
    judged = (
        last_month
        if (last_month.budget_cents or last_month.spent_cents or last_month.set_aside_cents)
        else None
    )

    category = db.get(Category, category_id) if category_id is not None else None

    return SavingsOut(
        target_cents=target,
        salary_category_id=category_id,
        salary_category_name=category.name if category else None,
        closed=_month_out(judged),
        open=_month_out(this_month),
        met=None if judged is None or target is None else judged.saved_cents >= target,
        allowance_cents=(
            None if target is None else this_month.allowance_cents(target)
        ),
    )


def _month_out(month: domain.SavingsMonth | None) -> SavingsMonthOut | None:
    if month is None:
        return None
    return SavingsMonthOut(
        month=month.month,
        salary_cents=month.salary_cents,
        other_income_cents=month.other_income_cents,
        budget_cents=month.budget_cents,
        spent_cents=month.spent_cents,
        saved_cents=month.saved_cents,
        set_aside_cents=month.set_aside_cents,
        is_open=month.is_open,
    )


@router.get("/series", response_model=SeriesOut)
def series(
    user: CurrentUserDep,
    db: DbDep,
    months: int = Query(default=DEFAULT_MONTHS, ge=0, le=600),
    end: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    liquid: bool = Query(default=False),
) -> SeriesOut:
    """Income, spending and net worth month by month, over a window you choose.

    `months` is how far back to look, counting the month `end` falls in.
    ⚠️ **Zero means "everything"** — from the month of the first movement — which
    is the honest reading of a "Max" button: not an arbitrary large number, but
    the point where the data actually starts.

    `account_id` draws one account's own curve; `liquid` leaves the investments
    out and shows only what could be spent. Neither changes the arithmetic —
    both just decide which accounts go in, which is why there is one function
    behind all three.

    ⚠️ **Every month is valued with the price that existed then.** Applying
    today's price backwards would redraw last March with August's market. Months
    before the first price fall back to the capital paid in, and `priced_from`
    says where that line is: without it, the first priced month looks like an
    extraordinary gain.

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

    if account_id is not None:
        accounts = [account for account in accounts if account.id == account_id]
    elif liquid:
        accounts = [
            account
            for account in accounts
            if account.kind != AccountKind.INVESTIMENTO.value
        ]

    prices, priced_from = _price_history(db, user.household_id)
    monthly = domain.monthly_series(movements, span)
    worth = domain.net_worth_series(
        balance_rows(accounts), movements, span, valuations=prices
    )

    return SeriesOut(
        priced_from=priced_from,
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


def _price_history(
    db: DbSession, household_id: int
) -> tuple[dict[int, list[tuple[date, int]]], date | None]:
    """Every valuation ever recorded, grouped by the account that holds it.

    The whole history, not the latest: each month of the curve picks the price
    that existed at its end, so the past cannot be redrawn with today's market.
    """
    rows = db.execute(
        select(Asset.account_id, AssetValuation.date, AssetValuation.value_cents)
        .join(AssetValuation, AssetValuation.asset_id == Asset.id)
        .where(Asset.household_id == household_id, Asset.closed_at.is_(None))
        .order_by(AssetValuation.date)
    ).all()

    # Several holdings can share an account, so a date's value is their sum.
    by_account_date: dict[tuple[int, date], int] = {}
    for account_id, when, value in rows:
        by_account_date[(account_id, when)] = by_account_date.get((account_id, when), 0) + value

    history: dict[int, list[tuple[date, int]]] = {}
    for (account_id, when), value in by_account_date.items():
        history.setdefault(account_id, []).append((when, value))
    for series in history.values():
        series.sort()

    first = min((when for _, when in by_account_date), default=None)
    return history, first


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


def _account_out(
    account: Account,
    totals: dict[int, int],
    valued: dict[int, int],
    valued_on: date | None,
) -> AccountOut:
    value = valued.get(account.id)
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
        value_cents=value,
        valued_on=valued_on if value is not None else None,
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
