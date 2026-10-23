#!/usr/bin/env python3
"""Build a table of contents for a Markdown file.

Scans # headings, skips fenced code blocks, and prints a nested list with
GitHub-style anchors. Can also insert or update the TOC in place.

Usage:
    markdown-toc.py README.md
    markdown-toc.py README.md --insert --marker "<!-- TOC -->"
"""

import argparse
import re
import sys

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text).strip("-")


def extract_toc(path):
    toc = []
    in_fence = False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise ValueError("cannot read %r: %s" % (path, exc))
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            toc.append((level, title, slugify(title)))
    return toc, lines


def render(toc, min_level=1, max_level=6):
    out = []
    for level, title, anchor in toc:
        if not min_level <= level <= max_level:
            continue
        indent = "  " * (level - min_level)
        out.append("%s- [%s](#%s)" % (indent, title, anchor))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a table of contents from Markdown headings.",
        epilog="Examples:\n"
               "  markdown-toc.py README.md\n"
               "  markdown-toc.py README.md --min 2 --max 3\n"
               "  markdown-toc.py README.md --insert",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="Markdown file to scan")
    parser.add_argument("--min", type=int, default=1, help="minimum heading level (default: 1)")
    parser.add_argument("--max", type=int, default=6, help="maximum heading level (default: 6)")
    parser.add_argument("--insert", action="store_true",
                        help="insert the TOC after the first heading, replacing an old TOC block")
    args = parser.parse_args(argv)

    if not 1 <= args.min <= 6 and not 1 <= args.max <= 6:
        parser.error("--min and --max must be 1-6")

    try:
        toc, lines = extract_toc(args.file)
    except ValueError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1

    if not toc:
        print("No headings found in %s" % args.file)
        return 0

    rendered = render(toc, args.min, args.max)

    if args.insert:
        start = end = None
        for i, line in enumerate(lines):
            if line.strip() == "<!-- TOC -->":
                start = i
            if line.strip() == "<!-- /TOC -->" and start is not None:
                end = i
                break
        block = ["<!-- TOC -->"] + rendered + ["<!-- /TOC -->"]
        if start is not None and end is not None:
            lines[start:end + 1] = block
        else:
            insert_at = next((i + 1 for i, l in enumerate(lines) if HEADING_RE.match(l)), 0)
            lines[insert_at:insert_at] = [""] + block + [""]
        try:
            with open(args.file, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        except OSError as exc:
            print("Error: cannot write %r: %s" % (args.file, exc), file=sys.stderr)
            return 1
        print("TOC written to %s (%d entries)" % (args.file, len(rendered)))
    else:
        print("\n".join(rendered))
    return 0


if __name__ == "__main__":
    sys.exit(main())
