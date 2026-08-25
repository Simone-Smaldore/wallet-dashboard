"""The closed vocabularies.

Closed because they are *structure*, not content: adding a value means deciding
what the rest of the code does when it meets one. Categories are the opposite —
those are content, you invent them, and they live in a table.

Mirrored in frontend/src/api/client.ts. When one of these changes, both move.
"""

from __future__ import annotations

from enum import StrEnum


class AccountKind(StrEnum):
    """Where money sits. All of them are immediate in V1.

    No deferred-debit card: a credit card, if it ever matters, is an account
    that goes negative and that you zero at the end of the month with a normal
    transfer. Representable without adding a concept.
    """

    CORRENTE = "corrente"
    DEPOSITO = "deposito"
    CONTANTE = "contante"
    PREPAGATA = "prepagata"


class TransactionKind(StrEnum):
    """What a movement is.

    The amount is always positive; this carries the sign. A transfer is one row
    with two accounts, which is what makes "a transfer is not an expense" a
    property of the table rather than a rule to remember in every query.
    """

    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


class CategoryKind(StrEnum):
    """Two separate lists, never mixed.

    "Stipendio" must not appear among the spending categories, and a chart must
    not be able to put the two lists in the same pie.
    """

    EXPENSE = "expense"
    INCOME = "income"


# Categories store the *token name*, not the hex. If DESIGN.md ever retunes a
# series, every category follows without a data migration — and it keeps the
# promise that no colour in this app is written anywhere but tokens.css.
CATEGORY_COLORS: tuple[str, ...] = (
    "chart-1",
    "chart-2",
    "chart-3",
    "chart-4",
    "chart-5",
    "chart-6",
)

# A curated slice of Lucide rather than the whole set: 1500 icons is not a
# choice, it is a search problem, and the twenty-four below cover what a
# household actually spends money on. Names are Lucide's, in PascalCase, and the
# frontend imports each one explicitly so the bundle only carries these.
CATEGORY_ICONS: tuple[str, ...] = (
    "ShoppingCart",
    "House",
    "Car",
    "UtensilsCrossed",
    "Coffee",
    "HeartPulse",
    "Pill",
    "Dumbbell",
    "Shirt",
    "Gift",
    "Plane",
    "Bus",
    "Fuel",
    "Wrench",
    "Smartphone",
    "Wifi",
    "Repeat",
    "BookOpen",
    "GraduationCap",
    "Film",
    "PawPrint",
    "Baby",
    "Banknote",
    "Ellipsis",
)


def is_known_color(value: str) -> bool:
    return value in CATEGORY_COLORS


def is_known_icon(value: str) -> bool:
    return value in CATEGORY_ICONS
