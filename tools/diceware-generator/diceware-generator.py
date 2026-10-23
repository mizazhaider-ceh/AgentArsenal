#!/usr/bin/env python3
"""Generate a diceware passphrase.

Picks random words from a built-in wordlist using the secrets module.
Default wordlist is a compact built-in set; pass --wordlist for a larger
file (one word per line).

Usage:
    diceware-generator.py
    diceware-generator.py -w 6 --separator -
"""

import argparse
import secrets
import sys

BUILTIN_WORDS = (
    "apple banana cherry dragon eagle forest grape harbor ivory jungle kiwi "
    "lemon mango night ocean piano quiet river stone tiger umbrella violet "
    "water xenon yellow zebra anchor bridge cloud dance ember flame globe "
    "house island juice kite lunar maple north orbit pilot quake ridge solar "
    "table unity vapor whale youth alarm blade coral drift echo frost glove "
    "hinge inlet joker knife lodge medal nerve onion pearl queen razor sable "
    "torch uncle vivid worry yacht".split()
)


def load_wordlist(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            words = [w.strip() for w in fh if w.strip() and not w.startswith("#")]
    except OSError as exc:
        raise ValueError("cannot read wordlist: %s" % exc)
    if len(words) < 10:
        raise ValueError("wordlist too small (%d words)" % len(words))
    return words


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a diceware-style passphrase from random words.",
        epilog="Examples:\n"
               "  diceware-generator.py\n"
               "  diceware-generator.py -w 6 --separator -\n"
               "  diceware-generator.py --wordlist /usr/share/dict/words -w 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-w", "--words", type=int, default=4,
                        help="number of words (default: 4)")
    parser.add_argument("--separator", default=" ",
                        help="word separator (default: space)")
    parser.add_argument("--wordlist", default=None,
                        help="path to a wordlist file (one word per line)")
    parser.add_argument("--capitalize", action="store_true",
                        help="capitalize each word")
    args = parser.parse_args(argv)

    if args.words < 1:
        parser.error("--words must be at least 1")

    words = BUILTIN_WORDS
    if args.wordlist:
        try:
            words = load_wordlist(args.wordlist)
        except ValueError as exc:
            print("Error: %s" % exc, file=sys.stderr)
            return 1

    picked = [secrets.choice(words) for _ in range(args.words)]
    if args.capitalize:
        picked = [w.capitalize() for w in picked]
    print(args.separator.join(picked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
