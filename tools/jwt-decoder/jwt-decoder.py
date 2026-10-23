#!/usr/bin/env python3
"""Decode a JWT without verifying its signature.

WARNING: this tool does NOT verify the signature. It only decodes the
header and payload so you can read them. Never trust an unverified token.

Usage:
    jwt-decoder.py eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0In0.signature
"""

import argparse
import base64
import json
import sys


def b64url_decode(part):
    padding = "=" * (-len(part) % 4)
    return base64.urlsafe_b64decode((part + padding).encode("ascii"))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Decode a JWT header and payload (decode only, no signature check).",
        epilog="Examples:\n"
               "  jwt-decoder.py <token>\n"
               "  echo '<token>' | jwt-decoder.py\n"
               "  jwt-decoder.py <token> --payload-only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("token", nargs="?", default=None,
                        help="the JWT string (default: read from stdin)")
    parser.add_argument("--payload-only", action="store_true",
                        help="print only the payload JSON")
    args = parser.parse_args(argv)

    if args.token is None:
        if sys.stdin.isatty():
            parser.error("provide a token as an argument or on stdin")
        token = sys.stdin.read().strip()
    else:
        token = args.token.strip()

    parts = token.split(".")
    if len(parts) != 3:
        print("Error: a JWT must have three dot-separated parts, got %d" % len(parts),
              file=sys.stderr)
        return 2

    print("WARNING: signature NOT verified. Do not trust this token.",
          file=sys.stderr)
    try:
        header = json.loads(b64url_decode(parts[0]).decode("utf-8"))
        payload = json.loads(b64url_decode(parts[1]).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        print("Error: cannot decode token: %s" % exc, file=sys.stderr)
        return 1

    if args.payload_only:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("Header:")
        print(json.dumps(header, indent=2, ensure_ascii=False))
        print("Payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("Signature (base64url, not verified): %s" % parts[2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
