#!/usr/bin/env python3
"""Encode and decode ROT13.

ROT13 is the Caesar cipher with a fixed shift of 13: encoding and decoding
are the same operation.

Usage:
    rot13-codec.py "hello world"
    echo "uryyb" | rot13-codec.py
"""

import argparse
import codecs
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Apply ROT13 to text (encoding and decoding are identical).",
        epilog="Examples:\n"
               "  rot13-codec.py \"hello world\"\n"
               "  rot13-codec.py \"uryyb jbeyq\"\n"
               "  echo hello | rot13-codec.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", default=None,
                        help="input text (default: read from stdin)")
    args = parser.parse_args(argv)

    if args.text is None:
        if sys.stdin.isatty():
            parser.error("provide text as an argument or pipe it on stdin")
        text = sys.stdin.read()
    else:
        text = args.text

    print(codecs.encode(text, "rot13"), end="" if text.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
