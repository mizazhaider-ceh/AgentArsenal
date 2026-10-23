#!/usr/bin/env python3
"""Extract printable strings from a binary file (like the `strings` command).

Prints runs of printable ASCII (and optionally UTF-16) characters at least
N characters long, with optional file offsets.

Usage:
    string-extractor.py firmware.bin
    string-extractor.py program.elf -n 8 --offset
"""

import argparse
import sys


def extract(data, min_len, wide):
    results = []
    if wide:
        try:
            text = data.decode("utf-16-le", errors="ignore")
        except ValueError:
            text = ""
        buf = []
        for ch in text:
            if 32 <= ord(ch) <= 126:
                buf.append(ch)
            else:
                if len(buf) >= min_len:
                    results.append(("".join(buf), None))
                buf = []
        if len(buf) >= min_len:
            results.append(("".join(buf), None))
        return results

    buf = []
    start = 0
    for i, byte in enumerate(data):
        if 32 <= byte <= 126:
            if not buf:
                start = i
            buf.append(chr(byte))
        else:
            if len(buf) >= min_len:
                results.append(("".join(buf), start))
            buf = []
    if len(buf) >= min_len:
        results.append(("".join(buf), start))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract printable strings from a binary file (a simple "
                    "`strings` clone).",
        epilog="Examples:\n"
               "  string-extractor.py firmware.bin\n"
               "  string-extractor.py program.elf -n 8 --offset\n"
               "  string-extractor.py driver.sys --wide",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="binary file to scan")
    parser.add_argument("-n", "--min-length", type=int, default=4,
                        help="minimum string length (default: 4)")
    parser.add_argument("--offset", action="store_true",
                        help="print the file offset of each string")
    parser.add_argument("--wide", action="store_true",
                        help="also scan for UTF-16LE wide strings (offsets not shown)")
    args = parser.parse_args(argv)

    if args.min_length < 1:
        parser.error("--min-length must be at least 1")

    try:
        with open(args.file, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        print("Error: cannot read %r: %s" % (args.file, exc), file=sys.stderr)
        return 1

    results = extract(data, args.min_length, False)
    if args.wide:
        results += extract(data, args.min_length, True)

    for text, offset in results:
        if args.offset and offset is not None:
            print("%08x  %s" % (offset, text))
        else:
            print(text)
    print("Found %d strings in %s" % (len(results), args.file), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
