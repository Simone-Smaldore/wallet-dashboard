from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Account(Base, TimestampMixin):
    """A place where money sits: current account, savings, cash, prepaid card.

    ⚠️ There is no `balance` column, and there must never be one. The balance is
    `opening_balance_cents + Σ movements`, computed in domain/balances.py. A
    stored copy updated on every write is a second number that can disagree with
    the first, and in an app about money two numbers that disagree are worse
    than one number that takes a moment.

    ⚠️ Accounts are archived, never deleted. A closed account still holds the
    history of your movements, and the net-worth chart of two years ago runs
    through it. Archived means: gone from the pickers, still in the story.
    """

    __tablename__ = "account"
    __table_args__ = (
        # Case-insensitive uniqueness. Without the lower(), "Conto" and "conto"
        # are two rows nobody can tell apart in a picker, and half the movements
        # end up filed against the wrong one.
        Index(
            "uq_account_household_name",
            "household_id",
            text("lower(name)"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)

    # The point you start keeping track from. Everything before it is somebody
    # else's problem, and the balance counts from here.
    opening_balance_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    opening_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Off for money you are holding for someone else, or for a shared account.
    # It only takes the account out of the net-worth total: what you spend from
    # it is still what you spent, so it stays in the spending statistics.
    include_in_net_worth: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
