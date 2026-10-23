#!/usr/bin/env python3
"""Look up the meaning of an HTTP status code.

Prints the reason phrase and the code class (1xx informational, 2xx success,
3xx redirection, 4xx client error, 5xx server error), with a short note for
common codes.

Usage:
    http-status-lookup.py 404
    http-status-lookup.py 418
"""

import argparse
import http
import sys

NOTES = {
    200: "OK, the standard success response.",
    201: "Created, a new resource was made.",
    204: "No Content, success with an empty body.",
    301: "Moved Permanently, update bookmarks and links.",
    302: "Found, temporary redirect.",
    304: "Not Modified, use the cached copy.",
    400: "Bad Request, the server could not parse it.",
    401: "Unauthorized, authentication is required.",
    403: "Forbidden, you lack permission.",
    404: "Not Found, wrong URL or removed resource.",
    405: "Method Not Allowed for this URL.",
    408: "Request Timeout.",
    409: "Conflict with the current state.",
    418: "I am a teapot (April Fools joke, RFC 2324).",
    422: "Unprocessable Entity, semantic errors in the body.",
    429: "Too Many Requests, slow down (rate limited).",
    500: "Internal Server Error, something broke server-side.",
    502: "Bad Gateway, upstream server gave a bad reply.",
    503: "Service Unavailable, try again later.",
    504: "Gateway Timeout, upstream took too long.",
}


def describe(code):
    try:
        phrase = http.HTTPStatus(code).phrase
    except ValueError:
        return None
    cls = {1: "Informational", 2: "Success", 3: "Redirection",
           4: "Client error", 5: "Server error"}.get(code // 100, "Unknown")
    return phrase, cls


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Look up the meaning of an HTTP status code.",
        epilog="Examples:\n"
               "  http-status-lookup.py 404\n"
               "  http-status-lookup.py 503\n"
               "  http-status-lookup.py 200 301 404",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("codes", nargs="+", help="one or more status codes, e.g. 404")
    args = parser.parse_args(argv)

    failed = False
    for raw in args.codes:
        try:
            code = int(raw)
        except ValueError:
            print("Error: %r is not a number" % raw, file=sys.stderr)
            failed = True
            continue
        result = describe(code)
        if result is None:
            print("%d: not a standard HTTP status code" % code)
            continue
        phrase, cls = result
        print("%d %s  [%s]" % (code, phrase, cls))
        if code in NOTES:
            print("    %s" % NOTES[code])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
