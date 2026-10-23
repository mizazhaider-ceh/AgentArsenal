#!/usr/bin/env python3
"""Encode and decode base64.

Reads from an argument or stdin, writes the result to stdout.

Usage:
    base64-codec.py encode "hello world"
    base64-codec.py decode aGVsbG8gd29ybGQ=
    echo aGVsbG8= | base64-codec.py decode
"""

import argparse
import base64
import binascii
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Encode text to base64 or decode base64 back to text.",
        epilog="Examples:\n"
               "  base64-codec.py encode \"hello world\"\n"
               "  base64-codec.py decode aGVsbG8gd29ybGQ=\n"
               "  base64-codec.py decode --urlsafe 'aGVsbG8td29ybGQ_'\n"
               "  echo hello | base64-codec.py encode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=["encode", "decode"],
                        help="encode text to base64, or decode base64 to text")
    parser.add_argument("data", nargs="?", default=None,
                        help="input text (default: read from stdin)")
    parser.add_argument("--urlsafe", action="store_true",
                        help="use the URL-safe alphabet (- and _)")
    args = parser.parse_args(argv)

    if args.data is None:
        if sys.stdin.isatty():
            parser.error("provide data as an argument or pipe it on stdin")
        raw = sys.stdin.read()
    else:
        raw = args.data
    raw = raw.strip()

    try:
        if args.mode == "encode":
            encoded = (base64.urlsafe_b64encode if args.urlsafe else base64.b64encode)(
                raw.encode("utf-8"))
            print(encoded.decode("ascii"))
        else:
            decoded = (base64.urlsafe_b64decode if args.urlsafe else base64.b64decode)(
                raw.encode("ascii"), validate=True)
            sys.stdout.write(decoded.decode("utf-8", "replace"))
            sys.stdout.write("\n")
    except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
