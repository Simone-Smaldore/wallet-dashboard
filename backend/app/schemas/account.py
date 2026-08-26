from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.vocabulary import AccountKind


class AccountBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", check_fields=False)
    @classmethod
    def trim(cls, value: str | None) -> str | None:
        """Whitespace is not part of a name, and " Conto " would sort oddly."""
        return value.strip() if value is not None else None


class AccountCreate(AccountBase):
    name: str = Field(min_length=1, max_length=120)
    kind: AccountKind
    # In cents, like everywhere else. The frontend converts what was typed.
    opening_balance_cents: int = 0
    opening_date: date
    include_in_net_worth: bool = True


class AccountUpdate(AccountBase):
    """Partial: an absent field is left alone, which is what makes archiving,
    renaming and reordering the same endpoint without stepping on each other."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: AccountKind | None = None
    opening_balance_cents: int | None = None
    opening_date: date | None = None
    include_in_net_worth: bool | None = None
    position: int | None = Field(default=None, ge=0)
    is_archived: bool | None = None


class AccountOut(BaseModel):
    id: int
    name: str
    kind: AccountKind
    opening_balance_cents: int
    opening_date: date
    include_in_net_worth: bool
    position: int
    is_archived: bool
    # Computed, never stored: opening balance plus every movement that touches
    # this account. See domain/balances.py.
    #
    # ⚠️ For an investment account this is the **capital paid in**, not what it
    # is worth: the two are different facts and the screen shows both.
    balance_cents: int

    #: What the holdings inside it are worth, when there are any and a price has
    #: been found. Null everywhere else — including an investment account whose
    #: assets have never been priced, where the balance is the honest answer.
    #:
    #: ⚠️ Computed **here** and not on each screen. It was worked out inside the
    #: Conti page first, which meant the Riepilogo could not know it and showed
    #: the capital instead: two screens, two answers, one of them wrong. A number
    #: this app shows twice has to be decided once.
    value_cents: int | None = None
    #: ⚠️ Travels with `value_cents`, always. A value that looks current and is
    #: three weeks old is worse than none: on a missing number you check, on a
    #: stale one you rely.
    valued_on: date | None = None


class AccountList(BaseModel):
    """The list plus the numbers the screen shows above it.

    Sent together on purpose: the total is a property of the whole set, and
    letting the client add up the balances would be fine arithmetically but
    would put the rule about which accounts count in two places.
    """

    accounts: list[AccountOut]
    net_worth_cents: int
    #: The same split the Riepilogo shows, from the same function: what you
    #: could spend, and what is invested.
    liquid_cents: int = 0
    invested_cents: int = 0
    valued_on: date | None = None
