"""Crypto prices, from CoinGecko's public endpoint.

    https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur
    -> {"bitcoin":{"eur":67359}}

The only source in here that is an actual API: documented, no key, and a rate
limit far above one call a day. It is also the only asset class where a free and
durable price feed exists at all, which is why the plan singled it out.

`source_ref` is the coin id — `bitcoin`, `ethereum` — not the ticker. CoinGecko
has several coins per ticker and exactly one per id.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal

from app.domain.vocabulary import PriceSource
from app.prices import TIMEOUT_SECONDS, USER_AGENT, Quote

URL = "https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=eur"


def fetch(coin_id: str, *, today: date | None = None) -> Quote | None:
    """The price of one coin in euro, or None if the answer was not usable.

    ⚠️ Every failure returns None rather than raising. A daily job that stops on
    the first unreachable host leaves every later asset unpriced, and the reason
    would be buried in a log nobody reads.

    ⚠️ The date is today's: this endpoint quotes a live price and carries no
    timestamp of its own. That is honest for crypto, which trades continuously —
    unlike a closed exchange, there is no "last session" to point at.
    """
    request = urllib.request.Request(
        URL.format(ids=urllib.parse.quote(coin_id)),
        headers={"user-agent": USER_AGENT, "accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    price = payload.get(coin_id, {}).get("eur")
    if not isinstance(price, (int, float)):
        return None

    return Quote(
        # ⚠️ `str(price)` before Decimal, and every digit kept. CoinGecko quotes
        # CRO at 0,050484 €: rounding that to five cents here would be a 1%
        # error baked in before anyone could notice it.
        unit_price=Decimal(str(price)),
        date=today or date.today(),
        source=PriceSource.COINGECKO,
    )
