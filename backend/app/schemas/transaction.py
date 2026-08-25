# Aliased because the field is *called* `date`: without this the annotation on
# the second model resolves to the field defined above it instead of the type.
from datetime import date as DateType

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.vocabulary import CategoryKind, TransactionKind


class TransactionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("description", check_fields=False)
    @classmethod
    def trim(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        # An empty note is no note, not a note made of spaces.
        return trimmed or None


class TransactionCreate(TransactionWrite):
    kind: TransactionKind
    date: DateType
    # Always positive: the sign lives in `kind`. See domain/money.py.
    amount_cents: int = Field(gt=0)
    account_id: int
    counter_account_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def shape_matches_kind(self) -> "TransactionCreate":
        """The same rules the database CHECKs enforce, said in Italian.

        ⚠️ Not a replacement for them — the database stays the last word — but
        an IntegrityError reaching the client as a 500 is a bug report, not a
        message. This turns it into a 422 that says what is wrong.
        """
        if self.kind is TransactionKind.TRANSFER:
            if self.counter_account_id is None:
                raise ValueError("Un trasferimento ha bisogno del conto di destinazione")
            if self.counter_account_id == self.account_id:
                raise ValueError("Un trasferimento non può avere lo stesso conto ai due lati")
            if self.category_id is not None:
                # The rule the whole model rests on: a transfer is neither an
                # expense nor income, so it cannot be filed under one.
                raise ValueError("Un trasferimento non ha categoria")
        else:
            if self.counter_account_id is not None:
                raise ValueError("Solo un trasferimento ha un secondo conto")
        return self


class TransactionUpdate(TransactionWrite):
    """Partial, but the shape still has to hold once applied.

    The router re-validates the merged result rather than each field on its own:
    changing only `kind` can make an otherwise fine row impossible.
    """

    kind: TransactionKind | None = None
    date: DateType | None = None
    amount_cents: int | None = Field(default=None, gt=0)
    account_id: int | None = None
    counter_account_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)


class TransactionOut(BaseModel):
    """A movement, with enough of its neighbours to draw a row.

    Names and colours are denormalised **into the response**, never into the
    table: renaming a category still propagates everywhere, and the list does
    not have to wait for two other queries to have loaded before it can render.
    """

    id: int
    kind: TransactionKind
    date: DateType
    amount_cents: int
    description: str | None
    is_adjustment: bool

    account_id: int
    account_name: str
    counter_account_id: int | None
    counter_account_name: str | None

    category_id: int | None
    category_name: str | None
    category_kind: CategoryKind | None
    category_color: str | None
    category_icon: str | None


class TransactionPage(BaseModel):
    """One page of the list, plus where to carry on from.

    ⚠️ The cursor is a keyset, not an offset: recording a spend from last month
    while someone is scrolling would slide every later page under their fingers,
    repeating some rows and skipping others.
    """

    transactions: list[TransactionOut]
    #: Opaque "date,id" of the last row; pass it back as `cursor` for the next page.
    next_cursor: str | None


class ReconcileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: What the bank says, today.
    balance_cents: int


class ReconcileResult(BaseModel):
    """What the adjustment did, so the screen can say it rather than imply it."""

    difference_cents: int
    #: None when the balance already matched and nothing needed to be written.
    transaction: TransactionOut | None
    new_balance_cents: int
