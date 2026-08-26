"""Check that the data still means what it is supposed to mean.

    cd backend && python -m scripts.doctor
    cd backend && python -m scripts.doctor --fix
    cd backend && python -m scripts.doctor --fix --apply

Read-only unless you ask for `--fix`, and even then a dry run until `--apply`.

⚠️ **`--fix` repairs only what is safe to repair**, which here means: only
changes where there is exactly one possible right answer and no money moves. A
transfer missing its second account has no single answer — which account? — so
it is reported and left alone. Guessing would be worse than the fault, because a
guess looks repaired.

The checks are pure functions over rows already loaded, so they can be tested
without a database. Same rule as domain/: the part that can be wrong is the part
that must be testable.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select, text

from app.db import get_session_factory
from app.domain.vocabulary import CategoryKind, TransactionKind
from app.models import Account, Category, Transaction
from scripts._common import DryRun, header, plural, run, single_household


@dataclass(frozen=True)
class Finding:
    """One thing that is wrong, and whether this script can put it right."""

    check: str
    detail: str
    #: True only when there is exactly one possible repair and it moves no money.
    fixable: bool = False
    transaction_id: int | None = None


@dataclass
class Row:
    """A movement, as the checks need to see it.

    A plain object rather than the ORM one so the checks stay callable from a
    test with no database behind them.
    """

    id: int
    kind: str
    amount_cents: int
    account_id: int
    counter_account_id: int | None
    category_id: int | None
    is_adjustment: bool
    date: object = None


@dataclass
class World:
    """What exists to point at."""

    accounts: set[int] = field(default_factory=set)
    #: category id -> kind ("expense" / "income")
    categories: dict[int, str] = field(default_factory=dict)


def check_migration(applied: str | None, head: str | None) -> list[Finding]:
    """Is the database on the migration this checkout expects?

    ⚠️ First check for a reason. A column the code selects and the database does
    not have is a 500 with a stack trace three screens long, and nothing in it
    says "run alembic upgrade head". This is the question that would have
    answered it in one line.
    """
    if head is None:
        return [Finding("migrazione", "non riesco a leggere le migrazioni del repository")]
    if applied is None:
        return [
            Finding(
                "migrazione",
                "il database non ha nessuna migrazione applicata — alembic upgrade head",
            )
        ]
    if applied != head:
        return [
            Finding(
                "migrazione",
                f"il database è a {applied}, il repository a {head} — alembic upgrade head",
            )
        ]
    return []


def check_similar_names(categories: list[tuple[str, str]]) -> list[Finding]:
    """Categories that are probably the same thing said twice.

    Not a fault, a suggestion: "Bar" and "Bar e caffè" are both legal and almost
    always one category. The database already refuses "Bar" and "bar" — that is
    the case that would silently split a pie in two.

    ⚠️ Only within the same sign. "Regalo" on both lists is a present you bought
    and money someone gave you, which is exactly the distinction the two lists
    exist to keep.
    """
    found: list[Finding] = []
    for index, (kind, name) in enumerate(categories):
        for other_kind, other in categories[index + 1 :]:
            if kind != other_kind:
                continue
            short, long = sorted((name.lower(), other.lower()), key=len)
            if long.startswith(short) and short != long:
                found.append(
                    Finding(
                        "doppioni",
                        f"«{name}» e «{other}» sembrano la stessa cosa "
                        "— scripts.merge_categories le fonde",
                    )
                )
    return found


def check(rows: list[Row], world: World) -> list[Finding]:
    """Every check, in one pass. Returns what is wrong, oldest row first."""
    findings: list[Finding] = []

    for row in rows:
        findings.extend(_check_row(row, world))

    return findings


def _check_row(row: Row, world: World) -> list[Finding]:
    found: list[Finding] = []

    if row.account_id not in world.accounts:
        found.append(
            Finding(
                "orfano",
                f"movimento {row.id}: il conto {row.account_id} non esiste",
                transaction_id=row.id,
            )
        )

    if row.amount_cents <= 0:
        # ⚠️ Zero is not a movement, it is a row that survived a bug. The sign
        # lives in `kind`, so a negative amount is not "money out" either — it
        # is a number that would subtract where every sum expects it to add.
        found.append(
            Finding(
                "importo",
                f"movimento {row.id}: importo {row.amount_cents}, deve essere > 0",
                transaction_id=row.id,
            )
        )

    if row.kind == TransactionKind.TRANSFER.value:
        if row.counter_account_id is None:
            found.append(
                Finding(
                    "trasferimento",
                    f"movimento {row.id}: trasferimento senza conto di destinazione",
                    transaction_id=row.id,
                )
            )
        elif row.counter_account_id == row.account_id:
            found.append(
                Finding(
                    "trasferimento",
                    f"movimento {row.id}: stesso conto ai due lati",
                    transaction_id=row.id,
                )
            )
        elif row.counter_account_id not in world.accounts:
            found.append(
                Finding(
                    "orfano",
                    f"movimento {row.id}: il conto {row.counter_account_id} non esiste",
                    transaction_id=row.id,
                )
            )

        if row.category_id is not None:
            # ⚠️ The rule the whole model rests on. Fixable, and safely: a
            # transfer has no category by definition, so clearing it is not a
            # choice between answers — it is the only answer.
            found.append(
                Finding(
                    "trasferimento",
                    f"movimento {row.id}: un trasferimento non ha categoria",
                    fixable=True,
                    transaction_id=row.id,
                )
            )

    elif row.counter_account_id is not None:
        found.append(
            Finding(
                "conto",
                f"movimento {row.id}: solo un trasferimento ha un secondo conto",
                transaction_id=row.id,
            )
        )

    if row.category_id is not None:
        kind = world.categories.get(row.category_id)
        if kind is None:
            found.append(
                Finding(
                    "orfano",
                    f"movimento {row.id}: la categoria {row.category_id} non esiste",
                    transaction_id=row.id,
                )
            )
        elif row.kind != TransactionKind.TRANSFER.value and kind != row.kind:
            # ⚠️ A spend filed under an income category, or the reverse. Not
            # fixable here: moving it to the right *list* would mean choosing a
            # category, and choosing one changes what a chart says.
            wanted = (
                CategoryKind.EXPENSE.value
                if row.kind == TransactionKind.EXPENSE.value
                else CategoryKind.INCOME.value
            )
            found.append(
                Finding(
                    "categoria",
                    f"movimento {row.id}: è {row.kind} ma la categoria è {kind} "
                    f"(dovrebbe essere {wanted})",
                    transaction_id=row.id,
                )
            )

    if row.is_adjustment and row.category_id is not None:
        found.append(
            Finding(
                "rettifica",
                f"movimento {row.id}: una rettifica non ha categoria",
                fixable=True,
                transaction_id=row.id,
            )
        )

    return found


def _applied_revision(db) -> str | None:
    try:
        return db.scalar(text("select version_num from alembic_version"))
    except Exception:
        # No table at all: the database has never been migrated.
        db.rollback()
        return None


def _head_revision() -> str | None:
    """The newest revision in the repository, read from Alembic itself."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        here = Path(__file__).resolve().parent.parent
        return ScriptDirectory.from_config(Config(str(here / "alembic.ini"))).get_current_head()
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlla lo stato dei dati")
    parser.add_argument("--fix", action="store_true", help="ripara quello che è sicuro")
    parser.add_argument("--apply", action="store_true", help="esegui davvero le riparazioni")
    args = parser.parse_args()

    header(args.apply or not args.fix, "Controllo dei dati")

    db = get_session_factory()()
    try:
        household = single_household(db)

        world = World(
            accounts={
                row for row in db.scalars(
                    select(Account.id).where(Account.household_id == household.id)
                )
            },
            categories=dict(
                db.execute(
                    select(Category.id, Category.kind).where(
                        Category.household_id == household.id
                    )
                ).all()
            ),
        )

        movements = db.scalars(
            select(Transaction)
            .where(Transaction.household_id == household.id)
            .order_by(Transaction.id)
        ).all()

        rows = [
            Row(
                id=m.id,
                kind=m.kind,
                amount_cents=m.amount_cents,
                account_id=m.account_id,
                counter_account_id=m.counter_account_id,
                category_id=m.category_id,
                is_adjustment=m.is_adjustment,
                date=m.date,
            )
            for m in movements
        ]

        print(
            f"{plural(len(rows), 'movimento', 'movimenti')}, "
            f"{plural(len(world.accounts), 'conto', 'conti')}, "
            f"{plural(len(world.categories), 'categoria', 'categorie')}"
        )
        print()

        findings = check_migration(_applied_revision(db), _head_revision())
        findings += check(rows, world)
        findings += check_similar_names(
            [
                (kind, name)
                for kind, name in db.execute(
                    select(Category.kind, Category.name).where(
                        Category.household_id == household.id,
                        Category.is_archived.is_(False),
                    )
                ).all()
            ]
        )

        if not findings:
            print("Tutto a posto.")
            return

        for finding in findings:
            mark = "riparabile" if finding.fixable else "da guardare a mano"
            print(f"  [{finding.check}] {finding.detail}  ({mark})")
        print()
        print(f"{plural(len(findings), 'problema', 'problemi')} trovati.")

        fixable = [f for f in findings if f.fixable]
        if not args.fix:
            if fixable:
                print(f"{len(fixable)} si possono riparare con --fix")
            return

        print()
        plan = DryRun(args.apply)
        by_id = {m.id: m for m in movements}
        for finding in fixable:
            movement = by_id.get(finding.transaction_id or -1)
            if movement is None:
                continue
            plan.note(f"movimento {movement.id}: tolgo la categoria")
            movement.category_id = None

        plan.finish(db)
    finally:
        db.close()


if __name__ == "__main__":
    run(main)
