"""The movements.

The heart of the app: everything else either feeds this table or reads it.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session as DbSession, aliased

from app.api.accounts import get_owned as get_owned_account
from app.api.categories import get_owned as get_owned_category
from app.api.deps import CurrentUserDep, DbDep
from app.domain.vocabulary import TransactionKind
from app.models import Account, Category, Transaction, User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

#: One screenful and a bit. Small enough that the first page is instant on a
#: cold Neon connection, large enough that scrolling rarely asks twice.
PAGE_SIZE = 50


@router.get("", response_model=TransactionPage)
def list_transactions(
    user: CurrentUserDep,
    db: DbDep,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    account_id: int | None = None,
    category_id: int | None = None,
    kind: TransactionKind | None = None,
    q: str = Query(default="", max_length=120),
    cursor: str | None = None,
    limit: int = Query(default=PAGE_SIZE, ge=1, le=200),
) -> TransactionPage:
    statement = _select_rows(user.household_id)

    if date_from is not None:
        statement = statement.where(Transaction.date >= date_from)
    if date_to is not None:
        # Both ends belong to the period: see domain/period.py.
        statement = statement.where(Transaction.date <= date_to)
    if account_id is not None:
        # A transfer belongs to both of its accounts, so filtering by one has to
        # look at both columns — otherwise money arriving on a savings account
        # would be invisible from that account's own list.
        statement = statement.where(
            or_(
                Transaction.account_id == account_id,
                Transaction.counter_account_id == account_id,
            )
        )
    if category_id is not None:
        statement = statement.where(Transaction.category_id == category_id)
    if kind is not None:
        statement = statement.where(Transaction.kind == kind.value)
    if q.strip():
        statement = statement.where(Transaction.description.ilike(f"%{q.strip()}%"))

    if cursor:
        cursor_date, cursor_id = _parse_cursor(cursor)
        # Strictly "older than" in the list's own order, which is what makes the
        # page boundary stable even while rows are being inserted above it.
        statement = statement.where(
            or_(
                Transaction.date < cursor_date,
                (Transaction.date == cursor_date) & (Transaction.id < cursor_id),
            )
        )

    statement = statement.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(
        limit + 1
    )

    rows = db.execute(statement).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    transactions = [_to_schema(row) for row in rows]
    next_cursor = (
        f"{transactions[-1].date.isoformat()},{transactions[-1].id}"
        if has_more and transactions
        else None
    )
    return TransactionPage(transactions=transactions, next_cursor=next_cursor)


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate, user: CurrentUserDep, db: DbDep
) -> TransactionOut:
    _check_references(db, user, payload.account_id, payload.counter_account_id, payload.category_id, payload.kind)

    movement = Transaction(
        household_id=user.household_id,
        kind=payload.kind.value,
        date=payload.date,
        amount_cents=payload.amount_cents,
        account_id=payload.account_id,
        counter_account_id=payload.counter_account_id,
        category_id=payload.category_id,
        description=payload.description,
        created_by_user_id=user.id,
    )
    db.add(movement)
    db.commit()

    _remember_last_account(db, user, payload.account_id)
    return _load(db, user.household_id, movement.id)


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: int, payload: TransactionUpdate, user: CurrentUserDep, db: DbDep
) -> TransactionOut:
    movement = _get_owned(db, user.household_id, transaction_id)
    provided = payload.model_fields_set

    merged_kind = payload.kind or TransactionKind(movement.kind)
    merged_account = payload.account_id if "account_id" in provided else movement.account_id
    merged_counter = (
        payload.counter_account_id
        if "counter_account_id" in provided
        else movement.counter_account_id
    )
    merged_category = (
        payload.category_id if "category_id" in provided else movement.category_id
    )

    # Re-validate the *result*, not the change: switching kind alone can turn a
    # perfectly good row into an impossible one.
    _check_shape(merged_kind, merged_account, merged_counter, merged_category)
    _check_references(db, user, merged_account, merged_counter, merged_category, merged_kind)

    movement.kind = merged_kind.value
    movement.account_id = merged_account
    movement.counter_account_id = merged_counter
    movement.category_id = merged_category
    if "date" in provided and payload.date is not None:
        movement.date = payload.date
    if "amount_cents" in provided and payload.amount_cents is not None:
        movement.amount_cents = payload.amount_cents
    if "description" in provided:
        movement.description = payload.description

    db.commit()
    return _load(db, user.household_id, movement.id)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, user: CurrentUserDep, db: DbDep) -> None:
    """⚠️ A real delete, unlike accounts and categories.

    An archived account is history; a mistyped movement is not history, it is a
    typo. Keeping it "archived" would mean every total is wrong forever, which
    is a stranger outcome than losing a row that recorded something that never
    happened.
    """
    movement = _get_owned(db, user.household_id, transaction_id)
    db.delete(movement)
    db.commit()


# --------------------------------------------------------------------------
# Shared with api/accounts.py (reconciliation writes one of these too)
# --------------------------------------------------------------------------


def _select_rows(household_id: int) -> Select:
    """The list query, with both accounts and the category joined in.

    Denormalised into the response and not into the table: renaming a category
    still propagates by itself, because the row points at it rather than
    carrying a copy.
    """
    counter = aliased(Account)
    return (
        select(Transaction, Account.name, counter.name, Category)
        .join(Account, Account.id == Transaction.account_id)
        .outerjoin(counter, counter.id == Transaction.counter_account_id)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(Transaction.household_id == household_id)
    )


def _to_schema(row) -> TransactionOut:
    movement, account_name, counter_name, category = row
    return TransactionOut(
        id=movement.id,
        kind=movement.kind,
        date=movement.date,
        amount_cents=movement.amount_cents,
        description=movement.description,
        is_adjustment=movement.is_adjustment,
        account_id=movement.account_id,
        account_name=account_name,
        counter_account_id=movement.counter_account_id,
        counter_account_name=counter_name,
        category_id=movement.category_id,
        category_name=category.name if category else None,
        category_kind=category.kind if category else None,
        category_color=category.color if category else None,
        category_icon=category.icon if category else None,
    )


def load_one(db: DbSession, household_id: int, transaction_id: int) -> TransactionOut:
    return _load(db, household_id, transaction_id)


def _load(db: DbSession, household_id: int, transaction_id: int) -> TransactionOut:
    row = db.execute(
        _select_rows(household_id).where(Transaction.id == transaction_id)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movimento non trovato"
        )
    return _to_schema(row)


def _get_owned(db: DbSession, household_id: int, transaction_id: int) -> Transaction:
    movement = db.get(Transaction, transaction_id)
    if movement is None or movement.household_id != household_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movimento non trovato"
        )
    return movement


def _check_shape(
    kind: TransactionKind,
    account_id: int,
    counter_account_id: int | None,
    category_id: int | None,
) -> None:
    """The CHECK constraints, restated for a PATCH that has already merged."""
    if kind is TransactionKind.TRANSFER:
        if counter_account_id is None:
            _refuse("Un trasferimento ha bisogno del conto di destinazione")
        if counter_account_id == account_id:
            _refuse("Un trasferimento non può avere lo stesso conto ai due lati")
        if category_id is not None:
            _refuse("Un trasferimento non ha categoria")
    elif counter_account_id is not None:
        _refuse("Solo un trasferimento ha un secondo conto")


def _check_references(
    db: DbSession,
    user: User,
    account_id: int,
    counter_account_id: int | None,
    category_id: int | None,
    kind: TransactionKind,
) -> None:
    """Every id has to belong to this household, and a category to the right list.

    ⚠️ The sign check matters: filing a spend under "Stipendio" would put money
    on the wrong side of every chart, and nothing downstream would notice.
    """
    get_owned_account(db, user.household_id, account_id)
    if counter_account_id is not None:
        get_owned_account(db, user.household_id, counter_account_id)

    if category_id is not None:
        category = get_owned_category(db, user.household_id, category_id)
        if category.kind != kind.value:
            _refuse(
                f"La categoria «{category.name}» è di "
                f"{'entrata' if category.kind == 'income' else 'uscita'}"
            )


def _refuse(message: str) -> None:
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


def _parse_cursor(cursor: str) -> tuple[date, int]:
    try:
        raw_date, raw_id = cursor.split(",", 1)
        return date.fromisoformat(raw_date), int(raw_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Cursore non valido"
        ) from None


def _remember_last_account(db: DbSession, user: User, account_id: int) -> None:
    """The next quick entry starts from the account this one used.

    In `preferences` because it is personal: which account you reach for is
    about you, not about the household's money.
    """
    if user.preferences.get("last_account_id") == account_id:
        return
    user.preferences = {**user.preferences, "last_account_id": account_id}
    db.commit()
