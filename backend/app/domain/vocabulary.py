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
    # The first six are the chart series, in this order: a line or a pie uses
    # them and nothing else, because more than six lines on one chart stop being
    # readable. The rest exist for categories, which can easily be a dozen and
    # need to be told apart in a list at a glance.
    "chart-1",
    "chart-2",
    "chart-3",
    "chart-4",
    "chart-5",
    "chart-6",
    "chart-7",
    "chart-8",
    "chart-9",
    "chart-10",
)

# A curated slice of Lucide rather than the whole set: 1500 icons is not a
# choice, it is a search problem. Fifty-six is still a curated set — it covers
# what a household actually spends money on — and the picker shows them eight at
# a time in themed pages, so the number never lands on screen all at once.
#
# The grouping lives in the frontend, which is where it is looked at; the order
# here matches it so the two do not drift. Names are Lucide's, in PascalCase,
# and the frontend imports each one explicitly so the bundle carries only these.
CATEGORY_ICONS: tuple[str, ...] = (
    # Casa
    "House",
    "Key",
    "Zap",
    "Droplet",
    "Flame",
    "Wifi",
    "Sofa",
    "Hammer",
    # Spesa e cibo
    "ShoppingCart",
    "ShoppingBag",
    "UtensilsCrossed",
    "Coffee",
    "Pizza",
    "Beer",
    "Cake",
    "Store",
    # Trasporti
    "Car",
    "Bus",
    "Train",
    "Bike",
    "Fuel",
    "Plane",
    "ParkingCircle",
    "Ticket",
    # Salute e cura
    "HeartPulse",
    "Pill",
    "Stethoscope",
    "Dumbbell",
    "Scissors",
    "Glasses",
    "Baby",
    "PawPrint",
    # Svago
    "Film",
    "Music",
    "Gamepad2",
    "Camera",
    "BookOpen",
    "GraduationCap",
    "Palette",
    "Sparkles",
    # Soldi e lavoro
    "Banknote",
    "Coins",
    "PiggyBank",
    "CreditCard",
    "Briefcase",
    "Laptop",
    "TrendingUp",
    "Repeat",
    # Altro
    "Gift",
    "Smartphone",
    "Wrench",
    "Package",
    "Umbrella",
    "Heart",
    "Shirt",
    "Ellipsis",
)



#: What a category created on the fly gets until you give it a better one.
#: Neutral on purpose: a wrong icon costs nothing, a wrong colour costs a chart.
DEFAULT_CATEGORY_ICON = "Ellipsis"


def is_known_color(value: str) -> bool:
    return value in CATEGORY_COLORS


def is_known_icon(value: str) -> bool:
    return value in CATEGORY_ICONS
