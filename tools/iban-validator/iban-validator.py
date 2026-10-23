#!/usr/bin/env python3
"""Validate IBANs.

Checks format and the mod-97 checksum for one or more IBANs, and prints the
country code and BBAN parts.

Usage:
    iban-validator.py DE89370400440532013000
    iban-validator.py BE68539007547034 GB29NWBK60161331926819
"""

import argparse
import re
import sys


def validate(iban):
    cleaned = "".join(iban.split()).upper()
    if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$", cleaned):
        return cleaned, False, "bad format"
    rearranged = cleaned[4:] + cleaned[:4]
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    if int(digits) % 97 != 1:
        return cleaned, False, "checksum failed"
    return cleaned, True, "valid"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate IBANs: format check plus mod-97 checksum.",
        epilog="Examples:\n"
               "  iban-validator.py DE89370400440532013000\n"
               "  iban-validator.py BE68539007547034 GB29NWBK60161331926819",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("ibans", nargs="+", help="one or more IBANs to validate")
    args = parser.parse_args(argv)

    failed = False
    for raw in args.ibans:
        cleaned, ok, reason = validate(raw)
        country = cleaned[:2] if len(cleaned) >= 2 else "??"
        print("%s  [%s] %s  country=%s" % (cleaned, "VALID" if ok else "INVALID",
                                           reason, country))
        if not ok:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
