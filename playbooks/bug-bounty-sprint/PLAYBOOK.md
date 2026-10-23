---
name: bug-bounty-sprint
kind: playbook
description: Use when you need to run a focused, time-boxed bug bounty sprint against a program's scope, from OSINT and target mapping through vulnerability discovery to clean, high-signal reports. Covers passive recon, attack surface mapping, manual testing of web and API targets, and report writing that gets triaged fast. Load this playbook when a bounty program opens or updates scope and you need ordered phases, owners, skills, brains, and decision gates for a productive sprint.
version: 1.0.0
---

# Bug Bounty Sprint Playbook

Authorized work only. Stay inside the program's published scope at all times. Respect the program's rules on rate limits, automated scanning, social engineering, and disclosure. When in doubt, ask the program before testing.

## Objective

Find valid, high-impact vulnerabilities within the sprint window and submit reports that triage quickly and pay out. Success is measured by valid submissions, signal quality (accepted versus duplicate or informative), and coverage of the in-scope attack surface.

## Phase table

| phase | owner agent | skills used | brains used | decision gates | exit criteria |
|-------|-------------|-------------|-------------|----------------|---------------|
| 1. Program intake and scope | bug-bounty-hunter-agent | bug-bounty-workflow, technical-writing | cost-of-attack, incident-command-mindset | GO_NO_GO_GATES | Scope parsed, rules noted, targets prioritized |
| 2. OSINT and target mapping | osint-agent | osint-methodology, domain-osint, social-media-osint, recon-passive | attacker-mindset, assume-breach | GO_NO_GO_GATES | Asset inventory per in-scope domain, tech stack mapped |
| 3. Attack surface enumeration | bug-bounty-hunter-agent | recon-active, webapp-pentest-methodology, api-security-testing | attacker-mindset, hypothesis-driven-testing | ESCALATION_POLICY | Endpoints, parameters, and API operations inventoried |
| 4. Vulnerability discovery | web-exploitation-agent, api-security-agent | web-sqli, web-xss, jwt-attacks, ssrf, xxe, auth-attacks, open-redirect, cache-poisoning, file-upload-attacks | hypothesis-driven-testing, cost-of-attack | RISK_MATRIX | Findings validated with minimal-impact proof |
| 5. Reporting and triage follow-up | bug-bounty-hunter-agent | bug-bounty-workflow, technical-writing | evidence-chain, root-cause-analysis | COST_BENEFIT | Reports submitted, triage questions answered, retests done |

## Detailed phases

### Phase 1. Program intake and scope

Steps:
1. Read the full program policy: in-scope assets, out-of-scope list, forbidden test types, bounty table, and disclosure rules.
2. Check for scope updates and previously disclosed reports to avoid duplicates.
3. Prioritize targets by bounty value, attack surface size, and how fresh the target is.
4. Set the sprint window and the daily target list.

Evidence to collect: scope snapshot with date, rules summary, target priority list, sprint schedule.

### Phase 2. OSINT and target mapping

Steps:
1. Enumerate subdomains, acquisitions, and related domains from public sources, then verify each against the scope before touching it.
2. Map the technology stack per target: frameworks, CDNs, third-party integrations, and API versions.
3. Look for leaked credentials, exposed code, and forgotten staging or development hosts that are in scope.
4. Score each target by likelihood of findings versus time cost, and order the sprint accordingly.

Evidence to collect: subdomain lists with scope verification, stack fingerprints, leak sightings, prioritized target list.

### Phase 3. Attack surface enumeration

Steps:
1. Enumerate live web targets within the program's rate limits: endpoints, parameters, API operations, and file upload points.
2. Document authentication and authorization models per application: roles, tokens, and object references.
3. Note interesting functionality: payments, file handling, integrations, and admin panels.
4. Keep enumeration light and targeted. Heavy scanning gets you banned and finds nothing new.

Commands (where relevant):
```bash
mkdir -p ~/bounty/<program>/enum
# keep request rates inside the program limits; log every scan with timestamps
```

Evidence to collect: endpoint inventories, auth model notes, interesting functionality list, scan logs.

### Phase 4. Vulnerability discovery

Steps:
1. Test by impact first: authentication bypass, IDOR, SSRF, and injection on the highest-value targets.
2. Validate each finding with the smallest proof that demonstrates impact. No data exfiltration, no destructive actions, no pivoting into out-of-scope systems.
3. Check for duplicates against disclosed reports before writing up.
4. Record the full request and response chain for every candidate finding.

Evidence to collect: candidate findings with proof pairs, duplicate check notes, test logs with timestamps.

### Phase 5. Reporting and triage follow-up

Steps:
1. Write the report the way triagers like: clear title, severity, affected asset, step-by-step reproduction, impact statement, and the proof.
2. Include the fix suggestion. It shows you understand the root cause and speeds up triage.
3. Answer triage questions fast and completely. Provide retest confirmation when the program asks.
4. Log the outcome: accepted, duplicate, informative, or not applicable, with the payout and the lesson.

Evidence to collect: submitted reports, triage correspondence, outcome log with payouts, lessons per sprint.

## Decision gates

- **GO_NO_GO_GATES** (decisions/GO_NO_GO_GATES.md): used in Phases 1 and 2. Checks: program policy read and understood, scope verified, rules on automation and disclosure noted. Testing never starts before this passes.
- **ESCALATION_POLICY** (decisions/ESCALATION_POLICY.md): used in Phase 3. Asset that looks in scope but is ambiguous: ask the program first. Finding that affects another customer or tenant: stop and report immediately.
- **RISK_MATRIX** (decisions/RISK_MATRIX.md): used in Phase 4. Every proof of concept is scored for impact before running. Anything beyond minimal demonstration needs program approval.
- **COST_BENEFIT** (decisions/COST_BENEFIT.md): used in Phases 4 and 5. Time is the sprint budget: high-impact, low-effort targets first, and reports written only for findings worth the triage signal.

## Deliverables

1. Scope snapshot and target priority list.
2. OSINT asset inventory with scope verification.
3. Attack surface enumeration per target.
4. Validated findings with proof pairs.
5. Submitted reports with triage outcomes.
6. Sprint outcome log with payouts and lessons.
