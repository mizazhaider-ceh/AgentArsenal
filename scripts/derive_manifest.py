#!/usr/bin/env python3
"""Derive arsenal-manifest.json from skills/<domain>/<skill>/SKILL.md files.

Scans the skills tree, parses each SKILL.md YAML frontmatter with a minimal
hand-written parser (stdlib only), computes a sha256 of each file, and writes
the manifest to the repo root.

Usage:
    scripts/derive_manifest.py            # write/refresh arsenal-manifest.json
    scripts/derive_manifest.py --check     # exit 1 if checked-in manifest drifts
    scripts/derive_manifest.py --json      # also print counters as JSON
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")
MANIFEST_PATH = os.path.join(REPO_ROOT, "arsenal-manifest.json")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_inline_list(value):
    """Parse a value like [a, b, "c d"]. Returns a list of strings."""
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    items = []
    for part in re.split(r",(?=(?:[^'\"]*['\"][^'\"]*['\"])*[^'\"]*$)", inner):
        part = part.strip()
        if len(part) >= 2 and part[0] == part[-1] and part[0] in ("'", '"'):
            part = part[1:-1]
        items.append(part)
    return items


def parse_frontmatter(text):
    """Minimal YAML frontmatter parser.

    Supports: scalar strings (optionally quoted), inline lists [a, b],
    block lists of scalars, and block lists of maps (used for tools:).
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("missing or malformed YAML frontmatter (--- ... ---)")
    raw = match.group(1)
    data = {}
    current_key = None
    current_map = None

    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))

        if indent == 0 and ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            current_map = None
            if value == "":
                current_key = key
                data[key] = []
            elif value.startswith("[") and value.endswith("]"):
                current_key = None
                data[key] = parse_inline_list(value)
            else:
                current_key = None
                data[key] = strip_quotes(value)
        elif line.lstrip().startswith("- ") and current_key and indent >= 2:
            item_text = line.lstrip()[2:].strip()
            if ":" in item_text and not item_text.startswith(("\"", "'")):
                current_map = {}
                k, _, v = item_text.partition(":")
                current_map[k.strip()] = strip_quotes(v.strip())
                data.setdefault(current_key, []).append(current_map)
            else:
                current_map = None
                data.setdefault(current_key, []).append(strip_quotes(item_text))
        elif current_map is not None and ":" in line and indent >= 4:
            k, _, v = line.partition(":")
            current_map[k.strip()] = strip_quotes(v.strip())
        else:
            continue

    return data


def strip_quotes(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def derive():
    skills = []
    if not os.path.isdir(SKILLS_DIR):
        return {"generated_at": now_utc(), "skills": []}

    for domain in sorted(os.listdir(SKILLS_DIR)):
        domain_path = os.path.join(SKILLS_DIR, domain)
        if not os.path.isdir(domain_path):
            continue
        for skill in sorted(os.listdir(domain_path)):
            skill_path = os.path.join(domain_path, skill)
            md_path = os.path.join(skill_path, "SKILL.md")
            if not os.path.isfile(md_path):
                continue
            with open(md_path, "r", encoding="utf-8") as fh:
                text = fh.read()
            try:
                fm = parse_frontmatter(text)
            except ValueError as exc:
                print("error: %s: %s" % (md_path, exc), file=sys.stderr)
                sys.exit(2)
            skills.append({
                "name": fm.get("name", skill),
                "version": fm.get("version", "0.0.0"),
                "domain": fm.get("domain", domain),
                "path": "skills/%s/%s" % (domain, skill),
                "sha256": sha256_of(md_path),
                "lifecycle": fm.get("lifecycle", "experimental"),
                "requires": fm.get("requires", []) or [],
                "extends": fm.get("extends", []) or [],
                "relates": fm.get("relates", []) or [],
            })

    skills.sort(key=lambda s: s["name"])
    return {"generated_at": now_utc(), "skills": skills}


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    parser = argparse.ArgumentParser(description="Derive arsenal-manifest.json")
    parser.add_argument("--check", action="store_true",
                        help="fail with exit 1 if the manifest on disk differs")
    parser.add_argument("--json", action="store_true",
                        help="print counters as JSON on stdout")
    args = parser.parse_args()

    manifest = derive()

    if args.check:
        if not os.path.isfile(MANIFEST_PATH):
            print("check failed: %s does not exist" % MANIFEST_PATH, file=sys.stderr)
            sys.exit(1)
        with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
            on_disk = json.load(fh)
        if on_disk.get("skills") != manifest["skills"]:
            print("check failed: checked-in manifest differs from derived manifest",
                  file=sys.stderr)
            sys.exit(1)
        print("ok: manifest matches derived skills (%d skills)" % len(manifest["skills"]))
        return

    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    print("wrote %s (%d skills)" % (MANIFEST_PATH, len(manifest["skills"])))

    if args.json:
        by_domain = {}
        for skill in manifest["skills"]:
            by_domain[skill["domain"]] = by_domain.get(skill["domain"], 0) + 1
        print(json.dumps({"skills": len(manifest["skills"]), "by_domain": by_domain}))


if __name__ == "__main__":
    main()
