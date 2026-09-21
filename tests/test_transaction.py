import tempfile
import unittest
from pathlib import Path

from src.transaction import Transaction, TransactionManager


class TransactionTestCase(unittest.TestCase):
    def test_transaction_creation(self) -> None:
        transaction = Transaction.create("10001", "Deposit", 5000, 55000)
        self.assertEqual(transaction.account_number, "10001")
        self.assertEqual(transaction.transaction_type, "Deposit")
        self.assertEqual(transaction.amount, 5000)

    def test_transaction_is_saved_and_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = TransactionManager(Path(directory) / "transactions.json")
            manager.add(Transaction.create("10001", "Deposit", 5000, 55000))
            records = manager.latest_for_account("10001")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].balance_after_transaction, 55000)


if __name__ == "__main__":
    unittest.main()