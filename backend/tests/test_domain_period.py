"""Periods, where every number the dashboard shows gets its boundaries."""

from datetime import date, timedelta

from app.domain.period import (
    Period,
    format_month,
    month_of,
    months_between,
    previous_period,
    shift_month,
)


def test_a_month_runs_from_the_first_to_the_last_day():
    """Both ends belong to it: a movement on the 1st and one on the 31st are
    both March, which is the whole point of a closed interval."""
    march = month_of(date(2026, 3, 17))

    assert march == Period(date(2026, 3, 1), date(2026, 3, 31))
    assert march.contains(date(2026, 3, 1))
    assert march.contains(date(2026, 3, 31))
    assert not march.contains(date(2026, 4, 1))
    assert not march.contains(date(2026, 2, 28))


def test_february_knows_about_leap_years():
    assert month_of(date(2024, 2, 10)).end == date(2024, 2, 29)
    assert month_of(date(2026, 2, 10)).end == date(2026, 2, 28)


def test_the_previous_month_is_the_month_before():
    """⚠️ Not "thirty days earlier". Comparing March against the 30 days ending
    in February would quietly drop a day of spending, and nobody would ever
    spot it in a percentage."""
    assert previous_period(month_of(date(2026, 3, 15))) == Period(
        date(2026, 2, 1), date(2026, 2, 28)
    )


def test_january_goes_back_to_december_of_the_year_before():
    assert previous_period(month_of(date(2026, 1, 9))) == Period(
        date(2025, 12, 1), date(2025, 12, 31)
    )


def test_a_free_interval_compares_with_one_of_the_same_length():
    week = Period(date(2026, 3, 9), date(2026, 3, 15))
    before = previous_period(week)

    assert before == Period(date(2026, 3, 2), date(2026, 3, 8))
    assert before.days == week.days
    # They touch and do not overlap: no day counted twice, none skipped.
    assert before.end == week.start - timedelta(days=1)


def test_shifting_a_month_clamps_the_day():
    """⚠️ There is no 31 February. Clamping is the only answer that neither
    throws nor rolls silently into March."""
    assert shift_month(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert shift_month(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert shift_month(date(2026, 3, 31), -1) == date(2026, 2, 28)
    assert shift_month(date(2026, 12, 15), 1) == date(2027, 1, 15)


def test_months_between_covers_every_month_touched():
    """The net-worth chart needs a point for the months where nothing happened
    too, or the line jumps over them as if they had not existed."""
    months = months_between(date(2025, 11, 20), date(2026, 2, 3))

    assert months == [
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]


def test_months_between_is_empty_when_the_interval_is_backwards():
    assert months_between(date(2026, 3, 1), date(2026, 2, 1)) == []


def test_month_labels_are_italian_and_not_the_host_locale():
    assert format_month(date(2026, 3, 1)) == "marzo 2026"
    assert format_month(date(2026, 12, 31)) == "dicembre 2026"


def test_a_quarter_compares_with_the_quarter_before():
    """⚠️ Not "ninety-one days earlier".

    April to June is 91 days; counting them back from 31 March reaches into the
    previous December by a day and drops one off the other end. The numbers
    would be wrong by a Tuesday and nothing on screen would say so.
    """
    q2 = Period(start=date(2026, 4, 1), end=date(2026, 6, 30))

    assert previous_period(q2) == Period(start=date(2026, 1, 1), end=date(2026, 3, 31))


def test_a_calendar_year_compares_with_the_year_before():
    year = Period(start=date(2026, 1, 1), end=date(2026, 12, 31))

    assert previous_period(year) == Period(start=date(2025, 1, 1), end=date(2025, 12, 31))


def test_a_span_that_is_not_whole_months_falls_back_to_the_same_number_of_days():
    """A free from–to has no calendar predecessor, so it gets the honest one."""
    week = Period(start=date(2026, 3, 9), end=date(2026, 3, 15))

    assert previous_period(week) == Period(start=date(2026, 3, 2), end=date(2026, 3, 8))
