---
name: bugbounty-report-writing-cvss-scoring
parent: bugbounty-report-writing
description: Use when a program asks for CVSS with your report and you need a defensible score for an in-scope finding. Covers the CVSS v3.1 base metrics one by one with web bug examples (attack vector, complexity, privileges, user interaction, scope, confidentiality, integrity, availability), common mis-scorings hunters make, when to include temporal and environmental metrics, and how to present the vector string alongside your severity justification. Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-report-writing]
extends: []
relates: [bugbounty-report-writing-impact-statements, bugbounty-report-writing-proof-of-concept-format, bug-bounty-workflow]
tools:
  - name: Python
    version: 3.12
---

CVSS is the shared language for severity when a program asks for it. A correct vector string with one sentence per metric choice defends your severity better than any adjective. This sub-skill walks the CVSS v3.1 base metrics with web bug examples, flags the mis-scorings hunters make most, and shows how to present the score in a report. Score only vulnerabilities found inside program scope.

## Quick Workflow

1. Confirm the program actually wants CVSS; if it uses its own table, the table wins.
2. Score the base metrics from the demonstrated impact, not the theoretical worst case.
3. Write one sentence of justification per metric you set.
4. Compute the score with the official calculator and record the vector string.
5. Sanity-check the number against the impact ladder; if they disagree, re-examine the metrics.
6. Present the vector string plus your severity justification in the report.
7. Add temporal or environmental metrics only when they change the decision.

## 1. Base metrics with web examples

Attack Vector (AV): Network for anything reachable over the internet, which is nearly every web bug. Adjacent only for LAN-reachable services, Physical almost never in bounty.

Attack Complexity (AC): Low if the attack works reliably with no special conditions. High if it needs a race window, a specific configuration, or improbable timing. A race condition you win 3 of 10 runs is High.

Privileges Required (PR): None for unauthenticated bugs. Low for any authenticated user. High for admin-only bugs. An IDOR any logged-in user can hit is PR:Low.

User Interaction (UI): None for stored XSS that fires on page view without clicks, or CSRF that needs none beyond visiting. Required for reflected XSS needing a click, or any flow where the victim must act.

Scope (S): Unchanged when the compromise stays in the vulnerable component. Changed when the bug in one component compromises another security authority: stored XSS in a support app that steals admin sessions for the whole platform is S:Changed.

Confidentiality, Integrity, Availability (C/I/A): set each to None, Low, or High based on demonstrated effect. Reading another user's full PII is C:High. Defacing your own profile is I:Low. A single request crashing a worker is A:Low; taking the site down is A:High.

Example vectors:

```
Stored XSS in admin ticket queue:
CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:N  -> 9.0 Critical
(Admin must view the queue: UI:R. Session theft crosses into the
admin component: S:C. Full admin session compromise: C:H/I:H.)

IDOR reading other users' invoices:
CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N  -> 6.5 Medium
(Any authenticated user, no interaction, confidentiality of PII only.)
```

## 2. Common hunter mis-scorings

- Setting Scope:Changed for every XSS. Scope changes only when a different security authority falls, not whenever the impact feels big.
- PR:None on bugs requiring login. If you logged in to exploit it, privileges were required.
- UI:None on reflected XSS. The victim clicking the link is user interaction.
- C:H/I:H/A:H "just in case." Score what you demonstrated; the calculator punishes honest inputs less than triagers punish inflated ones.
- Forgetting that CVSS measures the vulnerability, not the report quality. A perfect PoC does not raise the score.

## 3. Temporal and environmental metrics

Most bounty reports need base metrics only. Add temporal metrics (Exploit Code Maturity, Remediation Level, Report Confidence) when the program's process uses them, e.g. Report Confidence:Confirmed once the vendor reproduces. Add environmental metrics (modified base metrics for the program's actual deployment) when you know the deployment well enough, e.g. a staging-only bug gets lower environmental confidentiality requirements. When in doubt, ship the base vector and say so.

## 4. Presenting the score

In the report, one block:

```
CVSS: 9.0 (Critical)
Vector: CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:N
Justification: Network-reachable (AV:N), reliable (AC:L), any
authenticated user (PR:L), admin must view the queue (UI:R), compromise
crosses into the admin security authority (S:C), full session and data
compromise demonstrated (C:H/I:H), no availability effect (A:N).
```

Then tie it to the program's table: "Maps to High per the program bounty table." If the program's table disagrees with the CVSS number, the table wins and you note the mapping.

## Edge cases

- The program uses CVSS v4.0: the metric names differ (no more Scope, new Supplemental metrics). Say which version you scored and use its calculator.
- The bug is a chain: score the chain's combined impact as one vector, and note the per-link vectors in an appendix line. Do not average them.
- Impact is data-dependent (PII versus non-sensitive): score for the most sensitive data you demonstrated access to, and state that assumption.
- The calculator gives a number that feels wrong: trust the metrics, not the feeling, then re-read the metric definitions. The feeling is usually Scope or UI mis-set.

## Escalation

- Triager disputes the vector: walk the metrics one by one with your justifications. Metric-level debate resolves; number-level debate does not.
- Program has no severity framework at all: give the vector plus your plain-language impact paragraph and let them map it. Do not invent a mapping for them.

## Detection and defender view

- CVSS vectors let defenders prioritize across reports from many hunters consistently; insist on vector strings, not bare numbers.
- Ingest the vector into your vuln management: the per-metric breakdown tells you which control failed (PR:L everywhere means an authz review; UI:R patterns mean output encoding gaps).
- Environmental metrics are the defender's tool: re-score with your deployment's actual confidentiality and integrity requirements to prioritize fixes.
- Track which metrics hunters mis-set most; it shows where your triage guidance needs examples.

## Key references

- CVSS v3.1 specification: https://www.first.org/cvss/
- CVSS v3.1 calculator: https://www.first.org/cvss/calculator/3.1
- CVSS v3.1 user guide: https://www.first.org/cvss/user-guide
- NVD CVSS guidance: https://nvd.nist.gov/vuln-metrics/cvss
- HackerOne severity guidance: https://docs.hackerone.com
