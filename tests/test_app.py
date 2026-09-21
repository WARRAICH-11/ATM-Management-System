import tempfile
import unittest
from pathlib import Path

from src.app import create_app


class AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(Path(self.temp_dir.name)).test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_login_and_protected_routes(self) -> None:
        login_page = self.app.get("/login")
        self.assertEqual(login_page.status_code, 200)
        login_page.close()
        self.assertEqual(self.app.get("/api/dashboard").status_code, 401)
        for path in ("/dashboard", "/transactions", "/transfer", "/money", "/profile", "/security"):
            self.assertEqual(self.app.get(path).status_code, 302)
            self.assertEqual(self.app.get(path).location, "/login")
        response = self.app.post("/api/login", json={"account_number": "10001", "pin": "1234"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.app.get("/api/dashboard").status_code, 200)
        for path in ("/dashboard", "/transactions", "/transfer", "/money", "/profile", "/security"):
            page = self.app.get(path)
            self.assertEqual(page.status_code, 200)
            page.close()

    def test_transfer_and_search(self) -> None:
        self.app.post("/api/login", json={"account_number": "10001", "pin": "1234"})
        response = self.app.post("/api/transfer", json={"receiver_account": "10002", "amount": 100})
        self.assertEqual(response.status_code, 200)
        records = self.app.get("/api/transactions?type=Transfer%20Sent")
        self.assertEqual(len(records.get_json()["transactions"]), 1)

    def test_each_page_renders_its_own_feature_content(self) -> None:
        self.app.post("/login", data={"account_number": "10001", "pin": "1234"})
        page_markers = {
            "/dashboard": "Recent transactions",
            "/transactions": "Transaction ID",
            "/transfer": "Send money",
            "/money": "Deposit money",
            "/profile": "Account profile",
            "/security": "Change PIN",
        }
        for path, marker in page_markers.items():
            response = self.app.get(path)
            body = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(marker, body)

        dashboard = self.app.get("/dashboard").get_data(as_text=True)
        self.assertNotIn("<form", dashboard)
        self.assertNotIn("<table", dashboard)

    def test_invalid_transfer_targets(self) -> None:
        self.app.post("/api/login", json={"account_number": "10001", "pin": "1234"})
        self.assertEqual(
            self.app.post("/api/transfer", json={"receiver_account": "10001", "amount": 100}).status_code,
            400,
        )
        self.assertEqual(
            self.app.post("/api/transfer", json={"receiver_account": "99999", "amount": 100}).status_code,
            400,
        )

    def test_logout(self) -> None:
        self.app.post("/api/login", json={"account_number": "10001", "pin": "1234"})
        self.app.post("/api/logout")
        self.assertEqual(self.app.get("/api/dashboard").status_code, 401)
        self.assertEqual(self.app.get("/logout").status_code, 302)
        self.assertEqual(self.app.get("/logout").location, "/login")


if __name__ == "__main__":
    unittest.main()
