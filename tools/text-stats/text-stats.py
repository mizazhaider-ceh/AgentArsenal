#!/usr/bin/env python3
"""Count text statistics for a file or stdin.

Reports lines, words, characters, bytes, blank lines, average line length,
and the most common words.

Usage:
    text-stats.py essay.txt
    cat essay.txt | text-stats.py --top 20
"""

import argparse
import re
import sys
from collections import Counter

WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def analyze(text):
    lines = text.splitlines()
    words = WORD_RE.findall(text.lower())
    chars = len(text)
    nonblank = [l for l in lines if l.strip()]
    avg_len = sum(len(l) for l in lines) / len(lines) if lines else 0
    return {
        "lines": len(lines),
        "blank_lines": len(lines) - len(nonblank),
        "words": len(words),
        "unique_words": len(set(words)),
        "chars": chars,
        "bytes": len(text.encode("utf-8")),
        "avg_line_len": avg_len,
        "common": Counter(words).most_common(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Text statistics: lines, words, chars, top words.",
        epilog="Examples:\n"
               "  text-stats.py essay.txt\n"
               "  cat essay.txt | text-stats.py --top 20\n"
               "  text-stats.py notes.md --top 0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="?", default=None,
                        help="file to analyze (default: stdin)")
    parser.add_argument("--top", type=int, default=10,
                        help="show the N most common words (default: 10, 0 to hide)")
    args = parser.parse_args(argv)

    if args.top < 0:
        parser.error("--top must be 0 or more")

    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        else:
            if sys.stdin.isatty():
                parser.error("provide a file or pipe text on stdin")
            text = sys.stdin.read()
    except OSError as exc:
        print("Error: cannot read %r: %s" % (args.file, exc), file=sys.stderr)
        return 1

    s = analyze(text)
    print("Lines:        %d (%d blank)" % (s["lines"], s["blank_lines"]))
    print("Words:        %d (%d unique)" % (s["words"], s["unique_words"]))
    print("Characters:   %d" % s["chars"])
    print("Bytes (utf8): %d" % s["bytes"])
    print("Avg line len: %.1f chars" % s["avg_line_len"])
    if args.top and s["common"]:
        print("Most common words:")
        for word, count in s["common"][:args.top]:
            print("  %5d  %s" % (count, word))
    return 0


if __name__ == "__main__":
    sys.exit(main())
