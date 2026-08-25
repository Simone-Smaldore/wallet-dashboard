"""Amounts, where they are pure.

The whole module exists to keep floats away from money; these tests are what
say so out loud.
"""

import pytest

from app.domain.money import InvalidAmount, format_amount, parse_amount


@pytest.mark.parametrize(
    ("typed", "cents"),
    [
        ("12,50", 1250),
        # The dot as a decimal separator: people type it, phones offer it.
        ("12.50", 1250),
        ("1.234,56", 123456),
        ("  12,5  ", 1250),
        # "12,5" is fifty cents, not five.
        ("0,01", 1),
        ("100", 10000),
        ("-45,20", -4520),
        ("12,50 €", 1250),
        ("1.234.567,89", 123456789),
        # A lone dotted group is thousands, not decimals.
        ("1.234", 123400),
    ],
)
def test_what_people_type_becomes_cents(typed, cents):
    assert parse_amount(typed) == cents


def test_the_float_trap():
    """⚠️ The reason this module does not use float().

    `19.99 * 100` in binary floating point is 1998.9999999999998, so a naive
    conversion truncates to 1998 and quietly loses a cent — on prices ending in
    99, which is most of them.
    """
    assert parse_amount("19,99") == 1999
    assert parse_amount("19.99") == 1999

    # And it is not just one value: every .99 in a realistic range must land.
    for euro in range(1, 200):
        assert parse_amount(f"{euro},99") == euro * 100 + 99


@pytest.mark.parametrize(
    "typed",
    [
        "",  # ⚠️ an empty box is an error, never zero
        "   ",
        "abc",
        "12,345",  # three decimals: more precision than the app can store
        "1,2,3",
        "12..5",
        "12.",
        "-",
    ],
)
def test_nonsense_is_refused_rather_than_guessed(typed):
    with pytest.raises(InvalidAmount):
        parse_amount(typed)


@pytest.mark.parametrize(
    ("cents", "text"),
    [
        (1250, "12,50 €"),
        (123456, "1.234,56 €"),
        (1, "0,01 €"),
        (0, "0,00 €"),
        (-4520, "-45,20 €"),
        (100000000, "1.000.000,00 €"),
    ],
)
def test_cents_are_shown_as_euro(cents, text):
    assert format_amount(cents) == text


def test_the_user_never_sees_a_cent_value():
    """The whole point of the representation being internal."""
    shown = format_amount(1999)
    assert shown == "19,99 €"
    assert "1999" not in shown


def test_round_trip():
    for cents in (0, 1, 99, 100, 12345, -6789, 100000000):
        assert parse_amount(format_amount(cents, with_symbol=False)) == cents
