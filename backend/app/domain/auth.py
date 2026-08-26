"""Authentication rules, with no database and no web framework in sight.

Everything here takes plain values and returns plain values, which is what lets
the whole magic-link flow be tested without spinning up Postgres.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# 32 bytes of entropy, URL-safe. Long enough that guessing is hopeless, short
# enough to survive an email client wrapping the link.
TOKEN_BYTES = 32


class AuthError(Exception):
    """Base for everything this module refuses to do."""


class InvalidToken(AuthError):
    """The token does not exist, is expired, or has already been spent."""


def normalize_email(email: str) -> str:
    """Emails are compared case-insensitively and without surrounding spaces."""
    return email.strip().lower()


def is_allowed(email: str, allowed: list[str]) -> bool:
    return normalize_email(email) in {normalize_email(item) for item in allowed}


def generate_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Tokens are stored hashed, never in clear.

    A leaked database dump then yields no usable credentials: an attacker would
    have to reverse SHA-256 to get a token worth replaying.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(token: str, token_hash: str) -> bool:
    """Constant-time comparison, so timing cannot be used to guess a token."""
    return hmac.compare_digest(hash_token(token), token_hash)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def expiry_from(now: datetime, *, minutes: int = 0, days: int = 0) -> datetime:
    return now + timedelta(minutes=minutes, days=days)


def _as_aware(moment: datetime) -> datetime:
    """Postgres can hand back naive datetimes; treat those as UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def is_expired(expires_at: datetime, now: datetime | None = None) -> bool:
    return _as_aware(expires_at) <= (now or utcnow())


@dataclass(frozen=True)
class LoginTokenState:
    """The two facts that decide whether a magic link still opens a session."""

    expires_at: datetime
    used_at: datetime | None

    def check(self, now: datetime | None = None) -> None:
        moment = now or utcnow()
        if self.used_at is not None:
            # ⚠️ The message says what to do, not just what went wrong.
            # "Already used" almost always means it was opened in a browser
            # while the app was waiting for it — and without that sentence the
            # next attempt is the same attempt.
            raise InvalidToken(
                "Questo link è già stato usato. Se hai l'app installata, "
                "chiedine un altro e copialo invece di aprirlo."
            )
        if is_expired(self.expires_at, moment):
            raise InvalidToken("Il link è scaduto")


@dataclass(frozen=True)
class SessionState:
    expires_at: datetime
    revoked_at: datetime | None

    def is_active(self, now: datetime | None = None) -> bool:
        moment = now or utcnow()
        if self.revoked_at is not None:
            return False
        return not is_expired(self.expires_at, moment)


def rate_limit_exceeded(recent_requests: int, ceiling: int) -> bool:
    """Guard on the number of links already sent to one address this hour.

    Without it anyone who knows the URL can drain the daily email quota.
    """
    return recent_requests >= ceiling


def build_magic_link(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/accedi/conferma?token={token}"
