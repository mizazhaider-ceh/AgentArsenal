#!/usr/bin/env python3
"""Verify a file against a known checksum.

Compares the hash of a file with an expected value (md5, sha1, sha256,
sha512 auto-detected by length, or picked with --algo).

Usage:
    checksum-verifier.py file.iso 5d41402abc4b2a76b9719d911017c592
    checksum-verifier.py file.iso <sha256> --algo sha256
"""

import argparse
import hashlib
import sys

LENGTH_TO_ALGO = {32: "md5", 40: "sha1", 64: "sha256", 128: "sha512"}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify a file against an expected checksum (algo auto-detected).",
        epilog="Examples:\n"
               "  checksum-verifier.py file.iso 5d41402abc4b2a76b9719d911017c592\n"
               "  checksum-verifier.py file.iso <sha256sum> --algo sha256\n"
               "  sha256sum file.iso | checksum-verifier.py --from-stdin file.iso",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="file to check")
    parser.add_argument("expected", nargs="?", default=None,
                        help="expected hex digest (or read from stdin)")
    parser.add_argument("--algo", choices=["md5", "sha1", "sha256", "sha512"],
                        default=None, help="hash algorithm (default: detect from length)")
    parser.add_argument("--from-stdin", action="store_true",
                        help="read 'hash  filename' lines (sha256sum style) from stdin")
    args = parser.parse_args(argv)

    if args.from_stdin:
        pairs = []
        for line in sys.stdin:
            parts = line.split()
            if len(parts) >= 2:
                pairs.append((parts[1].lstrip("*"), parts[0]))
        if not pairs:
            parser.error("no checksum lines on stdin")
        failed = False
        for path, expected in pairs:
            ok = check_one(path, expected, args.algo)
            failed = failed or not ok
        return 1 if failed else 0

    if args.expected is None:
        parser.error("provide the expected checksum (or use --from-stdin)")
    ok = check_one(args.file, args.expected, args.algo)
    return 0 if ok else 1


def check_one(path, expected, algo):
    expected = expected.strip().lower()
    if algo is None:
        algo = LENGTH_TO_ALGO.get(len(expected))
        if algo is None:
            print("Error: cannot detect algorithm from %d hex chars, use --algo"
                  % len(expected), file=sys.stderr)
            return False
    try:
        digest = hashlib.new(algo)
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        print("Error: cannot read %r: %s" % (path, exc), file=sys.stderr)
        return False
    actual = digest.hexdigest()
    if actual == expected:
        print("%s: OK (%s matches)" % (path, algo))
        return True
    print("%s: FAILED" % path)
    print("  expected: %s" % expected)
    print("  actual:   %s" % actual)
    return False


if __name__ == "__main__":
    sys.exit(main())
