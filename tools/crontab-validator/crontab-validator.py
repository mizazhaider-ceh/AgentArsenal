#!/usr/bin/env python3
"""Validate crontab files and lines.

Checks each line of a crontab: five time fields, @special shortcuts, and a
command. Reports errors with line numbers. Also understands environment
assignments (NAME=value).

Usage:
    crontab-validator.py mycron
    crontab-validator.py --line "*/15 * * * * /usr/bin/backup.sh"
"""

import argparse
import re
import sys

SPECIALS = {"@reboot", "@yearly", "@annually", "@monthly", "@weekly",
            "@daily", "@midnight", "@hourly"}
FIELD_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
MONTH_WORDS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
               "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
DOW_WORDS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}


def words_to_numbers(field, mapping):
    def repl(m):
        return str(mapping[m.group(0).lower()])
    return re.sub(r"[a-zA-Z]+", repl, field)


def check_field(field, low, high, mapping=None):
    if mapping:
        try:
            field = words_to_numbers(field, mapping)
        except KeyError:
            return "unknown name in %r" % field
    for part in field.split(","):
        step = "1"
        if "/" in part:
            part, step = part.split("/", 1)
            if not step.isdigit() or int(step) < 1:
                return "bad step in %r" % field
        if part == "*":
            continue
        bounds = part.split("-", 1)
        for bound in bounds:
            if not bound.isdigit():
                return "bad value %r in %r" % (bound, field)
            if not low <= int(bound) <= high:
                return "value %s out of range %d-%d" % (bound, low, high)
        if len(bounds) == 2 and int(bounds[0]) > int(bounds[1]):
            return "range start after end in %r" % field
    return None


def validate_line(line, lineno):
    errors = []
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return []
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", stripped):
        return []
    parts = stripped.split(None, 5)
    if parts[0] in SPECIALS:
        if len(parts) < 2:
            errors.append("line %d: %s needs a command" % (lineno, parts[0]))
        return errors
    if len(parts) < 6:
        errors.append("line %d: need 5 time fields plus a command" % lineno)
        return errors
    mappings = [None, None, None, MONTH_WORDS, DOW_WORDS]
    names = ["minute", "hour", "day of month", "month", "day of week"]
    for i, ((low, high), mapping, name) in enumerate(zip(FIELD_RANGES, mappings, names)):
        err = check_field(parts[i], low, high, mapping)
        if err:
            errors.append("line %d, %s field: %s" % (lineno, name, err))
    if not parts[5].strip():
        errors.append("line %d: empty command" % lineno)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate crontab files: time fields, @specials, and commands.",
        epilog="Examples:\n"
               "  crontab-validator.py mycron\n"
               "  crontab-validator.py --line \"*/15 * * * * /usr/bin/backup.sh\"\n"
               "  crontab -l | crontab-validator.py --stdin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("file", nargs="?", default=None, help="crontab file to check")
    group.add_argument("--line", default=None, help="validate a single crontab line")
    group.add_argument("--stdin", action="store_true", help="read crontab from stdin")
    args = parser.parse_args(argv)

    if args.line is not None:
        lines = [args.line]
    elif args.stdin:
        if sys.stdin.isatty():
            parser.error("--stdin needs piped input")
        lines = sys.stdin.read().splitlines()
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except OSError as exc:
            print("Error: cannot read %r: %s" % (args.file, exc), file=sys.stderr)
            return 1
    else:
        parser.error("give a file, --line, or --stdin")

    errors = []
    for lineno, line in enumerate(lines, 1):
        errors.extend(validate_line(line, lineno))

    if errors:
        print("Found %d problem(s):" % len(errors))
        for e in errors:
            print("  " + e)
        return 1
    print("OK: %d line(s), crontab looks valid" % len(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
