"""What a holding is worth.

Three lines of arithmetic, and the place an investment total goes wrong by a
factor of a hundred.
"""

from decimal import Decimal

from app.domain.assets import gain_cents, value_cents
from app.domain.vocabulary import PriceBasis


def test_a_share_is_quoted_in_euro():
    """Three shares of an ETF at 126,53 € are 379,59 €."""
    assert value_cents(Decimal("3"), Decimal("126.53"), PriceBasis.PER_UNIT) == 37_959


def test_a_price_smaller_than_a_cent_keeps_its_digits():
    """⚠️ Found on real data, and the reason the price is not an integer.

    CRO trades at 0,050484 €. Rounded to five cents first, 321,3 of them come to
    16,07 € instead of 16,22 — a 1% error, invisible, and multiplied by however
    many hundreds of thousands of a cheap token somebody holds.
    """
    exact = value_cents(Decimal("321.3"), Decimal("0.050484"), PriceBasis.PER_UNIT)
    rounded_first = value_cents(Decimal("321.3"), Decimal("0.05"), PriceBasis.PER_UNIT)

    assert exact == 1_622
    assert rounded_first == 1_607


def test_a_bond_is_quoted_as_a_percentage_of_its_nominal():
    """⚠️ The one that would be wrong by a hundred.

    The BTP Mz72 shows 55,78 on Borsa Italiana. That is not 55,78 € — it is
    55,78% of the nominal, so 10.000 € of nominal are 5.578 €. Read as euro it
    would enter the net worth as 557.800 €, and the only sign would be a total
    that looks implausible.
    """
    assert (
        value_cents(Decimal("10000"), Decimal("55.78"), PriceBasis.PERCENT_OF_NOMINAL)
        == 557_800
    )


def test_the_same_numbers_read_the_other_way_are_a_hundred_times_out():
    """Stated once, so the size of the mistake is on the record."""
    per_unit = value_cents(Decimal("10000"), Decimal("55.78"), PriceBasis.PER_UNIT)
    as_bond = value_cents(
        Decimal("10000"), Decimal("55.78"), PriceBasis.PERCENT_OF_NOMINAL
    )

    assert per_unit == as_bond * 100


def test_eight_decimal_places_of_a_coin_survive():
    """⚠️ `quantity` is the only decimal in this project because of this row.
    A satoshi is 0,00000001 BTC, and rounding it away early is how a crypto
    holding quietly becomes the wrong size."""
    # 0,5 BTC at 67.405,00 € is 33.702,50 €.
    price = Decimal("67405")
    assert value_cents(Decimal("0.5"), price, PriceBasis.PER_UNIT) == 3_370_250
    # And the smallest unit does not vanish on the way.
    assert value_cents(Decimal("0.00000001"), price, PriceBasis.PER_UNIT) == 0
    assert value_cents(Decimal("0.001"), price, PriceBasis.PER_UNIT) == 6_741


def test_rounding_is_half_up_once_at_the_end():
    """The reading a person checking by hand would do."""
    assert value_cents(Decimal("1.005"), Decimal("10"), PriceBasis.PER_UNIT) == 1_005
    assert value_cents(Decimal("3"), Decimal("16.67"), PriceBasis.PER_UNIT) == 5_001


def test_a_gain_is_the_difference_and_nothing_more():
    """⚠️ Described, never advised: the app says what happened, not whether it
    was clever, and it never projects it forward."""
    assert gain_cents(1_391_000, 1_240_200) == 150_800
    assert gain_cents(1_100_000, 1_240_200) == -140_200
