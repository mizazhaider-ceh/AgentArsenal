#!/usr/bin/env python3
"""Check numbers with the Luhn algorithm.

Validates credit card numbers, IMEI numbers, and similar identifiers that
use the Luhn checksum. Spaces and dashes are ignored.

Usage:
    luhn-checker.py 4532015112830366
    luhn-checker.py 356938035643809
"""

import argparse
import re
import sys


def luhn_ok(number):
    digits = [int(d) for d in number]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def check_digit(partial):
    for d in range(10):
        if luhn_ok(partial + str(d)):
            return str(d)
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate numbers with the Luhn checksum (cards, IMEI, etc).",
        epilog="Examples:\n"
               "  luhn-checker.py 4532015112830366\n"
               "  luhn-checker.py 4532-0151-1283-0366\n"
               "  luhn-checker.py 453201511283036 --complete",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("numbers", nargs="+", help="numbers to check")
    parser.add_argument("--complete", action="store_true",
                        help="compute the missing check digit instead of validating")
    args = parser.parse_args(argv)

    failed = False
    for raw in args.numbers:
        cleaned = re.sub(r"[\s-]", "", raw)
        if not cleaned.isdigit():
            print("Error: %r contains non-digit characters" % raw, file=sys.stderr)
            failed = True
            continue
        if args.complete:
            digit = check_digit(cleaned)
            print("%s -> check digit: %s (full: %s%s)" % (cleaned, digit, cleaned, digit))
        else:
            ok = luhn_ok(cleaned)
            print("%s  [%s]" % (cleaned, "VALID" if ok else "INVALID"))
            if not ok:
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
