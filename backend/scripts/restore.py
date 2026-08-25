"""Put a backup back.

    cd backend && python -m scripts.restore backup-2026-08-25.json
    cd backend && python -m scripts.restore backup-2026-08-25.json --apply

⚠️ **It replaces, it does not merge.** Everything is emptied and rebuilt from
the file. A backup is for getting back on your feet after a disaster, not for
reconciling two states — and reconciliation is exactly where this kind of script
goes wrong quietly, duplicating movements nobody notices until a total stops
making sense.

The ids inside the file mean nothing on another database and are all remapped;
the user is matched by email.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select

from app.db import get_session_factory
from app.models import Account, Category, Household, Transaction, User
from scripts._common import Abort, DryRun, confirm, header, plural, run, single_household

SUPPORTED_VERSION = 1


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Rimette un backup, sostituendo tutto")
    parser.add_argument("file", type=Path, help="il file JSON prodotto da scripts.backup")
    parser.add_argument("--apply", action="store_true", help="esegui davvero")
    parser.add_argument("--yes", action="store_true", help="salta la conferma scritta")
    args = parser.parse_args()

    if not args.file.exists():
        raise Abort(f"File non trovato: {args.file}")

    data = json.loads(args.file.read_text(encoding="utf-8"))
    version = data.get("format_version")
    if version != SUPPORTED_VERSION:
        # Refuse rather than guess: a file from a future shape restored by an
        # older reader is how you lose the columns it did not know about.
        raise Abort(
            f"Formato {version} non supportato da questo script (attende {SUPPORTED_VERSION})"
        )

    header(args.apply, f"Ripristino da {args.file.name}")

    db = get_session_factory()()
    try:
        household = single_household(db)
        plan = DryRun(args.apply)

        plan.note(f"svuoto conti, categorie e movimenti di «{household.name}»")
        plan.note(f"ripristino {plural(len(data['accounts']), 'conto', 'conti')}")
        plan.note(
            f"ripristino {plural(len(data['categories']), 'categoria', 'categorie')}"
        )
        plan.note(
            f"ripristino {plural(len(data['transactions']), 'movimento', 'movimenti')}"
        )

        if args.apply:
            confirm(household, args.yes)

            # Order matters and is explicit: movements point at accounts and
            # categories, so they go first. Relying on CASCADE would behave
            # differently on SQLite and on Postgres, which is precisely the
            # situation this ordering exists to avoid.
            db.execute(delete(Transaction).where(Transaction.household_id == household.id))
            db.execute(delete(Account).where(Account.household_id == household.id))
            db.execute(delete(Category).where(Category.household_id == household.id))
            db.flush()

            _restore(db, household, data)

        plan.finish(db)
    finally:
        db.close()


def _restore(db, household: Household, data: dict) -> None:
    accounts: dict[int, int] = {}
    for row in data["accounts"]:
        account = Account(
            household_id=household.id,
            name=row["name"],
            kind=row["kind"],
            opening_balance_cents=row["opening_balance_cents"],
            opening_date=_date(row["opening_date"]),
            include_in_net_worth=row["include_in_net_worth"],
            position=row["position"],
            is_archived=row["is_archived"],
        )
        db.add(account)
        db.flush()
        accounts[row["id"]] = account.id

    categories: dict[int, int] = {}
    for row in data["categories"]:
        category = Category(
            household_id=household.id,
            name=row["name"],
            kind=row["kind"],
            color=row["color"],
            icon=row["icon"],
            position=row["position"],
            is_archived=row["is_archived"],
        )
        db.add(category)
        db.flush()
        categories[row["id"]] = category.id

    for row in data["transactions"]:
        db.add(
            Transaction(
                household_id=household.id,
                date=_date(row["date"]),
                kind=row["kind"],
                amount_cents=row["amount_cents"],
                account_id=accounts[row["account_id"]],
                counter_account_id=(
                    accounts[row["counter_account_id"]]
                    if row["counter_account_id"] is not None
                    else None
                ),
                category_id=(
                    categories[row["category_id"]]
                    if row["category_id"] is not None
                    else None
                ),
                description=row["description"],
                is_adjustment=row["is_adjustment"],
            )
        )

    # Users are matched by email rather than recreated: the row that is already
    # here owns the sessions, and replacing it would sign you out of the app you
    # are restoring from.
    for row in data.get("users", []):
        user = db.scalar(select(User).where(User.email == row["email"]))
        if user is None:
            db.add(
                User(
                    household_id=household.id,
                    email=row["email"],
                    display_name=row["display_name"],
                    preferences=row["preferences"] or {},
                )
            )
        else:
            user.display_name = row["display_name"]
            user.preferences = row["preferences"] or {}

    db.flush()


if __name__ == "__main__":
    run(main)
