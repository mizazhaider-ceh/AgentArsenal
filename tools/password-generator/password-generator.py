#!/usr/bin/env python3
"""Generate random passwords with the secrets module.

Uses cryptographically strong randomness. Choose a character set and length,
or generate several at once.

Usage:
    password-generator.py
    password-generator.py -l 24 -n 5 --no-symbols
"""

import argparse
import secrets
import string
import sys


def build_alphabet(use_lower, use_upper, use_digits, use_symbols):
    alphabet = ""
    if use_lower:
        alphabet += string.ascii_lowercase
    if use_upper:
        alphabet += string.ascii_uppercase
    if use_digits:
        alphabet += string.digits
    if use_symbols:
        alphabet += "!@#$%^&*()-_=+[]{};:,.<>?"
    return alphabet


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate random passwords using cryptographically strong randomness.",
        epilog="Examples:\n"
               "  password-generator.py\n"
               "  password-generator.py -l 24 -n 5\n"
               "  password-generator.py --no-symbols --no-upper -l 12",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-l", "--length", type=int, default=16,
                        help="password length (default: 16)")
    parser.add_argument("-n", "--number", type=int, default=1,
                        help="how many passwords to print (default: 1)")
    parser.add_argument("--no-lower", action="store_true", help="exclude lowercase letters")
    parser.add_argument("--no-upper", action="store_true", help="exclude uppercase letters")
    parser.add_argument("--no-digits", action="store_true", help="exclude digits")
    parser.add_argument("--no-symbols", action="store_true", help="exclude symbols")
    args = parser.parse_args(argv)

    if args.length < 1:
        parser.error("--length must be at least 1")
    if args.number < 1:
        parser.error("--number must be at least 1")

    alphabet = build_alphabet(not args.no_lower, not args.no_upper,
                              not args.no_digits, not args.no_symbols)
    if not alphabet:
        parser.error("you excluded every character set, nothing left to use")

    for _ in range(args.number):
        print("".join(secrets.choice(alphabet) for _ in range(args.length)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
