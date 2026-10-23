#!/usr/bin/env python3
"""Fetch and inspect HTTP response headers.

Makes one GET request (http or https) and prints the status line, headers,
and a short security-header checklist. Follows redirects.

Usage:
    http-header-checker.py https://example.com
"""

import argparse
import http.client
import ssl
import sys
import urllib.parse

SECURITY_HEADERS = {
    "strict-transport-security": "HSTS (force HTTPS)",
    "content-security-policy": "CSP (limit resource loading)",
    "x-frame-options": "clickjacking protection",
    "x-content-type-options": "MIME sniffing protection",
    "referrer-policy": "referrer control",
    "permissions-policy": "feature control",
}


def fetch(url, timeout):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    context = ssl.create_default_context()
    if parsed.scheme == "https":
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=context)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)

    redirects = 0
    current_url = url
    while redirects <= 5:
        conn.request("GET", path, headers={"User-Agent": "http-header-checker/1.0"})
        resp = conn.getresponse()
        body_skip = resp.read(0)
        if resp.status in (301, 302, 303, 307, 308):
            location = resp.getheader("Location")
            if not location:
                break
            current_url = urllib.parse.urljoin(current_url, location)
            parsed = urllib.parse.urlparse(current_url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            conn.close()
            if parsed.scheme == "https":
                conn = http.client.HTTPSConnection(host, port, timeout=timeout,
                                                   context=context)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=timeout)
            redirects += 1
            continue
        return resp.status, resp.reason, resp.getheaders(), current_url
    raise RuntimeError("too many redirects")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch a URL and print its HTTP response headers plus a "
                    "security-header checklist.",
        epilog="Examples:\n"
               "  http-header-checker.py https://example.com\n"
               "  http-header-checker.py http://example.com --timeout 5\n"
               "  http-header-checker.py https://example.com --no-checklist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="URL to fetch (http:// or https://)")
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="request timeout in seconds (default: 10.0)")
    parser.add_argument("--no-checklist", action="store_true",
                        help="skip the security-header checklist")
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    try:
        status, reason, headers, final_url = fetch(args.url, args.timeout)
    except (ValueError, RuntimeError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        print("Error: request failed: %s" % exc, file=sys.stderr)
        return 1

    if final_url != args.url:
        print("Final URL: %s" % final_url)
    print("Status: %d %s" % (status, reason))
    print("--- Headers ---")
    present = set()
    for name, value in headers:
        print("%s: %s" % (name, value))
        present.add(name.lower())

    if not args.no_checklist:
        print("--- Security header checklist ---")
        for header, meaning in SECURITY_HEADERS.items():
            mark = "present" if header in present else "MISSING"
            print("[%s] %s: %s" % (mark, header, meaning))
    return 0


if __name__ == "__main__":
    sys.exit(main())
