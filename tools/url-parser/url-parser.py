#!/usr/bin/env python3
"""Parse a URL into its parts.

Shows scheme, host, port, path, query parameters, fragment, username, and
flags suspicious traits (credentials in URL, non-default port, IP host).

Usage:
    url-parser.py "https://user:pass@example.com:8443/path?a=1&b=2#frag"
"""

import argparse
import ipaddress
import sys
import urllib.parse


def is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Break a URL into its parts and flag suspicious traits.",
        epilog="Examples:\n"
               "  url-parser.py \"https://example.com/path?a=1&b=2#frag\"\n"
               "  url-parser.py \"http://user:pass@192.168.1.1:8080/login\"\n"
               "  echo \"https://example.com\" | url-parser.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", nargs="?", default=None,
                        help="URL to parse (default: read from stdin)")
    args = parser.parse_args(argv)

    if args.url is None:
        if sys.stdin.isatty():
            parser.error("provide a URL as an argument or on stdin")
        raw = sys.stdin.read().strip()
    else:
        raw = args.url.strip()
    if not raw:
        parser.error("empty URL")

    parsed = urllib.parse.urlparse(raw)
    print("Scheme:   %s" % (parsed.scheme or "(none)"))
    print("Host:     %s" % (parsed.hostname or "(none)"))
    print("Port:     %s" % (parsed.port if parsed.port else "(default)"))
    print("Path:     %s" % (parsed.path or "/"))
    print("Fragment: %s" % (parsed.fragment or "(none)"))
    if parsed.username:
        print("Username: %s" % parsed.username)
    if parsed.password:
        print("Password: (present, %d chars)" % len(parsed.password))

    params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    print("Query params: %d" % len(params))
    for key, value in params:
        print("  %s = %s" % (key, value))

    print("--- Checks ---")
    warnings = []
    if parsed.username or parsed.password:
        warnings.append("credentials embedded in URL (they leak in logs)")
    if parsed.hostname and is_ip(parsed.hostname):
        warnings.append("host is a raw IP address, not a domain")
    if parsed.scheme == "http":
        warnings.append("plain HTTP, traffic is not encrypted")
    if not parsed.scheme:
        warnings.append("no scheme, parsing may be unreliable")
    if not warnings:
        print("No suspicious traits found.")
    else:
        for w in warnings:
            print("WARNING: %s" % w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
