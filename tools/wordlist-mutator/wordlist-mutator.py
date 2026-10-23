#!/usr/bin/env python3
"""Mutate a wordlist for password spraying and guessing.

Applies common mutations to each base word: case changes, year suffixes,
leet speak, and prefix/suffix symbols. Outputs one candidate per line.

Usage:
    wordlist-mutator.py words.txt
    wordlist-mutator.py --word admin --leet --years
"""

import argparse
import itertools
import sys

LEET = str.maketrans({"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7"})


def mutations(word, args):
    seen = set()
    cands = [word]
    if args.case:
        cands += [word.lower(), word.upper(), word.capitalize(),
                  word[0].upper() + word[1:].lower() if len(word) > 1 else word.upper()]
    results = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            results.append(c)
    if args.leet:
        leeted = [c.translate(LEET) for c in list(results)]
        for c in leeted:
            if c not in seen:
                seen.add(c)
                results.append(c)
    final = []
    for c in results:
        variants = [c]
        if args.years:
            variants += [c + y for y in ("2023", "2024", "2025", "2026", "123")]
        if args.symbols:
            variants += [c + s for s in ("!", "@", "#", "1", "12")]
            variants = [s + c for s in ("!",)] + variants
        if args.numbers:
            variants += [c + str(n) for n in range(10)]
        for v in variants:
            if v not in seen:
                seen.add(v)
                final.append(v)
    return results + final


def read_words(path, single):
    if single:
        return [single]
    words = []
    src = open(path, "r", encoding="utf-8", errors="replace") if path else sys.stdin
    with src:
        for line in src:
            w = line.strip()
            if w and not w.startswith("#"):
                words.append(w)
    return words


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mutate wordlist entries: case, leet speak, years, symbols, numbers. "
                    "Use only against systems you are allowed to test.",
        epilog="Examples:\n"
               "  wordlist-mutator.py words.txt\n"
               "  wordlist-mutator.py --word admin --leet --years --symbols\n"
               "  cat words.txt | wordlist-mutator.py --case --numbers | sort -u",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="?", default=None,
                        help="wordlist file (default: stdin)")
    parser.add_argument("--word", default=None, help="mutate a single word")
    parser.add_argument("--case", action="store_true", help="case variants")
    parser.add_argument("--leet", action="store_true", help="leet-speak variants")
    parser.add_argument("--years", action="store_true", help="append year-like suffixes")
    parser.add_argument("--symbols", action="store_true", help="append/prepend symbols")
    parser.add_argument("--numbers", action="store_true", help="append digits 0-9")
    parser.add_argument("--all", action="store_true", help="enable every mutation")
    args = parser.parse_args(argv)

    if args.all:
        args.case = args.leet = args.years = args.symbols = args.numbers = True
    if not any([args.case, args.leet, args.years, args.symbols, args.numbers]):
        parser.error("enable at least one mutation (--case, --leet, --years, --symbols, --numbers, --all)")

    if args.word is None and args.file is None and sys.stdin.isatty():
        parser.error("give a file, --word, or pipe words on stdin")

    try:
        words = read_words(args.file, args.word)
    except OSError as exc:
        print("Error: cannot read %r: %s" % (args.file, exc), file=sys.stderr)
        return 1
    if not words:
        parser.error("no words to mutate")

    count = 0
    for word in words:
        for mutant in mutations(word, args):
            print(mutant)
            count += 1
    print("Generated %d candidates from %d words" % (count, len(words)),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
