"""Magic-link authentication.

The two rules that shape this module:

1. /request-link always answers the same thing. Telling an unknown address that
   it is unknown would turn the endpoint into a way to discover who has access.
2. /verify is a POST, never a GET. Mail providers open links to scan them, and a
   GET would let a scanner spend the single-use token before the recipient ever
   clicked it. The emailed URL points at a frontend page that issues this POST
   from JavaScript, which scanners do not run.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session as DbSession

from app.api.deps import SESSION_COOKIE, CurrentUserDep, DbDep, SettingsDep
from app.config import Settings
from app.domain import auth as domain
from app.mail.sender import EmailNotSent, send_magic_link
from app.models import Household, LoginToken, Session, User
from app.schemas.auth import LinkRequest, LinkRequested, VerifyRequest
from app.schemas.user import UpdateProfile, UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/request-link", response_model=LinkRequested)
def request_link(payload: LinkRequest, db: DbDep, settings: SettingsDep) -> LinkRequested:
    email = domain.normalize_email(payload.email)

    # Every early return below is identical from the outside. Only the logs
    # distinguish them, and the logs are not public.
    if not domain.is_allowed(email, settings.allowed_emails):
        logger.info("Richiesta di accesso per un indirizzo non abilitato")
        return LinkRequested()

    user = _get_or_create_user(db, email)

    recent = db.scalar(
        select(func.count(LoginToken.id)).where(
            LoginToken.user_id == user.id,
            LoginToken.created_at >= domain.utcnow() - timedelta(hours=1),
        )
    )
    if domain.rate_limit_exceeded(recent or 0, settings.login_requests_per_hour):
        logger.warning("Rate limit raggiunto per l'utente %s", user.id)
        return LinkRequested()

    token = domain.generate_token()
    db.add(
        LoginToken(
            user_id=user.id,
            token_hash=domain.hash_token(token),
            expires_at=domain.expiry_from(
                domain.utcnow(), minutes=settings.login_token_ttl_minutes
            ),
        )
    )
    db.commit()

    try:
        send_magic_link(
            settings,
            to=email,
            link=domain.build_magic_link(settings.app_base_url, token),
        )
    except EmailNotSent as exc:
        # The caller still gets the neutral message, but this must not pass
        # silently: without the log a broken API key looks like a lost email.
        logger.error("Invio del link fallito: %s", exc)

    return LinkRequested()


@router.post("/verify", response_model=UserProfile)
def verify(
    payload: VerifyRequest, response: Response, db: DbDep, settings: SettingsDep
) -> UserProfile:
    record = db.scalar(
        select(LoginToken).where(LoginToken.token_hash == domain.hash_token(payload.token))
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link non valido")

    try:
        domain.LoginTokenState(expires_at=record.expires_at, used_at=record.used_at).check()
    except domain.InvalidToken as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    now = domain.utcnow()
    record.used_at = now

    session_token = domain.generate_token()
    db.add(
        Session(
            user_id=record.user_id,
            token_hash=domain.hash_token(session_token),
            expires_at=domain.expiry_from(now, days=settings.session_ttl_days),
            last_used_at=now,
        )
    )

    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link non valido")
    user.last_seen_at = now
    db.commit()

    _set_session_cookie(response, session_token, settings)
    return _to_schema(db, user)


@router.get("/me", response_model=UserProfile)
def me(user: CurrentUserDep, db: DbDep) -> UserProfile:
    return _to_schema(db, user)


@router.patch("/me", response_model=UserProfile)
def update_me(payload: UpdateProfile, user: CurrentUserDep, db: DbDep) -> UserProfile:
    """Partial update of the signed-in user's own profile.

    Only fields actually present in the request body are touched, which is what
    keeps `display_name: null` ("drop my name, show my email again") distinct
    from leaving the key out ("do not touch it").
    """
    provided = payload.model_fields_set

    if "display_name" in provided:
        user.display_name = payload.display_name

    if "preferences" in provided and payload.preferences is not None:
        # Merge rather than replace: a screen that saves one setting must not
        # wipe the ones it does not know about.
        user.preferences = {**user.preferences, **payload.preferences.model_dump()}

    db.commit()
    db.refresh(user)
    return _to_schema(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    user: CurrentUserDep,
    db: DbDep,
    settings: SettingsDep,
    wallet_session: Annotated[str | None, Cookie()] = None,
) -> None:
    """Revoke this browser's session only."""
    if wallet_session:
        db.execute(
            update(Session)
            .where(Session.token_hash == domain.hash_token(wallet_session))
            .values(revoked_at=domain.utcnow())
        )
        db.commit()
    _clear_session_cookie(response, settings)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    response: Response, user: CurrentUserDep, db: DbDep, settings: SettingsDep
) -> None:
    """Esci da tutti i dispositivi: revokes every session this user holds.

    The first thing to reach for if a phone goes missing. The session lasts 30
    days, and this is a large part of what makes accepting that safe.
    """
    db.execute(
        update(Session)
        .where(Session.user_id == user.id, Session.revoked_at.is_(None))
        .values(revoked_at=domain.utcnow())
    )
    db.commit()
    _clear_session_cookie(response, settings)


def _get_or_create_user(db: DbSession, email: str) -> User:
    """First sign-in of an allowed address joins the one household."""
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        return user

    household = db.scalar(select(Household).order_by(Household.id).limit(1))
    if household is None:
        # Only reachable if the seed migration was skipped; better to create it
        # than to refuse a legitimate login.
        household = Household(name="Wallet")
        db.add(household)
        db.flush()

    user = User(household_id=household.id, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _to_schema(db: DbSession, user: User) -> UserProfile:
    household = db.get(Household, user.household_id)
    return UserProfile(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        label=user.label,
        preferences=user.preferences or {},
        household_id=user.household_id,
        household_name=household.name if household else "",
    )


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        httponly=True,
        # Secure only in production: over plain http://localhost the browser
        # would drop the cookie and local development would be impossible.
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
