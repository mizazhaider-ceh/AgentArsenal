#!/usr/bin/env python3
"""Show a simple word-level diff of two files.

Splits both files into words and prints a unified-style diff where changed
words are marked with - (old) and + (new). Context words are shown plain.

Usage:
    diff-word.py old.txt new.txt
    diff-word.py old.txt new.txt --context 2
"""

import argparse
import difflib
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Word-level diff of two text files.",
        epilog="Examples:\n"
               "  diff-word.py old.txt new.txt\n"
               "  diff-word.py old.txt new.txt --context 2\n"
               "  diff-word.py a.txt b.txt --side-by-side",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file_a", help="original file")
    parser.add_argument("file_b", help="changed file")
    parser.add_argument("--context", type=int, default=3,
                        help="unchanged words of context around changes (default: 3)")
    parser.add_argument("--side-by-side", action="store_true",
                        help="print old and new word lists in two columns")
    args = parser.parse_args(argv)

    if args.context < 0:
        parser.error("--context must be 0 or more")

    try:
        with open(args.file_a, "r", encoding="utf-8", errors="replace") as fh:
            words_a = fh.read().split()
        with open(args.file_b, "r", encoding="utf-8", errors="replace") as fh:
            words_b = fh.read().split()
    except OSError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1

    if words_a == words_b:
        print("Files are identical (%d words)." % len(words_a))
        return 0

    if args.side_by_side:
        sm = difflib.SequenceMatcher(None, words_a, words_b, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for w in words_a[i1:i2]:
                    print("  %-30s %s" % (w, w))
            else:
                old = words_a[i1:i2]
                new = words_b[j1:j2]
                for k in range(max(len(old), len(new))):
                    o = old[k] if k < len(old) else ""
                    n = new[k] if k < len(new) else ""
                    mark = " " if o == n else "*"
                    print("%s %-30s %s" % (mark, o, n))
        return 0

    n = args.context
    sm = difflib.SequenceMatcher(None, words_a, words_b, autojunk=False)
    changed = 0
    for group in sm.get_grouped_opcodes(n):
        print("---")
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for w in words_a[i1:i2]:
                    print("  " + w)
            else:
                changed += 1
                for w in words_a[i1:i2]:
                    print("- " + w)
                for w in words_b[j1:j2]:
                    print("+ " + w)
    print("Changed blocks: %d" % changed, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
