#!/usr/bin/env python3
"""Pick a random sample from a list.

Reads items from arguments or a file (one per line) and prints N random
picks, with or without replacement. Uses the secrets module.

Usage:
    random-sample-picker.py alice bob carol dave -n 2
    random-sample-picker.py --file candidates.txt -n 3 --seed 42
"""

import argparse
import random
import secrets
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Pick N random items from a list (with or without replacement).",
        epilog="Examples:\n"
               "  random-sample-picker.py alice bob carol dave -n 2\n"
               "  random-sample-picker.py --file candidates.txt -n 3\n"
               "  cat names.txt | random-sample-picker.py -n 1\n"
               "  random-sample-picker.py a b c -n 5 --replace --seed 42",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("items", nargs="*", default=[],
                        help="items to pick from")
    parser.add_argument("--file", default=None,
                        help="file with one item per line")
    parser.add_argument("-n", "--number", type=int, default=1,
                        help="how many items to pick (default: 1)")
    parser.add_argument("--replace", action="store_true",
                        help="allow picking the same item twice")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed for reproducible picks (default: secure random)")
    args = parser.parse_args(argv)

    if args.number < 1:
        parser.error("--number must be at least 1")

    items = list(args.items)
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                items += [l.strip() for l in fh if l.strip()]
        except OSError as exc:
            print("Error: cannot read %r: %s" % (args.file, exc), file=sys.stderr)
            return 1
    if not items and not sys.stdin.isatty():
        items += [l.strip() for l in sys.stdin if l.strip()]
    if not items:
        parser.error("no items to pick from (give arguments, --file, or stdin)")

    rng = random.Random(args.seed) if args.seed is not None else secrets.SystemRandom()

    if not args.replace and args.number > len(items):
        parser.error("cannot pick %d unique items from %d (use --replace)"
                     % (args.number, len(items)))

    if args.replace:
        picks = [rng.choice(items) for _ in range(args.number)]
    else:
        picks = rng.sample(items, args.number)

    for pick in picks:
        print(pick)
    return 0


if __name__ == "__main__":
    sys.exit(main())
