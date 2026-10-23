#!/usr/bin/env python3
"""Generate and verify TOTP codes (RFC 6238).

Generates the current 6-digit code for a base32 secret, or verifies a code
you type. Also prints a provisioning URI you can turn into a QR code.

Usage:
    totp-generator.py JBSWY3DPEHPK3PXP
    totp-generator.py JBSWY3DPEHPK3PXP --verify 123456
"""

import argparse
import base64
import binascii
import hashlib
import hmac
import struct
import sys
import time


def hotp(secret, counter, digits=6, algo="sha1"):
    msg = struct.pack(">Q", counter)
    mac = hmac.new(secret, msg, getattr(hashlib, algo)).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** digits)).zfill(digits)


def totp(secret, when=None, step=30, digits=6, algo="sha1"):
    when = time.time() if when is None else when
    return hotp(secret, int(when // step), digits, algo)


def decode_secret(raw):
    cleaned = "".join(raw.split()).upper()
    padding = "=" * (-len(cleaned) % 8)
    try:
        return base64.b32decode(cleaned + padding)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("bad base32 secret: %s" % exc)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate or verify TOTP codes (RFC 6238) from a base32 secret.",
        epilog="Examples:\n"
               "  totp-generator.py JBSWY3DPEHPK3PXP\n"
               "  totp-generator.py JBSWY3DPEHPK3PXP --verify 123456\n"
               "  totp-generator.py JBSWY3DPEHPK3PXP --issuer myapp --account user@example.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("secret", help="base32-encoded TOTP secret")
    parser.add_argument("--verify", default=None, metavar="CODE",
                        help="check this code instead of generating one")
    parser.add_argument("--digits", type=int, choices=[6, 8], default=6,
                        help="code length (default: 6)")
    parser.add_argument("--step", type=int, default=30,
                        help="time step in seconds (default: 30)")
    parser.add_argument("--algo", choices=["sha1", "sha256", "sha512"], default="sha1",
                        help="HMAC hash (default: sha1)")
    parser.add_argument("--issuer", default=None, help="issuer name for the provisioning URI")
    parser.add_argument("--account", default="user", help="account name for the provisioning URI")
    args = parser.parse_args(argv)

    if args.step < 1:
        parser.error("--step must be at least 1")

    try:
        secret = decode_secret(args.secret)
    except ValueError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 2

    if args.verify is not None:
        now = int(time.time() // args.step)
        ok = any(totp(secret, (c * args.step), args.step, args.digits, args.algo)
                 == args.verify for c in (now - 1, now, now + 1))
        print("Code %s" % ("VALID" if ok else "INVALID"))
        return 0 if ok else 1

    code = totp(secret, step=args.step, digits=args.digits, algo=args.algo)
    remaining = args.step - int(time.time() % args.step)
    print("Current code: %s (expires in %ds)" % (code, remaining))
    uri = "otpauth://totp/%s?secret=%s&issuer=%s&digits=%d&period=%d&algorithm=%s" % (
        args.account, "".join(args.secret.split()).upper(),
        args.issuer or "totp-generator", args.digits, args.step, args.algo.upper())
    print("Provisioning URI: %s" % uri)
    return 0


if __name__ == "__main__":
    sys.exit(main())
