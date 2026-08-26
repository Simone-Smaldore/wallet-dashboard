"""Who has been in, and how to throw a session out.

    cd backend && python -m scripts.users
    cd backend && python -m scripts.users --logout simone@example.com --apply
    cd backend && python -m scripts.users --logout-all --apply
    cd backend && python -m scripts.users --forget simone@example.com --apply

`--logout-all` is the one to run first if a phone goes missing.

⚠️ **This script does not decide who can get in.** That is `ALLOWED_EMAILS`, an
environment variable on Vercel. Deleting a row here closes nothing: the next
magic link recreates it. To take access away, take the address out of
`ALLOWED_EMAILS` — and then revoke the sessions here, because a session already
open keeps working until it expires.

Revoking is the same UPDATE the app runs for "esci da tutti i dispositivi",
which is the whole reason sessions are opaque tokens rather than JWTs.
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.config import get_settings
from app.db import get_session_factory
from app.domain.auth import normalize_email, utcnow
from app.models import LoginToken, Session, User
from scripts._common import Abort, DryRun, announce, plural, run


def main() -> None:
    parser = argparse.ArgumentParser(description="Accessi e sessioni")
    parser.add_argument("--logout", metavar="EMAIL", help="chiude tutte le sue sessioni")
    parser.add_argument(
        "--logout-all", action="store_true", help="chiude le sessioni di chiunque"
    )
    parser.add_argument(
        "--forget", metavar="EMAIL", help="cancella la riga dell'utente (non l'accesso)"
    )
    parser.add_argument("--apply", action="store_true", help="esegui davvero")
    args = parser.parse_args()

    announce("Utenti e sessioni")

    allowed = get_settings().allowed_emails
    print("Chi può entrare (ALLOWED_EMAILS, dall'ambiente):")
    for address in allowed or ["— nessuno configurato —"]:
        print(f"  {address}")
    print()

    db = get_session_factory()()
    try:
        now = utcnow()
        users = list(db.scalars(select(User).order_by(User.id)))

        if not users:
            print("Nessun utente ha ancora fatto accesso.")
        else:
            print("Chi ha una riga a database:")
            for user in users:
                sessions = list(db.scalars(select(Session).where(Session.user_id == user.id)))
                active = [
                    s for s in sessions if s.revoked_at is None and s.expires_at > now
                ]
                seen = user.last_seen_at.date().isoformat() if user.last_seen_at else "mai"
                mark = "" if user.email in allowed else "  ⚠️ non è in ALLOWED_EMAILS"
                print(
                    f"  {user.email} — ultimo accesso {seen}, "
                    f"{plural(len(active), 'sessione attiva', 'sessioni attive')}"
                    f" su {len(sessions)}{mark}"
                )
        print()

        if not (args.logout or args.logout_all or args.forget):
            return

        plan = DryRun(args.apply)

        if args.logout_all:
            _close(db, plan, None, now)
        if args.logout:
            _close(db, plan, _find(db, args.logout), now)

        if args.forget:
            user = _find(db, args.forget)
            # ⚠️ Sessions first and explicitly, not by CASCADE: this has to
            # behave the same on SQLite and on Postgres.
            _close(db, plan, user, now)
            plan.note(
                f"cancello la riga di {user.email}"
                " — ⚠️ non chiude l'accesso: togli l'indirizzo da ALLOWED_EMAILS,"
                " o il prossimo magic link la ricrea"
            )
            for session in db.scalars(select(Session).where(Session.user_id == user.id)):
                db.delete(session)
            for token in db.scalars(select(LoginToken).where(LoginToken.user_id == user.id)):
                db.delete(token)
            db.delete(user)

        plan.finish(db)
    finally:
        db.close()


def _find(db, address: str) -> User:
    email = normalize_email(address)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise Abort(f"Nessun utente con indirizzo {email}")
    return user


def _close(db, plan: DryRun, user: User | None, now) -> None:
    """Revoke open sessions — everyone's, or one person's.

    The same UPDATE the app runs for "esci da tutti i dispositivi", which is the
    whole reason a session is an opaque token and not a JWT: a JWT would need a
    revocation list, which is this table with extra steps.
    """
    query = select(Session).where(Session.revoked_at.is_(None))
    if user is not None:
        query = query.where(Session.user_id == user.id)

    closed = 0
    for session in db.scalars(query):
        session.revoked_at = now
        closed += 1

    who = user.email if user is not None else "tutti"
    if closed:
        plan.note(f"chiudo {plural(closed, 'sessione', 'sessioni')} di {who}")
    else:
        print(f"Nessuna sessione aperta per {who}.")


if __name__ == "__main__":
    run(main)
