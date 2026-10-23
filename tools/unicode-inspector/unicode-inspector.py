#!/usr/bin/env python3
"""Inspect Unicode characters.

For each character shows codepoint (U+XXXX), UTF-8 bytes, name, category,
and whether it is a confusable lookalike risk (non-ASCII in identifiers).

Usage:
    unicode-inspector.py "café"
    unicode-inspector.py "paypaI" --confusables
"""

import argparse
import sys
import unicodedata


def describe(ch):
    code = ord(ch)
    try:
        name = unicodedata.name(ch)
    except ValueError:
        name = "<no name>"
    cat = unicodedata.category(ch)
    utf8 = ch.encode("utf-8")
    return {
        "char": ch,
        "codepoint": "U+%04X" % code,
        "utf8": " ".join("%02x" % b for b in utf8),
        "name": name,
        "category": cat,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Inspect Unicode characters: codepoint, name, category, UTF-8 bytes.",
        epilog="Examples:\n"
               "  unicode-inspector.py \"café\"\n"
               "  unicode-inspector.py \"\\u0430\" --confusables\n"
               "  echo \"hello\" | unicode-inspector.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", default=None,
                        help="text to inspect (default: read from stdin)")
    parser.add_argument("--confusables", action="store_true",
                        help="flag non-ASCII characters that look like ASCII (homoglyph risk)")
    args = parser.parse_args(argv)

    if args.text is None:
        if sys.stdin.isatty():
            parser.error("provide text as an argument or pipe it on stdin")
        text = sys.stdin.read().rstrip("\n")
    else:
        text = args.text
    if not text:
        parser.error("empty input")

    risky = False
    for ch in text:
        info = describe(ch)
        print("%s  %-28s  UTF-8: %-11s  cat: %s  %r" % (
            info["codepoint"], info["name"], info["utf8"],
            info["category"], info["char"]))
        if args.confusables and ord(ch) > 127:
            print("    WARNING: non-ASCII char, possible homoglyph/confusable")
            risky = True

    if args.confusables:
        print("Confusable check: %s" % ("RISKY characters found" if risky
                                        else "all ASCII, clean"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
