"""The accounts.

Balances are computed here, never stored — see domain/balances.py for why.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import CurrentUserDep, DbDep
from app.domain import balances as domain
from app.domain.vocabulary import TransactionKind
from app.models import Account, Transaction
from app.schemas.account import AccountCreate, AccountList, AccountOut, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=AccountList)
def list_accounts(user: CurrentUserDep, db: DbDep) -> AccountList:
    accounts = list(
        db.scalars(
            select(Account)
            .where(Account.household_id == user.household_id)
            # Archived accounts sink to the bottom rather than disappearing:
            # they still hold history, and hiding them entirely would make a
            # balance that no longer adds up look like a bug.
            .order_by(Account.is_archived, Account.position, func.lower(Account.name))
        ).all()
    )

    rows = _balance_rows(accounts)
    movements = _movement_rows(db, user.household_id)

    totals = domain.balances(rows, movements)
    net_worth = domain.net_worth(rows, movements)

    return AccountList(
        accounts=[
            AccountOut(
                id=account.id,
                name=account.name,
                kind=account.kind,
                opening_balance_cents=account.opening_balance_cents,
                opening_date=account.opening_date,
                include_in_net_worth=account.include_in_net_worth,
                position=account.position,
                is_archived=account.is_archived,
                balance_cents=totals.get(account.id, account.opening_balance_cents),
            )
            for account in accounts
        ],
        net_worth_cents=net_worth,
    )


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, user: CurrentUserDep, db: DbDep) -> AccountOut:
    _refuse_duplicate(db, user.household_id, payload.name)

    highest = db.scalar(
        select(func.max(Account.position)).where(Account.household_id == user.household_id)
    )

    account = Account(
        household_id=user.household_id,
        name=payload.name,
        kind=payload.kind.value,
        opening_balance_cents=payload.opening_balance_cents,
        opening_date=payload.opening_date,
        include_in_net_worth=payload.include_in_net_worth,
        position=(highest or 0) + 1,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    # A brand new account has no movements, so its balance is its opening one.
    return _to_schema(account, account.opening_balance_cents)


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int, payload: AccountUpdate, user: CurrentUserDep, db: DbDep
) -> AccountOut:
    account = get_owned(db, user.household_id, account_id)
    provided = payload.model_fields_set

    if "name" in provided and payload.name is not None:
        _refuse_duplicate(db, user.household_id, payload.name, excluding=account.id)
        account.name = payload.name

    if "kind" in provided and payload.kind is not None:
        account.kind = payload.kind.value
    if "opening_balance_cents" in provided and payload.opening_balance_cents is not None:
        account.opening_balance_cents = payload.opening_balance_cents
    if "opening_date" in provided and payload.opening_date is not None:
        account.opening_date = payload.opening_date
    if "include_in_net_worth" in provided and payload.include_in_net_worth is not None:
        account.include_in_net_worth = payload.include_in_net_worth
    if "position" in provided and payload.position is not None:
        account.position = payload.position
    if "is_archived" in provided and payload.is_archived is not None:
        account.is_archived = payload.is_archived

    db.commit()
    db.refresh(account)

    totals = domain.balances(
        _balance_rows([account]), _movement_rows(db, user.household_id)
    )
    return _to_schema(account, totals.get(account.id, account.opening_balance_cents))


def get_owned(db: DbSession, household_id: int, account_id: int) -> Account:
    account = db.get(Account, account_id)
    # Same answer for "does not exist" and "belongs to someone else": the second
    # would otherwise confirm that an id is in use.
    if account is None or account.household_id != household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conto non trovato")
    return account


def _refuse_duplicate(
    db: DbSession, household_id: int, name: str, *, excluding: int | None = None
) -> None:
    """Case-insensitive, matching the unique index on the table.

    Two accounts called "Conto" and "conto" would be two rows nobody can tell
    apart in a picker, and every movement filed against the wrong one.
    """
    statement = select(Account).where(
        Account.household_id == household_id,
        func.lower(Account.name) == name.strip().lower(),
    )
    clash = db.scalar(statement)
    if clash is not None and clash.id != excluding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Esiste già un conto chiamato {clash.name}",
        )


def _balance_rows(accounts: list[Account]) -> list[domain.AccountRow]:
    return [
        domain.AccountRow(
            id=account.id,
            opening_balance_cents=account.opening_balance_cents,
            include_in_net_worth=account.include_in_net_worth,
        )
        for account in accounts
    ]


def _movement_rows(db: DbSession, household_id: int) -> list[domain.MovementRow]:
    """Every movement of the household, as plain values for the domain.

    Loading them all is fine at this scale — a year of real use is around 1.500
    rows — and it keeps the rule about what counts inside a pure function. Past
    tens of thousands this becomes a GROUP BY; the note in CLAUDE.md says where
    the line is.
    """
    rows = db.execute(
        select(
            Transaction.kind,
            Transaction.amount_cents,
            Transaction.account_id,
            Transaction.counter_account_id,
        ).where(Transaction.household_id == household_id)
    ).all()

    return [
        domain.MovementRow(
            kind=TransactionKind(kind),
            amount_cents=amount,
            account_id=account_id,
            counter_account_id=counter_account_id,
        )
        for kind, amount, account_id, counter_account_id in rows
    ]


def _to_schema(account: Account, balance_cents: int) -> AccountOut:
    return AccountOut(
        id=account.id,
        name=account.name,
        kind=account.kind,
        opening_balance_cents=account.opening_balance_cents,
        opening_date=account.opening_date,
        include_in_net_worth=account.include_in_net_worth,
        position=account.position,
        is_archived=account.is_archived,
        balance_cents=balance_cents,
    )
