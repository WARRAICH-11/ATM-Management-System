"""Account model and validation rules for the banking application."""

from dataclasses import dataclass
from datetime import date


@dataclass
class Account:
	"""Represent one customer account."""

	account_number: str
	account_holder: str
	pin: str
	balance: float
	account_type: str = "Savings"
	status: str = "Active"
	created_at: str = ""

	def __post_init__(self) -> None:
		self.account_number = str(self.account_number)
		self.pin = str(self.pin)
		self.created_at = self.created_at or date.today().isoformat()
		self._validate_pin(self.pin)
		if self.balance < 0:
			raise ValueError("Balance cannot be negative.")

	@staticmethod
	def _validate_pin(pin: str) -> None:
		if len(pin) != 4 or not pin.isdigit():
			raise ValueError("PIN must be exactly 4 digits.")

	def verify_pin(self, pin: str) -> bool:
		return self.pin == str(pin)

	def check_balance(self) -> float:
		return self.balance

	def deposit(self, amount: float) -> float:
		if amount <= 0:
			raise ValueError("Deposit amount must be greater than zero.")
		self.balance += amount
		return self.balance

	def withdraw(self, amount: float) -> float:
		if amount <= 0:
			raise ValueError("Withdrawal amount must be greater than zero.")
		if amount > self.balance:
			raise ValueError("Insufficient balance for this withdrawal.")
		self.balance -= amount
		return self.balance

	def change_pin(self, old_pin: str, new_pin: str) -> None:
		if not self.verify_pin(old_pin):
			raise ValueError("Current PIN is incorrect.")
		self._validate_pin(str(new_pin))
		if str(new_pin) == self.pin:
			raise ValueError("New PIN must be different from the old PIN.")
		self.pin = str(new_pin)

	def to_dict(self) -> dict[str, object]:
		return {
			"account_number": self.account_number,
			"account_holder": self.account_holder,
			"pin": self.pin,
			"balance": self.balance,
			"account_type": self.account_type,
			"status": self.status,
			"created_at": self.created_at,
		}

	@classmethod
	def from_dict(cls, data: dict[str, object]) -> "Account":
		return cls(
			account_number=str(data["account_number"]),
			account_holder=str(data["account_holder"]),
			pin=str(data["pin"]),
			balance=float(str(data["balance"])),
			account_type=str(data.get("account_type", "Savings")),
			status=str(data.get("status", "Active")),
			created_at=str(data.get("created_at", "")),
		)
