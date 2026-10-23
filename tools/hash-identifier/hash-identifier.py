#!/usr/bin/env python3
"""Identify a hash by its format.

Matches the input against known hash formats (length, character set, and
known prefixes like $2b$, {SHA}, etc). This is a format guess, not a crack.
It never reveals the original value.

Usage:
    hash-identifier.py 5d41402abc4b2a76b9719d911017c592
"""

import argparse
import re
import sys

CANDIDATES = [
    # (name, regex, note)
    ("MD5", r"^[0-9a-f]{32}$", "32 hex chars"),
    ("SHA-1", r"^[0-9a-f]{40}$", "40 hex chars"),
    ("SHA-224", r"^[0-9a-f]{56}$", "56 hex chars"),
    ("SHA-256", r"^[0-9a-f]{64}$", "64 hex chars"),
    ("SHA-384", r"^[0-9a-f]{96}$", "96 hex chars"),
    ("SHA-512", r"^[0-9a-f]{128}$", "128 hex chars"),
    ("SHA-3-256", r"^[0-9a-f]{64}$", "same length as SHA-256, check context"),
    ("SHA-3-512", r"^[0-9a-f]{128}$", "same length as SHA-512, check context"),
    ("MD4", r"^[0-9a-f]{32}$", "same length as MD5, check context"),
    ("NTLM", r"^[0-9a-f]{32}$", "same length as MD5, check context"),
    ("LM", r"^[0-9a-f]{32}$", "same length as MD5, check context"),
    ("RIPEMD-160", r"^[0-9a-f]{40}$", "same length as SHA-1, check context"),
    ("SHA-512 crypt", r"^\$6\$[./0-9A-Za-z]{1,16}\$[./0-9A-Za-z]{86}$",
     "Linux shadow $6$ format"),
    ("SHA-256 crypt", r"^\$5\$[./0-9A-Za-z]{1,16}\$[./0-9A-Za-z]{43}$",
     "Linux shadow $5$ format"),
    ("bcrypt", r"^\$2[aby]\$\d{2}\$[./0-9A-Za-z]{53}$", "Blowfish crypt"),
    ("MD5 crypt", r"^\$1\$[./0-9A-Za-z]{1,8}\$[./0-9A-Za-z]{22}$", "old Unix $1$"),
    ("yescrypt", r"^\$y\$[./0-9A-Za-z]+\$[./0-9A-Za-z]+$", "modern Linux default"),
    ("LDAP {SSHA}", r"^\{SSHA\}[0-9A-Za-z+/=]+$", "salted SHA-1, base64"),
    ("LDAP {SHA}", r"^\{SHA\}[0-9A-Za-z+/=]{28}$", "plain SHA-1, base64"),
    ("LDAP {MD5}", r"^\{MD5\}[0-9A-Za-z+/=]{24}$", "plain MD5, base64"),
    ("MySQL 4.1+", r"^\*[0-9A-F]{40}$", "leading asterisk"),
    ("Cisco Type 7", r"^[0-9A-F]{4}([0-9A-F]{2})+$", "weak reversible"),
    ("JWT-like", r"^[0-9A-Za-z_-]+\.[0-9A-Za-z_-]+\.[0-9A-Za-z_-]+$",
     "three base64url parts, not a password hash"),
]


def identify(value):
    matches = []
    lowered = value.strip()
    for name, pattern, note in CANDIDATES:
        if re.match(pattern, lowered, re.IGNORECASE if name in ("MySQL 4.1+",) else 0):
            matches.append((name, note))
    return matches


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Guess the type of a hash from its format. "
                    "This only identifies the format, it does not crack the hash.",
        epilog="Examples:\n"
               "  hash-identifier.py 5d41402abc4b2a76b9719d911017c592\n"
               "  hash-identifier.py '$2b$12$abcdefghijklmnopqrstuuABCDEF1234567890abcdef'\n"
               "  echo 'da39a3ee5e6b4b0d3255bfef95601890afd80709' | hash-identifier.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("hash", nargs="?", default=None,
                        help="hash string to identify (or read from stdin)")
    args = parser.parse_args(argv)

    value = args.hash
    if value is None:
        if sys.stdin.isatty():
            parser.error("provide a hash argument or pipe one on stdin")
        value = sys.stdin.read().strip()
    value = value.strip()
    if not value:
        parser.error("empty hash input")

    matches = identify(value)
    if not matches:
        print("No known format matched for: %s" % value)
        print("It may be truncated, salted, or a custom scheme.")
        return 0
    print("Possible types for %s:" % value)
    for name, note in matches:
        print("  - %s (%s)" % (name, note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
