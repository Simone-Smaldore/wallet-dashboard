"""Periods.

⚠️ The only place in the backend where date arithmetic happens, together with
its mirror frontend/src/lib/period.ts. It is the kind of code that diverges
quietly, and when it diverges a movement dated the 31st lands in two months or
in none.

Everything here is pure and takes plain dates.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

MONTHS = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)


@dataclass(frozen=True)
class Period:
    """A closed interval: both ends belong to it.

    Closed rather than half-open because these dates are shown to a person and
    typed by one. "1 marzo – 31 marzo" is what a month is called; explaining
    that the end is exclusive would be explaining an implementation detail.
    """

    start: date
    end: date

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


def month_of(day: date) -> Period:
    """The calendar month a date falls in."""
    _, last = monthrange(day.year, day.month)
    return Period(day.replace(day=1), day.replace(day=last))


def shift_month(day: date, months: int) -> date:
    """Move by whole months, clamping the day to what the target month has.

    ⚠️ 31 January minus one month is 31 December, but plus one month is 28 or 29
    February — there is no 31st. Clamping is the only answer that does not throw
    or silently roll into the next month.
    """
    index = day.month - 1 + months
    year = day.year + index // 12
    month = index % 12 + 1
    _, last = monthrange(year, month)
    return date(year, month, min(day.day, last))


def previous_period(period: Period) -> Period:
    """The period to compare against.

    ⚠️ For a run of **whole calendar months** this is the same number of months
    before it: March compares with February, the second quarter with the first,
    2026 with 2025. Not "ninety-one days earlier" — comparing April–June with
    the 91 days ending 31 March would reach back into December by a day and
    quietly drop one at the other end, and nobody would ever notice the numbers
    were off by a Tuesday.

    For any other interval — a free from–to — it is the same number of days,
    ending the day before this one starts. There is nothing better available:
    an arbitrary span has no calendar predecessor.
    """
    months = _whole_months(period)
    if months is not None:
        start = shift_month(period.start, -months)
        return Period(start, month_of(shift_month(start, months - 1)).end)

    end = period.start - timedelta(days=1)
    return Period(end - timedelta(days=period.days - 1), end)


def months_between(start: date, end: date) -> list[date]:
    """The first day of every month touched by the interval, in order.

    Used by the net-worth chart, which needs a point per month even for the
    months where nothing happened.
    """
    if end < start:
        return []

    months = []
    cursor = start.replace(day=1)
    last = end.replace(day=1)
    while cursor <= last:
        months.append(cursor)
        cursor = shift_month(cursor, 1)
    return months


def format_month(day: date) -> str:
    """`marzo 2026`. Italian, and not from the system locale.

    A server's locale is whatever the host decided; product text is not
    something to leave to that.
    """
    return f"{MONTHS[day.month - 1]} {day.year}"


def _whole_months(period: Period) -> int | None:
    """How many whole calendar months the period is, or None if it is not.

    Whole means it starts on a first and ends on a last: one month, a quarter,
    a year, or any other run of them.
    """
    if period.start.day != 1 or period.end != month_of(period.end).end:
        return None
    return (period.end.year - period.start.year) * 12 + period.end.month - period.start.month + 1
