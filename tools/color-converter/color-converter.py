#!/usr/bin/env python3
"""Convert colors between HEX, RGB, and HSL.

Accepts a hex color like #ff8800 or ff8800, or rgb()/hsl() notation, and
prints all three forms plus a terminal color preview.

Usage:
    color-converter.py "#ff8800"
    color-converter.py "rgb(255, 136, 0)"
    color-converter.py "hsl(32, 100%, 50%)"
"""

import argparse
import colorsys
import re
import sys


def parse_color(text):
    text = text.strip()
    m = re.match(r"^#?([0-9a-fA-F]{6})$", text)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r"^#?([0-9a-fA-F]{3})$", text)
    if m:
        return tuple(int(c * 2, 16) for c in m.group(1))
    m = re.match(r"^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$", text, re.I)
    if m:
        rgb = tuple(int(x) for x in m.groups())
        if all(0 <= x <= 255 for x in rgb):
            return rgb
        raise ValueError("RGB values must be 0-255")
    m = re.match(r"^hsl\(\s*(\d{1,3})\s*,\s*(\d{1,3})%\s*,\s*(\d{1,3})%\s*\)$", text, re.I)
    if m:
        h, s, l = (int(x) for x in m.groups())
        if not (0 <= h <= 360 and 0 <= s <= 100 and 0 <= l <= 100):
            raise ValueError("HSL out of range (h: 0-360, s/l: 0-100%)")
        r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
        return (round(r * 255), round(g * 255), round(b * 255))
    raise ValueError("unrecognized color format: %r" % text)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert a color between HEX, RGB, and HSL.",
        epilog="Examples:\n"
               "  color-converter.py \"#ff8800\"\n"
               "  color-converter.py \"rgb(255, 136, 0)\"\n"
               "  color-converter.py \"hsl(32, 100%, 50%)\"",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("color", help="color as #rrggbb, rgb(...), or hsl(...)")
    parser.add_argument("--no-preview", action="store_true",
                        help="skip the terminal color preview block")
    args = parser.parse_args(argv)

    try:
        r, g, b = parse_color(args.color)
    except ValueError as exc:
        parser.error(str(exc))

    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    print("HEX: #%02x%02x%02x" % (r, g, b))
    print("RGB: rgb(%d, %d, %d)" % (r, g, b))
    print("HSL: hsl(%d, %d%%, %d%%)" % (round(h * 360), round(s * 100), round(l * 100)))
    if not args.no_preview:
        print("Preview: \x1b[48;2;%d;%d;%dm      \x1b[0m" % (r, g, b))
    return 0


if __name__ == "__main__":
    sys.exit(main())
