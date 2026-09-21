"""JSON storage helpers for accounts and transactions."""

import json
from pathlib import Path
from typing import Any

from src.account import Account


DEMO_ACCOUNTS = [
    Account("10001", "Hassan", "1234", 50000, "Savings"),
    Account("10002", "Ali", "5678", 30000, "Current"),
    Account("10003", "Ahmed", "1111", 75000, "Savings"),
]


class JsonStorage:
    """Load and save the small JSON data files used by the app."""

    def __init__(self, data_directory: Path) -> None:
        self.data_directory = data_directory
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.accounts_file = data_directory / "accounts.json"
        self.transactions_file = data_directory / "transactions.json"
        self.ensure_files()

    def ensure_files(self) -> None:
        if not self.accounts_file.exists():
            self.save_accounts({account.account_number: account for account in DEMO_ACCOUNTS})
        if not self.transactions_file.exists():
            self.transactions_file.write_text("[]", encoding="utf-8")

    def load_accounts(self) -> dict[str, Account]:
        try:
            data = json.loads(self.accounts_file.read_text(encoding="utf-8"))
            records = data if isinstance(data, list) else []
            demo_by_number = {account.account_number: account for account in DEMO_ACCOUNTS}
            accounts = {}
            for item in records:
                account_number = str(item["account_number"])
                if "account_type" not in item and account_number in demo_by_number:
                    item = {**item, "account_type": demo_by_number[account_number].account_type}
                accounts[account_number] = Account.from_dict(item)
            if accounts:
                changed = False
                for demo_account in DEMO_ACCOUNTS:
                    if demo_account.account_number not in accounts:
                        accounts[demo_account.account_number] = demo_account
                        changed = True
                if changed:
                    self.save_accounts(accounts)
                return accounts
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
        accounts = {account.account_number: account for account in DEMO_ACCOUNTS}
        self.save_accounts(accounts)
        return accounts

    def save_accounts(self, accounts: dict[str, Account]) -> None:
        records = [account.to_dict() for account in accounts.values()]
        self.accounts_file.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def load_transactions(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.transactions_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def save_transactions(self, transactions: list[dict[str, Any]]) -> None:
        self.transactions_file.write_text(json.dumps(transactions, indent=2), encoding="utf-8")
