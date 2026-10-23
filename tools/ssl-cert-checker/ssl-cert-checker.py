#!/usr/bin/env python3
"""Inspect a TLS certificate of a remote host.

Connects to host:port, reads the peer certificate, and prints subject,
issuer, validity dates, SANs, and days until expiry.

Usage:
    ssl-cert-checker.py example.com
    ssl-cert-checker.py example.com:8443
"""

import argparse
import datetime
import socket
import ssl
import sys


def parse_hostport(value):
    if value.count(":") == 1:
        host, port_s = value.split(":", 1)
        try:
            port = int(port_s)
        except ValueError:
            raise ValueError("bad port in %r" % value)
    else:
        host, port = value, 443
    if not host:
        raise ValueError("empty host in %r" % value)
    if not 1 <= port <= 65535:
        raise ValueError("port must be 1-65535")
    return host, port


def name_to_str(name):
    return ", ".join("%s=%s" % (k, v) for rdn in name for k, v in rdn)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Show the TLS certificate details for a host (subject, issuer, "
                    "dates, SANs, days left).",
        epilog="Examples:\n"
               "  ssl-cert-checker.py example.com\n"
               "  ssl-cert-checker.py example.com:8443\n"
               "  ssl-cert-checker.py example.com --timeout 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", help="hostname, optionally with :port (default port 443)")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="timeout in seconds (default: 10.0)")
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    try:
        host, port = parse_hostport(args.target)
    except ValueError as exc:
        parser.error(str(exc))

    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=args.timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
                version = tls.version()
                cipher = tls.cipher()
    except socket.gaierror as exc:
        print("Error: cannot resolve %r: %s" % (host, exc), file=sys.stderr)
        return 2
    except (OSError, ssl.SSLError) as exc:
        print("Error: TLS connection failed: %s" % exc, file=sys.stderr)
        return 1

    print("Host:    %s:%d" % (host, port))
    if version:
        print("TLS:     %s" % version)
    if cipher:
        print("Cipher:  %s" % cipher[0])
    print("Subject: %s" % name_to_str(cert.get("subject", [])))
    print("Issuer:  %s" % name_to_str(cert.get("issuer", [])))
    print("Valid from: %s" % cert.get("notBefore", "unknown"))
    print("Valid to:   %s" % cert.get("notAfter", "unknown"))

    try:
        expires = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        expires = expires.replace(tzinfo=datetime.timezone.utc)
        left = expires - datetime.datetime.now(datetime.timezone.utc)
        print("Days left: %d" % left.days)
        if left.days < 0:
            print("Status: EXPIRED")
        elif left.days < 30:
            print("Status: expiring soon (under 30 days)")
        else:
            print("Status: valid")
    except (KeyError, ValueError):
        print("Days left: unknown")

    sans = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
    if sans:
        print("SANs:")
        for san in sans:
            print("  - %s" % san)
    return 0


if __name__ == "__main__":
    sys.exit(main())
