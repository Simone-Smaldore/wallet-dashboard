from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LoginToken(Base, TimestampMixin):
    """A single-use magic link.

    Only the SHA-256 of the token is kept: the clear value exists just long
    enough to be put in an email. `used_at` makes the link single-use, and the
    row is kept afterwards because the rate limiter counts recent rows per user.
    """

    __tablename__ = "login_token"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Session(Base, TimestampMixin):
    """A logged-in browser.

    Opaque random token rather than a JWT: revoking one is a single UPDATE, and
    "esci da tutti i dispositivi" is the same UPDATE without the id filter. A JWT
    would need a revocation list, which is this table with extra steps.
    """

    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
