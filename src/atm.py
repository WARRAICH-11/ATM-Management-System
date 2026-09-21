"""Console ATM workflow and JSON account persistence."""

import json
from pathlib import Path

from src.account import Account
from src.transaction import Transaction, TransactionManager


class ATM:
	"""Coordinate login, account operations, and transaction history."""

	def __init__(self, data_directory: Path | None = None) -> None:
		project_root = Path(__file__).resolve().parent.parent
		self.data_directory = data_directory or project_root / "data"
		self.data_directory.mkdir(parents=True, exist_ok=True)
		self.accounts_file = self.data_directory / "accounts.json"
		self.transaction_manager = TransactionManager(
			self.data_directory / "transactions.json"
		)
		self.accounts = self._load_accounts()

	def _load_accounts(self) -> dict[str, Account]:
		if not self.accounts_file.exists():
			accounts = {
				"10001": Account("10001", "Hassan", "1234", 50000),
				"10002": Account("10002", "Ali", "5678", 30000),
			}
			self._save_accounts(accounts)
			return accounts

		try:
			with self.accounts_file.open("r", encoding="utf-8") as file:
				stored_accounts = json.load(file)
			return {
				str(data["account_number"]): Account.from_dict(data)
				for data in stored_accounts
			}
		except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
			print("Account data could not be read. Starting with demo accounts.")
			accounts = {
				"10001": Account("10001", "Hassan", "1234", 50000),
				"10002": Account("10002", "Ali", "5678", 30000),
			}
			self._save_accounts(accounts)
			return accounts

	def _save_accounts(self, accounts: dict[str, Account] | None = None) -> None:
		accounts_to_save = accounts or self.accounts
		with self.accounts_file.open("w", encoding="utf-8") as file:
			json.dump(
				[account.to_dict() for account in accounts_to_save.values()],
				file,
				indent=2,
			)

	def login(self) -> Account | None:
		"""Authenticate an account with up to three PIN attempts."""
		account_number = input("Enter account number: ").strip()
		account = self.accounts.get(account_number)
		if account is None:
			print("Account number not found.")
			return None

		for attempt in range(3):
			pin = input("Enter PIN: ").strip()
			if account.verify_pin(pin):
				print(f"\nWelcome, {account.account_holder}!")
				return account
			remaining = 2 - attempt
			if remaining:
				print(f"Incorrect PIN. {remaining} attempt(s) remaining.")

		print("Too many incorrect PIN attempts. Session terminated.")
		return None

	@staticmethod
	def _read_amount(prompt: str) -> float | None:
		try:
			amount = float(input(prompt).strip())
		except ValueError:
			print("Please enter a valid number.")
			return None
		return amount

	def _deposit(self, account: Account) -> None:
		amount = self._read_amount("Enter deposit amount: ")
		if amount is None:
			return
		try:
			new_balance = account.deposit(amount)
		except ValueError as error:
			print(error)
			return
		self._record_transaction(account, "Deposit", amount, new_balance)
		self._save_accounts()
		print(f"Rs. {amount:,.2f} deposited successfully.")
		print(f"New Balance: Rs. {new_balance:,.2f}")

	def _withdraw(self, account: Account) -> None:
		amount = self._read_amount("Enter withdrawal amount: ")
		if amount is None:
			return
		try:
			new_balance = account.withdraw(amount)
		except ValueError as error:
			print(error)
			return
		self._record_transaction(account, "Withdrawal", amount, new_balance)
		self._save_accounts()
		print(f"Please collect your cash: Rs. {amount:,.2f}")
		print(f"Remaining Balance: Rs. {new_balance:,.2f}")

	def _change_pin(self, account: Account) -> None:
		old_pin = input("Enter current PIN: ").strip()
		new_pin = input("Enter new PIN: ").strip()
		confirmation = input("Confirm new PIN: ").strip()
		if new_pin != confirmation:
			print("New PIN and confirmation do not match.")
			return
		try:
			account.change_pin(old_pin, new_pin)
		except ValueError as error:
			print(error)
			return
		self._save_accounts()
		print("PIN changed successfully.")

	def _show_statement(self, account: Account) -> None:
		transactions = self.transaction_manager.latest_for_account(
			account.account_number
		)
		print("\n========== MINI STATEMENT ==========")
		if not transactions:
			print("No transactions yet.")
		for transaction in transactions:
			print(f"{transaction.transaction_type:<12} Rs. {transaction.amount:,.2f}")
		print("-------------------------------------")
		print(f"Current Balance: Rs. {account.balance:,.2f}")
		print("=====================================")

	def _record_transaction(
		self, account: Account, transaction_type: str, amount: float, balance: float
	) -> None:
		self.transaction_manager.add(
			Transaction.create(account.account_number, transaction_type, amount, balance)
		)

	def show_menu(self, account: Account) -> None:
		"""Display the menu and handle operations until logout."""
		while True:
			print("\n========== ATM MENU ==========")
			print("1. Check Balance")
			print("2. Deposit Money")
			print("3. Withdraw Money")
			print("4. Change PIN")
			print("5. Mini Statement")
			print("6. Logout")
			print("===============================")
			choice = input("Choose an option: ").strip()
			if choice == "1":
				print(f"Current Balance: Rs. {account.balance:,.2f}")
			elif choice == "2":
				self._deposit(account)
			elif choice == "3":
				self._withdraw(account)
			elif choice == "4":
				self._change_pin(account)
			elif choice == "5":
				self._show_statement(account)
			elif choice == "6":
				print("Thank you for using the ATM. Goodbye!")
				return
			else:
				print("Invalid option. Please choose a number from 1 to 6.")

	def run(self) -> None:
		"""Run one login session."""
		print("==============================")
		print("       ATM MANAGEMENT SYSTEM")
		print("==============================")
		account = self.login()
		if account is not None:
			self.show_menu(account)
