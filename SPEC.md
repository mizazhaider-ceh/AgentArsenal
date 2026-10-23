# AgentArsenal Build Spec (single source of truth for all workers)

## Frontmatter standard (every SKILL.md, CI enforced)

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

Rules:
- `name` MUST equal the skill directory name, lowercase slug with hyphens.
- `version` is semver (X.Y.Z).
- `lifecycle` is one of: experimental, stable, deprecated.
- `last_verified` is YYYY-MM-DD, a real calendar date.
- `requires`, `extends`, `relates` list other skill NAMES (must exist in the repo, no cycles in requires+extends).
- `tools` entries each have name and version (use real, well-known versions; never invent a precise version you are unsure of, use "7.x" style only if truly unsure, prefer exact).
- No em dashes anywhere in any file. Ever. Use commas, colons, or parentheses.

## Frontmatter standard: sub-skills (wave 3)

A sub-skill lives at `skills/<domain>/<skill>/sub/<sub-name>/SKILL.md`. It
follows the skill standard above exactly, with one extra required field:

```yaml
parent: web-sqli   # must name the enclosing top-level skill
```

Rules:
- `name` MUST equal the sub-skill directory name (lowercase slug).
- `parent` must name a real top-level skill (not another sub-skill) and must
  equal the enclosing skill directory name.
- The parent edge is checked for dependency cycles but does NOT count as
  `requires` (it is composition, not a dependency).
- Sub-skill names share one global namespace with top-level skills: no two
  artifacts may use the same name.

## Frontmatter standard: agents (wave 3)

Each agent lives at `agents/<name>/AGENT.md`:

```yaml
---
name: agent-slug            # must match the directory name
kind: agent
description: Trigger-dense paragraph. States exactly when to load this agent ("Use when ..."). 80 to 1500 chars.
version: 1.0.0
role: One-line string naming the job this agent performs.
skills:                    # list of real skill names (top-level or sub-skill)
  - nmap-methodology
brains:                    # list of real brain names
  - attacker-mindset
memory_mode: stateless      # one of: stateless, persistent
escalation: decisions/ESCALATION_POLICY.md   # repo-relative path, must be a file under decisions/
constraints:               # list of non-empty strings, hard rules the agent never breaks
  - Never scan infrastructure you are not authorized to test.
---
```

Body skeleton: `## Mission`, `## Operating loop`, `## Inputs and outputs`,
`## Escalation triggers`, `## Quality bar`.

## Frontmatter standard: brains (wave 3)

Each brain lives at `brains/<name>/BRAIN.md`:

```yaml
---
name: brain-slug           # must match the directory name
kind: brain
description: Trigger-dense paragraph. States exactly when to load this brain ("Use when ..."). 80 to 1500 chars.
version: 1.0.0
provides:                  # list of non-empty strings, the frameworks/heuristics it gives
  - STRIDE threat-modeling checklist
used_by: []                # optional list of agent names, may be empty
---
```

Body skeleton: `## Mental models`, `## Heuristics`, `## Anti-patterns`,
`## Worked example`.

## Frontmatter standard: playbooks (wave 3)

Each playbook lives at `playbooks/<name>/PLAYBOOK.md`:

```yaml
---
name: playbook-slug        # must match the directory name
kind: playbook
description: Trigger-dense paragraph. States exactly when to run this playbook ("Use when ..."). 80 to 1500 chars.
version: 1.0.0
---
```

Bindings (agents, skills, brains, decisions files the playbook uses) may be
listed in frontmatter as a `bindings` list of `kind:target` entries
(`agent:`, `skill:`, `brain:`, `decisions:`), or in the body as a phase
table with `owner agent`, `skills used`, `brains used`, and `decision gates`
columns. At least one binding must be listed, and every binding must
resolve: agents to `agents/<name>/AGENT.md`, skills to a real skill or
sub-skill name, brains to `brains/<name>/BRAIN.md`, decision gates to a file
under `decisions/`.

Body skeleton: `## Objective`, `## Phase table`, `## Detailed phases`,
`## Roles and handoffs`, `## Stop conditions`, `## Artifacts produced`.

## Workflows (wave 3)

Each workflow is one markdown file directly under `workflows/`:
`workflows/<pattern-name>.md`. No frontmatter is required (frontmatter with
name/kind/description/version is accepted and ignored by validation). The
body must start with a `# Title` line and contain at least one phase
section: a `## Phase` or `### Phase` heading, or a `## Step sequence`
section describing the ordered stages.

## Memory and decisions (wave 3)

- `memory/`: the agent memory system. `MEMORY_SCHEMA.md` (episodic, semantic,
  procedural schemas), `LIFECYCLE.md` (capture, consolidate, recall, forget),
  `HYGIENE.md` (dedup, redaction, TTLs, audit). Implemented by
  `tools/memory-store/`.
- `decisions/`: standing decision documents every agent and playbook can
  bind: `ESCALATION_POLICY.md` (SEV-1 to SEV-4 tiers and response times),
  `RISK_MATRIX.md` (likelihood x impact scoring with a worked example),
  `GO_NO_GO_GATES.md` (authorization, safety, capability, detection posture,
  exit readiness), `ADR_TEMPLATE.md` (template plus a filled example),
  `COST_BENEFIT.md` (cost/benefit framework with a worked example).
  Individual ADRs live at `decisions/adr-<nnnn>-<slug>.md`.

## Domains added in wave 3

ai-security, hardware, ics-scada, blockchain, automotive, privacy, memory

(28 domains total: the 21 from waves 1-2 plus these 7.)

## Wave 3 artifact kinds

Wave 3 adds seven artifact kinds on top of skills and tools:

| Kind | Location | Key file |
| --- | --- | --- |
| Sub-skill | `skills/<domain>/<skill>/sub/<sub>/` | `SKILL.md` (+`parent` field) |
| Agent | `agents/<name>/` | `AGENT.md` |
| Brain | `brains/<name>/` | `BRAIN.md` |
| Memory | `memory/` | `MEMORY_SCHEMA.md`, `LIFECYCLE.md`, `HYGIENE.md` |
| Decisions | `decisions/` | `ESCALATION_POLICY.md`, `RISK_MATRIX.md`, `GO_NO_GO_GATES.md`, `ADR_TEMPLATE.md`, `COST_BENEFIT.md` |
| Playbook | `playbooks/<name>/` | `PLAYBOOK.md` |
| Workflow | `workflows/` | `<pattern>.md` |

`scripts/derive_manifest.py` emits new top-level keys `sub_skills`,
`agents`, `brains`, `playbooks`, `workflows`; the `skills` key keeps its
exact wave-2 shape. `scripts/score.py` scores agents and brains 0-100
(gate 70) and writes `scores.json` as
`{"skills": {...}, "agents": {...}, "brains": {...}}`.
`scripts/generate_docs.py` builds per-agent, per-brain, and per-playbook
pages, an agents index section, sub-skill trees on parent skill pages, and
agent to skill to brain edges in the dependency graph.

## Body skeleton (every SKILL.md)

1. One framing paragraph (what this skill covers, scope).
2. `## Quick Workflow`: numbered operator steps, concrete and ordered.
3. Per-phase sections with exact commands in fenced code blocks (bash).
4. `## Edge cases`: what goes wrong, how to detect it, workarounds.
5. `## Escalation`: what to try when the standard path fails (where relevant; may merge into Edge cases for engineering skills).
6. `## Detection and defender view`: how a defender sees this (offensive skills) or how to detect misuse/misconfig (engineering skills).
7. `## Key references`: MITRE ATT&CK technique IDs (offensive), CWE IDs (where relevant), OWASP refs, official tool docs. Real IDs only.

## Domains (wave 1)

recon, network, web, auth, privesc, ad, c2, engineering, incident, forensics, linux, api, cloud, crypto, bugbounty

## Domains added in wave 2

mobile, binary, malware, soc, osint, defensive

## Wave 1 skills (24, all original content)

Offensive (12): recon-passive, recon-active, nmap-methodology, web-sqli, web-xss, auth-attacks, password-attacks, privesc-linux, privesc-windows, ad-enumeration, network-pivoting, c2-fundamentals.
Engineering (12): code-reviewer, incident-response, python-cli-tooling, git-workflows, linux-hardening, api-security-testing, cloud-security-basics, webapp-pentest-methodology, crypto-fundamentals, forensics-fundamentals, bug-bounty-workflow, secure-coding.

Domain assignment:
- recon: recon-passive, recon-active
- network: nmap-methodology, network-pivoting
- web: web-sqli, web-xss, webapp-pentest-methodology
- auth: auth-attacks, password-attacks
- privesc: privesc-linux, privesc-windows
- ad: ad-enumeration
- c2: c2-fundamentals
- engineering: code-reviewer, python-cli-tooling, git-workflows, secure-coding
- incident: incident-response
- forensics: forensics-fundamentals
- linux: linux-hardening
- api: api-security-testing
- cloud: cloud-security-basics
- crypto: crypto-fundamentals
- bugbounty: bug-bounty-workflow

## Suggested dependency edges (writers may adjust, validator enforces existence and acyclicity)

- recon-active requires: [recon-passive]
- nmap-methodology relates: [recon-active]
- web-sqli relates: [web-xss, api-security-testing]
- web-xss relates: [web-sqli]
- auth-attacks relates: [password-attacks]
- password-attacks relates: [auth-attacks]
- privesc-linux relates: [privesc-windows, linux-hardening]
- privesc-windows relates: [privesc-linux]
- ad-enumeration requires: [recon-active]
- network-pivoting requires: [recon-active]
- c2-fundamentals requires: [network-pivoting]
- webapp-pentest-methodology requires: [recon-active, web-sqli, web-xss, auth-attacks]
- api-security-testing relates: [web-sqli, web-xss, auth-attacks]
- bug-bounty-workflow requires: [recon-passive, webapp-pentest-methodology]
- incident-response relates: [forensics-fundamentals]
- forensics-fundamentals relates: [incident-response]
- linux-hardening relates: [privesc-linux]
- secure-coding relates: [code-reviewer, web-sqli, web-xss]
- code-reviewer relates: [secure-coding]
- crypto-fundamentals relates: [web-sqli]
- cloud-security-basics relates: [recon-passive]
- python-cli-tooling relates: []
- git-workflows relates: []

## Global rules for all workers

- Do NOT run git. The coordinator commits.
- No em dashes in any file, filename, or output. Check your work with grep.
- Simple, direct English.
- All skill content 100 percent original. Learn from the source repos, never copy passages.
- Authorized security work only. No real victim infrastructure, no destructive defaults without warnings.
- Python scripts: stdlib only, no pip dependencies.
