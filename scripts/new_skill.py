#!/usr/bin/env python3
"""Interactive scaffolding CLI for new AgentArsenal skills.

Prompts for a skill name, domain, and description, validates each answer,
creates skills/<domain>/<name>/SKILL.md from the standard template, then
regenerates arsenal-manifest.json via scripts/derive_manifest.py.

Stdlib only. No em dashes anywhere in this file or its output.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

DOMAINS = [
    "recon", "network", "web", "auth", "privesc", "ad", "c2",
    "engineering", "incident", "forensics", "linux", "api",
    "cloud", "crypto", "bugbounty",
    "mobile", "binary", "malware", "soc", "osint", "defensive",
    "ai-security", "hardware", "ics-scada", "blockchain",
    "automotive", "privacy", "memory",
]

SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

TRIGGER_PHRASES = (
    "use when",
    "load when",
    "reach for",
    "when you need",
    "when facing",
    "when to load",
    "use this skill",
)

MIN_DESC = 80
MAX_DESC = 1500

EM_DASH = "\u2014"


def repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return Path(__file__).resolve().parent.parent


def yaml_dquote(value: str) -> str:
    """Wrap a single-line string as a YAML double-quoted scalar."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_skill_md(name: str, domain: str, description: str, today: str) -> str:
    desc = yaml_dquote(description)
    return f"""---
name: {name}
description: {desc}
version: 0.1.0
domain: {domain}
lifecycle: experimental
last_verified: {today}
requires: []
extends: []
relates: []
tools:
  # TODO: replace this example entry with the real tools this skill uses.
  # Use exact, well-known versions (never invent a precise version).
  - name: example-tool
    version: 0.0.0
---

# {name}

[TODO: One framing paragraph. Say what this skill covers and where its scope starts and stops.]

## Quick Workflow

1. [TODO: First operator step. Concrete and ordered.]
2. [TODO: Second operator step.]
3. [TODO: Third operator step.]

## Phase 1: [TODO: phase name]

[TODO: Describe what happens in this phase.]

```bash
# TODO: exact commands for this phase
```

## Phase 2: [TODO: phase name]

[TODO: Describe what happens in this phase.]

```bash
# TODO: exact commands for this phase
```

## Phase 3: [TODO: phase name]

[TODO: Describe what happens in this phase.]

```bash
# TODO: exact commands for this phase
```

## Edge cases

[TODO: What goes wrong, how to detect it, and workarounds.]

## Escalation

[TODO: What to try when the standard path fails. For engineering skills this section may merge into Edge cases.]

## Detection and defender view

[TODO: Offensive skill: how a defender sees this activity. Engineering skill: how to detect misuse or misconfiguration.]

## Key references

[TODO: Real IDs only. MITRE ATT&CK technique IDs for offensive skills, CWE IDs where relevant, OWASP references, official tool docs.]
"""


def ask(prompt: str) -> str:
    return input(prompt).strip()


def prompt_name() -> str:
    while True:
        raw = ask("Skill name (lowercase slug, e.g. web-sqli): ")
        if not raw:
            print("Name cannot be empty. Try again.")
            continue
        if EM_DASH in raw:
            print("Em dashes are not allowed. Use hyphens only.")
            continue
        if not SLUG_RE.match(raw):
            print(
                "Invalid slug. Use lowercase letters, digits, and hyphens only. "
                "It must start with a letter, with no leading, trailing, or double hyphens."
            )
            continue
        return raw


def prompt_domain() -> str:
    print("Domains:")
    for i, d in enumerate(DOMAINS, 1):
        print(f"  {i:2d}. {d}")
    while True:
        raw = ask("Domain (number or slug): ").lower()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(DOMAINS):
                return DOMAINS[idx]
            print(f"Pick a number between 1 and {len(DOMAINS)}.")
            continue
        if raw in DOMAINS:
            return raw
        print("Unknown domain. Pick a number from the list or type the slug exactly.")


def prompt_description() -> str:
    print(
        f"Description ({MIN_DESC}-{MAX_DESC} chars, trigger-dense: say when to load this skill)."
    )
    print("Type your text, then finish with an empty line:")
    while True:
        lines: list[str] = []
        while True:
            try:
                line = input()
            except EOFError:
                line = ""
            if line == "" and lines:
                break
            if line == "":
                continue
            lines.append(line)
        text = " ".join(" ".join(lines).split())
        if EM_DASH in text:
            print("Em dashes are not allowed. Rewrite with commas, colons, or parentheses.")
            print("Type your text again, finish with an empty line:")
            continue
        n = len(text)
        if n < MIN_DESC:
            print(f"Too short: {n} chars, need at least {MIN_DESC}. Type it again:")
            continue
        if n > MAX_DESC:
            print(f"Too long: {n} chars, max is {MAX_DESC}. Type it again:")
            continue
        lowered = text.lower()
        if not any(p in lowered for p in TRIGGER_PHRASES):
            print(
                "Warning: no trigger phrase found. Descriptions should say when to "
                "load the skill, e.g. start with 'Use when ...'."
            )
            keep = ask("Keep this description anyway? [y/N]: ").lower()
            if keep not in ("y", "yes"):
                print("Type it again, finish with an empty line:")
                continue
        return text


def validate_noninteractive(name: str, domain: str, description: str) -> tuple[str, str, str]:
    if EM_DASH in name or not SLUG_RE.match(name):
        raise ValueError(f"Invalid skill name: {name!r}")
    domain = domain.lower()
    if domain not in DOMAINS:
        raise ValueError(f"Unknown domain: {domain!r}. Valid: {', '.join(DOMAINS)}")
    text = " ".join(description.split())
    if EM_DASH in text:
        raise ValueError("Description contains an em dash, which is not allowed.")
    if not (MIN_DESC <= len(text) <= MAX_DESC):
        raise ValueError(
            f"Description is {len(text)} chars, must be {MIN_DESC}-{MAX_DESC}."
        )
    lowered = text.lower()
    if not any(p in lowered for p in TRIGGER_PHRASES):
        print(
            "Warning: description has no trigger phrase (e.g. 'Use when ...').",
            file=sys.stderr,
        )
    return name, domain, text


def regenerate_manifest(root: Path) -> bool:
    """Run scripts/derive_manifest.py in a subprocess. Returns True on success."""
    script = root / "scripts" / "derive_manifest.py"
    if not script.exists():
        print("Note: scripts/derive_manifest.py not found yet, skipping manifest regeneration.")
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as exc:  # noqa: BLE001 - report and continue
        print(f"Warning: could not run derive_manifest.py: {exc}", file=sys.stderr)
        return False
    if result.returncode != 0:
        print(
            f"Warning: derive_manifest.py exited with code {result.returncode}.",
            file=sys.stderr,
        )
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return False
    print("Regenerated arsenal-manifest.json via scripts/derive_manifest.py.")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new AgentArsenal skill under skills/<domain>/<name>/."
    )
    parser.add_argument("--name", help="Skill slug (non-interactive mode).")
    parser.add_argument("--domain", help="One of the 15 spec domains (non-interactive mode).")
    parser.add_argument("--description", help="Trigger-dense description (non-interactive mode).")
    parser.add_argument("--root", help="Repo root (default: parent of the scripts dir).")
    args = parser.parse_args(argv)

    root = repo_root(args.root)

    if args.name or args.domain or args.description:
        if not (args.name and args.domain and args.description):
            print(
                "Non-interactive mode needs --name, --domain, and --description together.",
                file=sys.stderr,
            )
            return 2
        try:
            name, domain, description = validate_noninteractive(
                args.name, args.domain, args.description
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
    else:
        name = prompt_name()
        domain = prompt_domain()
        description = prompt_description()

    skill_dir = root / "skills" / domain / name
    if skill_dir.exists():
        print(
            f"Error: {skill_dir} already exists. Refusing to overwrite "
            "(idempotent-safe: pick a new name or remove it first).",
            file=sys.stderr,
        )
        return 1

    today = datetime.date.today().isoformat()
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        build_skill_md(name, domain, description, today), encoding="utf-8"
    )
    print(f"\nCreated: skills/{domain}/{name}/SKILL.md")

    manifest_ok = regenerate_manifest(root)

    print("\nNext steps:")
    print("  1. Fill in every [TODO] section in the SKILL.md body")
    print("     (framing, workflow, phases, edge cases, escalation, defender view, references).")
    print("  2. Replace the example tools entry with real tools and exact versions.")
    print("  3. Set requires/extends/relates to real skill names from this repo.")
    print("  4. Rebuild the docs site: python3 scripts/generate_docs.py")
    if not manifest_ok:
        print("  5. Regenerate the manifest once scripts/derive_manifest.py exists:")
        print("     python3 scripts/derive_manifest.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
