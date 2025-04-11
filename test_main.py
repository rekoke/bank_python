"""Tests"""

import pytest
from main import (
    AccountActionError,
    AccountNotFoundError,
    AmountError,
    Bank,
    BankActionError,
    OwnerNotFoundError,
)

CHECKING = "checking"
SAVING = "saving"


def test_account_creation():
    """Tests account creation with default and custom values"""

    bank = Bank()

    bob_account_checking = bank.create_account("Bob", "1234")
    assert bob_account_checking.balance == 0
    assert bob_account_checking.account_type == CHECKING

    bob_account_saving = bank.create_account("Bob", "1234", account_type=SAVING)
    assert bob_account_saving.account_type == SAVING

    meri_account_saving = bank.create_account("Meri", "4321", 300, SAVING)
    assert meri_account_saving.balance == 300
    assert meri_account_saving.account_type == SAVING

    # Tests user trying to create a duplicate checkin account
    with pytest.raises(BankActionError):
        bank.create_account("Bob", "5678", account_type=CHECKING)


def test_authentication():
    """Tests user authentication and logged in operations"""
    bank = Bank()
    bob_account_checking = bank.create_account("Bob", "1234")

    bob_account_checking.login("1234")
    assert bob_account_checking.is_logged_in()

    bob_account_checking.logout()
    assert not bob_account_checking.is_logged_in()
    with pytest.raises(AccountActionError):
        bob_account_checking.logout()

    with pytest.raises(AccountActionError):
        bob_account_checking.login("5678")

    with pytest.raises(AccountActionError):
        bob_account_checking.get_transaction_history()

    bob_account_checking.login("1234")
    transaction_history = bob_account_checking.get_transaction_history()
    assert isinstance(transaction_history, list)


def test_account_operations():
    """Tests user account operations"""
    bank = Bank()
    bob_account_checking = bank.create_account("Bob", "1234", initial_balance=200)

    with pytest.raises(AccountActionError):
        bob_account_checking.deposit(300)

    bob_account_checking.login("1234")
    bob_account_checking.deposit(300)
    assert bob_account_checking.balance == 500

    with pytest.raises(AccountActionError):
        bob_account_checking.deposit(-300)

    with pytest.raises(AccountActionError):
        bob_account_checking.deposit(0)

    with pytest.raises(AccountActionError):
        bob_account_checking.deposit(10001)

    bob_account_checking.withdraw(100)
    assert bob_account_checking.balance == 400

    with pytest.raises(AccountActionError):
        bob_account_checking.withdraw(401)

    with pytest.raises(AccountActionError):
        bob_account_checking.withdraw(-10)


def test_transaction_history():
    """Tests transaction history generation"""
    bank = Bank()
    bob_account_checking = bank.create_account("Bob", "1234", initial_balance=200)
    bob_account_saving = bank.create_account(
        "Bob", "1234", initial_balance=0, account_type=SAVING
    )

    with pytest.raises(AccountActionError):
        bob_account_checking.get_transaction_history()

    bob_account_checking.login("1234")
    transaction_history = bob_account_checking.get_transaction_history()
    assert isinstance(transaction_history, list)

    bob_account_checking.deposit(300)
    bob_account_checking.withdraw(100)
    bank.self_transfer(bob_account_checking, 10)

    updated_history = bob_account_checking.get_transaction_history()
    assert len(updated_history) == 3

    deposit_entry = updated_history[-3]
    assert "Deposit: 300" in deposit_entry

    withdraw_entry = updated_history[-2]
    assert "Withdraw: 100" in withdraw_entry

    self_transaction_entry = updated_history[-1]
    assert "Sent 10 to your saving account" in self_transaction_entry

    bob_account_saving.login("1234")
    transaction_history_saving = bob_account_saving.get_transaction_history()
    assert "Received 10 from your checking account" in transaction_history_saving[-1]


def test_transfers_between_users():
    """Tests transfers between users"""
    bank = Bank()
    bob_account_checking = bank.create_account("Bob", "1234", initial_balance=200)

    with pytest.raises(OwnerNotFoundError):
        bank.transfer("Bob", "Meri", 20)

    bank.create_account("Meri", "1234", initial_balance=200, account_type=SAVING)

    with pytest.raises(AccountNotFoundError):
        bank.transfer("Bob", "Meri", 20)

    meri_account_checking = bank.create_account(
        "Meri", "1234", initial_balance=0, account_type=CHECKING
    )
    assert bank.transfer("Bob", "Meri", 20)

    bob_account_checking.login("1234")
    bob_transaction_history = bob_account_checking.get_transaction_history()
    assert "Sent 20 to Meri" in bob_transaction_history[-1]

    meri_account_checking.login("1234")
    meri_transaction_history = meri_account_checking.get_transaction_history()
    assert "Received 20 from Bob" in meri_transaction_history[-1]

    assert bob_account_checking.balance == 180
    assert meri_account_checking.balance == 20

    with pytest.raises(AmountError):
        bank.transfer("Meri", "Bob", 200)

    with pytest.raises(AmountError):
        bank.transfer("Bob", "Meri", -20)

    with pytest.raises(AmountError):
        bank.transfer("Bob", "Meri", 2000)

    with pytest.raises(BankActionError):
        bank.transfer("Meri", "Meri", 2)
