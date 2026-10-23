#!/usr/bin/env python3
"""Encode and decode hex.

Converts text to hex and back, or dumps a file as hex bytes. Reads from an
argument or stdin.

Usage:
    hex-codec.py encode "hello"
    hex-codec.py decode 68656c6c6f
    hex-codec.py dump /bin/ls
"""

import argparse
import binascii
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Encode text to hex, decode hex to text, or hex-dump a file.",
        epilog="Examples:\n"
               "  hex-codec.py encode \"hello\"\n"
               "  hex-codec.py decode 68656c6c6f\n"
               "  hex-codec.py dump /bin/ls | head\n"
               "  echo 41 42 | hex-codec.py decode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=["encode", "decode", "dump"],
                        help="encode text to hex, decode hex to text, or dump a file as hex")
    parser.add_argument("data", nargs="?", default=None,
                        help="input text or file path (default: read from stdin)")
    parser.add_argument("--upper", action="store_true",
                        help="print hex in uppercase")
    args = parser.parse_args(argv)

    try:
        if args.mode == "dump":
            if not args.data:
                parser.error("dump mode needs a file path")
            with open(args.data, "rb") as fh:
                blob = fh.read()
            hexed = binascii.hexlify(blob).decode("ascii")
            if args.upper:
                hexed = hexed.upper()
            for i in range(0, len(hexed), 64):
                print("%08x  %s" % (i // 2, " ".join(
                    hexed[j:j + 2] for j in range(i, min(i + 64, len(hexed)), 2))))
            return 0

        if args.data is None:
            if sys.stdin.isatty():
                parser.error("provide data as an argument or pipe it on stdin")
            raw = sys.stdin.read().strip()
        else:
            raw = args.data.strip()

        if args.mode == "encode":
            out = binascii.hexlify(raw.encode("utf-8")).decode("ascii")
            print(out.upper() if args.upper else out)
        else:
            cleaned = "".join(raw.split())
            out = binascii.unhexlify(cleaned)
            sys.stdout.write(out.decode("utf-8", "replace") + "\n")
    except (binascii.Error, ValueError, OSError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
