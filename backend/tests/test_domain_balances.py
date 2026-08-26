"""Balances and net worth.

The first test in this file is the one that must never break: it is the same
promise as the food project's hard dietary constraint, transposed. If a transfer
can move a total, every number the app shows is wrong.
"""

from datetime import date, timedelta

from app.domain.balances import (
    AccountRow,
    MovementRow,
    balances,
    net_worth,
    net_worth_parts,
)
from app.domain.vocabulary import TransactionKind

TODAY = date(2026, 3, 12)
TOMORROW = TODAY + timedelta(days=1)

CORRENTE = AccountRow(id=1, opening_balance_cents=100_000)
DEPOSITO = AccountRow(id=2, opening_balance_cents=500_000)
CONTANTE = AccountRow(id=3, opening_balance_cents=5_000)
ALL = [CORRENTE, DEPOSITO, CONTANTE]


def transfer(amount: int, source: int, target: int, when: date = TODAY) -> MovementRow:
    return MovementRow(
        kind=TransactionKind.TRANSFER,
        amount_cents=amount,
        account_id=source,
        counter_account_id=target,
        date=when,
    )


def expense(amount: int, account: int, when: date = TODAY) -> MovementRow:
    return MovementRow(
        kind=TransactionKind.EXPENSE, amount_cents=amount, account_id=account, date=when
    )


def income(amount: int, account: int, when: date = TODAY) -> MovementRow:
    return MovementRow(
        kind=TransactionKind.INCOME, amount_cents=amount, account_id=account, date=when
    )


def test_a_transfer_moves_two_accounts_and_no_totals():
    """⚠️ The untouchable one.

    Moving money between two accounts changes neither how much you have nor how
    much you spent. It is the error that makes a personal-finance dashboard
    useless: a salary split across three accounts would otherwise read as three
    incomes and three expenses, and every number on screen would be inflated.
    """
    before = net_worth(ALL, [])

    moved = [transfer(50_000, source=1, target=2)]
    after_totals = balances(ALL, moved)

    assert after_totals[1] == 100_000 - 50_000
    assert after_totals[2] == 500_000 + 50_000
    assert net_worth(ALL, moved) == before


def test_balance_is_opening_plus_movements():
    movements = [expense(2_000, 1), income(180_000, 1), expense(500, 3)]
    totals = balances(ALL, movements)

    assert totals[1] == 100_000 - 2_000 + 180_000
    assert totals[3] == 5_000 - 500
    # An account nothing touched keeps its opening balance.
    assert totals[2] == 500_000


def test_no_movements_means_the_opening_balance():
    """M2 lives entirely in this case, and the formula still has to be the real
    one rather than a shortcut that returns the opening balance."""
    assert balances(ALL, []) == {1: 100_000, 2: 500_000, 3: 5_000}


def test_excluded_accounts_leave_the_total_but_not_the_history():
    shared = AccountRow(id=4, opening_balance_cents=80_000, include_in_net_worth=False)
    accounts = [*ALL, shared]

    assert net_worth(accounts, []) == 100_000 + 500_000 + 5_000

    # It still has a balance of its own, and its movements still happened.
    totals = balances(accounts, [expense(10_000, 4)])
    assert totals[4] == 70_000


def test_moving_money_to_an_uncounted_account_lowers_the_total():
    """Not a leak: money parked somewhere you have declared is not yours has
    genuinely left your net worth."""
    shared = AccountRow(id=4, opening_balance_cents=0, include_in_net_worth=False)
    accounts = [*ALL, shared]

    moved = [transfer(30_000, source=1, target=4)]
    assert net_worth(accounts, moved) == net_worth(accounts, []) - 30_000


def test_an_adjustment_moves_the_balance():
    """Reconciliation is a movement, not a write on the balance: it is the only
    way the two numbers cannot end up disagreeing."""
    adjustment = MovementRow(
        kind=TransactionKind.EXPENSE, amount_cents=1_200, account_id=1, date=TODAY
    )
    assert balances(ALL, [adjustment])[1] == 100_000 - 1_200


def test_a_future_movement_counts_in_the_balance_and_not_as_of_today():
    """⚠️ The two readings the app needs, from one function.

    The balance on screen includes tomorrow's rent on purpose: it answers "how
    much will be left". Reconciliation asks the same function for the balance as
    of today, because a bank statement cannot contain tomorrow — without the
    cut-off the difference would include money that has not moved, and the
    adjustment born from it would be a movement that never happened.
    """
    rent = expense(80_000, 1, when=TOMORROW)

    assert balances(ALL, [rent])[1] == 100_000 - 80_000
    assert balances(ALL, [rent], as_of=TODAY)[1] == 100_000

    assert net_worth(ALL, [rent], as_of=TODAY) == net_worth(ALL, [])


def test_a_movement_dated_today_is_included_by_as_of_today():
    """The cut-off is inclusive: today has happened."""
    assert balances(ALL, [expense(5_000, 1)], as_of=TODAY)[1] == 95_000


def test_movements_of_unknown_accounts_are_ignored():
    """An archived account left out of the query must not crash the sum, and
    must not silently land its movements on someone else."""
    totals = balances([CORRENTE], [expense(1_000, 1), expense(9_999, 99)])
    assert totals == {1: 99_000}


# --------------------------------------------------------------------------
# Liquid and invested
# --------------------------------------------------------------------------


def test_paying_into_an_investment_moves_nothing_out_of_the_net_worth():
    """⚠️ The whole point of making an investment an account.

    As an expense, 400 € into an ETF took 400 € off what you own — which was
    simply false. As a transfer it moves between two pockets of yours: the
    liquid side falls, the invested side rises, the total does not move.
    """
    etf = AccountRow(id=9, opening_balance_cents=0, is_investment=True)
    accounts = [*ALL, etf]

    before = net_worth_parts(accounts, [])
    after = net_worth_parts(accounts, [transfer(40_000, source=1, target=9)])

    assert after.total_cents == before.total_cents
    assert after.liquid_cents == before.liquid_cents - 40_000
    assert after.invested_cents == 40_000


def test_an_investment_without_a_price_falls_back_to_what_was_paid_in():
    """An understatement, and the honest one: better than a market value nobody
    has. The screen says when the number is from, and "never" is an answer."""
    etf = AccountRow(id=9, opening_balance_cents=0, is_investment=True)

    worth = net_worth_parts([*ALL, etf], [transfer(40_000, source=1, target=9)])

    assert worth.invested_cents == 40_000


def test_a_price_replaces_the_capital_paid_in():
    """12.402 € paid in, worth 13.910 today: the second is the one that counts
    for what you own, and the first stays visible as the account's balance."""
    etf = AccountRow(id=9, opening_balance_cents=0, is_investment=True)

    worth = net_worth_parts(
        [*ALL, etf],
        [transfer(1_240_200, source=1, target=9)],
        valuations={9: 1_391_000},
    )

    assert worth.invested_cents == 1_391_000
    assert worth.total_cents == worth.liquid_cents + 1_391_000


def test_an_account_left_out_of_the_net_worth_is_in_neither_half():
    shared = AccountRow(id=8, opening_balance_cents=90_000, include_in_net_worth=False)

    worth = net_worth_parts([*ALL, shared], [])

    assert worth.liquid_cents == net_worth_parts(ALL, []).liquid_cents
    assert worth.invested_cents == 0
