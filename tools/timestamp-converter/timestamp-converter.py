#!/usr/bin/env python3
"""Convert between Unix timestamps and readable dates.

Converts epoch seconds (or milliseconds) to a UTC/local date, or parses a
date string into epoch seconds.

Usage:
    timestamp-converter.py 1700000000
    timestamp-converter.py "2023-11-14 22:13:20"
    timestamp-converter.py now
"""

import argparse
import calendar
import datetime
import sys
import time


def from_epoch(value):
    if value >= 1e12:
        value = value / 1000.0
        unit = "milliseconds"
    else:
        unit = "seconds"
    dt = datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
    local = dt.astimezone()
    print("Interpreted as %s" % unit)
    print("UTC:   %s" % dt.strftime("%Y-%m-%d %H:%M:%S"))
    print("Local: %s" % local.strftime("%Y-%m-%d %H:%M:%S %Z"))
    print("ISO:   %s" % dt.isoformat())


def to_epoch(text):
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
               "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError("could not parse date %r (try YYYY-MM-DD HH:MM:SS)" % text)
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    print("UTC assumed: %s" % dt.strftime("%Y-%m-%d %H:%M:%S"))
    print("Epoch seconds: %d" % int(dt.timestamp()))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert Unix timestamps to dates and dates to Unix timestamps.",
        epilog="Examples:\n"
               "  timestamp-converter.py 1700000000\n"
               "  timestamp-converter.py 1700000000000\n"
               "  timestamp-converter.py \"2023-11-14 22:13:20\"\n"
               "  timestamp-converter.py now",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("value", help="epoch seconds, epoch ms, a date string, or 'now'")
    args = parser.parse_args(argv)

    if args.value.lower() == "now":
        now = time.time()
        print("Now: %d" % int(now))
        from_epoch(now)
        return 0

    try:
        number = float(args.value)
    except ValueError:
        number = None

    try:
        if number is not None:
            from_epoch(number)
        else:
            to_epoch(args.value)
    except (ValueError, OverflowError, OSError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
