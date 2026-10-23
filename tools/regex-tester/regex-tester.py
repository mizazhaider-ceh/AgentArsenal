#!/usr/bin/env python3
"""Test a regex against sample text.

Shows which lines match, the matched groups, or validates the pattern only.
Useful for building patterns for logs, allow-lists, and parsers.

Usage:
    regex-tester.py "^\\d{3}-\\d{4}$" "555-1234"
    regex-tester.py "(?P<ip>\\d+\\.\\d+\\.\\d+\\.\\d+)" logfile.txt --file
"""

import argparse
import re
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Test a regular expression against text: show matches and groups.",
        epilog="Examples:\n"
               "  regex-tester.py \"^\\\\d{3}-\\\\d{4}$\" \"555-1234\"\n"
               "  regex-tester.py \"(?P<ip>\\\\d+\\\\.\\\\d+\\\\.\\\\d+\\\\.\\\\d+)\" log.txt --file\n"
               "  regex-tester.py \"[a-z\" --validate-only\n"
               "  echo \"abc123\" | regex-tester.py \"\\\\d+\"",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pattern", help="regular expression to test")
    parser.add_argument("text", nargs="?", default=None,
                        help="text to test, a file path with --file, or stdin")
    parser.add_argument("--file", action="store_true",
                        help="treat TEXT as a file path, test line by line")
    parser.add_argument("-i", "--ignore-case", action="store_true",
                        help="case-insensitive matching")
    parser.add_argument("--validate-only", action="store_true",
                        help="only check that the pattern compiles")
    parser.add_argument("--findall", action="store_true",
                        help="list every match, not just per-line yes/no")
    args = parser.parse_args(argv)

    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        regex = re.compile(args.pattern, flags)
    except re.error as exc:
        print("Invalid regex: %s" % exc, file=sys.stderr)
        return 1

    if args.validate_only:
        print("OK: pattern compiles")
        return 0

    if args.text is None:
        if sys.stdin.isatty():
            parser.error("provide text as an argument, a file, or on stdin")
        text = sys.stdin.read()
        lines = [text]
        labels = ["stdin"]
    elif args.file:
        try:
            with open(args.text, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError as exc:
            print("Error: cannot read %r: %s" % (args.text, exc), file=sys.stderr)
            return 1
        labels = ["line %d" % (i + 1) for i in range(len(lines))]
    else:
        lines = [args.text]
        labels = ["input"]

    hits = 0
    for label, line in zip(labels, lines):
        if args.findall:
            matches = list(regex.finditer(line))
            if matches:
                hits += len(matches)
                print("%s: %d match(es)" % (label, len(matches)))
                for m in matches:
                    groups = ", ".join("%s=%r" % (k, v)
                                       for k, v in m.groupdict().items()) or "no named groups"
                    print("    %r  (%s)" % (m.group(0), groups))
        else:
            m = regex.search(line)
            if m:
                hits += 1
                groups = ", ".join("%s=%r" % (k, v)
                                   for k, v in m.groupdict().items()) or "no named groups"
                print("%s: MATCH %r  (%s)" % (label, m.group(0), groups))
            elif len(lines) > 1:
                print("%s: no match" % label)

    print("Total matches: %d" % hits, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
