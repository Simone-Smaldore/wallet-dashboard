"""Balances and net worth.

Pure: it takes plain values and returns plain values, so the rule that decides
every number the app shows can be tested without a database.

⚠️ The balance is never a column. It is always `opening_balance + Σ movements`,
recomputed. A stored balance updated on every write is a second number that can
disagree with the first, and when it does you have no way to know which to
believe. The cost is a sum over a few thousand rows, which is nothing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.vocabulary import TransactionKind


@dataclass(frozen=True)
class AccountRow:
    """Only what a balance needs to know about an account."""

    id: int
    opening_balance_cents: int
    include_in_net_worth: bool = True


@dataclass(frozen=True)
class MovementRow:
    """Only what a balance needs to know about a movement."""

    kind: TransactionKind
    amount_cents: int
    account_id: int
    counter_account_id: int | None = None


def balances(
    accounts: Iterable[AccountRow], movements: Iterable[MovementRow]
) -> dict[int, int]:
    """Every account's balance, in cents, keyed by account id.

    A transfer touches two accounts from a single row: it leaves `account_id`
    and lands on `counter_account_id`. That is the whole reason the model keeps
    it as one row — the two sides can never disagree, because there is only one
    of them.
    """
    totals = {account.id: account.opening_balance_cents for account in accounts}

    for movement in movements:
        if movement.account_id in totals:
            if movement.kind is TransactionKind.INCOME:
                totals[movement.account_id] += movement.amount_cents
            else:
                # Expenses leave, and so does the outgoing side of a transfer.
                totals[movement.account_id] -= movement.amount_cents

        if (
            movement.kind is TransactionKind.TRANSFER
            and movement.counter_account_id is not None
            and movement.counter_account_id in totals
        ):
            totals[movement.counter_account_id] += movement.amount_cents

    return totals


def net_worth(accounts: Iterable[AccountRow], movements: Iterable[MovementRow]) -> int:
    """The total, counting only the accounts that are actually yours.

    `include_in_net_worth` is off for money you are holding for someone else or
    for an account you share: it comes out of this total and stays in the
    spending statistics, because what you spend from it is still what you spent.

    ⚠️ A transfer between two counted accounts cannot move this number: it
    subtracts and adds the same amount, so the total is unchanged. That is the
    arithmetic saying what the domain rule says — a transfer is not income and
    not an expense.

    A transfer *towards an account that is not counted* does lower it, and that
    is right rather than a leak: money moved somewhere you have declared is not
    yours has left your net worth. The same holds in reverse.
    """
    counted = [account for account in accounts if account.include_in_net_worth]
    totals = balances(counted, movements)
    return sum(totals.values())
