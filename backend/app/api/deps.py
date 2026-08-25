"""Shared FastAPI dependencies: a database session, and the caller's identity."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import Settings, get_settings
from app.db import get_session_factory
from app.domain import auth as domain
from app.models import Session, User

SESSION_COOKIE = "wallet_session"


def get_db() -> Iterator[DbSession]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


DbDep = Annotated[DbSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def current_user(
    db: DbDep,
    settings: SettingsDep,
    wallet_session: Annotated[str | None, Cookie()] = None,
) -> User:
    """Resolve the session cookie to a user, or refuse with 401.

    Also slides the expiry forward: any use of the app renews the 30 days, so an
    account you open every day is never logged out, while an abandoned session
    still dies on schedule.
    """
    if not wallet_session:
        raise _unauthorized()

    record = db.scalar(
        select(Session).where(Session.token_hash == domain.hash_token(wallet_session))
    )
    if record is None:
        raise _unauthorized()

    state = domain.SessionState(
        expires_at=record.expires_at, revoked_at=record.revoked_at
    )
    now = domain.utcnow()
    if not state.is_active(now):
        raise _unauthorized()

    record.last_used_at = now
    record.expires_at = domain.expiry_from(now, days=settings.session_ttl_days)

    user = db.get(User, record.user_id)
    if user is None:
        raise _unauthorized()
    user.last_seen_at = now
    db.commit()

    return user


CurrentUserDep = Annotated[User, Depends(current_user)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessione non valida",
    )
