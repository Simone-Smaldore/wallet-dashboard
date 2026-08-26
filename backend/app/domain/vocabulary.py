"""The closed vocabularies.

Closed because they are *structure*, not content: adding a value means deciding
what the rest of the code does when it meets one. Categories are the opposite —
those are content, you invent them, and they live in a table.

Mirrored in frontend/src/api/client.ts. When one of these changes, both move.
"""

from __future__ import annotations

from enum import StrEnum


class AccountKind(StrEnum):
    """Where money sits.

    No deferred-debit card: a credit card, if it ever matters, is an account
    that goes negative and that you zero at the end of the month with a normal
    transfer. Representable without adding a concept.

    ⚠️ `INVESTIMENTO` is the one that behaves differently, and it earns the
    exception. Paying into an ETF is a **transfer**, not a spend: the money is
    still yours, so the net worth must not move and the spending pie must not
    show it. But it *has* left the current account and cannot be spent twice, so
    the month's budget has to lose it — see stats.savings_month.

    ⚠️ Its balance is **capital contributed**, derived from the movements like
    every other balance. What it is worth today is a different fact and lives in
    `asset_valuation`. Two true numbers that say different things, shown
    together — never one number pretending to be both.
    """

    CORRENTE = "corrente"
    DEPOSITO = "deposito"
    CONTANTE = "contante"
    PREPAGATA = "prepagata"
    INVESTIMENTO = "investimento"


class AssetKind(StrEnum):
    """What an investment is made of.

    The kind decides how a price is read, not just how it is labelled: see
    `PriceBasis`.
    """

    CRYPTO = "crypto"
    ETF = "etf"
    OBBLIGAZIONE = "obbligazione"
    ALTRO = "altro"


class PriceBasis(StrEnum):
    """How a quoted price turns into money.

    ⚠️ **This exists because a bond is not quoted in euro.** The BTP Mz72 shows
    `55,78` on Borsa Italiana, and that is not 55,78 € — it is 55,78% of the
    nominal. An ETF at `126,53` *is* 126,53 € a share.

    Without the distinction a bond enters the net worth a hundred times too
    large, and it is the kind of error you only catch by looking at the total
    and finding it implausible.
    """

    #: value = quantity x price. Shares, coins.
    PER_UNIT = "per_unit"
    #: value = nominal x price / 100. Bonds.
    PERCENT_OF_NOMINAL = "percent_of_nominal"


class PriceSource(StrEnum):
    """Where a valuation came from.

    Kept on every valuation so a number can always be traced back to whoever
    said it — including "you did".
    """

    MANUAL = "manual"
    COINGECKO = "coingecko"
    BORSA_ITALIANA = "borsa_italiana"


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
