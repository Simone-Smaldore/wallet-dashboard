from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Asset(Base, TimestampMixin):
    """Something you own whose value changes on its own.

    ⚠️ **Liquidity is recorded, investments are valued**, and that is why this
    is not a movement. A current account has movements and a balance derived
    from them; an ETF has a quantity you rarely change and a price that changes
    every minute. Bending one model into the other would break the one that
    works.

    An asset lives **inside an investment account**, and the two answer
    different questions: the account's balance is what you paid in, this is what
    it is worth. Both are true, neither is the other, and the screen shows them
    side by side rather than picking one.
    """

    __tablename__ = "asset"
    __table_args__ = (
        UniqueConstraint("household_id", "name", name="uq_asset_household_name"),
        Index("ix_asset_household_account", "household_id", "account_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: The investment account this sits in. Its balance is the capital paid in.
    account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="RESTRICT"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)

    #: ⚠️ **The only decimal in this project, and it earns it.** A bitcoin is
    #: counted to eight places and an ETF to fractions of a share: integers do
    #: not reach, and the scale is not money's. Amounts stay integer cents
    #: everywhere else, `value_cents` included — these are two different kinds
    #: of number and confusing them truncates crypto at the hundredth of a coin.
    quantity: Mapped[Decimal] = mapped_column(Numeric(28, 8), nullable=False)

    #: ⚠️ How a quoted price becomes money. A bond quotes as a percentage of its
    #: nominal; a share quotes in euro. See domain.vocabulary.PriceBasis — this
    #: is the field that keeps a BTP from entering the net worth a hundred times
    #: too large.
    price_basis: Mapped[str] = mapped_column(String(24), nullable=False)

    #: Where tomorrow's price comes from, and what to ask it for: an ISIN for
    #: Borsa Italiana, a coin id for CoinGecko. `manual` means you type it.
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(60), nullable=True)

    opened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    #: Set when you sell out of it: closed assets keep their history and leave
    #: the net worth.
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AssetValuation(Base):
    """What an asset was worth on a day.

    ⚠️ **A dated snapshot, never a field overwritten.** A single "current value"
    updated in place would make the net-worth chart a retroactive lie: March
    recomputed with August's price, and the curve you are looking at would never
    have been true. History accumulates, like movements do.

    ⚠️ `date` is the day **the source is talking about**, not the day we asked.
    Borsa Italiana hands back its reference price with its own timestamp; if the
    market has been shut for three days, this valuation is three days old and
    has to say so.
    """

    __tablename__ = "asset_valuation"
    __table_args__ = (
        # One valuation per asset per day: a second fetch on the same day is a
        # correction of the first, not another point on the curve.
        UniqueConstraint("asset_id", "date", name="uq_asset_valuation_asset_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), nullable=False, index=True
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)
    #: What one unit cost, in cents. Kept for traceability: it is the number the
    #: source actually said, before any arithmetic of ours.
    unit_price_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    #: What the whole holding was worth. Integer cents, like every other amount.
    value_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)

    source: Mapped[str] = mapped_column(String(24), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
