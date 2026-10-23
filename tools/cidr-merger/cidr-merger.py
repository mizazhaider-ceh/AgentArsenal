#!/usr/bin/env python3
"""Merge overlapping or adjacent CIDR ranges.

Takes a list of networks (arguments or a file, one per line) and prints the
smallest set of CIDRs covering them, using ipaddress.collapse_addresses.

Usage:
    cidr-merger.py 192.168.1.0/24 192.168.2.0/24
    cidr-merger.py --file ranges.txt
"""

import argparse
import ipaddress
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Collapse overlapping or adjacent CIDR ranges into the minimal set.",
        epilog="Examples:\n"
               "  cidr-merger.py 192.168.1.0/24 192.168.2.0/24\n"
               "  cidr-merger.py 10.0.0.0/24 10.0.0.128/25 10.0.1.0/24\n"
               "  cidr-merger.py --file ranges.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("networks", nargs="*", default=[],
                        help="CIDR networks to merge")
    parser.add_argument("--file", default=None,
                        help="file with one CIDR per line (blank lines and # comments ignored)")
    parser.add_argument("--count", action="store_true",
                        help="also print the total address count")
    args = parser.parse_args(argv)

    raw = list(args.networks)
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.split("#", 1)[0].strip()
                    if line:
                        raw.append(line)
        except OSError as exc:
            print("Error: cannot read %r: %s" % (args.file, exc), file=sys.stderr)
            return 1

    if not raw:
        parser.error("no networks given (pass arguments or --file)")

    networks = []
    for item in raw:
        try:
            networks.append(ipaddress.ip_network(item.strip(), strict=False))
        except ValueError as exc:
            print("Error: invalid network %r: %s" % (item, exc), file=sys.stderr)
            return 2

    if any(n.version == 4 for n in networks) and any(n.version == 6 for n in networks):
        print("Note: mixing IPv4 and IPv6, collapsing each family separately",
              file=sys.stderr)

    merged = list(ipaddress.collapse_addresses(networks))
    for net in merged:
        print(net)
    if args.count:
        total = sum(n.num_addresses for n in merged)
        print("Total addresses: %d" % total, file=sys.stderr)
    print("Input: %d networks, output: %d networks" % (len(raw), len(merged)),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
