#!/usr/bin/env python3
"""Quote frontmatter plain scalars that contain ': ' so strict YAML
parsers (like the one in `npx skills`) accept them.

A plain YAML scalar may not contain a colon followed by a space, but
many skill descriptions do (for example "raw Cypher: shortest paths").
This script rewrites any top-level unquoted plain scalar whose folded
value contains ': ' as a single-line double-quoted string, escaping
backslashes and double quotes.

Usage: python3 scripts/fix_frontmatter_quotes.py [--check]

With --check, prints the files that would change and exits 1 if any.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(.*)$")


def needs_quotes(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if stripped[0] in ("'", '"'):
        return False
    if stripped.startswith("[") or stripped.startswith("{"):
        return False
    return bool(re.search(r":(\s|$)", stripped))


def quote(value: str) -> str:
    folded = re.sub(r"\s+", " ", value.strip())
    escaped = folded.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def fix_file(path: Path) -> bool:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return False
    fm_lines = m.group(1).splitlines()
    out: list[str] = []
    changed = False
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        km = KEY_RE.match(line)
        if km and not line.startswith((" ", "\t")):
            key, rest = km.group(1), km.group(2)
            if rest.strip() == "":
                # block value (list or map), keep as-is
                out.append(line)
                i += 1
                continue
            # collect folded continuation lines
            parts = [rest]
            j = i + 1
            while j < len(fm_lines) and fm_lines[j].startswith((" ", "\t")):
                parts.append(fm_lines[j])
                j += 1
            value = "\n".join(parts)
            if j > i + 1 and needs_quotes(value):
                out.append(f"{key}: {quote(value)}")
                changed = True
            elif j == i + 1 and needs_quotes(value):
                out.append(f"{key}: {quote(value)}")
                changed = True
            else:
                out.extend(fm_lines[i:j])
            i = j
        else:
            out.append(line)
            i += 1
    if changed:
        new_text = "---\n" + "\n".join(out) + "\n" + text[m.end():].lstrip("\n")
        # preserve the exact separator style: original had "---\n" after fm
        new_text = "---\n" + "\n".join(out) + "\n---\n" + text[m.end():].lstrip("\n")
        path.write_text(new_text)
    return changed


def main() -> int:
    check = "--check" in sys.argv
    files = sorted(REPO_ROOT.rglob("SKILL.md"))
    changed_files = []
    for path in files:
        if fix_file(path):
            changed_files.append(path.relative_to(REPO_ROOT))
    if check:
        for f in changed_files:
            print(f)
        return 1 if changed_files else 0
    print(f"fixed {len(changed_files)} files")
    for f in changed_files:
        print(" ", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
