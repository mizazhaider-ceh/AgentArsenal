#!/usr/bin/env python3
"""Search logs with regex and summarize the hits.

Prints matching lines, then a summary: total matches, matches per pattern,
and the most common matching lines. Useful for a first pass over server logs.

Usage:
    log-grep-analyzer.py /var/log/auth.log -p "Failed password" -p "Accepted"
    log-grep-analyzer.py app.log -p "ERROR" --top 5 --context 2
"""

import argparse
import re
import sys
from collections import Counter


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Grep a log file with regex patterns and summarize the matches.",
        epilog="Examples:\n"
               "  log-grep-analyzer.py /var/log/auth.log -p \"Failed password\"\n"
               "  log-grep-analyzer.py app.log -p \"ERROR|CRITICAL\" --top 10\n"
               "  log-grep-analyzer.py app.log -p \"timeout\" -i --no-lines --top 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("logfile", help="path to the log file to read")
    parser.add_argument("-p", "--pattern", action="append", required=True,
                        help="regex pattern to match (repeat for several)")
    parser.add_argument("-i", "--ignore-case", action="store_true",
                        help="match case-insensitively")
    parser.add_argument("--top", type=int, default=10,
                        help="show the N most common matching lines (default: 10)")
    parser.add_argument("--context", type=int, default=0,
                        help="print N lines of context around each match (default: 0)")
    parser.add_argument("--no-lines", action="store_true",
                        help="skip printing matching lines, show only the summary")
    parser.add_argument("--errors", default="replace",
                        help="how to handle undecodable bytes: replace, ignore, strict")
    args = parser.parse_args(argv)

    if args.top < 0:
        parser.error("--top must be 0 or more")
    if args.context < 0:
        parser.error("--context must be 0 or more")

    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        regexes = [re.compile(p, flags) for p in args.pattern]
    except re.error as exc:
        parser.error("bad regex: %s" % exc)

    try:
        with open(args.logfile, "r", encoding="utf-8", errors=args.errors) as fh:
            lines = fh.readlines()
    except OSError as exc:
        print("Error: cannot read %r: %s" % (args.logfile, exc), file=sys.stderr)
        return 1

    per_pattern = Counter()
    common_lines = Counter()
    total = 0
    matched_idx = set()

    for idx, line in enumerate(lines):
        hit = False
        for regex in regexes:
            if regex.search(line):
                per_pattern[regex.pattern] += 1
                hit = True
        if hit:
            total += 1
            matched_idx.add(idx)
            common_lines[line.rstrip("\n")] += 1

    if not args.no_lines:
        printed = set()
        for idx in sorted(matched_idx):
            if args.context:
                for j in range(max(0, idx - args.context), min(len(lines), idx + args.context + 1)):
                    if j not in printed:
                        mark = ">" if j == idx else " "
                        print("%s %d: %s" % (mark, j + 1, lines[j].rstrip("\n")))
                        printed.add(j)
            else:
                print("%d: %s" % (idx + 1, lines[idx].rstrip("\n")))

    print("\n--- Summary ---")
    print("Lines read:      %d" % len(lines))
    print("Matching lines:  %d" % total)
    for pattern, count in per_pattern.most_common():
        print("Pattern %-30r %d" % (pattern, count))
    if args.top and common_lines:
        print("Most common matching lines:")
        for line, count in common_lines.most_common(args.top):
            print("  %4d x  %s" % (count, line[:120]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
