"""ETF and bond prices, read off Borsa Italiana's instrument pages.

    /borsa/etf/scheda/IE00B4L5Y983.html            -> 126,53 - 25/08/26 17.55.00
    /borsa/obbligazioni/mot/btp/scheda/IT...html   -> 55,92, data 25/08/2026

⚠️ **This is scraping, and scraping is a guess about somebody else's markup.**
There is no free, durable price API for European ETFs and bonds — the serious
ones are paid, and the unofficial endpoints break without notice and without a
licence. So this reads the public page, and the whole module is built around the
day it stops working:

- a page that does not answer, or answers without a price, returns **None**;
- the caller writes nothing, and the previous valuation stays with its date;
- `doctor` reports assets whose automatic valuation has gone stale.

⚠️ It never raises. A daily job that stops at the first bad page leaves every
later asset unpriced for reasons nobody sees.

The parsing is deliberately anchored to the *label text* — "Prezzo di
riferimento" — rather than to a CSS class or a position in a table. Labels are
what the page is about; classes are what today's designer called them.
"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.domain.vocabulary import PriceSource
from app.prices import TIMEOUT_SECONDS, USER_AGENT, Quote

BASE = "https://www.borsaitaliana.it"

#: Tried in order until one yields a price. Borsa Italiana files instruments by
#: taxonomy and there is no single page for "whatever this ISIN is", so asking a
#: few is cheaper than making the caller know which shelf it sits on.
PATHS = (
    "/borsa/etf/scheda/{isin}.html",
    "/borsa/obbligazioni/mot/btp/scheda/{isin}.html",
    "/borsa/obbligazioni/mot/obbligazioni-euro/scheda/{isin}.html",
    "/borsa/azioni/scheda/{isin}.html",
)

#: The price of the last session. Preferred over "Prezzo ufficiale", which is a
#: volume-weighted average of the day and answers a different question.
PRICE_LABEL = "Prezzo di riferimento"
DATE_LABEL = "Data di riferimento"

#: `<strong>Label</strong>` … next `<span class="t-text -right">value</span>`.
FIELD = (
    r"<strong>\s*{label}\s*</strong>.*?"
    r'<span[^>]*class="[^"]*t-text[^"]*-right[^"]*"[^>]*>(.*?)</span>'
)

#: `126,53` or `1.234,56` — Italian, so the comma is the decimal separator.
NUMBER = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+),(\d+)")
#: `25/08/26` or `25/08/2026`.
DAY = re.compile(r"(\d{2})/(\d{2})/(\d{2,4})")


def fetch(isin: str, *, kind_hint: str | None = None) -> Quote | None:
    """The reference price for an ISIN, or None if the page did not give one."""
    isin = isin.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", isin):
        return None

    for path in _ordered_paths(kind_hint):
        html = _get(BASE + path.format(isin=isin))
        if html is None:
            continue
        quote = parse(html)
        if quote is not None:
            return quote
    return None


def parse(html: str) -> Quote | None:
    """Pull the reference price, and the day it belongs to, out of a page.

    Separate from the fetching so it can be tested against saved HTML: a test
    that calls the site fails on a Friday evening for reasons of its own.
    """
    raw = _field(html, PRICE_LABEL)
    if raw is None:
        return None

    price = _number(raw)
    if price is None:
        return None

    # The ETF page puts the day in the same cell as the price; the bond page
    # gives it its own row. Take whichever is there, and fall back to today
    # rather than refusing a price for want of a timestamp.
    when = _day(raw) or _day(_field(html, DATE_LABEL) or "") or date.today()

    return Quote(unit_price=price, date=when, source=PriceSource.BORSA_ITALIANA)


def _ordered_paths(kind_hint: str | None) -> tuple[str, ...]:
    """Ask the likely shelf first. Only an ordering — the rest are still tried."""
    if kind_hint == "obbligazione":
        return PATHS[1:] + PATHS[:1]
    return PATHS


#: ⚠️ One retry, after a breath. Asking Borsa Italiana for several instruments
#: in a row gets one of them refused — seen while building this, with a request
#: that worked perfectly on its own a second later. In a job that runs once a
#: day a transient no costs a stale number for twenty-four hours, which is
#: exactly the failure this module is built to avoid.
ATTEMPTS = 2
PAUSE_SECONDS = 2


def _get(url: str) -> str | None:
    for attempt in range(ATTEMPTS):
        html = _get_once(url)
        if html is not None:
            return html
        if attempt + 1 < ATTEMPTS:
            time.sleep(PAUSE_SECONDS)
    return None


def _get_once(url: str) -> str | None:
    request = urllib.request.Request(
        url,
        headers={
            # ⚠️ Not optional. Without a browser-shaped user-agent this is a
            # silent 403, and a silent 403 is indistinguishable from "no price
            # today" — the same trap as the Brevo sender.
            "user-agent": USER_AGENT,
            "accept": "text/html,application/xhtml+xml",
            "accept-language": "it-IT,it;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _field(html: str, label: str) -> str | None:
    match = re.search(
        FIELD.format(label=re.escape(label)), html, re.S | re.I
    )
    if match is None:
        return None
    # &nbsp; and friends: the cell is laid out for a human, not for this.
    return re.sub(r"\s+", " ", match.group(1).replace("&nbsp;", " ")).strip()


def _number(text: str) -> Decimal | None:
    match = NUMBER.search(text)
    if match is None:
        return None
    try:
        return Decimal(f"{match.group(1).replace('.', '')}.{match.group(2)}")
    except InvalidOperation:
        return None


def _day(text: str) -> date | None:
    match = DAY.search(text)
    if match is None:
        return None
    day, month, year = match.groups()
    pattern = "%d/%m/%y" if len(year) == 2 else "%d/%m/%Y"
    try:
        return datetime.strptime(f"{day}/{month}/{year}", pattern).date()
    except ValueError:
        return None
