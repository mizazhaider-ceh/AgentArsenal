#!/usr/bin/env python3
"""TCP port scanner using stdlib sockets and threads.

Scans a single host for open TCP ports. Scan only hosts you own or have
written permission to test. Unauthorized scanning can be illegal.

Usage:
    port-scanner.py example.com -p 1-1024
    port-scanner.py 192.168.1.10 -p 22,80,443,8000-8010 -t 0.5 -w 100
"""

import argparse
import ipaddress
import socket
import sys
from concurrent.futures import ThreadPoolExecutor


def parse_ports(spec):
    """Parse '80' or '22,80,443' or '1-1024' or mixed into a sorted list of ports."""
    ports = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            try:
                start, end = int(start_s), int(end_s)
            except ValueError:
                raise ValueError("bad port range: %r" % part)
            if not (1 <= start <= 65535 and 1 <= end <= 65535):
                raise ValueError("ports must be 1-65535: %r" % part)
            if start > end:
                raise ValueError("range start greater than end: %r" % part)
            ports.update(range(start, end + 1))
        else:
            try:
                port = int(part)
            except ValueError:
                raise ValueError("bad port: %r" % part)
            if not 1 <= port <= 65535:
                raise ValueError("ports must be 1-65535: %r" % part)
            ports.add(port)
    return sorted(ports)


def resolve_host(host):
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        try:
            return socket.gethostbyname(host)
        except socket.gaierror as exc:
            raise ValueError("cannot resolve host %r: %s" % (host, exc))


def is_open(target, port, timeout):
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return True
    except OSError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scan a host for open TCP ports (connect scan). "
                    "Only scan hosts you own or have permission to test.",
        epilog="Examples:\n"
               "  port-scanner.py scanme.example.com -p 1-1000\n"
               "  port-scanner.py 192.168.1.10 -p 22,80,443,8000-8100 -t 0.5 -w 100\n"
               "  port-scanner.py 10.0.0.5 -p 443 --timeout 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("host", help="target hostname or IP address")
    parser.add_argument("-p", "--ports", default="1-1024",
                        help="ports to scan: '80', '22,80,443', '1-1024', or mixed (default: 1-1024)")
    parser.add_argument("-t", "--timeout", type=float, default=1.0,
                        help="connection timeout in seconds (default: 1.0)")
    parser.add_argument("-w", "--workers", type=int, default=50,
                        help="parallel threads (default: 50)")
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    try:
        ports = parse_ports(args.ports)
    except ValueError as exc:
        parser.error(str(exc))
    if not ports:
        parser.error("no ports to scan")
    if len(ports) > 65535:
        parser.error("too many ports requested")

    try:
        target = resolve_host(args.host)
    except ValueError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 2

    open_ports = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = pool.map(lambda p: (p, is_open(target, p, args.timeout)), ports)
        for port, open_ in results:
            if open_:
                open_ports.append(port)

    for port in open_ports:
        print(port)
    print("Scanned %d ports on %s (%s): %d open" % (len(ports), args.host, target, len(open_ports)),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
