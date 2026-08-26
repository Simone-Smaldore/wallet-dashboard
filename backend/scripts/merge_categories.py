"""Fold one category into another.

    cd backend && python -m scripts.merge_categories "Spesa" "Supermercato"
    cd backend && python -m scripts.merge_categories "Spesa" "Supermercato" --apply

Every movement filed under the first moves to the second, and the first is
archived. Names, case-insensitive, or ids if two names collide.

⚠️ **The app deliberately cannot do this.** Merging is rare, irreversible
without a backup, and easy to trigger by accident from a list of tappable rows —
so it lives here, behind a dry run, instead of behind a menu on a phone.

⚠️ **Two categories of different signs are refused.** Folding "Stipendio" into
"Spesa" would move amounts from one side of every chart to the other, and there
is no reading of that request that is what someone meant.

The source is archived rather than deleted: `prune` removes it once nothing
points at it, and until then it is still the label on the movements you just
moved — the history stays readable while you check the merge did what you
wanted.
"""

from __future__ import annotations

import argparse

from sqlalchemy import func, select

from app.db import get_session_factory
from app.models import Category, Transaction
from scripts._common import Abort, DryRun, header, plural, run, single_household


def find(db, household_id: int, needle: str) -> Category:
    """By id if it is a number, otherwise by name, case-insensitively."""
    if needle.isdigit():
        category = db.get(Category, int(needle))
        if category is not None and category.household_id == household_id:
            return category
        raise Abort(f"Nessuna categoria con id {needle}")

    matches = list(
        db.scalars(
            select(Category).where(
                Category.household_id == household_id,
                func.lower(Category.name) == needle.strip().lower(),
            )
        )
    )
    if not matches:
        raise Abort(f"Nessuna categoria chiamata «{needle}»")
    if len(matches) > 1:
        # The same name on the two lists is legal — "Regalo" bought and
        # received — so this is a real case, not a corrupt one.
        which = ", ".join(f"{c.id} ({c.kind})" for c in matches)
        raise Abort(f"«{needle}» esiste su entrambe le liste: usa l'id — {which}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fonde due categorie")
    parser.add_argument("source", help="la categoria da svuotare (nome o id)")
    parser.add_argument("target", help="la categoria che riceve (nome o id)")
    parser.add_argument("--apply", action="store_true", help="esegui davvero")
    args = parser.parse_args()

    header(args.apply, "Fusione di categorie")

    db = get_session_factory()()
    try:
        household = single_household(db)
        source = find(db, household.id, args.source)
        target = find(db, household.id, args.target)

        if source.id == target.id:
            raise Abort("Sono la stessa categoria")

        if source.kind != target.kind:
            raise Abort(
                f"«{source.name}» è {source.kind} e «{target.name}» è {target.kind}: "
                "fonderle sposterebbe degli importi da una parte all'altra di ogni grafico"
            )

        movements = list(
            db.scalars(select(Transaction).where(Transaction.category_id == source.id))
        )

        plan = DryRun(args.apply)
        plan.note(
            f"sposto {plural(len(movements), 'movimento', 'movimenti')} "
            f"da «{source.name}» a «{target.name}»"
        )
        if not source.is_archived:
            plan.note(f"archivio «{source.name}»")

        if args.apply:
            for movement in movements:
                movement.category_id = target.id
            source.is_archived = True
            if household.salary_category_id == source.id:
                # The household pointed at the category being emptied; it has to
                # follow the movements, or the salary cycle silently stops
                # finding any salary at all.
                plan.note(f"lo stipendio ora punta a «{target.name}»")
                household.salary_category_id = target.id
            db.flush()

        plan.finish(db)
    finally:
        db.close()


if __name__ == "__main__":
    run(main)
