"""Where tomorrow's prices come from.

One module per source, each with the same shape: ask for a reference, get back a
`Quote` — or **nothing**.

⚠️ **Nothing is a first-class answer here.** These are HTML pages and a public
endpoint, not a contract: the market is shut, the markup changed, the host is
having an afternoon. When a source does not answer, the caller writes no row and
the last known valuation stays where it is, **with its date on screen**. The way
a price feed betrays you is not by breaking loudly — it is by standing still
while you believe it is keeping up.

⚠️ **A test never calls the network.** The parsers are tested against saved
HTML; a test that fetches Borsa Italiana fails on a Friday evening for reasons
that have nothing to do with the code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.vocabulary import PriceSource

#: ⚠️ Explicit, and not optional. It is the same trap as Brevo: a default
#: `Python-urllib/3.x` gets a silent 403 from anything behind a CDN, and the
#: failure looks exactly like "no price today".
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

#: Long enough for a slow page, short enough that a daily job cannot hang on it.
TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Quote:
    """One price, and the day it is about.

    ⚠️ **The price is a Decimal in euro, not an integer number of cents**, and
    that is not the usual rule of this project reversed — it is the same rule
    applied properly. Amounts are integers because a euro amount *is* a whole
    number of cents; a quoted price is not. CRO trades at 0,050484 €: rounded to
    5 cents it is 1% out, and on a holding of a few hundred thousand cheap
    tokens the error stops being academic.

    So the price keeps its digits, and the rounding happens **once**, where the
    quantity meets it — in `domain.assets.value_cents`, which produces the
    integer amount everything else uses.
    """

    unit_price: Decimal
    #: ⚠️ The date **the source is talking about**, not the day we asked. Borsa
    #: Italiana hands back its reference price with its own timestamp; if the
    #: market has been shut since Friday, this is Friday's price and the screen
    #: has to say Friday.
    date: Date
    source: PriceSource

    @property
    def unit_price_cents(self) -> int:
        """The price as cents, for storing and showing. Display only: the value
        of a holding is never computed from this."""
        return int(
            (self.unit_price * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        )
