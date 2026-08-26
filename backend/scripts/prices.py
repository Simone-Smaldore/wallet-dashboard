"""Fetch today's prices and write down what came back.

    cd backend && python -m scripts.prices
    cd backend && python -m scripts.prices --apply

The same code the daily cron runs, so what you see here is what happens at
night — no second implementation to drift.

⚠️ **A source that does not answer changes nothing.** The line says so and the
previous valuation stays with its own date. That is the failure this whole
mechanism is built around: a scraper does not betray you by breaking loudly, it
betrays you by standing still while you believe it is keeping up.
"""

from __future__ import annotations

import argparse

from app.db import get_session_factory
from app.prices.refresh import refresh
from scripts._common import DryRun, header, run, single_household


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggiorna i prezzi degli investimenti")
    parser.add_argument("--apply", action="store_true", help="scrivi le valutazioni")
    args = parser.parse_args()

    header(args.apply, "Prezzi degli investimenti")

    db = get_session_factory()()
    try:
        household = single_household(db)
        plan = DryRun(args.apply)

        # ⚠️ The fetches happen either way: a dry run that skipped them would
        # tell you nothing about the only part that can fail.
        outcomes = refresh(db, household.id)
        if not outcomes:
            print("Nessun asset da aggiornare.")
            return

        for outcome in outcomes:
            plan.note(f"{'✓' if outcome.ok else '✗'} {outcome.asset}: {outcome.detail}")

        failed = [o for o in outcomes if not o.ok]
        if failed:
            print()
            print(f"⚠️  {len(failed)} senza prezzo: le valutazioni precedenti restano.")

        plan.finish(db)
    finally:
        db.close()


if __name__ == "__main__":
    run(main)
