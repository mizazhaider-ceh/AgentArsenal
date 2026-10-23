#!/usr/bin/env python3
"""Apply the Caesar cipher (letter shift).

Shifts each letter by N positions. Use --brute to try all 25 shifts when
decoding unknown text.

Usage:
    caesar-cipher.py encode "hello" --shift 3
    caesar-cipher.py decode "khoor" --shift 3
    caesar-cipher.py brute "khoor"
"""

import argparse
import string
import sys

LOWER = string.ascii_lowercase
UPPER = string.ascii_uppercase


def shift_text(text, shift):
    out = []
    for ch in text:
        if ch in LOWER:
            out.append(LOWER[(LOWER.index(ch) + shift) % 26])
        elif ch in UPPER:
            out.append(UPPER[(UPPER.index(ch) + shift) % 26])
        else:
            out.append(ch)
    return "".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Encode or decode text with the Caesar cipher (letter shift).",
        epilog="Examples:\n"
               "  caesar-cipher.py encode \"hello\" --shift 3\n"
               "  caesar-cipher.py decode \"khoor\" --shift 3\n"
               "  caesar-cipher.py brute \"khoor\"\n"
               "  echo hello | caesar-cipher.py encode --shift 13",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=["encode", "decode", "brute"],
                        help="encode, decode, or try all shifts")
    parser.add_argument("text", nargs="?", default=None,
                        help="input text (default: read from stdin)")
    parser.add_argument("-s", "--shift", type=int, default=3,
                        help="shift amount (default: 3)")
    args = parser.parse_args(argv)

    if args.text is None:
        if sys.stdin.isatty():
            parser.error("provide text as an argument or pipe it on stdin")
        text = sys.stdin.read().rstrip("\n")
    else:
        text = args.text

    shift = args.shift % 26
    if args.mode == "encode":
        print(shift_text(text, shift))
    elif args.mode == "decode":
        print(shift_text(text, -shift))
    else:
        for s in range(1, 26):
            print("shift %2d: %s" % (s, shift_text(text, -s)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
