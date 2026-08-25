from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# JSONB on Postgres, plain JSON on SQLite so the test suite can run offline.
# Same Python type either way; only the storage differs.
PREFERENCES_TYPE = JSON().with_variant(JSONB(), "postgresql")


class User(Base, TimestampMixin):
    """Someone allowed in.

    There is no password column and there never will be: identity is proven by
    receiving a magic link at a known address.

    Two kinds of property live here, on purpose:

    - `display_name` is a real column. It is shown on screen and will be sorted
      and searched, so it deserves the type checking a column can get.
    - `preferences` is a JSON blob for interface settings. Those change often
      and are always read whole, never queried one key at a time; a column each
      would mean a migration per checkbox. The shape is still validated on the
      way in and out by schemas.user.UserPreferences.

    Anything about the money rather than the person — the saving target, the
    default account — belongs on Household instead.
    """

    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Stored already normalized (lowercase, trimmed) by domain.auth.normalize_email.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(
        PREFERENCES_TYPE, nullable=False, default=dict, server_default="{}"
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    household: Mapped["Household"] = relationship(back_populates="users")  # noqa: F821

    @property
    def label(self) -> str:
        """What to show on screen: the chosen name, or the email until there is one."""
        return self.display_name or self.email
