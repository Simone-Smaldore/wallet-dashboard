"""Money, in one place.

⚠️ Amounts are integers in cents everywhere: database, API, frontend state. An
integer survives JSON and stays exact in JavaScript, where numbers are float64
but represent integers exactly up to 2^53 — ninety thousand billion euro, in
cents. That is what lets the frontend add up amounts itself.

⚠️ The user never meets a cent. It is an internal representation: you write
`12,50` and you read `12,50 €`. The two conversions live here and in the mirror
file frontend/src/lib/money.ts, and nowhere else.
"""

from __future__ import annotations

import re

CENTS_PER_EURO = 100

# "1.234" and "1.234.567": dots used as thousands separators, nothing else.
_THOUSANDS_ONLY = re.compile(r"^\d{1,3}(\.\d{3})+$")
_DIGITS = re.compile(r"^\d+$")


class InvalidAmount(ValueError):
    """The text is not an amount this app is willing to guess at."""


def parse_amount(text: str) -> int:
    """Turn what a person typed into cents.

    ⚠️ Deliberately *not* `float(text) * 100`. In binary floating point
    `19.99 * 100` is `1998.9999999999998`, so truncating loses a cent on a good
    share of real prices — quietly, and only on some of them, which is the worst
    way to be wrong about money. This works on the digits instead: the integer
    part and the decimal part are separated as text and joined back as an
    integer, so no float is ever involved.

    An empty string is an error, not zero: an empty box means the user has not
    said yet, and guessing zero would record a movement that did not happen.
    """
    cleaned = text.strip().replace(" ", " ").replace(" ", "")
    if not cleaned:
        raise InvalidAmount("Manca l'importo")

    cleaned = cleaned.removesuffix("€").strip()

    sign = 1
    if cleaned.startswith(("-", "+")):
        sign = -1 if cleaned[0] == "-" else 1
        cleaned = cleaned[1:]

    if not cleaned:
        raise InvalidAmount(f"Importo non valido: {text!r}")

    whole_text, decimals_text = _split(cleaned, original=text)

    if whole_text and not _DIGITS.match(whole_text):
        raise InvalidAmount(f"Importo non valido: {text!r}")
    if not whole_text and not decimals_text:
        raise InvalidAmount(f"Importo non valido: {text!r}")

    whole = int(whole_text or "0")
    # "12,5" means fifty cents, not five.
    decimals = int((decimals_text or "").ljust(2, "0") or "0")

    return sign * (whole * CENTS_PER_EURO + decimals)


def _split(cleaned: str, *, original: str) -> tuple[str, str]:
    """Separate the integer part from the decimals, resolving the dot.

    The comma is unambiguous in Italian: it is the decimal separator, and any
    dots around it are thousands. The dot alone is not — `1.234` is one thousand
    two hundred and thirty-four, while `12.50` is twelve euro fifty, and both
    get typed. The rule: a string made only of well-formed thousands groups is
    read as thousands, everything else treats the last dot as decimal.
    """
    if "," in cleaned:
        whole_text, _, decimals_text = cleaned.rpartition(",")
        if "," in whole_text:
            raise InvalidAmount(f"Importo non valido: {original!r}")
        return whole_text.replace(".", ""), _checked_decimals(decimals_text, original)

    if "." not in cleaned:
        return cleaned, ""

    if _THOUSANDS_ONLY.match(cleaned):
        return cleaned.replace(".", ""), ""

    whole_text, _, decimals_text = cleaned.rpartition(".")
    return _checked_whole(whole_text, original), _checked_decimals(decimals_text, original)


def _checked_whole(whole_text: str, original: str) -> str:
    """What is left of the dots in the integer part has to be well formed.

    Without this `12..5` reads as `12,50`, because stripping the dots hides the
    fact that the text was nonsense. An amount is not somewhere to be generous.
    """
    if not whole_text:
        return ""
    if _DIGITS.match(whole_text) or _THOUSANDS_ONLY.match(whole_text):
        return whole_text.replace(".", "")
    raise InvalidAmount(f"Importo non valido: {original!r}")


def _checked_decimals(decimals_text: str, original: str) -> str:
    """Two decimals is the whole precision this app has.

    Three would mean an amount that cannot be stored without rounding, and
    rounding someone's input under their fingers is exactly what this codebase
    refuses to do elsewhere.
    """
    if not _DIGITS.match(decimals_text) or len(decimals_text) > 2:
        raise InvalidAmount(f"Importo non valido: {original!r}")
    return decimals_text


def format_amount(cents: int, *, with_symbol: bool = True) -> str:
    """Cents to Italian text: `1.234,56 €`.

    ⚠️ The division by 100 happens here and only here. Divide anywhere else and
    you are holding a float, which is the whole thing this module exists to
    avoid.
    """
    sign = "-" if cents < 0 else ""
    whole, decimals = divmod(abs(cents), CENTS_PER_EURO)
    grouped = f"{whole:,}".replace(",", ".")
    text = f"{sign}{grouped},{decimals:02d}"
    return f"{text} €" if with_symbol else text
