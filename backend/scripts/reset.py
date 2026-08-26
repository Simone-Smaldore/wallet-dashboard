"""Empty the database, in levels.

    cd backend && python -m scripts.reset --transactions
    cd backend && python -m scripts.reset --categories
    cd backend && python -m scripts.reset --accounts
    cd backend && python -m scripts.reset --all --apply

⚠️ **Run `backup` first.** Last March's spending does not exist anywhere else.

⚠️ **The levels are nested, and the script says so before doing anything.** An
account cannot be deleted while a movement names it, and a movement with no
account means nothing — so `--accounts` takes the movements with it, and
`--categories` does too. Being told this after the fact is how you lose a year
of data believing you were clearing a list of labels.

⚠️ **Deletions are explicit, never left to the database's CASCADE.** The tests
run on SQLite, which does not enforce foreign keys unless told to, and
production is Postgres: a wipe that leaned on the database would behave
differently in the two places, and the difference would only show up here.
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db import get_session_factory
from app.models import Account, Category, Household, Transaction, User
from scripts._common import Abort, DryRun, confirm, header, plural, run, single_household


def main() -> None:
    parser = argparse.ArgumentParser(description="Svuota il database, a livelli")
    parser.add_argument("--transactions", action="store_true", help="solo i movimenti")
    parser.add_argument(
        "--categories", action="store_true", help="categorie e i movimenti che le usano"
    )
    parser.add_argument(
        "--accounts", action="store_true", help="conti, categorie e tutti i movimenti"
    )
    parser.add_argument("--all", action="store_true", help="tutto, utenti compresi")
    parser.add_argument("--apply", action="store_true", help="esegui davvero")
    parser.add_argument("--yes", action="store_true", help="salta la conferma scritta")
    args = parser.parse_args()

    levels = [args.transactions, args.categories, args.accounts, args.all]
    if sum(levels) != 1:
        raise Abort(
            "Scegli un livello solo: --transactions, --categories, --accounts o --all"
        )

    header(args.apply, "Svuotamento")
    print("⚠️  Hai lanciato scripts.backup di recente?")
    print()

    db = get_session_factory()()
    try:
        household = single_household(db)
        plan = DryRun(args.apply)

        movements = _count(db, Transaction, household)
        categories = _count(db, Category, household)
        accounts = _count(db, Account, household)
        users = _count(db, User, household)

        # Everything above the chosen level goes too, and it is said out loud.
        wipe_movements = True
        wipe_categories = args.categories or args.accounts or args.all
        wipe_accounts = args.accounts or args.all
        wipe_users = args.all

        if wipe_movements and movements:
            plan.note(f"cancello {plural(movements, 'movimento', 'movimenti')}")
        if wipe_categories and categories:
            plan.note(
                f"cancello {plural(categories, 'categoria', 'categorie')}"
                " — e i movimenti qui sopra vanno con loro"
            )
        if wipe_accounts and accounts:
            plan.note(
                f"cancello {plural(accounts, 'conto', 'conti')}"
                " — un conto non si cancella finché un movimento lo nomina"
            )
        if wipe_users and users:
            plan.note(
                f"cancello {plural(users, 'utente', 'utenti')}"
                " — ⚠️ ma non l'accesso: quello è ALLOWED_EMAILS, e il prossimo"
                " magic link ricrea la riga"
            )

        # ⚠️ Only when actually applying. A dry run writes nothing, so asking it
        # to be confirmed would train the habit of typing the name without
        # reading — which is the one thing the confirmation exists to prevent.
        if args.apply and not plan.empty and (args.all or args.accounts):
            confirm(household, args.yes)

        if args.apply and not plan.empty:
            # Order matters and is written out rather than delegated: children
            # first, always.
            if wipe_movements:
                _delete_all(db, Transaction, household)
            if wipe_categories:
                # The household points at one of these; that pointer has to go
                # first or the delete is refused.
                household.salary_category_id = None
                db.flush()
                _delete_all(db, Category, household)
            if wipe_accounts:
                _delete_all(db, Account, household)
            if wipe_users:
                # Sessions and login links hang off the user and are cascaded by
                # the database here — but the user rows themselves are deleted
                # explicitly, like everything else.
                _delete_all(db, User, household)

        plan.finish(db)
    finally:
        db.close()


def _count(db, model, household: Household) -> int:
    return len(list(db.scalars(select(model.id).where(model.household_id == household.id))))


def _delete_all(db, model, household: Household) -> None:
    for row in db.scalars(select(model).where(model.household_id == household.id)):
        db.delete(row)
    db.flush()


if __name__ == "__main__":
    run(main)
