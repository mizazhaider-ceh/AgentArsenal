#!/usr/bin/env python3
"""Encode and decode Morse code.

Letters are separated by spaces, words by " / ". Supports A-Z, 0-9, and a
few punctuation marks.

Usage:
    morse-codec.py encode "SOS"
    morse-codec.py decode "... --- ..."
"""

import argparse
import sys

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.",
    "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-",
    "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-",
    "+": ".-.-.", "-": "-....-", "_": "..--.-", '"': ".-..-.",
    "$": "...-..-", "@": ".--.-.",
}
REVERSE = {code: letter for letter, code in MORSE.items()}


def encode(text):
    parts = []
    for word in text.upper().split():
        letters = []
        for ch in word:
            if ch not in MORSE:
                raise ValueError("cannot encode character: %r" % ch)
            letters.append(MORSE[ch])
        parts.append(" ".join(letters))
    return " / ".join(parts)


def decode(text):
    words = []
    for word in text.strip().split(" / "):
        letters = []
        for code in word.split():
            if code not in REVERSE:
                raise ValueError("unknown morse code: %r" % code)
            letters.append(REVERSE[code])
        words.append("".join(letters))
    return " ".join(words)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Encode text to Morse code or decode Morse code to text.",
        epilog="Examples:\n"
               "  morse-codec.py encode \"HELLO WORLD\"\n"
               "  morse-codec.py decode \".... . .-.. .-.. ---\"\n"
               "  echo SOS | morse-codec.py encode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=["encode", "decode"],
                        help="encode text to morse, or decode morse to text")
    parser.add_argument("data", nargs="?", default=None,
                        help="input (default: read from stdin)")
    args = parser.parse_args(argv)

    if args.data is None:
        if sys.stdin.isatty():
            parser.error("provide input as an argument or pipe it on stdin")
        raw = sys.stdin.read().strip()
    else:
        raw = args.data.strip()
    if not raw:
        parser.error("empty input")

    try:
        print(encode(raw) if args.mode == "encode" else decode(raw))
    except ValueError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
