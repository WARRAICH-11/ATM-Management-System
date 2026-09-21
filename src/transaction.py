"""Transaction records and JSON transaction history management."""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Transaction:
	"""Represent one account activity."""

	account_number: str
	transaction_type: str
	amount: float
	date_time: str
	balance_after_transaction: float
	transaction_id: str = ""
	description: str = ""
	related_account: str = ""

	@property
	def balance_after(self) -> float:
		return self.balance_after_transaction

	@classmethod
	def create(
		cls,
		account_number: str,
		transaction_type: str,
		amount: float,
		balance_after_transaction: float,
		description: str = "",
		related_account: str = "",
	) -> "Transaction":
		return cls(
			account_number=str(account_number),
			transaction_type=transaction_type,
			amount=amount,
			date_time=datetime.now().isoformat(timespec="seconds"),
			balance_after_transaction=balance_after_transaction,
			transaction_id=uuid.uuid4().hex[:10].upper(),
			description=description or transaction_type,
			related_account=related_account,
		)


class TransactionManager:
	"""Read, write, and filter transaction history in a JSON file."""

	def __init__(self, file_path: Path) -> None:
		self.file_path = file_path
		self.file_path.parent.mkdir(parents=True, exist_ok=True)
		if not self.file_path.exists():
			self._save([])

	def _load(self) -> list[dict[str, object]]:
		try:
			with self.file_path.open("r", encoding="utf-8") as file:
				data = json.load(file)
			return data if isinstance(data, list) else []
		except (json.JSONDecodeError, OSError):
			return []

	def _save(self, transactions: list[dict[str, object]]) -> None:
		with self.file_path.open("w", encoding="utf-8") as file:
			json.dump(transactions, file, indent=2)

	def add(self, transaction: Transaction) -> None:
		transactions = self._load()
		transactions.append(asdict(transaction))
		self._save(transactions)

	def latest_for_account(self, account_number: str, limit: int = 5) -> list[Transaction]:
		records = [
			Transaction(
				account_number=str(record["account_number"]),
				transaction_type=str(record["transaction_type"]),
				amount=float(str(record["amount"])),
				date_time=str(record["date_time"]),
				balance_after_transaction=float(str(record.get("balance_after_transaction", record.get("balance_after", 0)))),
				transaction_id=str(record.get("transaction_id", uuid.uuid4().hex[:10].upper())),
				description=str(record.get("description", record.get("transaction_type", "Transaction"))),
				related_account=str(record.get("related_account", "")),
			)
			for record in self._load()
			if str(record.get("account_number")) == str(account_number)
		]
		return records[-limit:]
