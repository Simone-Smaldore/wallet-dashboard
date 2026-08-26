"""Ask every source for today's prices and write down what came back.

Used by two callers that must behave identically: the daily cron
(`api/cron.py`) and `python -m scripts.prices`, run by hand when you want to see
it work.

⚠️ **A source that does not answer changes nothing.** No row, no zero, no
placeholder: the previous valuation stays exactly where it is, with its own
date, and the screen keeps showing that date. A price feed does not betray you
by breaking loudly — it betrays you by standing still while you believe it is
keeping up, which is why every screen that shows an invested figure shows when
it was true.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.domain.assets import value_cents
from app.domain.vocabulary import PriceSource
from app.models import Asset, AssetValuation
from app.prices import Quote, borsa_italiana, coingecko


#: Long enough to be a good guest, short enough that a dozen holdings still
#: finish inside a serverless function's budget.
POLITE_PAUSE_SECONDS = 1.5


@dataclass(frozen=True)
class Outcome:
    """What happened to one asset, in words a person can read."""

    asset: str
    ok: bool
    detail: str


def refresh(db: DbSession, household_id: int, *, today: date | None = None) -> list[Outcome]:
    """Update every open, automatically-priced asset. Returns one line each."""
    day = today or date.today()
    outcomes: list[Outcome] = []
    asked = False

    assets = db.scalars(
        select(Asset).where(
            Asset.household_id == household_id,
            Asset.closed_at.is_(None),
        )
    ).all()

    for asset in assets:
        if asset.source == PriceSource.MANUAL.value:
            # Nothing to ask: you are the source. Said out loud rather than
            # skipped in silence, so the report accounts for every asset.
            outcomes.append(Outcome(asset.name, True, "a mano, non lo tocco"))
            continue

        # ⚠️ A breath between instruments. Hammering a public page for six
        # holdings in a row is how you get one of them refused — and a refusal
        # here costs a stale number until tomorrow.
        if asked:
            time.sleep(POLITE_PAUSE_SECONDS)
        asked = True

        quote = _ask(asset, day)
        if quote is None:
            last = _latest(db, asset.id)
            when = f", resta quella del {last.date}" if last else ", e non ne ha nessuna"
            outcomes.append(
                Outcome(asset.name, False, f"nessun prezzo da {asset.source}{when}")
            )
            continue

        value = value_cents(asset.quantity, quote.unit_price, asset.price_basis)
        _record(db, asset.id, quote, value)
        outcomes.append(
            Outcome(
                asset.name,
                True,
                f"{quote.unit_price:,.6f} al {quote.date} "
                f"-> {value / 100:,.2f} €",
            )
        )

    return outcomes


def _ask(asset: Asset, day: date) -> Quote | None:
    if not asset.source_ref:
        return None
    if asset.source == PriceSource.COINGECKO.value:
        return coingecko.fetch(asset.source_ref, today=day)
    if asset.source == PriceSource.BORSA_ITALIANA.value:
        return borsa_italiana.fetch(asset.source_ref, kind_hint=asset.kind)
    return None


def _latest(db: DbSession, asset_id: int) -> AssetValuation | None:
    return db.scalar(
        select(AssetValuation)
        .where(AssetValuation.asset_id == asset_id)
        .order_by(AssetValuation.date.desc())
        .limit(1)
    )


def _record(db: DbSession, asset_id: int, quote: Quote, value: int) -> None:
    """One valuation per asset per day.

    ⚠️ A second fetch on the same day **corrects** the first rather than adding
    a point: two values for one day would make the curve depend on how often the
    job happened to run.
    """
    existing = db.scalar(
        select(AssetValuation).where(
            AssetValuation.asset_id == asset_id, AssetValuation.date == quote.date
        )
    )
    if existing is not None:
        existing.unit_price_cents = quote.unit_price_cents
        existing.value_cents = value
        existing.source = quote.source.value
        return

    db.add(
        AssetValuation(
            asset_id=asset_id,
            date=quote.date,
            unit_price_cents=quote.unit_price_cents,
            value_cents=value,
            source=quote.source.value,
        )
    )
