"""Application entry point for the web and console applications."""

import argparse

from src.app import app
from src.atm import ATM


def main() -> None:
	parser = argparse.ArgumentParser(description="Personal Banking System")
	parser.add_argument("--console", action="store_true", help="run the original console ATM")
	args = parser.parse_args()
	if args.console:
		ATM().run()
	else:
		app.run(host="127.0.0.1", port=8000, debug=False)


if __name__ == "__main__":
	main()
