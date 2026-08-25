from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Transaction(Base, TimestampMixin):
    """A movement: money out, money in, or money moved.

    Written by nobody yet — the screens arrive with M3 — but the table is here
    from M2 because its rules *are* the model, and a balance computed over a
    table that does not exist would be a placeholder rather than the real thing.

    ⚠️ **A transfer is one row, not two.** Double entry is the textbook answer
    and the wrong one here: it would double the rows of every list, forcing each
    screen and each statistic to filter half of them out, and forgetting once is
    enough for a salary moved to savings to show up as income. With one row and
    two account columns, "a transfer is not an expense" stops being a rule to
    remember and becomes a property of the table.

    ⚠️ **The amount is always positive**; `kind` carries the sign. If the sign
    lived in the number, every sum in the codebase would need an abs() nobody
    would remember, and sooner or later there would be a -0 somewhere.

    ⚠️ **A date, not a timestamp.** A spend is "12 March": turning it into an
    instant drags timezones into an app used on a phone in another country, and
    a purchase near midnight lands in the wrong month. `created_at` is a real
    timestamp and is metadata — it never groups anything by period.

    `is_adjustment` marks a row created by reconciling a balance. It moves the
    balance and the net worth and stays out of the spending statistics: it is
    not consumption, it is the measure of what you forgot to record.
    """

    __tablename__ = "transaction"
    __table_args__ = (
        # The model, enforced by the database rather than by good intentions.
        CheckConstraint("amount_cents > 0", name="ck_transaction_amount_positive"),
        CheckConstraint(
            "(kind = 'transfer') = (counter_account_id IS NOT NULL)",
            name="ck_transaction_transfer_has_counter_account",
        ),
        CheckConstraint(
            "kind <> 'transfer' OR category_id IS NULL",
            name="ck_transaction_transfer_has_no_category",
        ),
        CheckConstraint(
            "counter_account_id IS NULL OR counter_account_id <> account_id",
            name="ck_transaction_counter_account_differs",
        ),
        CheckConstraint(
            "NOT is_adjustment OR (category_id IS NULL AND kind <> 'transfer')",
            name="ck_transaction_adjustment_shape",
        ),
        # The order of the list, and the key of M3's keyset pagination.
        Index("ix_transaction_household_date_id", "household_id", "date", "id"),
        Index("ix_transaction_household_account", "household_id", "account_id"),
        Index(
            "ix_transaction_household_counter_account",
            "household_id",
            "counter_account_id",
        ),
        Index("ix_transaction_household_category", "household_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True
    )

    date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="RESTRICT"), nullable=False
    )
    # Only for transfers: the account the money lands on.
    counter_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("account.id", ondelete="RESTRICT"), nullable=True
    )
    # Only for expenses and income; never on a transfer.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("category.id", ondelete="RESTRICT"), nullable=True
    )

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_adjustment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
