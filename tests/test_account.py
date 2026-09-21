import unittest

from src.account import Account


class AccountTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.account = Account("10001", "Hassan", "1234", 50000)

    def test_pin_verification(self) -> None:
        self.assertTrue(self.account.verify_pin("1234"))
        self.assertFalse(self.account.verify_pin("0000"))

    def test_deposit(self) -> None:
        self.assertEqual(self.account.deposit(5000), 55000)

    def test_withdrawal(self) -> None:
        self.assertEqual(self.account.withdraw(2000), 48000)

    def test_insufficient_balance(self) -> None:
        with self.assertRaises(ValueError):
            self.account.withdraw(60000)

    def test_pin_change(self) -> None:
        self.account.change_pin("1234", "4321")
        self.assertTrue(self.account.verify_pin("4321"))


if __name__ == "__main__":
    unittest.main()