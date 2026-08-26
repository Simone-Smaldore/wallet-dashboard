from datetime import date as DateType
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.vocabulary import AssetKind, PriceBasis, PriceSource


class AssetWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "source_ref", "notes", check_fields=False)
    @classmethod
    def trim(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class AssetCreate(AssetWrite):
    account_id: int
    name: str = Field(min_length=1, max_length=120)
    kind: AssetKind
    #: ⚠️ Decimal, and the only one in the project: eight places, because a
    #: bitcoin needs them. `gt=0` — a holding of nothing is not a holding.
    quantity: Decimal = Field(gt=0, max_digits=28, decimal_places=8)
    #: ⚠️ A bond quotes as a percentage of its nominal, a share in euro. Getting
    #: this wrong values a BTP a hundred times over. See domain/assets.py.
    price_basis: PriceBasis
    source: PriceSource
    #: An ISIN for Borsa Italiana, a coin id for CoinGecko, nothing for manual.
    source_ref: str | None = Field(default=None, max_length=60)
    opened_at: DateType | None = None
    notes: str | None = Field(default=None, max_length=255)


class AssetUpdate(AssetWrite):
    account_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: AssetKind | None = None
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=28, decimal_places=8)
    price_basis: PriceBasis | None = None
    source: PriceSource | None = None
    source_ref: str | None = Field(default=None, max_length=60)
    #: Setting it sells the holding out: it keeps its history and leaves the net
    #: worth. Which is what you want far more often than deleting it.
    closed_at: DateType | None = None
    notes: str | None = Field(default=None, max_length=255)


class AssetOut(BaseModel):
    """A holding, with its last known value.

    ⚠️ **`valued_on` travels with `value_cents`, always.** A number that looks
    current and is three weeks old is worse than no number: on a missing one you
    ask, on a stale one you rely. Every screen that shows the value shows the
    day.
    """

    id: int
    account_id: int
    name: str
    kind: AssetKind
    quantity: Decimal
    price_basis: PriceBasis
    source: PriceSource
    source_ref: str | None
    opened_at: DateType | None
    closed_at: DateType | None
    notes: str | None

    #: Null when no price has ever been recorded — a fact, not a zero.
    value_cents: int | None
    unit_price_cents: int | None
    valued_on: DateType | None


class AssetPurchase(BaseModel):
    """Ho comprato: quante quote in più, e quanto sono costate.

    ⚠️ **Una richiesta sola, perché sono due scritture che non possono
    accadere a metà.** I soldi che escono dal conto e le quote che entrano
    nell'asset sono la stessa compera vista da due lati: se partisse il bonifico
    e non la quantità, il conto direbbe di aver versato di più e il guadagno
    diventerebbe finzione — e nessuno se ne accorgerebbe, perché entrambi i
    numeri sarebbero plausibili.
    """

    model_config = ConfigDict(extra="forbid")

    #: Quante quote, o quante monete, hai comprato. Si **somma** a quelle che ci
    #: sono: il totale lo fa l'app, non tu.
    quantity: Decimal = Field(gt=0, max_digits=28, decimal_places=8)
    #: Quanto hai pagato in tutto, commissioni comprese.
    amount_cents: int = Field(gt=0)
    #: Da dove sono usciti i soldi.
    from_account_id: int
    date: DateType
    description: str | None = Field(default=None, max_length=255)


class PriceProbe(BaseModel):
    """Ask a source for a price without saving anything."""

    model_config = ConfigDict(extra="forbid")

    source: PriceSource
    source_ref: str = Field(min_length=1, max_length=60)
    kind: AssetKind | None = None
    price_basis: PriceBasis = PriceBasis.PER_UNIT
    quantity: Decimal | None = Field(default=None, gt=0)


class PriceProbeResult(BaseModel):
    found: bool
    unit_price_cents: int | None = None
    date: DateType | None = None
    #: What the quantity would be worth, when one was given: it is the number
    #: that catches a wrong `price_basis` before it reaches the net worth.
    value_cents: int | None = None


class RefreshResult(BaseModel):
    """One line per asset, readable by a person.

    ⚠️ Including the failures. A price run that reports only what worked is a
    run you cannot tell apart from one that did nothing.
    """

    lines: list[str]
