import argparse
import sys
from statement import *

def main():
    parser = argparse.ArgumentParser(
        description="Parse a Chase PDF statement into a CSV."
    )

    parser.add_argument(
        "statement_path",
        help="Path to the Chase PDF statement"
    )

    parser.add_argument(
        "--first-page",
        type=int,
        default=3,
        help="Index of the first transaction page (default: 3)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        print(f"Input statement: {args.statement_path}")
        print(f"Using first transaction page index: {args.first_page}")

    try:
        parse_chase_statement(args.statement_path, first_page_idx=args.first_page)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
