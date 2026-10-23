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
