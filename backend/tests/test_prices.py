"""Reading a price off somebody else's page.

⚠️ **No test here touches the network.** The parsers run against saved extracts
of the real pages: a test that fetched Borsa Italiana would fail on a Friday
evening, during a deploy, and on a train — for reasons that have nothing to do
with this code, which is the fastest way to teach a team to ignore a red suite.

The fixtures are trimmed to the price table. A fixture you cannot read is not
evidence of anything.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from app.domain.vocabulary import PriceSource
from app.prices import borsa_italiana

FIXTURES = Path(__file__).parent / "fixtures"


def page(name: str) -> str:
    return (FIXTURES / f"borsa_{name}.html").read_text(encoding="utf-8")


def test_an_etf_page_gives_a_price_and_the_day_it_belongs_to():
    quote = borsa_italiana.parse(page("etf"))

    assert quote is not None
    assert quote.unit_price == Decimal("126.53")
    assert quote.unit_price_cents == 12_653
    # ⚠️ The date the source is talking about, not the day we asked. If the
    # market has been shut since Friday this is Friday's price, and the screen
    # has to say Friday.
    assert quote.date == date(2026, 8, 25)
    assert quote.source is PriceSource.BORSA_ITALIANA


def test_a_bond_page_carries_its_date_in_a_row_of_its_own():
    """The ETF page puts price and day in one cell, the bond page splits them.
    Both are read, because the page decides the layout and we do not."""
    quote = borsa_italiana.parse(page("btp"))

    assert quote is not None
    assert quote.unit_price == Decimal("55.92")
    assert quote.date == date(2026, 8, 25)


def test_a_page_without_a_price_is_no_price_rather_than_a_crash():
    """⚠️ The day Borsa Italiana changes its markup, this is what happens: None.

    Nothing is written, the previous valuation stays with its own date, and the
    screen keeps showing that date. A price feed betrays you by standing still
    while you believe it is keeping up — never by raising something you would
    have noticed.
    """
    assert borsa_italiana.parse("<html><body>manutenzione</body></html>") is None
    assert borsa_italiana.parse("") is None


def test_a_price_that_is_not_a_number_is_refused():
    """"N.D." is what the page says before the first trade of the day."""
    broken = page("etf").replace("126,53", "N.D.")

    assert borsa_italiana.parse(broken) is None


def test_an_isin_that_is_not_an_isin_is_never_even_fetched():
    """Twelve characters, two letters first. Checked before any request, so a
    typo in the form costs nothing and cannot be mistaken for a dead source."""
    assert borsa_italiana.fetch("non-un-isin") is None
    assert borsa_italiana.fetch("") is None
