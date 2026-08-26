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


class CycleOut(BaseModel):
    """One salary-to-salary stretch.

    ⚠️ The period a savings goal is judged on, and deliberately not the calendar
    month: money arrives on a day that is not the first, and the question is
    whether one salary was still partly there when the next one landed.
    """

    start: DateType
    #: For the open cycle this is today, because nobody knows when the next
    #: salary lands. It is the only honest end available for it.
    end: DateType
    salary_cents: int
    spent_cents: int
    #: What the salary had left over. Negative means it did not last.
    saved_cents: int
    is_open: bool


class SavingsOut(BaseModel):
    """The savings goal, judged the way a salary judges it."""

    target_cents: int | None
    salary_category_id: int | None
    salary_category_name: str | None

    #: The last completed cycle: the one a new salary has already closed, and
    #: therefore the only one that can carry a verdict.
    closed: CycleOut | None
    #: The cycle being lived. It gets an allowance, not a verdict.
    open: CycleOut | None

    #: Whether the closed cycle made the target. Null when there is no closed
    #: cycle or no target — which is not the same as False, and the screen says
    #: which.
    met: bool | None
    #: How much can still be spent in the open cycle and still hit the target.
    #: Negative means the target is already out of reach for this cycle.
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


class CalendarOut(BaseModel):
    """The months that have at least one movement, oldest first.

    First days of months. The Analisi screen builds its period picker out of
    this, so it can only offer periods there is something to look at.
    """

    months: list[DateType]


class SummaryOut(BaseModel):
    """Everything the Riepilogo draws, in one round trip."""

    on: DateType
    period: PeriodOut
    net_worth_cents: int
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
