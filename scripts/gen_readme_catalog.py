#!/usr/bin/env python3
"""Regenerate the skill-count badge and skill catalog table in README.md.

Reads arsenal-manifest.json, then rewrites the README sections between
<!-- SKILLCOUNT:START --> / <!-- SKILLCOUNT:END --> (shields.io badge with
the live skill count) and <!-- CATALOG:START --> / <!-- CATALOG:END -->
(markdown table grouped by domain, plus a total row).

Idempotent: running it twice produces identical output.
Stdlib only.
"""

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "arsenal-manifest.json"
README = REPO_ROOT / "README.md"

SKILLCOUNT_START = "<!-- SKILLCOUNT:START -->"
SKILLCOUNT_END = "<!-- SKILLCOUNT:END -->"
CATALOG_START = "<!-- CATALOG:START -->"
CATALOG_END = "<!-- CATALOG:END -->"


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as fh:
        data = json.load(fh)
    skills = data.get("skills", [])
    if not skills:
        raise SystemExit("error: arsenal-manifest.json contains no skills")
    return skills


def badge_block(count):
    return (
        SKILLCOUNT_START
        + "\n"
        + f"![skills](https://img.shields.io/badge/skills-{count}-blue)"
        + "\n"
        + SKILLCOUNT_END
    )


def catalog_block(skills):
    by_domain = OrderedDict()
    for skill in sorted(skills, key=lambda s: (s["domain"], s["name"])):
        by_domain.setdefault(skill["domain"], []).append(skill["name"])

    lines = [CATALOG_START]
    lines.append("| Domain | Skills |")
    lines.append("| --- | --- |")
    for domain, names in by_domain.items():
        lines.append(f"| {domain} | {', '.join(names)} |")
    lines.append(f"| **Total** | **{len(skills)} skills across {len(by_domain)} domains** |")
    lines.append(CATALOG_END)
    return "\n".join(lines)


def replace_section(text, start, end, replacement):
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.DOTALL
    )
    new_text, n = pattern.subn(replacement, text)
    if n != 1:
        raise SystemExit(
            f"error: expected exactly one {start} ... {end} block, found {n}"
        )
    return new_text


def main():
    skills = load_manifest()
    count = len(skills)

    text = README.read_text(encoding="utf-8")
    text = replace_section(text, SKILLCOUNT_START, SKILLCOUNT_END, badge_block(count))
    text = replace_section(text, CATALOG_START, CATALOG_END, catalog_block(skills))
    README.write_text(text, encoding="utf-8")

    if "\u2014" in text:
        print("warning: README contains an em dash", file=sys.stderr)

    print(f"README updated: {count} skills.")


if __name__ == "__main__":
    main()
