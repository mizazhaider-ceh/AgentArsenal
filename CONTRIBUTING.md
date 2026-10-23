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

## The sub-skill template

A sub-skill is a focused drill-down inside a parent skill, at
`skills/<domain>/<skill>/sub/<sub-name>/SKILL.md`. Same template as a skill,
plus one required field:

```yaml
parent: skill-slug   # the enclosing top-level skill; must exist, must not be a sub-skill
```

The `parent` edge is checked for cycles but does not count as `requires`.
Sub-skill names share the global skill namespace: no duplicates anywhere.

## The agent template

Every `agents/<name>/AGENT.md` starts with this frontmatter:

```yaml
---
name: agent-slug
kind: agent
description: Trigger-dense paragraph ("Use when ..."). 80 to 1500 chars.
version: 1.0.0
role: One-line string naming the job this agent performs.
skills:
  - nmap-methodology
brains:
  - attacker-mindset
memory_mode: stateless
escalation: decisions/ESCALATION_POLICY.md
constraints:
  - Never scan infrastructure you are not authorized to test.
---
```

Rules: `name` matches the directory; `kind` is exactly `agent`;
`description` needs a "use when" trigger; `skills` and `brains` name real
artifacts; `memory_mode` is `stateless` or `persistent`; `escalation` is a
repo-relative path to a file under `decisions/`. Body sections: Mission,
Operating loop, Inputs and outputs, Escalation triggers, Quality bar.

## The brain template

Every `brains/<name>/BRAIN.md` starts with this frontmatter:

```yaml
---
name: brain-slug
kind: brain
description: Trigger-dense paragraph. 80 to 1500 chars.
version: 1.0.0
provides:
  - STRIDE threat-modeling checklist
used_by: []
---
```

Rules: `name` matches the directory; `kind` is exactly `brain`; `provides`
lists at least one framework or heuristic; `used_by` is optional and may be
empty. Body sections: Mental models, Heuristics, Anti-patterns, Worked
example.

## The playbook template

Every `playbooks/<name>/PLAYBOOK.md` starts with this frontmatter:

```yaml
---
name: playbook-slug
kind: playbook
description: Trigger-dense paragraph ("Use when ..."). 80 to 1500 chars.
version: 1.0.0
---
```

Bindings (the agents, skills, brains, and decisions files the playbook
uses) go either in a frontmatter `bindings` list (`agent:`, `skill:`,
`brain:`, `decisions:` entries) or in a phase table with `owner agent`,
`skills used`, `brains used`, and `decision gates` columns. Every binding
must resolve, or CI fails. Body sections: Objective, Phase table, Detailed
phases, Roles and handoffs, Stop conditions, Artifacts produced.

## The workflow template

Each workflow is `workflows/<pattern>.md`: a `# Title` first line and at
least one phase section (`## Phase` heading or `## Step sequence` with
ordered stages, entry and exit criteria each).

## Quality gates

An artifact merges only when it passes its gates:

1. `python3 scripts/validate.py` exits 0 (frontmatter, naming, bindings,
   dates, dependency acyclicity, no em dashes).
2. `python3 scripts/score.py` gives the artifact 70 or higher out of 100
   (skills, agents, and brains are scored; playbooks and workflows are
   validated, not scored).

Write to beat the bar, not to scrape past it: dense triggers, real runnable
commands or procedures, documented edge cases, honest defender view where
relevant, correct references, and bindings that actually resolve.

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

The same two gates apply to agents and brains. Playbooks and workflows
pass gate 1 only. See "Quality gates" above for the per-kind rules.

Write to beat the bar, not to scrape past it: dense triggers, real runnable commands, documented edge cases, honest defender view, correct references.

## How to propose a skill

```bash
python3 scripts/new_skill.py <skill-slug> --domain <domain-slug>
```

This scaffolds `skills/<domain>/<skill-slug>/SKILL.md` with the template above. Fill it in, run the validator and scorer, fix what they flag, then open a PR.

## Changelog requirement

Every PR that adds or changes a skill must add an entry under `[Unreleased]` in CHANGELOG.md. No changelog entry, no merge.
