#!/usr/bin/env python3
"""Basic phone number parser.

Normalizes a phone number to E.164-ish digits, splits a possible country
code, and validates length. This is a simple heuristic parser, not a full
libphonenumber replacement.

Usage:
    phone-parser-basic.py "+32 470 12 34 56"
    phone-parser-basic.py 0032470123456 --default-cc 32
"""

import argparse
import re
import sys

COUNTRY_CODES = {
    "1": "North America", "7": "Russia/Kazakhstan", "20": "Egypt",
    "27": "South Africa", "30": "Greece", "31": "Netherlands", "32": "Belgium",
    "33": "France", "34": "Spain", "39": "Italy", "40": "Romania",
    "41": "Switzerland", "43": "Austria", "44": "UK", "45": "Denmark",
    "46": "Sweden", "47": "Norway", "48": "Poland", "49": "Germany",
    "52": "Mexico", "55": "Brazil", "61": "Australia", "64": "New Zealand",
    "81": "Japan", "82": "South Korea", "86": "China", "91": "India",
    "92": "Pakistan", "351": "Portugal", "352": "Luxembourg", "353": "Ireland",
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Normalize and inspect a phone number (basic heuristic parser).",
        epilog="Examples:\n"
               "  phone-parser-basic.py \"+32 470 12 34 56\"\n"
               "  phone-parser-basic.py 0032470123456\n"
               "  phone-parser-basic.py 0470123456 --default-cc 32",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("number", help="phone number in any common format")
    parser.add_argument("--default-cc", default=None,
                        help="country code to assume when none is present, e.g. 32")
    args = parser.parse_args(argv)

    raw = args.number.strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("00"):
        digits = digits[2:]
        international = True
    elif raw.startswith("+"):
        international = True
    else:
        international = False

    cc = None
    national = digits
    if international or args.default_cc is None:
        for length in (3, 2, 1):
            if digits[:length] in COUNTRY_CODES:
                cc, national = digits[:length], digits[length:]
                break
    if cc is None and args.default_cc:
        cc, national = args.default_cc, digits.lstrip("0")

    print("Input:    %s" % raw)
    print("Digits:   %s" % digits)
    if cc:
        print("Country:  +%s (%s)" % (cc, COUNTRY_CODES.get(cc, "unknown")))
        print("National: %s" % national)
        print("E.164:    +%s%s" % (cc, national))
    else:
        print("Country:  (not detected, use --default-cc)")
        print("National: %s" % national)

    total = len((cc or "") + national)
    if 7 <= total <= 15:
        print("Length:   OK (%d digits, E.164 allows up to 15)" % total)
    else:
        print("Length:   SUSPICIOUS (%d digits)" % total)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
