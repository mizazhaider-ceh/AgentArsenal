#!/usr/bin/env python3
"""Grab service banners from TCP ports.

Connects to host:port and reads whatever the service sends first. Optionally
sends a probe string first (useful for HTTP or SMTP). Only probe hosts you
own or have permission to test.

Usage:
    banner-grabber.py example.com 80
    banner-grabber.py example.com 80 --probe "HEAD / HTTP/1.0"
"""

import argparse
import socket
import sys


def grab(host, port, probe, timeout):
    """Connect, optionally send a probe, read up to 4 KiB. Returns bytes."""
    data = b""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        if probe:
            sock.sendall(probe.encode("utf-8", "replace") + b"\r\n")
        try:
            while len(data) < 4096:
                chunk = sock.recv(4096 - len(data))
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Grab the banner a TCP service sends when you connect. "
                    "Only probe hosts you own or have permission to test.",
        epilog="Examples:\n"
               "  banner-grabber.py 192.168.1.10 22\n"
               "  banner-grabber.py example.com 80 --probe \"HEAD / HTTP/1.0\"\n"
               "  banner-grabber.py mail.example.com 25 --timeout 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("host", help="target hostname or IP address")
    parser.add_argument("port", type=int, help="TCP port to connect to")
    parser.add_argument("--probe", default="",
                        help="text to send before reading (sent with CRLF)")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="timeout in seconds (default: 5.0)")
    args = parser.parse_args(argv)

    if not 1 <= args.port <= 65535:
        parser.error("port must be 1-65535")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    try:
        data = grab(args.host, args.port, args.probe, args.timeout)
    except socket.gaierror as exc:
        print("Error: cannot resolve %r: %s" % (args.host, exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print("Error: connection to %s:%d failed: %s" % (args.host, args.port, exc),
              file=sys.stderr)
        return 1

    if data:
        text = data.decode("utf-8", "replace")
        print(text, end="" if text.endswith("\n") else "\n")
    else:
        print("(no data received)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
