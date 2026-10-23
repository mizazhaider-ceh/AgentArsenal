#!/usr/bin/env python3
"""Expand port range specs into full port lists.

Turns specs like "80,443,8000-8005" into one port per line, or a compact
comma list. Also validates with an optional nmap-style "T:" prefix strip.

Usage:
    port-list-expander.py "80,443,8000-8005"
    port-list-expander.py "1-1024" --compact
"""

import argparse
import sys


def expand(spec):
    ports = set()
    cleaned = spec.strip()
    if cleaned.upper().startswith("T:"):
        cleaned = cleaned[2:]
    for part in cleaned.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            try:
                start, end = int(start_s), int(end_s)
            except ValueError:
                raise ValueError("bad range: %r" % part)
            if not (0 <= start <= 65535 and 0 <= end <= 65535):
                raise ValueError("ports must be 0-65535: %r" % part)
            if start > end:
                raise ValueError("range start after end: %r" % part)
            ports.update(range(start, end + 1))
        else:
            try:
                port = int(part)
            except ValueError:
                raise ValueError("bad port: %r" % part)
            if not 0 <= port <= 65535:
                raise ValueError("ports must be 0-65535: %r" % part)
            ports.add(port)
    return sorted(ports)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Expand a port range spec (80,443,8000-8005) into a full port list.",
        epilog="Examples:\n"
               "  port-list-expander.py \"80,443,8000-8005\"\n"
               "  port-list-expander.py \"1-1024\" --compact\n"
               "  port-list-expander.py \"T:22,80\" --count-only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("spec", help="port spec: numbers, ranges, comma lists, optional T: prefix")
    parser.add_argument("--compact", action="store_true",
                        help="print as one comma-separated line")
    parser.add_argument("--count-only", action="store_true",
                        help="print only the number of ports")
    args = parser.parse_args(argv)

    try:
        ports = expand(args.spec)
    except ValueError as exc:
        parser.error(str(exc))

    if args.count_only:
        print(len(ports))
    elif args.compact:
        print(",".join(str(p) for p in ports))
    else:
        for port in ports:
            print(port)
    if not args.count_only:
        print("Total: %d ports" % len(ports), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
