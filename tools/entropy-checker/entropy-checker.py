#!/usr/bin/env python3
"""Measure the Shannon entropy of input data.

Reads text from an argument or a file and reports bits of entropy per
symbol plus a plain-English verdict. High entropy (near 8 bits per byte)
suggests random or encrypted data; low entropy suggests plain text.

Usage:
    entropy-checker.py "hello world"
    entropy-checker.py --file secret.bin
"""

import argparse
import math
import sys
from collections import Counter


def shannon(data):
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def verdict(bits):
    if bits >= 7.5:
        return "very high: looks random, encrypted, or compressed"
    if bits >= 6.0:
        return "high: possibly encoded or hashed data"
    if bits >= 4.5:
        return "medium: mixed content"
    return "low: likely plain text or repetitive data"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Measure Shannon entropy of text or a file (bits per byte).",
        epilog="Examples:\n"
               "  entropy-checker.py \"hello world\"\n"
               "  entropy-checker.py --file secret.bin\n"
               "  echo -n password123 | entropy-checker.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", default=None,
                        help="text to measure (default: read from stdin)")
    parser.add_argument("--file", action="store_true",
                        help="treat TEXT as a file path and measure its bytes")
    args = parser.parse_args(argv)

    if args.file:
        if not args.text:
            parser.error("--file needs a file path")
        try:
            with open(args.text, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            print("Error: cannot read %r: %s" % (args.text, exc), file=sys.stderr)
            return 1
        symbols = list(data)
        unit = "bytes"
    else:
        if args.text is None:
            if sys.stdin.isatty():
                parser.error("provide text as an argument or pipe it on stdin")
            raw = sys.stdin.read()
        else:
            raw = args.text
        symbols = list(raw.encode("utf-8"))
        unit = "bytes (utf-8)"

    bits = shannon(symbols)
    print("Symbols: %d %s" % (len(symbols), unit))
    print("Unique symbols: %d" % len(set(symbols)))
    print("Entropy: %.4f bits per byte (max 8.0)" % bits)
    print("Verdict: %s" % verdict(bits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
