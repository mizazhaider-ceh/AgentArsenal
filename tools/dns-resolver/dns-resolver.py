#!/usr/bin/env python3
"""Resolve DNS records with stdlib sockets.

Looks up A, AAAA, and reverse (PTR) records. This uses the system resolver,
so it shows what your machine sees, not a full authoritative lookup.

Usage:
    dns-resolver.py example.com
    dns-resolver.py example.com --reverse
    dns-resolver.py 93.184.216.34 --reverse
"""

import argparse
import ipaddress
import socket
import sys


def is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Resolve DNS records for a hostname or IP using the system resolver.",
        epilog="Examples:\n"
               "  dns-resolver.py example.com\n"
               "  dns-resolver.py 93.184.216.34 --reverse\n"
               "  dns-resolver.py example.com --all",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", help="hostname or IP address")
    parser.add_argument("--reverse", action="store_true",
                        help="do a reverse (PTR) lookup on an IP")
    parser.add_argument("--all", action="store_true",
                        help="show all address families (A and AAAA)")
    args = parser.parse_args(argv)

    if args.reverse:
        if not is_ip(args.target):
            parser.error("--reverse needs an IP address")
        try:
            name, aliases, _ = socket.gethostbyaddr(args.target)
        except (socket.herror, socket.gaierror, OSError) as exc:
            print("Error: reverse lookup failed: %s" % exc, file=sys.stderr)
            return 1
        print("PTR: %s" % name)
        for alias in aliases:
            print("Alias: %s" % alias)
        return 0

    try:
        infos = socket.getaddrinfo(args.target, None, socket.AF_UNSPEC,
                                   socket.SOCK_STREAM)
    except socket.gaierror as exc:
        print("Error: cannot resolve %r: %s" % (args.target, exc), file=sys.stderr)
        return 1

    seen = []
    for family, _, _, _, sockaddr in infos:
        ip = sockaddr[0]
        kind = "AAAA" if family == socket.AF_INET6 else "A"
        if (kind, ip) not in seen:
            seen.append((kind, ip))

    if not args.all:
        seen = [entry for entry in seen if entry[0] == "A"] or seen

    for kind, ip in seen:
        print("%s: %s" % (kind, ip))

    try:
        canon = socket.getfqdn(args.target)
        print("FQDN: %s" % canon)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
