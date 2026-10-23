#!/usr/bin/env python3
"""Pretty-print and validate JSON.

Reads JSON from a file, an argument, or stdin. Prints it indented and sorted,
or compacts it to one line. Exits 1 when the input is not valid JSON.

Usage:
    json-formatter.py data.json
    echo '{"b":2,"a":1}' | json-formatter.py --sort
    json-formatter.py data.json --compact
"""

import argparse
import json
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Pretty-print and validate JSON.",
        epilog="Examples:\n"
               "  json-formatter.py data.json\n"
               "  echo '{\"b\":2,\"a\":1}' | json-formatter.py --sort\n"
               "  json-formatter.py data.json --compact --indent 4\n"
               "  json-formatter.py --check data.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", nargs="?", default=None,
                        help="JSON string or path to a .json file (default: stdin)")
    parser.add_argument("--indent", type=int, default=2,
                        help="indent spaces for pretty output (default: 2)")
    parser.add_argument("--sort", action="store_true",
                        help="sort object keys alphabetically")
    parser.add_argument("--compact", action="store_true",
                        help="print minified JSON on one line")
    parser.add_argument("--check", action="store_true",
                        help="only validate, print OK or the error")
    args = parser.parse_args(argv)

    if args.indent < 0:
        parser.error("--indent must be 0 or more")

    if args.source is None:
        if sys.stdin.isatty():
            parser.error("provide JSON as an argument, a file, or on stdin")
        raw = sys.stdin.read()
    elif args.source.endswith(".json"):
        try:
            with open(args.source, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            print("Error: cannot read %r: %s" % (args.source, exc), file=sys.stderr)
            return 1
    else:
        raw = args.source

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        print("Invalid JSON: %s" % exc, file=sys.stderr)
        return 1

    if args.check:
        print("OK: valid JSON")
        return 0

    if args.compact:
        print(json.dumps(obj, sort_keys=args.sort, separators=(",", ":")))
    else:
        print(json.dumps(obj, sort_keys=args.sort, indent=args.indent,
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
