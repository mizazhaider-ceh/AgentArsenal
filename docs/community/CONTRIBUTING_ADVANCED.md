# Advanced Contributor Guide

This guide is for contributors who already read `CONTRIBUTING.md` and
want to write skills that score well, fit the knowledge graph, and pass
every quality gate. The basics (frontmatter template, validator rules)
are in `CONTRIBUTING.md`; this page goes deeper.

## How the pieces fit

- **Skills** (`skills/<domain>/<skill>/SKILL.md`) are the core unit:
  a technique or workflow an agent loads on demand.
- **Sub-skills** (`skills/<domain>/<skill>/sub/<sub>/SKILL.md`) drill
  into one parent skill. They share the global name namespace, so no
  two skills or sub-skills may share a name.
- **Agents** (`agents/`) bundle skills and brains into a persona with a
  role, escalation path, and constraints.
- **Brains** (`brains/`) are reusable reasoning modules agents load.
- **Decisions** (`decisions/`) are escalation and decision policies.
- **Playbooks** (`playbooks/`) sequence agents, skills, and decisions
  in phase tables for end-to-end operations.
- **Workflows** (`workflows/`) describe repeatable multi-step patterns.

`scripts/validate.py` checks every file against `SPEC.md` in CI. It also
checks the manifest (`arsenal-manifest.json` hashes), the install.sh
platform list, and rejects em dashes in markdown. Run it before every
pull request:

```bash
python3 scripts/validate.py
```

## Writing a skill that scores well

`scripts/score.py` grades each skill 0-100 (gate: 70) on depth,
freshness, trigger quality, tooling, and edge-case coverage. The
benchmarks in `BENCHMARKS.md` measure the same shape statically. The
practical recipe:

1. **Description first.** It is the discovery surface. Write 2-4
   sentences that name the tools, the techniques, and the exact
   situations ("Use when ..."). Benchmark scenario S3 looks for at
   least 3 distinct trigger phrases: mix routing language ("use when",
   "when the") with technique language ("covers", "including",
   "such as", "for example", "walkthrough").
2. **Pin real tool versions.** Every `tools:` entry needs a name and a
   version you have actually used. `scripts/freshness_check.py` flags
   pins older than 12 months relative to `last_verified`, so re-check
   versions when you touch a skill.
3. **Teach by example.** At least one fenced command block per major
   section, with the exact command and what to look for in the output.
   Benchmark scenario S2 requires this; reviewers expect it.
4. **Name the tool in the body.** Benchmark scenario S1 checks that the
   first pinned tool is mentioned in the body text. If the workflow
   uses the tool, this happens naturally.
5. **Write real edge cases.** The required `## Edge cases` section must
   hold situations you have actually hit: WAF behavior, false
   positives, ordering problems, tool quirks. Generic filler ("check
   permissions") scores badly and helps nobody.
6. **Reference real sources.** The required `## Key references` section
   should cite MITRE ATT&CK technique IDs, CWE numbers, OWASP guides,
   or vendor docs you opened while writing.

## Graph hygiene: requires, extends, relates, parent

- `requires`: hard dependency. The agent should load this skill first.
  Keep the list short; every edge is checked for cycles.
- `extends`: soft specialization. "This skill is a deeper cut of
  that one." Also cycle-checked.
- `relates`: loose association for discovery. Not cycle-checked.
- `parent` (sub-skills only): the enclosing top-level skill. Checked
  for cycles but never counts as `requires`.

Rules of thumb: prefer `relates` over `requires` unless the workflow
truly breaks without the other skill. Never create a dependency both
ways. When adding a new skill, grep the repo for the technique first;
a `relates` link to the nearest existing skill is usually better than
a new top-level skill that overlaps.

## Lifecycle transitions

Every skill carries `lifecycle: experimental`, `stable`, or
`deprecated`.

- Start new skills as `experimental`. They can still be excellent; the
  label just says "recently added, limited field feedback."
- Promote to `stable` after the content has been reviewed against a
  real target or lab and the tool pins are current. Update
  `last_verified` to the review date at the same time.
- Mark `deprecated` when the technique or tool is dead (vendor EOL,
  removed feature). Keep the file: deprecated skills are history, not
  trash. Point `extends` or the body at the replacement.

## Scoring, benchmarks, freshness: the quality loop

1. `python3 scripts/score.py` writes `scores.json`. Gate is 70.
2. `python3 scripts/benchmark.py` writes `BENCHMARKS.md` with
   per-domain static pass rates. Fix S3 (descriptions) first; it is
   the cheapest win.
3. `python3 scripts/freshness_check.py` flags stale tool pins. See
   `docs/quality/FRESHNESS.md` for the weekly schedule.

Run all three before a pull request that touches skills. They are
stdlib-only and finish in seconds.

## Advanced: sub-skills, decisions, playbooks

- **Sub-skills** decompose a parent that grew too large. Aim for 3-6
  sub-skills per parent, each covering one phase (e.g. detection,
  exploitation, evasion). The parent keeps the overview and links down.
- **Decisions** files are referenced by agents (`escalation:`) and
  playbooks (`decisions:` bindings). Write them as checklists with
  clear escalation triggers, not essays.
- **Playbooks** bind everything in a phase table with columns for the
  owner agent, skills used, brains used, and decision gates. Every
  binding must resolve to a real artifact, or CI fails.

## Review checklist for pull requests

- [ ] `python3 scripts/validate.py` passes.
- [ ] New skill: name matches directory, description 80-1500 chars with
      a "use when" trigger, semver version, real tool pins.
- [ ] `requires`/`extends`/`relates` point at existing skills; no
      cycles; no duplicate names.
- [ ] Body has `## Quick Workflow`, `## Edge cases`,
      `## Key references` with exact headings.
- [ ] At least one fenced command block per major section.
- [ ] `last_verified` is the date of a real review, not the PR date.
- [ ] No em dashes anywhere in markdown (CI rejects U+2014).
- [ ] If you added artifacts, regenerate the manifest and scores with
      the repo's derive scripts so hashes match.

## Good first skill ideas

Each idea below was checked against the current skill list: none of
them exist yet. They are scoped small enough for a first contribution
and useful enough to keep.

1. **mcp-security**: auditing Model Context Protocol servers for tool
   poisoning, prompt injection through tool descriptions, and
   over-permissioned MCP tool scopes.
2. **saml-attacks**: SAML response forgery, signature wrapping, and
   Golden SAML, with IdP/SP misconfiguration checks using real
   metadata files.
3. **rfid-nfc-cloning**: cloning low-frequency badges and testing
   NFC access tokens with Proxmark3, plus cloning countermeasures.
4. **voip-sip-security**: SIP enumeration, extension brute-forcing,
   RTP eavesdropping, and PBX toll-fraud checks on authorized
   engagements.
5. **nuclei-template-development**: writing and testing custom Nuclei
   templates, matcher logic, and safe template QA before scanning.
6. **web-fuzzing-ffuf**: directory, vhost, and parameter fuzzing with
   ffuf: wordlist choice, recursion control, and filtering noise.
7. **macos-forensics**: unified logs, Spotlight metadata, TCC
   databases, and keychain artifacts in incident response.
8. **zigbee-zwave-security**: sniffing and replaying smart-home radio
   traffic, key extraction pitfalls, and pairing weaknesses.
9. **sbom-supply-chain**: generating and auditing CycloneDX/SPDX
   SBOMs, spotting vulnerable components before they ship.
10. **red-team-infrastructure**: redirectors, domain fronting
    alternatives, and short-lived C2 profiles that keep test traffic
    separate from the team server.
11. **pci-dss-scoping**: scoping cardholder data environments,
    segmentation testing, and evidence collection for assessors.
12. **sim-swap-defense**: detecting SIM-swap attack paths in account
    recovery flows and hardening telecom-facing verification.
13. **browser-extension-security**: auditing extension permissions,
    content-script injection risks, and malicious update channels.
14. **dns-over-https-tunneling**: detecting and testing DoH-based
    exfiltration and C2 in networks that allow encrypted DNS.
15. **kubernetes-admission-security**: auditing admission controllers
    and validating policies: what gets blocked, what slips through,
    and how misconfigured webhooks become an attack path.
