"""What a holding is worth, given a quoted price.

Pure, like the rest of `domain/`: a quantity, a price and a convention in, an
integer number of cents out. It is three lines of arithmetic and it gets its own
module because those three lines are where an investment total goes wrong by a
factor of a hundred.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.domain.vocabulary import PriceBasis

#: A bond's price is a percentage of its nominal, so the nominal has to be
#: divided back down. Named rather than written as a bare 100 in the middle of
#: an expression, because a bare 100 in money code is exactly the kind of thing
#: that later gets "simplified" away.
PERCENT = Decimal(100)


def value_cents(
    quantity: Decimal, unit_price: Decimal, basis: PriceBasis | str
) -> int:
    """What the whole holding is worth, in cents.

    ⚠️ **The basis is not decoration.** An ETF at `126,53` is 126,53 € a share:
    three shares are 379,59 €. A BTP at `55,78` is *not* 55,78 € — it is 55,78%
    of the nominal, so 10.000 € of nominal are 5.578 €, not 557.800 €.

    Getting this wrong does not raise anything and does not look wrong up close.
    It looks wrong only at the total, once, in a way you would have to already
    suspect to notice — which is why the convention is a field on the asset and
    a branch here, rather than something the caller is trusted to remember.

    ⚠️ Decimal arithmetic all the way, **rounded once, here**. Both sides keep
    their digits until this line: the quantity because a bitcoin needs eight
    places, and the price because CRO trades at 0,050484 € and rounding that to
    five cents first would be a 1% error nobody would ever trace.
    """
    exact = Decimal(quantity) * Decimal(unit_price) * 100
    if PriceBasis(basis) is PriceBasis.PERCENT_OF_NOMINAL:
        exact /= PERCENT

    # Half up: the ordinary reading of "round", and the one a person checking by
    # hand would do.
    return int(exact.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def gain_cents(value: int, contributed: int) -> int:
    """What the holding has made, or lost, against what was paid in.

    ⚠️ A description, never advice. The app says what happened to the money; it
    does not say whether that was clever, and it does not project it forward.
    """
    return value - contributed
