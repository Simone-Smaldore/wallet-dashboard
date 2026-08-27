"""What the two dashboard screens are sent.

One response per screen rather than one per chart. The Riepilogo is opened
several times a day against a serverless function that starts cold, and three
requests in a row are felt; and the numbers on one screen are all views of the
same set of movements, which the server has already loaded.
"""

from datetime import date as DateType

from pydantic import BaseModel

from app.schemas.account import AccountOut
from app.schemas.transaction import TransactionOut


class PeriodOut(BaseModel):
    """A closed interval: both ends belong to it, as in domain/period.py."""

    start: DateType
    end: DateType


class TotalsOut(BaseModel):
    """⚠️ Transfers and adjustments are in none of these. See domain/stats.py."""

    income_cents: int
    expense_cents: int
    savings_cents: int
    #: How many movements actually counted. Zero here means "nothing recorded",
    #: which the screen says in words instead of drawing axes at zero.
    movement_count: int


class CategorySliceOut(BaseModel):
    """One slice, with its name and colour already resolved.

    Denormalised into the response like everywhere else: the chart draws itself
    without waiting for the category list to have loaded too.
    """

    category_id: int | None
    name: str
    color: str | None
    icon: str | None
    total_cents: int
    #: Out of 1000. Integers, and they add up to exactly 1000: see
    #: domain/stats._with_shares for why the remainder lands where it does.
    share_permille: int
    previous_cents: int
    delta_cents: int


class MonthPointOut(BaseModel):
    """One month of the long charts. `month` is the first day of it."""

    month: DateType
    income_cents: int
    expense_cents: int
    savings_cents: int
    #: Net worth at the **end** of this month, not the latest one repeated.
    net_worth_cents: int
    movement_count: int


class PaceOut(BaseModel):
    """⚠️ `projection_cents` is a linear projection, not a forecast: today's
    average carried to the end of the period. It knows nothing about the rent
    due on the 28th, and the label on screen has to say so."""

    elapsed_days: int
    total_days: int
    spent_cents: int
    daily_average_cents: int
    projection_cents: int


class SavingsMonthOut(BaseModel):
    """A month judged against the goal.

    ⚠️ **The salary that funds a month arrived the month before.** Pay lands on
    the 27th, so September is lived on August's salary, and September's own
    salary belongs to October. Only the salary shifts: a refund or a gift is
    spent in the month it arrives.
    """

    #: First day of the month this is about.
    month: DateType
    #: The salary from the month before, which is what this month lives on.
    salary_cents: int
    #: Everything else that came in during this month.
    other_income_cents: int
    #: Salary plus the rest: what there was to live on.
    budget_cents: int
    spent_cents: int
    #: Budget minus spending. Negative means the month cost more than it had.
    saved_cents: int
    #: ⚠️ Money moved into an investment account this month, net of anything
    #: taken back out. Not spending — it is still yours — but it has left the
    #: current account, so the month's budget loses it and the goal measures
    #: what you keep on top of what you invest.
    set_aside_cents: int
    #: True for the month being lived: it gets an allowance, not a verdict.
    is_open: bool


class SavingsOut(BaseModel):
    """The savings goal, month by month."""

    target_cents: int | None
    salary_category_id: int | None
    salary_category_name: str | None

    #: Last month: finished, so it is the only one that can carry a verdict.
    closed: SavingsMonthOut | None
    #: This month. It gets an allowance instead.
    open: SavingsMonthOut | None

    #: Whether last month made the target. Null when there is nothing to judge
    #: or no target — which is not the same as False, and the screen says which.
    met: bool | None
    #: How much can still be spent this month and still hit the target. Negative
    #: means the target is already out of reach.
    allowance_cents: int | None


class SeriesOut(BaseModel):
    """The long charts, over a window you choose.

    ⚠️ Its own endpoint, and not part of the analysis response, because it
    answers a different question over a different window: the period selector
    picks *what to break down*, this picks *how far back to look*. Tying them
    together would mean re-fetching seven charts to widen a line, and re-fetching
    a line to change the month.
    """

    months: list[MonthPointOut]
    #: ⚠️ The first day any holding had a market price. Months before it are
    #: drawn at the capital paid in, which is a different quantity — so the
    #: first priced month steps up by whatever had been gained in silence, and
    #: the screen has to say so or it reads as a very good month.
    priced_from: DateType | None = None


class CalendarOut(BaseModel):
    """The months that have at least one movement, oldest first.

    First days of months. The Analisi screen builds its period picker out of
    this, so it can only offer periods there is something to look at.
    """

    months: list[DateType]


class NetWorthOut(BaseModel):
    """What you have, split into what you could spend and what is invested.

    ⚠️ `valued_on` is the **oldest** valuation behind the invested figure. A
    total that looks current and is three weeks old is worse than no total: on a
    missing number you check, on a stale one you rely.
    """

    total_cents: int
    liquid_cents: int
    invested_cents: int
    #: Null when nothing is invested, or when nothing has ever been priced.
    valued_on: DateType | None


class SummaryOut(BaseModel):
    """Everything the Riepilogo draws, in one round trip."""

    on: DateType
    period: PeriodOut
    net_worth_cents: int
    net_worth: NetWorthOut
    accounts: list[AccountOut]
    totals: TotalsOut
    savings: SavingsOut
    recent: list[TransactionOut]


class AnalysisOut(BaseModel):
    """Everything the Analisi screen draws, in one round trip."""

    period: PeriodOut
    #: For a whole month this is the month before, not "thirty days earlier".
    previous: PeriodOut
    totals: TotalsOut
    previous_totals: TotalsOut
    by_category: list[CategorySliceOut]
    top_expenses: list[TransactionOut]
    pace: PaceOut
