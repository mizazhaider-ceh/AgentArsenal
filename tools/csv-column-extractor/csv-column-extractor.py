#!/usr/bin/env python3
"""Extract columns from a CSV file.

Prints selected columns by name or index, optionally deduplicated or counted.

Usage:
    csv-column-extractor.py users.csv --columns name,email
    csv-column-extractor.py data.csv -c 0,2 --unique --count
"""

import argparse
import csv
import sys
from collections import Counter


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract columns from a CSV file by name or index.",
        epilog="Examples:\n"
               "  csv-column-extractor.py users.csv --columns name,email\n"
               "  csv-column-extractor.py data.csv -c 0,2 --unique\n"
               "  csv-column-extractor.py log.csv -c status --count --top 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("csvfile", help="path to the CSV file")
    parser.add_argument("-c", "--columns", required=True,
                        help="comma-separated column names or 0-based indexes")
    parser.add_argument("--delimiter", default=",",
                        help="field delimiter (default: ,)")
    parser.add_argument("--no-header", action="store_true",
                        help="file has no header row (columns must be indexes)")
    parser.add_argument("--unique", action="store_true",
                        help="print only unique value combinations")
    parser.add_argument("--count", action="store_true",
                        help="count occurrences instead of printing rows")
    parser.add_argument("--top", type=int, default=10,
                        help="with --count, show the top N (default: 10)")
    args = parser.parse_args(argv)

    try:
        fh = open(args.csvfile, "r", encoding="utf-8", newline="")
    except OSError as exc:
        print("Error: cannot read %r: %s" % (args.csvfile, exc), file=sys.stderr)
        return 1

    with fh:
        reader = csv.reader(fh, delimiter=args.delimiter)
        rows = list(reader)

    if not rows:
        print("Error: file is empty", file=sys.stderr)
        return 1

    if args.no_header:
        header = None
        data = rows
    else:
        header = rows[0]
        data = rows[1:]

    wanted = [c.strip() for c in args.columns.split(",") if c.strip()]
    indexes = []
    for col in wanted:
        if col.isdigit():
            idx = int(col)
            width = len(header) if header else (len(data[0]) if data else 0)
            if not 0 <= idx < width:
                parser.error("column index %d out of range" % idx)
            indexes.append(idx)
        else:
            if args.no_header:
                parser.error("column names need a header row (drop --no-header)")
            if col not in header:
                parser.error("unknown column %r (have: %s)" % (col, ", ".join(header)))
            indexes.append(header.index(col))

    extracted = [tuple(row[i] if i < len(row) else "" for i in indexes) for row in data]

    if args.count:
        counter = Counter(extracted)
        print("Unique combinations: %d" % len(counter))
        for combo, n in counter.most_common(args.top if args.top > 0 else None):
            print("%5d  %s" % (n, ", ".join(combo)))
    elif args.unique:
        for combo in sorted(set(extracted)):
            print(", ".join(combo))
    else:
        for combo in extracted:
            print(", ".join(combo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
