"""Shared plumbing for the maintenance scripts.

Three things live here because getting any of them wrong costs real data:

  - **which database you are about to touch**, printed before anything happens;
  - **the dry run**, which is the default everywhere and has to be opted out of;
  - **the confirmation** in front of the two irreversible commands.

These scripts exist so that the most delicate operations do not have to be done
by hand in the Neon console, which is the place with the least safety net.
"""

from __future__ import annotations

import sys
from urllib.parse import urlsplit

# ⚠️ These scripts print Italian — accents, and «guillemets» around names — and
# on Windows the default console encoding is cp1252, which turns half of that
# into question marks. Asking for UTF-8 costs nothing on a console that already
# speaks it and fixes the one that does not; `replace` means a stubborn terminal
# still gets readable output instead of a crash while it is deleting rows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.models import Household


class Abort(RuntimeError):
    """Something is wrong enough that the script should stop and say so."""


def target_database() -> str:
    """"ep-xxx.eu-central-1.aws.neon.tech / neondb", never the password.

    Printed by every script before it does anything. It is the guard against
    the one mistake that has no undo: being somewhere else than you thought.
    """
    url = get_settings().database_url
    if not url:
        raise Abort("DATABASE_URL non è configurata")

    parts = urlsplit(url)
    name = parts.path.lstrip("/") or "?"
    return f"{parts.hostname or '?'} / {name}"


def plural(count: int, one: str, many: str) -> str:
    """"1 conto" and "5 conti" — these strings are read by a person."""
    return f"{count} {one if count == 1 else many}"


def announce(what: str) -> None:
    print(f"database: {target_database()}")
    print(what)
    print()


def single_household(db: DbSession) -> Household:
    """The one space.

    The model allows several on purpose — it stays honest, and the day the app
    is shared nothing has to move — but the product has exactly one, and a
    script that silently picked the first of many would be a script that edits
    the wrong data.
    """
    households = list(db.scalars(select(Household).order_by(Household.id)).all())
    if not households:
        raise Abort(
            "Nessuno household a database: la migrazione iniziale non è stata applicata?"
        )
    if len(households) > 1:
        names = ", ".join(f"{h.id}:{h.name}" for h in households)
        raise Abort(f"Più di uno household ({names}): questi script ne assumono uno solo")
    return households[0]


class DryRun:
    """Says what would happen, and only does it when told to.

    The default is to do nothing. A destructive command typed in a hurry should
    cost a printout, not a restore from backup — and you get to read the damage
    before agreeing to it.
    """

    def __init__(self, apply: bool) -> None:
        self.apply = apply
        self._planned: list[str] = []

    def note(self, line: str) -> None:
        """Record something that will happen (or would have)."""
        self._planned.append(line)
        print(f"  {line}")

    @property
    def empty(self) -> bool:
        return not self._planned

    def finish(self, db: DbSession) -> None:
        """Commit, or explain how to."""
        print()
        if self.empty:
            print("Niente da fare.")
            return

        if self.apply:
            db.commit()
            print("Fatto.")
        else:
            db.rollback()
            print("Prova a vuoto: niente è stato scritto.")
            print("Per eseguire davvero, aggiungi --apply")


def header(apply: bool, title: str) -> None:
    announce(title if apply else f"{title}\nPROVA A VUOTO — niente verrà scritto")


def confirm(household: Household, yes: bool) -> None:
    """The extra step in front of the irreversible ones.

    Dry-run already protects against a slip; this protects against meaning it
    and being wrong anyway. Typing the name is short enough not to be theatre
    and long enough to interrupt.
    """
    if yes:
        return
    if not sys.stdin.isatty():
        raise Abort("Conferma richiesta: rilancia in un terminale, oppure aggiungi --yes")

    print(f'Scrivi "{household.name}" per confermare, o invio per annullare.')
    if input("> ").strip() != household.name:
        raise Abort("Annullato.")


def run(main) -> None:
    """Turn an Abort into a clean message and a non-zero exit."""
    try:
        main()
    except Abort as stop:
        print(f"\n{stop}", file=sys.stderr)
        raise SystemExit(1) from stop
