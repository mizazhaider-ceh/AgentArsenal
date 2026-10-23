#!/usr/bin/env python3
"""Parse and summarize email headers.

Reads a raw email (file or stdin) and shows From, To, Subject, Date, plus a
Received-hop chain with delays, and flags common spoofing signs.

Usage:
    email-header-analyzer.py message.eml
    cat message.eml | email-header-analyzer.py
"""

import argparse
import email
import email.policy
import email.utils
import re
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Parse email headers: addresses, dates, Received hops, spoofing signs.",
        epilog="Examples:\n"
               "  email-header-analyzer.py message.eml\n"
               "  cat message.eml | email-header-analyzer.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="?", default=None,
                        help="email file in mbox/raw format (default: stdin)")
    args = parser.parse_args(argv)

    try:
        if args.file:
            with open(args.file, "rb") as fh:
                msg = email.message_from_binary_file(fh, policy=email.policy.default)
        else:
            if sys.stdin.isatty():
                parser.error("provide a file or pipe an email on stdin")
            msg = email.message_from_binary_file(sys.stdin.buffer,
                                                 policy=email.policy.default)
    except OSError as exc:
        print("Error: cannot read %r: %s" % (args.file, exc), file=sys.stderr)
        return 1

    print("From:    %s" % msg.get("From", "(missing)"))
    print("To:      %s" % msg.get("To", "(missing)"))
    print("Subject: %s" % msg.get("Subject", "(missing)"))
    print("Date:    %s" % msg.get("Date", "(missing)"))
    print("Message-ID: %s" % msg.get("Message-ID", "(missing)"))
    reply_to = msg.get("Reply-To")
    if reply_to:
        print("Reply-To: %s" % reply_to)

    received = msg.get_all("Received", [])
    print("\nReceived hops: %d" % len(received))
    prev_ts = None
    for i, hop in enumerate(reversed(received), 1):
        one_line = " ".join(hop.split())
        stamp = email.utils.parsedate_to_datetime(
            one_line.rsplit(";", 1)[-1].strip()) if ";" in one_line else None
        delay = ""
        if stamp is not None and prev_ts is not None:
            delay = " (+%ds)" % int((stamp - prev_ts).total_seconds())
        if stamp is not None:
            prev_ts = stamp
        print("  hop %d:%s %s" % (i, delay, one_line[:160]))

    print("\n--- Spoofing checks ---")
    warnings = []
    from_addr = str(msg.get("From", ""))
    if reply_to and reply_to.strip() not in from_addr:
        warnings.append("Reply-To differs from From: possible spoofing")
    from_domain = email.utils.parseaddr(from_addr)[1].split("@")[-1].lower()
    auth = str(msg.get("Authentication-Results", "")).lower()
    if auth:
        if "spf=fail" in auth or "spf=softfail" in auth:
            warnings.append("SPF failed for this message")
        if "dkim=fail" in auth:
            warnings.append("DKIM failed for this message")
        if "dmarc=fail" in auth:
            warnings.append("DMARC failed for this message")
    else:
        warnings.append("no Authentication-Results header present")
    if re.search(r"[^\x00-\x7f]", from_addr):
        warnings.append("From contains non-ASCII characters (possible homoglyph)")
    if not warnings:
        print("No obvious spoofing signs found.")
    else:
        for w in warnings:
            print("WARNING: %s" % w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
