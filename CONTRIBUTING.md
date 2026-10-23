# Contributing

## The skill template

Every SKILL.md starts with this frontmatter (validated by `scripts/validate.py` in CI):

```yaml
---
name: skill-slug
description: Trigger-dense paragraph. States exactly when to load this skill ("Use when ..."). Names tools, techniques, scenarios. 80 to 1500 chars.
version: 1.0.0
domain: domain-slug
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: []
tools:
  - name: nmap
    version: 7.98
---
```

Rules: `name` must equal the skill directory name (lowercase slug with hyphens). `version` is semver. `lifecycle` is one of: experimental, stable, deprecated. `last_verified` is a real YYYY-MM-DD date. `requires`, `extends`, `relates` list skill names that exist in the repo; `requires` plus `extends` must form no cycles. Every `tools` entry has a name and a real, well-known version.

The body follows this skeleton:

1. One framing paragraph (what the skill covers, scope).
2. `## Quick Workflow`: numbered operator steps, concrete and ordered.
3. Per-phase sections with exact commands in fenced bash code blocks.
4. `## Edge cases`: what goes wrong, how to detect it, workarounds.
5. `## Escalation`: what to try when the standard path fails (may merge into Edge cases for engineering skills).
6. `## Detection and defender view`: how a defender sees this (offensive skills), or how to detect misuse/misconfiguration (engineering skills).
7. `## Key references`: MITRE ATT&CK technique IDs (offensive), CWE IDs (where relevant), OWASP references, official tool docs. Real IDs only.

## One-skill-one-surface

Each skill covers exactly one topic. If your draft needs two "Quick Workflow" sections, it is two skills. Split it.

## Quality bar

A skill merges only when it passes both gates:

1. `python3 scripts/validate.py` exits 0 (frontmatter, naming, dependencies, dates, banned patterns).
2. `python3 scripts/score.py` gives the skill 70 or higher out of 100.

Write to beat the bar, not to scrape past it: dense triggers, real runnable commands, documented edge cases, honest defender view, correct references.

## How to propose a skill

```bash
python3 scripts/new_skill.py <skill-slug> --domain <domain-slug>
```

This scaffolds `skills/<domain>/<skill-slug>/SKILL.md` with the template above. Fill it in, run the validator and scorer, fix what they flag, then open a PR.

## Changelog requirement

Every PR that adds or changes a skill must add an entry under `[Unreleased]` in CHANGELOG.md. No changelog entry, no merge.
