#!/usr/bin/env python3
"""Generate UUIDs.

Prints version 4 (random), version 1 (time-based), version 3 (MD5 name-based),
or version 5 (SHA-1 name-based) UUIDs.

Usage:
    uuid-generator.py
    uuid-generator.py -n 5 -v 4
    uuid-generator.py -v 5 --namespace dns --name example.com
"""

import argparse
import sys
import uuid

NAMESPACES = {
    "dns": uuid.NAMESPACE_DNS,
    "url": uuid.NAMESPACE_URL,
    "oid": uuid.NAMESPACE_OID,
    "x500": uuid.NAMESPACE_X500,
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate UUIDs (versions 1, 3, 4, 5).",
        epilog="Examples:\n"
               "  uuid-generator.py\n"
               "  uuid-generator.py -n 5\n"
               "  uuid-generator.py -v 5 --namespace dns --name example.com\n"
               "  uuid-generator.py -v 1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-n", "--number", type=int, default=1,
                        help="how many UUIDs to print (default: 1)")
    parser.add_argument("-v", "--version", type=int, choices=[1, 3, 4, 5], default=4,
                        help="UUID version (default: 4)")
    parser.add_argument("--namespace", choices=sorted(NAMESPACES), default="dns",
                        help="namespace for v3/v5 (default: dns)")
    parser.add_argument("--name", default="example.com",
                        help="name for v3/v5 (default: example.com)")
    parser.add_argument("--upper", action="store_true",
                        help="print in uppercase")
    args = parser.parse_args(argv)

    if args.number < 1:
        parser.error("--number must be at least 1")

    for _ in range(args.number):
        if args.version == 1:
            value = uuid.uuid1()
        elif args.version == 3:
            value = uuid.uuid3(NAMESPACES[args.namespace], args.name)
            print(str(value).upper() if args.upper else str(value))
            return 0
        elif args.version == 5:
            value = uuid.uuid5(NAMESPACES[args.namespace], args.name)
            print(str(value).upper() if args.upper else str(value))
            return 0
        else:
            value = uuid.uuid4()
        text = str(value)
        print(text.upper() if args.upper else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
