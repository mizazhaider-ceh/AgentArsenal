#!/usr/bin/env python3
"""Hash one or more files with MD5, SHA-1, and SHA-256.

Reads each file in chunks so large files stay fast and memory-light.

Usage:
    file-hasher.py file1 file2
    file-hasher.py --sha256-only big.iso
"""

import argparse
import hashlib
import os
import sys

ALGOS = ["md5", "sha1", "sha256"]
CHUNK = 65536


def hash_file(path, algos):
    digests = {a: hashlib.new(a) for a in algos}
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(CHUNK)
            if not chunk:
                break
            for d in digests.values():
                d.update(chunk)
    return {a: d.hexdigest() for a, d in digests.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compute MD5, SHA-1, and SHA-256 hashes for files (chunked reads).",
        epilog="Examples:\n"
               "  file-hasher.py document.pdf\n"
               "  file-hasher.py a.iso b.iso --sha256-only\n"
               "  file-hasher.py /bin/*",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="+", help="files to hash")
    parser.add_argument("--sha256-only", action="store_true",
                        help="compute only SHA-256")
    parser.add_argument("--md5-only", action="store_true",
                        help="compute only MD5")
    args = parser.parse_args(argv)

    if args.sha256_only and args.md5_only:
        parser.error("pick only one of --sha256-only and --md5-only")
    algos = ["sha256"] if args.sha256_only else (["md5"] if args.md5_only else ALGOS)

    failed = False
    for path in args.files:
        if not os.path.isfile(path):
            print("Error: not a file: %r" % path, file=sys.stderr)
            failed = True
            continue
        try:
            digests = hash_file(path, algos)
        except OSError as exc:
            print("Error: cannot read %r: %s" % (path, exc), file=sys.stderr)
            failed = True
            continue
        print("File: %s" % path)
        for algo in algos:
            print("  %s: %s" % (algo.upper(), digests[algo]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
