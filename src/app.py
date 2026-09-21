"""Flask web application for the Personal Banking System."""

import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from src.account import Account
from src.storage import JsonStorage
from src.transaction import Transaction


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIRECTORY = PROJECT_ROOT / "templates"
STATIC_DIRECTORY = PROJECT_ROOT / "static"


def create_app(data_directory: Path | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIRECTORY),
        static_folder=str(STATIC_DIRECTORY),
    )
    app.config["SECRET_KEY"] = "personal-banking-demo-secret"
    storage = JsonStorage(data_directory or PROJECT_ROOT / "data")
    accounts = storage.load_accounts()
    failed_attempts: dict[str, int] = {}
    locked_until: dict[str, datetime] = {}

    def current_account() -> Account | None:
        account_number = session.get("account_number")
        return accounts.get(str(account_number)) if account_number else None

    def account_payload(account: Account) -> dict[str, Any]:
        return {"account_number": account.account_number, "account_holder": account.account_holder,
                "balance": account.balance, "account_type": account.account_type,
                "status": account.status, "created_at": account.created_at}

    def all_transactions(account_number: str) -> list[dict[str, Any]]:
        records = [record for record in storage.load_transactions()
                   if str(record.get("account_number")) == account_number]
        return sorted(records, key=lambda item: str(item.get("date_time", "")), reverse=True)

    def add_transaction(account: Account, transaction_type: str, amount: float,
                        description: str, related_account: str = "") -> None:
        records = storage.load_transactions()
        transaction = Transaction.create(account.account_number, transaction_type, amount,
                                         account.balance, description, related_account)
        records.append(transaction.__dict__)
        storage.save_transactions(records)

    def json_error(message: str, status: int = 400):
        return jsonify({"error": message}), status

    def protected(function: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any):
            if current_account() is None:
                return json_error("Please log in first.", 401)
            return function(*args, **kwargs)
        wrapper.__name__ = function.__name__
        return wrapper

    def page_protected(function: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any):
            if current_account() is None:
                return redirect("/login")
            return function(*args, **kwargs)
        wrapper.__name__ = function.__name__
        return wrapper

    def page_context(account: Account) -> dict[str, Any]:
        return {"account": account, "active_page": request.endpoint}

    def dashboard_data(account: Account) -> dict[str, Any]:
        records = all_transactions(account.account_number)
        stats = {
            "deposits": sum(float(r.get("amount", 0)) for r in records if r.get("transaction_type") == "Deposit"),
            "withdrawals": sum(float(r.get("amount", 0)) for r in records if r.get("transaction_type") == "Withdrawal"),
            "transfers": sum(float(r.get("amount", 0)) for r in records if r.get("transaction_type") in ("Transfer Sent", "Transfer Received")),
        }
        return {"stats": stats, "recent_transactions": records[:5]}

    def filtered_transactions(account_number: str) -> list[dict[str, Any]]:
        records = all_transactions(account_number)
        search = request.args.get("search", "").lower().strip()
        kind = request.args.get("type", "All")
        period = request.args.get("period", "All Time")
        today = datetime.now().date()
        if search:
            records = [
                record for record in records
                if search in " ".join(
                    str(record.get(key, ""))
                    for key in ("transaction_id", "transaction_type", "description")
                ).lower()
            ]
        if kind != "All":
            records = [record for record in records if record.get("transaction_type") == kind]
        if period != "All Time":
            days = {"Today": 0, "This Week": 7, "This Month": 31}.get(period)
            if days is not None:
                records = [
                    record for record in records
                    if (today - datetime.fromisoformat(str(record["date_time"])).date()).days <= days
                ]
        return records

    @app.get("/")
    def index():
        return redirect("/dashboard" if current_account() else "/login")

    @app.route("/login", methods=["GET", "POST"])
    def login_page():
        if current_account():
            return redirect(url_for("dashboard_page"))
        if request.method == "POST":
            account_number = request.form.get("account_number", "").strip()
            pin = request.form.get("pin", "").strip()
            account = accounts.get(account_number)
            now = datetime.now()
            if account_number in locked_until and locked_until[account_number] > now:
                flash("Account is temporarily locked. Try again later.", "error")
            elif account is None:
                flash("Invalid account number.", "error")
            elif not account.verify_pin(pin):
                failed_attempts[account_number] = failed_attempts.get(account_number, 0) + 1
                if failed_attempts[account_number] >= 3:
                    locked_until[account_number] = now + timedelta(minutes=5)
                    failed_attempts[account_number] = 0
                    flash("Account is temporarily locked after 3 failed attempts.", "error")
                else:
                    remaining = 3 - failed_attempts[account_number]
                    flash(f"Incorrect PIN. {remaining} attempt(s) remaining.", "error")
            else:
                failed_attempts.pop(account_number, None)
                session.clear()
                session["account_number"] = account_number
                flash(f"Welcome, {account.account_holder}!", "success")
                return redirect(url_for("dashboard_page"))
        return render_template("login.html")

    @app.get("/dashboard")
    @page_protected
    def dashboard_page():
        account = current_account()
        return render_template("dashboard.html", **page_context(account), **dashboard_data(account))

    @app.get("/transactions")
    @page_protected
    def transactions_page():
        account = current_account()
        return render_template(
            "transactions.html",
            **page_context(account),
            transactions=filtered_transactions(account.account_number),
            search=request.args.get("search", ""),
            selected_type=request.args.get("type", "All"),
            selected_period=request.args.get("period", "All Time"),
        )

    @app.route("/transfer", methods=["GET", "POST"])
    @page_protected
    def transfer_page():
        account = current_account()
        if request.method == "POST":
            receiver_number = request.form.get("receiver_account", "").strip()
            receiver = accounts.get(receiver_number)
            try:
                amount = float(request.form.get("amount", ""))
                if receiver is None:
                    raise ValueError("Receiver account not found.")
                if receiver is account:
                    raise ValueError("You cannot transfer money to your own account.")
                account.withdraw(amount)
                receiver.deposit(amount)
            except (TypeError, ValueError) as error:
                flash(str(error) or "Please enter a valid amount.", "error")
            else:
                add_transaction(account, "Transfer Sent", amount, f"Transfer to {receiver.account_holder}", receiver.account_number)
                add_transaction(receiver, "Transfer Received", amount, f"Transfer from {account.account_holder}", account.account_number)
                storage.save_accounts(accounts)
                flash(f"Transfer successful. Rs. {amount:,.2f} sent to {receiver.account_holder}.", "success")
                return redirect(url_for("transfer_page"))
        return render_template("transfer.html", **page_context(account))

    @app.route("/money", methods=["GET", "POST"])
    @page_protected
    def money_page():
        account = current_account()
        if request.method == "POST":
            action = request.form.get("action", "")
            try:
                amount = float(request.form.get("amount", ""))
                if action == "deposit":
                    new_balance = account.deposit(amount)
                    message = f"Rs. {amount:,.2f} deposited successfully. New balance: Rs. {new_balance:,.2f}"
                    transaction_type = "Deposit"
                    description = "Money deposited"
                elif action == "withdraw":
                    new_balance = account.withdraw(amount)
                    message = f"Rs. {amount:,.2f} withdrawn successfully. Remaining balance: Rs. {new_balance:,.2f}"
                    transaction_type = "Withdrawal"
                    description = "Cash withdrawal"
                else:
                    raise ValueError("Choose a valid money operation.")
            except (TypeError, ValueError) as error:
                flash(str(error) or "Please enter a valid amount.", "error")
            else:
                add_transaction(account, transaction_type, amount, description)
                storage.save_accounts(accounts)
                flash(message, "success")
                return redirect(url_for("money_page"))
        return render_template("money.html", **page_context(account))

    @app.get("/profile")
    @page_protected
    def profile_page():
        return render_template("profile.html", **page_context(current_account()))

    @app.route("/security", methods=["GET", "POST"])
    @page_protected
    def security_page():
        account = current_account()
        if request.method == "POST":
            if request.form.get("new_pin", "") != request.form.get("confirmation", ""):
                flash("New PIN and confirmation do not match.", "error")
            else:
                try:
                    account.change_pin(request.form.get("old_pin", ""), request.form.get("new_pin", ""))
                except ValueError as error:
                    flash(str(error), "error")
                else:
                    storage.save_accounts(accounts)
                    flash("PIN changed successfully.", "success")
                    return redirect(url_for("security_page"))
        return render_template("security.html", **page_context(account))

    @app.get("/logout")
    def logout_page():
        session.clear()
        return redirect("/login")

    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True) or {}
        account_number = str(data.get("account_number", "")).strip()
        pin = str(data.get("pin", "")).strip()
        account = accounts.get(account_number)
        now = datetime.now()
        if account_number in locked_until and locked_until[account_number] > now:
            return json_error("Account is temporarily locked. Try again later.", 423)
        if account is None:
            return json_error("Invalid account number.", 401)
        if not account.verify_pin(pin):
            failed_attempts[account_number] = failed_attempts.get(account_number, 0) + 1
            if failed_attempts[account_number] >= 3:
                locked_until[account_number] = now + timedelta(minutes=5)
                failed_attempts[account_number] = 0
                return json_error("Account is temporarily locked after 3 failed attempts.", 423)
            remaining = 3 - failed_attempts[account_number]
            return json_error(f"Incorrect PIN. {remaining} attempt(s) remaining.", 401)
        failed_attempts.pop(account_number, None)
        session.clear()
        session["account_number"] = account_number
        return jsonify({"message": f"Welcome, {account.account_holder}!", **account_payload(account)})

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify({"message": "Logged out successfully."})

    @app.get("/api/session")
    @protected
    def get_session():
        return jsonify(account_payload(current_account()))

    @app.get("/api/dashboard")
    @protected
    def dashboard():
        account = current_account()
        records = all_transactions(account.account_number)
        stats = {"deposits": sum(float(r.get("amount", 0)) for r in records if r.get("transaction_type") == "Deposit"),
                 "withdrawals": sum(float(r.get("amount", 0)) for r in records if r.get("transaction_type") == "Withdrawal"),
                 "transfers": sum(float(r.get("amount", 0)) for r in records if r.get("transaction_type") in ("Transfer Sent", "Transfer Received")),
                 "transaction_count": len(records)}
        return jsonify({"account": account_payload(account), "stats": stats, "recent_transactions": records[:5]})

    @app.get("/api/transactions")
    @protected
    def transactions():
        account = current_account()
        records = all_transactions(account.account_number)
        search = request.args.get("search", "").lower().strip()
        kind = request.args.get("type", "All")
        period = request.args.get("period", "All Time")
        today = datetime.now().date()
        if search:
            records = [r for r in records if search in " ".join(str(r.get(key, "")) for key in ("transaction_id", "transaction_type", "description")).lower()]
        if kind != "All":
            records = [r for r in records if r.get("transaction_type") == kind]
        if period != "All Time":
            days = {"Today": 0, "This Week": 7, "This Month": 31}.get(period)
            if days is not None:
                records = [r for r in records if (today - datetime.fromisoformat(str(r["date_time"])).date()).days <= days]
        return jsonify({"transactions": records})

    @app.get("/api/statement")
    @protected
    def statement():
        return jsonify({"transactions": all_transactions(current_account().account_number)[:5]})

    @app.get("/api/download-statement")
    @protected
    def download_statement():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Transaction ID", "Type", "Description", "Amount", "Balance"])
        for record in all_transactions(current_account().account_number):
            writer.writerow([record.get("date_time", ""), record.get("transaction_id", ""), record.get("transaction_type", ""), record.get("description", ""), record.get("amount", 0), record.get("balance_after_transaction", record.get("balance_after", 0))])
        response = app.response_class(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=statement.csv"
        return response

    def amount_from_request() -> float:
        value = (request.get_json(silent=True) or {}).get("amount")
        amount = float(value)
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        return amount

    @app.post("/api/deposit")
    @protected
    def deposit():
        account = current_account()
        try:
            amount = amount_from_request()
            account.deposit(amount)
        except (TypeError, ValueError):
            return json_error("Please enter a valid amount greater than zero.")
        add_transaction(account, "Deposit", amount, "Money deposited")
        storage.save_accounts(accounts)
        return jsonify({"message": "Deposit successful.", **account_payload(account)})

    @app.post("/api/withdraw")
    @protected
    def withdraw():
        account = current_account()
        try:
            amount = amount_from_request()
            account.withdraw(amount)
        except ValueError as error:
            return json_error(str(error))
        except (TypeError, ValueError):
            return json_error("Please enter a valid amount greater than zero.")
        add_transaction(account, "Withdrawal", amount, "Cash withdrawal")
        storage.save_accounts(accounts)
        return jsonify({"message": "Withdrawal successful.", **account_payload(account)})

    @app.post("/api/transfer")
    @protected
    def transfer():
        sender = current_account()
        data = request.get_json(silent=True) or {}
        receiver_number = str(data.get("receiver_account", "")).strip()
        receiver = accounts.get(receiver_number)
        if receiver is None:
            return json_error("Receiver account not found.")
        if receiver is sender:
            return json_error("You cannot transfer money to your own account.")
        try:
            amount = float(data.get("amount"))
            sender.withdraw(amount)
        except (TypeError, ValueError) as error:
            return json_error(str(error) or "Please enter a valid amount.")
        receiver.deposit(amount)
        add_transaction(sender, "Transfer Sent", amount, f"Transfer to {receiver.account_holder}", receiver.account_number)
        add_transaction(receiver, "Transfer Received", amount, f"Transfer from {sender.account_holder}", sender.account_number)
        storage.save_accounts(accounts)
        return jsonify({"message": f"Transfer successful. Rs. {amount:,.2f} sent to {receiver.account_holder}.", **account_payload(sender)})

    @app.post("/api/change-pin")
    @protected
    def change_pin():
        account = current_account()
        data = request.get_json(silent=True) or {}
        new_pin = str(data.get("new_pin", ""))
        if new_pin != str(data.get("confirmation", "")):
            return json_error("New PIN and confirmation do not match.")
        try:
            account.change_pin(str(data.get("old_pin", "")), new_pin)
        except ValueError as error:
            return json_error(str(error))
        storage.save_accounts(accounts)
        return jsonify({"message": "PIN changed successfully."})

    return app


app = create_app()
