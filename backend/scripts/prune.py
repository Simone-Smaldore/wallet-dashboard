"""Throw away what is dead: spent links, closed sessions, unused archives.

    cd backend && python -m scripts.prune
    cd backend && python -m scripts.prune --apply

⚠️ **Nothing here touches a movement, an account or a category that is in use.**
This script only removes rows whose whole purpose is already over: a magic link
that was used or has expired, a session that was revoked or has run out, and an
archived account or category that no movement points at any more.

An archived account or category that *is* still referenced stays, and stays
forever: it is the label on a past movement, and deleting it would leave a chart
of 2025 with a hole in it.
"""

from __future__ import annotations

import argparse

from sqlalchemy import func, or_, select

from app.db import get_session_factory
from app.domain.auth import utcnow
from app.models import Account, Category, LoginToken, Session, Transaction
from scripts._common import DryRun, header, plural, run, single_household


def main() -> None:
    parser = argparse.ArgumentParser(description="Toglie token, sessioni e archivi morti")
    parser.add_argument("--apply", action="store_true", help="esegui davvero")
    args = parser.parse_args()

    header(args.apply, "Pulizia")

    db = get_session_factory()()
    try:
        household = single_household(db)
        plan = DryRun(args.apply)
        now = utcnow()

        # --- login links -------------------------------------------------
        # A used one is spent; an expired one can no longer be used either.
        # Both are kept for a while by the rate limiter, which counts recent
        # rows — so this is deliberately run by hand and not on a timer.
        tokens = list(
            db.scalars(
                select(LoginToken).where(
                    or_(LoginToken.used_at.is_not(None), LoginToken.expires_at < now)
                )
            )
        )
        if tokens:
            plan.note(f"cancello {plural(len(tokens), 'link di accesso', 'link di accesso')} usati o scaduti")
            for token in tokens:
                db.delete(token)

        # --- sessions ----------------------------------------------------
        sessions = list(
            db.scalars(
                select(Session).where(
                    or_(Session.revoked_at.is_not(None), Session.expires_at < now)
                )
            )
        )
        if sessions:
            plan.note(f"cancello {plural(len(sessions), 'sessione chiusa', 'sessioni chiuse')}")
            for session in sessions:
                db.delete(session)

        # --- archived and unused ------------------------------------------
        for account in db.scalars(
            select(Account).where(
                Account.household_id == household.id, Account.is_archived.is_(True)
            )
        ):
            used = db.scalar(
                select(func.count())
                .select_from(Transaction)
                .where(
                    or_(
                        Transaction.account_id == account.id,
                        Transaction.counter_account_id == account.id,
                    )
                )
            )
            if used:
                # It is the label on money that moved. It stays.
                continue
            plan.note(f"cancello il conto archiviato «{account.name}», non usato da nessun movimento")
            db.delete(account)

        for category in db.scalars(
            select(Category).where(
                Category.household_id == household.id, Category.is_archived.is_(True)
            )
        ):
            used = db.scalar(
                select(func.count())
                .select_from(Transaction)
                .where(Transaction.category_id == category.id)
            )
            if used:
                continue
            plan.note(
                f"cancello la categoria archiviata «{category.name}», non usata da nessun movimento"
            )
            db.delete(category)

        plan.finish(db)
    finally:
        db.close()


if __name__ == "__main__":
    run(main)
