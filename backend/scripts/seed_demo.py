"""A few months of invented movements, to have charts to look at.

    cd backend && python -m scripts.seed_demo
    cd backend && python -m scripts.seed_demo --months 8 --apply

⚠️ **It refuses to run if there is already a movement.** This is the script for
building against, and run by mistake on the real database it would mix invented
spending into real spending with no way to tell them apart afterwards — every
total wrong forever, and no error message anywhere. The check is not a
convenience, it is the whole safety of the thing.

The numbers are deterministic: same seed, same data, so a chart that looked
wrong yesterday looks wrong the same way today.
"""

from __future__ import annotations

import argparse
import random
from datetime import date, timedelta

from sqlalchemy import func, select

from app.db import get_session_factory
from app.domain.period import month_of, shift_month
from app.domain.vocabulary import CategoryKind, TransactionKind
from app.models import Account, Category, Transaction
from scripts._common import Abort, DryRun, header, plural, run, single_household

#: Fixed, so two runs produce the same story.
SEED = 20260826

#: (category name, how many a month, cents from, cents to)
SPENDING = [
    ("Spesa", 8, 1_500, 9_000),
    ("Casa", 2, 3_000, 80_000),
    ("Trasporti", 5, 200, 4_000),
    ("Ristoranti", 4, 1_200, 6_500),
    ("Svago", 2, 800, 4_000),
    ("Salute", 1, 2_000, 12_000),
]

SALARY_CENTS = 185_000
SALARY_DAY = 27


def main() -> None:
    parser = argparse.ArgumentParser(description="Movimenti finti per avere grafici")
    parser.add_argument("--months", type=int, default=6, help="quanti mesi indietro")
    parser.add_argument("--apply", action="store_true", help="esegui davvero")
    args = parser.parse_args()

    header(args.apply, f"Dati di prova, {plural(args.months, 'mese', 'mesi')}")

    db = get_session_factory()()
    try:
        household = single_household(db)

        existing = db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.household_id == household.id)
        )
        if existing:
            raise Abort(
                f"Ci sono già {plural(existing, 'movimento', 'movimenti')} a database.\n"
                "Questo script scrive spese inventate e non c'è modo di distinguerle dopo:\n"
                "svuota con scripts.reset --transactions, oppure lancialo su un altro database."
            )

        accounts = list(
            db.scalars(select(Account).where(Account.household_id == household.id))
        )
        if not accounts:
            raise Abort("Nessun conto: creane almeno uno dall'app prima di seminare i dati")

        categories = {
            (category.kind, category.name.lower()): category
            for category in db.scalars(
                select(Category).where(Category.household_id == household.id)
            )
        }

        rng = random.Random(SEED)
        plan = DryRun(args.apply)
        rows: list[Transaction] = []

        main_account = accounts[0]
        today = date.today()
        first_month = shift_month(month_of(today).start, -(args.months - 1))

        for index in range(args.months):
            month = shift_month(first_month, index)
            span = month_of(month)

            salary_category = categories.get((CategoryKind.INCOME.value, "stipendio"))
            salary_day = min(SALARY_DAY, span.end.day)
            salary_date = month.replace(day=salary_day)
            if salary_date <= today:
                rows.append(
                    Transaction(
                        household_id=household.id,
                        kind=TransactionKind.INCOME.value,
                        date=salary_date,
                        # A little variation, so the salary cycle has something
                        # to compare against month to month.
                        amount_cents=SALARY_CENTS + rng.randrange(-5_000, 12_000, 100),
                        account_id=main_account.id,
                        category_id=salary_category.id if salary_category else None,
                        description="Stipendio",
                    )
                )

            for name, per_month, low, high in SPENDING:
                category = categories.get((CategoryKind.EXPENSE.value, name.lower()))
                for _ in range(rng.randint(max(1, per_month - 2), per_month + 2)):
                    when = span.start + timedelta(days=rng.randrange(span.days))
                    if when > today:
                        continue
                    rows.append(
                        Transaction(
                            household_id=household.id,
                            kind=TransactionKind.EXPENSE.value,
                            date=when,
                            amount_cents=rng.randrange(low, high, 50),
                            account_id=rng.choice(accounts).id,
                            category_id=category.id if category else None,
                            description=None,
                        )
                    )

            # One transfer a month, so the charts get to prove they ignore them.
            if len(accounts) > 1 and salary_date <= today:
                rows.append(
                    Transaction(
                        household_id=household.id,
                        kind=TransactionKind.TRANSFER.value,
                        date=salary_date + timedelta(days=1),
                        amount_cents=30_000,
                        account_id=main_account.id,
                        counter_account_id=accounts[1].id,
                        description="Verso il deposito",
                    )
                )

        plan.note(f"creo {plural(len(rows), 'movimento', 'movimenti')} finti")
        missing = [
            name for name, *_ in SPENDING
            if (CategoryKind.EXPENSE.value, name.lower()) not in categories
        ]
        if missing:
            plan.note(
                f"senza categoria (non esistono qui): {', '.join(missing)}"
            )

        if args.apply:
            db.add_all(rows)
            db.flush()

        plan.finish(db)
    finally:
        db.close()


if __name__ == "__main__":
    run(main)
