# Personal Banking System

A beginner-friendly Flask banking application with JSON persistence and real server-rendered pages.

## Features

- Session login with three failed PIN attempts and temporary lockout
- Separate Dashboard, Transactions, Transfer, Money, Profile, and Security pages
- Deposits, withdrawals, transfers, PIN changes, and logout
- Searchable and filterable transaction history
- CSV statement download
- Multiple demo accounts
- JSON-only persistence with no database

## Project Structure

```text
src/
  app.py          Flask routes, API endpoints, and form handlers
  main.py         Main web/console entry point
  account.py      Account model and validation
  transaction.py  Transaction model and JSON history
  storage.py      JSON persistence

templates/
  base.html
  login.html
  dashboard.html
  transactions.html
  transfer.html
  money.html
  profile.html
  security.html

static/
  style.css

data/
  accounts.json
  transactions.json

tests/
```

Each authenticated route renders its own template. The Dashboard is overview-only; feature forms are not embedded in it.

## Installation

```powershell
py -m pip install -r requirements.txt
```

## Run the Web Application

```powershell
py -m src.main
```

Open http://127.0.0.1:8000/login.

The compatibility launcher also works:

```powershell
py -m src.api
```

The original console workflow remains available with:

```powershell
py -m src.main --console
```

## Demo Accounts

| Account | Name | PIN | Type | Balance |
| --- | --- | --- | --- | ---: |
| 10001 | Hassan | 1234 | Savings | Rs. 50,000 |
| 10002 | Ali | 5678 | Current | Rs. 30,000 |
| 10003 | Ahmed | 1111 | Savings | Rs. 75,000 |

These credentials are for local demonstration only.

## Test

```powershell
py -m unittest discover
```
