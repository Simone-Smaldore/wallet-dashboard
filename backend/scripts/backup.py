"""Export everything to a JSON file you can keep.

⚠️ **This is the script that matters most in this project.** The Neon free tier
does not hold backups for long, and what is in here cannot be rebuilt: last
March's spending does not exist anywhere else, except partly in a bank statement
the app cannot read. A recipe you can retype. A year of movements you cannot.

    cd backend && python -m scripts.backup
    cd backend && python -m scripts.backup --out ~/Desktop/wallet.json

Read-only: it never writes to the database, so there is no dry run to speak of.
Run it on a real cadence — the first of the month, with the balance check.

⚠️ **Sessions and login tokens are deliberately not in the file.** They are
secrets, and restoring them would mean resurrecting logins that were closed.
Everything else is here, including the user, so the name and preferences come
back too.

⚠️ The file holds every movement and every balance, plus the email address.
`backup-*.json` is in .gitignore; if you rename it, do not rename it out of that
rule.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

from app.db import get_session_factory
from app.models import Account, Category, Household, Transaction, User
from scripts._common import announce, run, single_household

#: Bumped when the shape changes, so `restore` can refuse a file it cannot read
#: rather than guessing at it.
FORMAT_VERSION = 1


def _plain(value):
    """JSON has no dates; keep them lossless as ISO strings."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _row(obj, *fields: str) -> dict:
    return {field: _plain(getattr(obj, field)) for field in fields}


def collect(db, household: Household) -> dict:
    return {
        "format_version": FORMAT_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "household": _row(household, "id", "name"),
        "users": [
            _row(user, "id", "email", "display_name", "preferences", "last_seen_at")
            for user in db.scalars(
                select(User).where(User.household_id == household.id)
            ).all()
        ],
        "accounts": [
            _row(
                account,
                "id",
                "name",
                "kind",
                "opening_balance_cents",
                "opening_date",
                "include_in_net_worth",
                "position",
                "is_archived",
            )
            for account in db.scalars(
                select(Account).where(Account.household_id == household.id)
            ).all()
        ],
        "categories": [
            _row(
                category,
                "id",
                "name",
                "kind",
                "color",
                "icon",
                "position",
                "is_archived",
            )
            for category in db.scalars(
                select(Category).where(Category.household_id == household.id)
            ).all()
        ],
        "transactions": [
            _row(
                movement,
                "id",
                "date",
                "kind",
                "amount_cents",
                "account_id",
                "counter_account_id",
                "category_id",
                "description",
                "is_adjustment",
            )
            for movement in db.scalars(
                select(Transaction)
                .where(Transaction.household_id == household.id)
                .order_by(Transaction.date, Transaction.id)
            ).all()
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Esporta tutto in un file JSON")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="dove scrivere; per default backup-AAAA-MM-GG.json nella cartella corrente",
    )
    args = parser.parse_args()

    announce("Backup in sola lettura")

    db = get_session_factory()()
    try:
        household = single_household(db)
        data = collect(db, household)
    finally:
        db.close()

    destination = args.out or Path(f"backup-{date.today().isoformat()}.json")
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    size = destination.stat().st_size / 1024
    print(f"Scritto {destination} ({size:.0f} KB)")
    for label, key in (
        ("conti", "accounts"),
        ("categorie", "categories"),
        ("movimenti", "transactions"),
        ("utenti", "users"),
    ):
        print(f"  {len(data[key]):>5} {label}")


if __name__ == "__main__":
    run(main)
