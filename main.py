"""Bank classes"""

import base64
from datetime import datetime
import hashlib
import os
from typing import Literal


def hash_password(password: str) -> dict[str, str]:
    """Generate a salted hash of a password"""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return {
        "salt": base64.b64encode(salt).decode(),
        "key": base64.b64encode(key).decode(),
    }


def verify_password(stored_hash: dict[str, str], password_to_check: str) -> bool:
    """Verifies password by comparing it to stored hash"""
    salt = base64.b64decode(stored_hash["salt"])
    stored_key = base64.b64decode(stored_hash["key"])
    new_key = hashlib.pbkdf2_hmac("sha256", password_to_check.encode(), salt, 100000)
    return new_key == stored_key


class OwnerNotFoundError(Exception):
    """Owner does not exist in the bank."""


class AccountNotFoundError(Exception):
    """Owner does not have the specified account type."""


class AmountError(Exception):
    """There's something wrong with the amounts"""


class AccountActionError(Exception):
    """There's something wrong with the actions performed by the user"""


class BankActionError(Exception):
    """There's something wrong with the actions performed by the user"""


DEPOSIT_LIMIT = 10000
DEPOSIT = "deposit"
WITHDRAW = "withdraw"
TRANSFER_SENT = "transfer sent"
TRANSFER_RECEIVED = "transfer received"
SELF_TRANSFER_SENT = "self transfer sent"
SELF_TRANSFER_RECEIVED = "self transfer received"
CHECKING = "checking"
SAVING = "saving"

AccountType = Literal["checking", "saving"]


class BankAccount:
    """Performs all the actions that the user can do with its account"""

    def __init__(
        self,
        owner: str,
        balance: int = 0,
        password: str = "",
        account_type: AccountType = CHECKING,
    ):

        self.owner = owner
        self.password = password
        self.balance = balance
        self.transaction_history = []
        self.account_type = account_type
        self._logged_in = False

    def __str__(self):
        return (
            f"{self.owner}'s {self.account_type} account with balance: {self.balance}"
        )

    def login(self, password: str) -> bool:
        """Logs the user in if password is correct"""

        if verify_password(self.password, password):
            self._logged_in = True
            return True
        raise AccountActionError("Invalid password")

    def logout(self) -> bool:
        """Logs the user out"""
        if self._logged_in:
            self._logged_in = False
            return True
        raise AccountActionError("You are already logged out")

    def is_logged_in(self) -> bool:
        """Checks if user is logged in"""
        return self._logged_in

    def deposit(self, amount: int) -> bool:
        """Deposits money in the user's balance"""
        if not self._logged_in:
            raise AccountActionError(
                "You must be logged in to operate with your account"
            )

        if amount <= 0:
            raise AccountActionError(
                "Deposit amount must be positive and greater than 0"
            )
        if amount > DEPOSIT_LIMIT:
            raise AccountActionError("Deposit amount exceeds limit")

        self.set_transaction_history(DEPOSIT, amount)
        self.balance += amount
        return True

    def withdraw(self, amount: int) -> bool:
        """Withdraws money from the user's balance"""
        if not self._logged_in:
            raise AccountActionError(
                "You must be logged in to operate with your account"
            )
        if amount <= 0:
            raise AccountActionError(
                "Deposit amount must be positive and greater than 0"
            )
        if self.balance - amount < 0:
            raise AccountActionError("Insufficient funds")
        self.balance -= amount
        self.set_transaction_history(WITHDRAW, amount)
        return True

    def get_transaction_history(self) -> list:
        """Returns the user's account transaction history"""
        if not self._logged_in:
            raise AccountActionError(
                "You must be logged in to operate with your account"
            )
        return self.transaction_history

    def set_transaction_history(
        self, transaction_type: str, amount: int, account: "BankAccount" = None
    ) -> None:
        """Sets the user's account transaction history"""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if transaction_type == DEPOSIT:
            self.transaction_history.append(f"{timestamp} - Deposit: {amount}")
        elif transaction_type == WITHDRAW:
            self.transaction_history.append(f"{timestamp} - Withdraw: {amount}")

        elif transaction_type == TRANSFER_SENT:
            self.transaction_history.append(
                f"{timestamp} - Sent {amount} to {account.owner}"
            )
        elif transaction_type == TRANSFER_RECEIVED:
            self.transaction_history.append(
                f"{timestamp} - Received {amount} from {account.owner}"
            )
        elif transaction_type == SELF_TRANSFER_SENT:
            self.transaction_history.append(
                f"{timestamp} - Sent {amount} to your {account.account_type} account"
            )
        elif transaction_type == SELF_TRANSFER_RECEIVED:
            self.transaction_history.append(
                f"{timestamp} - Received {amount} from your {account.account_type} account"
            )
        else:
            raise AccountActionError(
                "Invalid transaction type or missing account for transfer."
            )


class Bank:
    """Manages the whole bank app"""

    def __init__(self):
        self.users: dict[str, UserProfile] = {}

    def create_account(
        self,
        owner: str,
        password: str,
        initial_balance: int = 0,
        account_type: AccountType = CHECKING,
    ) -> BankAccount:
        """Creates a new bank account"""

        if password == "":
            raise BankActionError("Please provide a password")
        if owner not in self.users:
            self.users[owner] = UserProfile(owner)

        if self.users[owner].has_account_type(account_type):
            raise BankActionError(
                f"{account_type.capitalize()} account for {owner} already exists"
            )

        new_account = BankAccount(
            owner, initial_balance, hash_password(password), account_type
        )
        self.users[owner].add_account(new_account)

        return new_account

    def get_account(
        self, owner: str, account_type: AccountType = CHECKING
    ) -> BankAccount:
        """Gets the specified type bank account for the specified owner"""

        if owner not in self.users:
            raise OwnerNotFoundError(f"No account found for client '{owner}'.")

        if not self.users[owner].has_account_type(account_type):
            raise AccountNotFoundError(
                f"{owner} doesn't have a {account_type}'s account"
            )

        return self.users[owner].get_account(account_type)

    # Transfers between users only allowed from checking to checking account
    # This should be using BankAccount objects instead of strings
    def transfer(self, payer: str, recipient: str, amount: int) -> bool:
        """If conditions are passed makes a transfer between users"""

        if payer == recipient:
            raise BankActionError("You cannot transfer to yourself")
        if payer not in self.users or recipient not in self.users:
            raise OwnerNotFoundError("One or both accounts don't exist")

        if not self.users[payer].has_account_type(CHECKING):
            raise AccountNotFoundError(f"{payer} doesn't have a checking's account")
        if not self.users[recipient].has_account_type(CHECKING):
            raise AccountNotFoundError(f"{recipient} doesn't have a checking's account")

        payer_checking_acc: BankAccount = self.users[payer].get_account(CHECKING)
        recipient_checking_acc: BankAccount = self.users[recipient].get_account(
            CHECKING
        )

        if payer_checking_acc.balance < amount:
            raise AmountError("Balance is not enough")
        if amount <= 0:
            raise AmountError("Amount needs to be a positive number bigger than 0")

        payer_checking_acc.balance -= amount
        recipient_checking_acc.balance += amount

        payer_checking_acc.set_transaction_history(
            TRANSFER_SENT, amount, recipient_checking_acc
        )
        recipient_checking_acc.set_transaction_history(
            TRANSFER_RECEIVED, amount, payer_checking_acc
        )

        return True

    def self_transfer(self, origin_account: BankAccount, amount: int) -> bool:
        """Transfers funds between a user's accounts"""

        user_profile = self.users[origin_account.owner]
        destination_account = (
            user_profile.get_account(CHECKING)
            if origin_account.account_type == SAVING
            else user_profile.get_account(SAVING)
        )
        if origin_account.balance < amount:
            raise AccountActionError(
                f"Insufficient funds in your {origin_account.account_type}'s account"
            )
        origin_account.balance -= amount
        destination_account.balance += amount

        origin_account.set_transaction_history(
            SELF_TRANSFER_SENT, amount, destination_account
        )
        destination_account.set_transaction_history(
            SELF_TRANSFER_RECEIVED, amount, origin_account
        )

        return True


class UserProfile:
    """Organizer for all the accounts that belong to a user"""

    def __init__(self, owner: str):
        self.owner = owner
        self.accounts = {}

    def has_account_type(self, account_type) -> bool:
        """Checks if user has account of the specified type"""
        return account_type in self.accounts

    def get_account(self, account_type) -> BankAccount:
        """Retrieves an account"""
        if self.accounts.get(account_type):
            return self.accounts.get(account_type)
        raise AccountNotFoundError(
            f"There's no {account_type} account for {self.owner}"
        )

    def add_account(self, account: BankAccount) -> None:
        """Adds an account"""
        self.accounts[account.account_type] = account
