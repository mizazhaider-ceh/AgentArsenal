#!/usr/bin/env python3
"""Explain a cron schedule in plain English.

Parses the five standard cron fields (minute hour day-of-month month
day-of-week) and describes when the job runs.

Usage:
    cron-explainer.py "*/15 * * * *"
    cron-explainer.py "0 9 * * 1-5"
"""

import argparse
import sys

FIELD_NAMES = ["minute", "hour", "day of month", "month", "day of week"]
FIELD_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def expand_field(field, low, high):
    values = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            try:
                step = int(step_s)
            except ValueError:
                raise ValueError("bad step in %r" % field)
            if step < 1:
                raise ValueError("step must be at least 1 in %r" % field)
        if part == "*":
            start, end = low, high
        elif "-" in part:
            start_s, end_s = part.split("-", 1)
            try:
                start, end = int(start_s), int(end_s)
            except ValueError:
                raise ValueError("bad range in %r" % field)
        else:
            try:
                start = end = int(part)
            except ValueError:
                raise ValueError("bad value %r in field %r" % (part, field))
        if not (low <= start <= high and low <= end <= high):
            raise ValueError("value out of range %d-%d in %r" % (low, high, field))
        if start > end:
            raise ValueError("range start after end in %r" % field)
        values.update(range(start, end + 1, step))
    return sorted(values)


def describe_field(values, low, high, names=None):
    if values == list(range(low, high + 1)) or (low == 0 and high == 7
            and set(values) == set(range(0, 8))):
        return "every value"
    if names:
        return ", ".join(names[v % len(names)] for v in values)
    if len(values) <= 6:
        return ", ".join(str(v) for v in values)
    diffs = {b - a for a, b in zip(values, values[1:])}
    if len(diffs) == 1:
        return "every %d starting at %d" % (diffs.pop(), values[0])
    return "%d values from %d to %d" % (len(values), values[0], values[-1])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Explain a cron schedule (five fields) in plain English.",
        epilog="Examples:\n"
               "  cron-explainer.py \"*/15 * * * *\"\n"
               "  cron-explainer.py \"0 9 * * 1-5\"\n"
               "  cron-explainer.py \"30 2 1 * *\"",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("schedule", help="cron expression, e.g. \"*/15 * * * *\"")
    args = parser.parse_args(argv)

    fields = args.schedule.split()
    if len(fields) != 5:
        parser.error("a cron schedule needs exactly 5 fields, got %d" % len(fields))

    expanded = []
    for field, (low, high) in zip(fields, FIELD_RANGES):
        try:
            expanded.append(expand_field(field, low, high))
        except ValueError as exc:
            parser.error(str(exc))

    minute, hour, dom, month, dow = expanded
    print("Schedule: %s" % args.schedule)
    print("Runs at minute:      %s" % describe_field(minute, 0, 59))
    print("Runs at hour:        %s" % describe_field(hour, 0, 23))
    print("Runs on day:         %s" % describe_field(dom, 1, 31))
    print("Runs in month:       %s" % describe_field(month, 1, 12, MONTH_NAMES))
    print("Runs on weekday:     %s" % describe_field(dow, 0, 7, DOW_NAMES))

    summary = []
    if len(minute) == 1 and len(hour) == 1:
        summary.append("at %02d:%02d" % (hour[0], minute[0]))
    elif len(hour) == 1:
        summary.append("during hour %02d" % hour[0])
    if len(dow) < 7:
        summary.append("on " + describe_field(dow, 0, 7, DOW_NAMES))
    if len(dom) == 1 and len(month) == 12:
        summary.append("on day %d of the month" % dom[0])
    if summary:
        print("In short: runs " + ", ".join(summary) + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
