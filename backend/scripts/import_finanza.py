"""Import the years kept in the "Finanza <anno>.xlsx" spreadsheets.

    cd backend && python -m scripts.import_finanza ../dati_finanza
    cd backend && python -m scripts.import_finanza ../dati_finanza --apply

⚠️ **It replaces.** Every movement is deleted first and the accounts' opening
balances are rewritten to 1 January 2024. Run `scripts.backup` before, always.

How the spreadsheets are read
-----------------------------

**The accounts.** The sheets call them by function, the app by name:

    Conto Principale        -> Conto BDM
    Conto Cuscinetto        -> Conto Credem
    Conto Spese Variabili   -> Conto Buddybank
    Conto Spese fisse       -> Conto Hype
    Conto Intesa, Satispay  -> themselves

⚠️ **"Investimenti" is not an account**, and the spreadsheet says so itself: its
"Conto Principale Totale" minus "a disposizione" is exactly the investment
balance, so the pot lived inside the main account. Money paid into an ETF is an
expense from the account it left; money coming back out is income into it.

**Uscite** are movements as they stand: a date, a description, an amount, an
account, a category.

**Entrate** are a row per income, with the amount that arrived and then one
column per account showing how it was split. The first column after the amount
is what *stayed*; every other column is a transfer out. So each row becomes one
income plus N transfers — which is exactly the app's model, arrived at
independently.

⚠️ **The Entrate sheet has no dates.** Salaries are dated the 27th, which is
when they land; anything else takes the month of the salary above it in the
sheet, because the rows are in order. It is a reading, not a record, and it is
the one place this import invents something — noted here so nobody later
mistakes it for data.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db import get_session_factory
from app.domain.vocabulary import CategoryKind, TransactionKind
from app.models import Account, Category, Transaction
from scripts._common import Abort, DryRun, confirm, header, plural, run, single_household
from scripts._xlsx import Workbook

YEARS = (2024, 2025, 2026)

# --------------------------------------------------------------------------
# The accounts
# --------------------------------------------------------------------------

ACCOUNTS = {
    "conto principale": "Conto BDM",
    "conto cuscinetto": "Conto Credem",
    "conto spese variabili": "Conto Buddybank",
    "conto spese fisse (casa macchina tasse)": "Conto Hype",
    "conto intesa": "Conto intesa",
    "satispay": "Satispay",
    # ⚠️ The pot inside the main account. Never its own row in the app.
    "investimenti": "Conto BDM",
}

#: What each account held on 1 January 2024, from "Cifre Iniziali 2024".
OPENING = {
    "Conto BDM": 5_660_066,
    "Conto Credem": 0,
    "Conto Buddybank": 6_873,
    "Conto Hype": 3_777,
    "Conto intesa": 0,
    "Satispay": 0,
    "Contanti": 0,
}
OPENING_DATE = date(2024, 1, 1)

#: What each account really holds now, from "Cifre Attuali 2026" — plus the cash
#: in a pocket, which no spreadsheet ever tracked.
TODAY_IS = {
    "Conto BDM": 8_281_077,
    "Conto Credem": 165_000,
    "Conto Buddybank": 2_149,
    "Conto Hype": 20_389,
    "Conto intesa": 508_909,
    "Satispay": 20_000,
    "Contanti": 17_000,
}

#: Where an income lands, per year, and which account each following column
#: transfers to. `None` is the investment pot: money that stays where it is
#: until an ETF payment takes it out.
INCOME_COLUMNS = {
    2024: ["Conto BDM", "Conto Credem", "Conto Buddybank", "Conto Hype", None],
    2025: ["Conto BDM", "Conto Credem", "Conto Buddybank", "Conto Hype", None],
    # ⚠️ 2026 the salary moved to Intesa, and the investment share is a real
    # transfer to BDM: the ETF payments still left from there.
    2026: [
        "Conto intesa",
        "Conto BDM",
        "Conto Credem",
        "Conto Buddybank",
        "Conto Hype",
        "Conto BDM",
        "Satispay",
    ],
}

# --------------------------------------------------------------------------
# The categories
# --------------------------------------------------------------------------

#: Sheet category -> app category. Matched lowercased and trimmed, because the
#: same name appears with a trailing space and three different capitalisations.
SPENDING = {
    "spesa": "Spesa",
    "casa": "Casa",
    "affitto": "Casa",
    "trasporti": "Trasporti",
    "macchina": "Macchina",
    "regali": "Regali",
    "vestiti": "Vestiti",
    "vestiti e abbigliamento": "Vestiti",
    "abbigliamento": "Vestiti",
    "accessori": "Vestiti",
    "telefonia": "Telefonia",
    "svago": "Svago",
    "passioni varie": "Svago",
    "sport": "Sport",
    "attività fisica": "Sport",
    "viaggi": "Viaggi",
    "vacanze": "Viaggi",
    "tasse": "Tasse",
    "tecnologia": "Tecnologia",
    "salute": "Salute",
    "medicine": "Salute",
    "barbiere": "Barbiere",
    "lavoro": "Lavoro",
    "vari": "Altro",
    "varie": "Altro",
    "altro": "Altro",
    "investimenti": "Investimenti",
    "investimenti etf": "Investimenti",
    "investimenti recrowd": "Investimenti",
    "prelievo": "Contanti",
    "prelievo contanti": "Contanti",
}

#: ⚠️ The sheet's biggest category, "Serate Fuori e Cibo", is two things: a
#: dinner out and a trip to the butcher. Splitting it by description is a
#: reading of the words, so it is done with a short list of the ones that are
#: unambiguous and everything else falls to the sheet's dominant sense.
GROCERIES = re.compile(
    r"\b(spesa|spesina|pane|frutta|verdur|macellai|mercato|latte|uova|carne|"
    r"salumi|formaggi|conad|lidl|esselunga|eurospin|coop|pam\b|bennet|carrefour|"
    r"supermercat|panini|acqua|caramelle|tomini|tagliata)",
    re.I,
)
EATING_OUT = re.compile(
    r"\b(cena|pranzo|colazione|pizz|sushi|bar\b|birr|cocktail|aperitiv|apericena|"
    r"gelat|ristorant|osteria|trattoria|pub\b|mcdonald|burger|hamburger|kebab|"
    r"caff[eè]|brioche|cornett|serata|bevuta|drink|spritz|mangiata|sagra|"
    r"poormanger|bowling|paninoteca|braceria|forno)",
    re.I,
)

#: New categories this import needs, with a colour and an icon each.
NEW_SPENDING = [
    ("Macchina", "chart-8", "Car"),
    ("Telefonia", "chart-7", "Smartphone"),
    ("Sport", "chart-6", "Dumbbell"),
    ("Viaggi", "chart-3", "Plane"),
    ("Tasse", "chart-9", "Landmark" ),
    ("Tecnologia", "chart-2", "Laptop"),
    ("Investimenti", "chart-5", "TrendingUp"),
    ("Contanti", "chart-10", "Banknote"),
    ("Lavoro", "chart-4", "Briefcase"),
]
NEW_INCOME = [
    ("Interessi", "chart-6", "PiggyBank"),
    ("Investimenti", "chart-5", "TrendingUp"),
]

SALARY = re.compile(r"stipendio|tredicesima", re.I)

MONTHS = (
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
)


def income_category(description: str) -> str:
    text = description.lower()
    if SALARY.search(text):
        return "Stipendio"
    if "interess" in text:
        return "Interessi"
    if "recrowd" in text or "btc" in text or "investiment" in text:
        return "Investimenti"
    if "rimborso" in text or "monetizzazione" in text or "buono" in text:
        return "Rimborso"
    if "regalo" in text or "regali" in text:
        return "Regalo"
    return "Altro"


def spending_category(sheet_category: str, description: str) -> str:
    key = sheet_category.strip().lower()
    key = re.sub(r"\s+", " ", key)

    if "serate" in key and "cibo" in key:
        return "Spesa" if GROCERIES.search(description) else "Ristoranti"
    if key == "cibo":
        return "Ristoranti" if EATING_OUT.search(description) else "Spesa"
    return SPENDING.get(key, "Altro")


def cents(value) -> int:
    """⚠️ Integers from the first moment. A float here is a cent lost later.

    Anything that is not a number is zero: these sheets have title rows and
    stray labels sitting in columns that otherwise hold amounts, and a crash
    halfway through an import is worse than a row skipped and reported.
    """
    if not isinstance(value, (int, float)):
        return 0
    return int(round(float(value) * 100))


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa lo storico dai fogli Excel")
    parser.add_argument("folder", type=Path, help="la cartella con i tre file .xlsx")
    parser.add_argument("--apply", action="store_true", help="esegui davvero")
    parser.add_argument("--yes", action="store_true", help="salta la conferma scritta")
    args = parser.parse_args()

    header(args.apply, "Import dello storico")
    print("⚠️  Cancella tutti i movimenti e riscrive i saldi di apertura.")
    print("    Hai lanciato scripts.backup?")
    print()

    books = {}
    for year in YEARS:
        path = args.folder / f"Finanza {year}.xlsx"
        if not path.exists():
            raise Abort(f"Manca {path}")
        books[year] = Workbook(path)

    db = get_session_factory()()
    try:
        household = single_household(db)
        plan = DryRun(args.apply)

        accounts = {
            account.name: account
            for account in db.scalars(
                select(Account).where(Account.household_id == household.id)
            )
        }
        missing = [name for name in OPENING if name not in accounts]
        if missing:
            raise Abort("Conti mancanti nell'app: " + ", ".join(missing))

        categories = {
            (category.kind, category.name.lower()): category
            for category in db.scalars(
                select(Category).where(Category.household_id == household.id)
            )
        }

        # --- categories that do not exist yet ---------------------------
        wanted = [(CategoryKind.EXPENSE, *row) for row in NEW_SPENDING]
        wanted += [(CategoryKind.INCOME, *row) for row in NEW_INCOME]
        for kind, name, colour, icon in wanted:
            if (kind.value, name.lower()) in categories:
                continue
            plan.note(f"creo la categoria {name} ({kind.value})")
            if args.apply:
                created = Category(
                    household_id=household.id,
                    name=name,
                    kind=kind.value,
                    color=colour,
                    icon=icon,
                    position=0,
                )
                db.add(created)
                db.flush()
                categories[(kind.value, name.lower())] = created

        def category_id(kind: CategoryKind, name: str) -> int | None:
            found = categories.get((kind.value, name.lower()))
            if found is None and args.apply:
                raise Abort(f"Categoria mancante: {name} ({kind.value})")
            return found.id if found else None

        # --- out with the old -------------------------------------------
        existing = list(
            db.scalars(select(Transaction).where(Transaction.household_id == household.id))
        )
        if existing:
            plan.note(f"cancello {plural(len(existing), 'movimento', 'movimenti')} già a database")

        plan.note("riscrivo i saldi di apertura al 1 gennaio 2024")

        rows = _read(books, plan)
        plan.note(f"importo {plural(len(rows), 'movimento', 'movimenti')}")

        _report(rows)
        gaps = _gaps(rows)
        for name, difference in gaps.items():
            plan.note(
                f"rettifica su {name}: {difference / 100:+,.2f} "
                f"(importato {(TODAY_IS[name] - difference) / 100:,.2f}, "
                f"reale {TODAY_IS[name] / 100:,.2f})"
            )

        if args.apply:
            confirm(household, args.yes)

            for movement in existing:
                db.delete(movement)
            db.flush()

            for name, opening in OPENING.items():
                accounts[name].opening_balance_cents = opening
                accounts[name].opening_date = OPENING_DATE

            for row in rows:
                db.add(
                    Transaction(
                        household_id=household.id,
                        kind=row["kind"].value,
                        date=row["date"],
                        amount_cents=row["amount"],
                        account_id=accounts[row["account"]].id,
                        counter_account_id=(
                            accounts[row["counter"]].id if row.get("counter") else None
                        ),
                        category_id=(
                            category_id(
                                CategoryKind.INCOME
                                if row["kind"] is TransactionKind.INCOME
                                else CategoryKind.EXPENSE,
                                row["category"],
                            )
                            if row.get("category")
                            else None
                        ),
                        description=row["description"][:255] if row["description"] else None,
                    )
                )
            db.flush()

            # --- and the truth, on top -----------------------------------
            today = date.today()
            for name, difference in gaps.items():
                db.add(
                    Transaction(
                        household_id=household.id,
                        kind=(
                            TransactionKind.INCOME.value
                            if difference > 0
                            else TransactionKind.EXPENSE.value
                        ),
                        date=today,
                        amount_cents=abs(difference),
                        account_id=accounts[name].id,
                        is_adjustment=True,
                        description="Rettifica: allineamento al saldo reale",
                    )
                )

            # The savings goal can only work once the app knows which category
            # is the salary.
            salary = categories.get((CategoryKind.INCOME.value, "stipendio"))
            if salary is not None and household.salary_category_id is None:
                household.salary_category_id = salary.id
                plan.note("imposto «Stipendio» come categoria dello stipendio")

        plan.finish(db)
    finally:
        db.close()


def _read(books: dict[int, Workbook], plan: DryRun) -> list[dict]:
    """Every movement the three spreadsheets describe, in one list."""
    movements: list[dict] = []
    unknown: set[str] = set()

    for year in YEARS:
        book = books[year]

        # ---- Uscite -------------------------------------------------
        for row in book.rows("Uscite"):
            if len(row) < 6 or not isinstance(row[2], date):
                continue
            amount = cents(row[3])
            if amount <= 0:
                continue

            sheet_account = re.sub(r"\s+", " ", str(row[4]).strip()).lower()
            account = ACCOUNTS.get(sheet_account)
            if account is None:
                unknown.add(str(row[4]))
                continue

            description = str(row[1] or "").strip()
            sheet_category = str(row[5] or "")

            # ⚠️ Topping up Satispay is not spending: the money is still yours,
            # it has moved. Filing it as an expense would count it twice — once
            # here and once when the bread was actually bought from Satispay.
            if "satispay" in sheet_category.strip().lower() and account != "Satispay":
                movements.append({
                    "kind": TransactionKind.TRANSFER,
                    "date": row[2],
                    "amount": amount,
                    "account": account,
                    "counter": "Satispay",
                    "category": None,
                    "description": description,
                })
                continue

            movements.append({
                "kind": TransactionKind.EXPENSE,
                "date": row[2],
                "amount": amount,
                "account": account,
                "category": spending_category(sheet_category, description),
                "description": description,
            })

        # ---- Entrate ------------------------------------------------
        columns = INCOME_COLUMNS[year]
        landing = columns[0]
        month = 1

        for row in book.rows("Entrate"):
            if len(row) < 3:
                continue
            description = str(row[1] or "").strip()
            if description in ("Descrizione", "TOT"):
                continue
            # A row without an amount in the amount column is a heading, a
            # spacer, or the sheet's own title floating in the middle.
            if not isinstance(row[2], (int, float)):
                continue

            total = cents(row[2])
            splits = [cents(row[i]) if i < len(row) else 0 for i in range(3, 3 + len(columns))]
            if total == 0 and not any(splits):
                continue

            # ⚠️ The sheet has no dates. A salary names its month and lands on
            # the 27th; anything else takes the month of the salary above it,
            # because the rows are in order. It is the one invention here.
            named = _month_of(description)
            if named:
                month = named
            when = date(year, month, min(27, 28))

            if total:
                movements.append({
                    "kind": TransactionKind.INCOME,
                    "date": when,
                    "amount": total,
                    "account": landing,
                    "category": income_category(description),
                    "description": description or "Entrata (senza descrizione nel foglio)",
                })

            # The first column is what stayed; the rest moved.
            for target, moved in zip(columns[1:], splits[1:], strict=False):
                if target is None or moved == 0 or target == landing:
                    continue
                # A negative share means the money went the other way.
                source, sink = (landing, target) if moved > 0 else (target, landing)
                movements.append({
                    "kind": TransactionKind.TRANSFER,
                    "date": when,
                    "amount": abs(moved),
                    "account": source,
                    "counter": sink,
                    "category": None,
                    "description": description or "Ripartizione",
                })

    if unknown:
        plan.note("⚠️ conti sconosciuti, righe saltate: " + ", ".join(sorted(unknown)))

    movements.sort(key=lambda row: row["date"])
    return movements


def _month_of(description: str) -> int | None:
    text = description.lower()
    for index, name in enumerate(MONTHS, start=1):
        if name in text:
            return index
    if "tredicesima" in text:
        return 12
    return None


def _gaps(rows: list[dict]) -> dict[str, int]:
    """What each account is short of, or over, once everything is imported.

    ⚠️ Closed with a rectification, not with a movement invented to fit. The
    2024 and 2025 sheets add up to the cent; 2026 is the year still being lived
    and its bookkeeping has drifted. A made-up expense would put a lie in the
    charts — a rectification says "this much I could not account for", which is
    the whole reason that row type exists, and it stays out of every spending
    figure.
    """
    balances = dict(OPENING)

    for row in rows:
        if row["kind"] is TransactionKind.INCOME:
            balances[row["account"]] += row["amount"]
        else:
            balances[row["account"]] -= row["amount"]
            if row["kind"] is TransactionKind.TRANSFER:
                balances[row["counter"]] += row["amount"]

    return {
        name: target - balances[name]
        for name, target in TODAY_IS.items()
        if target != balances[name]
    }


def _report(rows: list[dict]) -> None:
    """What the mapping decided, so it can be argued with before it is written."""
    from collections import Counter

    spending = Counter(
        row["category"] for row in rows if row["kind"] is TransactionKind.EXPENSE
    )
    income = Counter(
        row["category"] for row in rows if row["kind"] is TransactionKind.INCOME
    )
    transfers = sum(1 for row in rows if row["kind"] is TransactionKind.TRANSFER)

    print()
    print("  USCITE per categoria")
    for name, count in spending.most_common():
        total = sum(
            row["amount"]
            for row in rows
            if row["kind"] is TransactionKind.EXPENSE and row["category"] == name
        )
        print(f"    {name:16} {count:>4} movimenti  {total / 100:>12,.2f}")
    print("  ENTRATE per categoria")
    for name, count in income.most_common():
        print(f"    {name:16} {count:>4}")
    print(f"  TRASFERIMENTI     {transfers:>4}")
    print()


if __name__ == "__main__":
    run(main)
