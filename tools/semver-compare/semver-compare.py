#!/usr/bin/env python3
"""Compare semantic versions.

Parses two semver strings (MAJOR.MINOR.PATCH with optional pre-release and
build metadata) and reports which is newer, or tests a constraint.

Usage:
    semver-compare.py 1.2.3 1.10.0
    semver-compare.py 2.0.0-rc.1 2.0.0
    semver-compare.py 1.2.3 --gte 1.0.0
"""

import argparse
import re
import sys

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)


def parse(version):
    m = SEMVER_RE.match(version.strip().lstrip("v"))
    if not m:
        raise ValueError("not a semantic version: %r" % version)
    major, minor, patch, pre, build = m.groups()
    pre_parts = []
    if pre:
        for part in pre.split("."):
            pre_parts.append(int(part) if part.isdigit() else part)
    return (int(major), int(minor), int(patch), pre_parts, build)


def compare(a, b):
    for x, y in zip(a[:3], b[:3]):
        if x != y:
            return -1 if x < y else 1
    pa, pb = a[3], b[3]
    if not pa and not pb:
        return 0
    if not pa:
        return 1
    if not pb:
        return -1
    for x, y in zip(pa, pb):
        if x == y:
            continue
        if isinstance(x, int) and isinstance(y, int):
            return -1 if x < y else 1
        if isinstance(x, int):
            return -1
        if isinstance(y, int):
            return 1
        return -1 if str(x) < str(y) else 1
    if len(pa) != len(pb):
        return -1 if len(pa) < len(pb) else 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare semantic versions (semver.org rules).",
        epilog="Examples:\n"
               "  semver-compare.py 1.2.3 1.10.0\n"
               "  semver-compare.py 2.0.0-rc.1 2.0.0\n"
               "  semver-compare.py 1.2.3 --gte 1.0.0\n"
               "  semver-compare.py 1.2.3 --satisfies '>=1.0.0 <2.0.0'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("version", help="first version")
    parser.add_argument("other", nargs="?", default=None, help="second version to compare against")
    parser.add_argument("--gte", default=None, metavar="VERSION",
                        help="exit 0 if VERSION >= this, else exit 1")
    parser.add_argument("--satisfies", default=None, metavar="RANGE",
                        help="simple range like '>=1.0.0 <2.0.0' to test")
    args = parser.parse_args(argv)

    try:
        v = parse(args.version)
    except ValueError as exc:
        parser.error(str(exc))

    if args.satisfies:
        ok = True
        for token in args.satisfies.split():
            m = re.match(r"^(>=|<=|>|<|=|==)?(.+)$", token)
            op, ver_s = m.group(1) or "=", m.group(2)
            try:
                other = parse(ver_s)
            except ValueError as exc:
                parser.error(str(exc))
            c = compare(v, other)
            good = {">": c > 0, ">=": c >= 0, "<": c < 0, "<=": c <= 0,
                    "=": c == 0, "==": c == 0}[op]
            ok = ok and good
        print("%s satisfies %r: %s" % (args.version, args.satisfies, ok))
        return 0 if ok else 1

    if args.gte:
        try:
            other = parse(args.gte)
        except ValueError as exc:
            parser.error(str(exc))
        result = compare(v, other) >= 0
        print("%s >= %s: %s" % (args.version, args.gte, result))
        return 0 if result else 1

    if args.other is None:
        parser.error("need a second version, --gte, or --satisfies")

    try:
        other = parse(args.other)
    except ValueError as exc:
        parser.error(str(exc))

    c = compare(v, other)
    relation = "equal to" if c == 0 else ("older than" if c < 0 else "newer than")
    print("%s is %s %s" % (args.version, relation, args.other))
    return 0


if __name__ == "__main__":
    sys.exit(main())
