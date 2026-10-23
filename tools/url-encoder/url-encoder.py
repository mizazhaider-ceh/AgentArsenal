#!/usr/bin/env python3
"""URL-encode and URL-decode text.

Reads from an argument or stdin. Handles percent-encoding and optional
query-string parsing.

Usage:
    url-encoder.py encode "hello world & more"
    url-encoder.py decode "hello%20world%20%26%20more"
    url-encoder.py parse "https://example.com/?a=1&b=two%20words"
"""

import argparse
import sys
import urllib.parse


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="URL-encode or URL-decode text, or parse a query string.",
        epilog="Examples:\n"
               "  url-encoder.py encode \"hello world & more\"\n"
               "  url-encoder.py decode \"hello%20world%20%26%20more\"\n"
               "  url-encoder.py parse \"https://example.com/search?q=hello+world&page=2\"\n"
               "  echo \"a b\" | url-encoder.py encode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=["encode", "decode", "parse"],
                        help="encode, decode, or parse a query string into pairs")
    parser.add_argument("data", nargs="?", default=None,
                        help="input text or URL (default: read from stdin)")
    parser.add_argument("--plus", action="store_true",
                        help="with encode: encode spaces as + (form style)")
    args = parser.parse_args(argv)

    if args.data is None:
        if sys.stdin.isatty():
            parser.error("provide data as an argument or pipe it on stdin")
        raw = sys.stdin.read().strip()
    else:
        raw = args.data.strip()

    if args.mode == "encode":
        if args.plus:
            print(urllib.parse.quote_plus(raw, safe=""))
        else:
            print(urllib.parse.quote(raw, safe=""))
    elif args.mode == "decode":
        print(urllib.parse.unquote_plus(raw))
    else:
        parsed = urllib.parse.urlparse(raw)
        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not pairs:
            print("No query parameters found in: %s" % raw)
            return 0
        for key, value in pairs:
            print("%s = %s" % (key, value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
