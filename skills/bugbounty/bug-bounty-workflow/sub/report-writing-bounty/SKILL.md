---
name: report-writing-bounty
description: Use when writing a bug bounty report that gets triaged fast
  and paid well. Covers report structure, proof-of-concept quality,
  impact statements, and severity self-assessment. Use when submitting a
  finding, when the PoC needs to be reproducible, when the impact needs
  selling honestly, or when a report was rejected and needs rewriting.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
parent: bug-bounty-workflow
requires: [bug-bounty-workflow]
extends: []
relates: [web-sqli, web-xss]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
---

The bounty report is the product: a great find with a bad report pays
like a bad find. This skill covers writing reports that triage quickly:
clear titles, reproducible PoCs, honest impact, and the right severity.
Triagers process hundreds of reports; yours must make the vulnerability
obvious in the first thirty seconds.

## Quick Workflow

1. Reproduce the finding from scratch in a clean session.
2. Write the title: vulnerability plus location, no hype.
3. Document reproduction steps that work copy-paste.
4. Show the impact with the minimal proof.
5. State the severity with reasoning, not just a label.
6. Suggest the fix briefly (one paragraph).
7. Submit and track; respond to triager questions fast.

## 1. Structure that triages fast

```bash
cat > /tmp/bounty_report_template.txt <<'EOF'
Title: <Vuln type> in <endpoint/parameter> allows <impact>
       e.g. "Stored XSS in support ticket subject executes in admin panel"

Severity: <your assessment + one-line reasoning>

Summary: <3 sentences: what, where, worst case>

Steps to reproduce:
1. <exact step, with the request or click>
2. <exact step>
3. <observed result>

Proof of concept:
<the exact request, curl command, or payload; copy-paste ready>

Impact: <what an attacker gains, concretely, with the proof>

Remediation: <the fix in one paragraph>

Notes: <test account used, scope confirmation, cleanup done>
EOF
```

The steps to reproduce are the report's core: a triager who cannot
reproduce in five minutes will deprioritize or close the report. Test
your own steps in a fresh browser and a fresh account before
submitting; your muscle memory hides missing steps.

## 2. PoC quality

```bash
# PoC quality bar:
# - Copy-paste ready: the exact curl, the exact payload, the exact clicks
# - Minimal: the shortest proof that shows the vulnerability
# - Safe: no real user data, no destructive actions, test accounts only
# - Complete: includes auth (which test account), the request, the response

# Example: IDOR PoC
# 1. Log in as testuser_a (provided test account)
# 2. GET /api/orders/1001 -> 200 with A's data (baseline)
# 3. Log in as testuser_b
# 4. GET /api/orders/1001 with B's token -> 200 with A's data (vulnerability)
# 5. Screenshot: B's session showing A's order details

# Video PoCs: for complex chains only; keep under 2 minutes, narrate the steps
```

Screenshots prove state; requests prove reproducibility. Include both
for visual findings (XSS rendering, UI issues) and lean on requests
for logic flaws. Redact nothing the triager needs; redact everything
else.

## 3. Impact and severity honesty

```bash
# Impact formula: capability + reach, stated plainly
# WEAK: "This is critical because XSS is dangerous"
# STRONG: "Any authenticated user can store this payload; it executes for
# every admin viewing tickets, allowing session theft and admin takeover.
# Shown: admin session cookie readable in console (screenshot)."

# Severity self-assessment:
# - Map to the program's severity guide explicitly
# - State assumptions ("assumes admin reviews tickets daily")
# - Do not inflate: triagers punish inflation with slower handling
# - Do not undersell chained impact: show the chain, each link proven
```

Honest impact with proof earns trust; inflated impact with hand-waving
earns skepticism that follows you to the next report. When the impact
needs a chain, prove every link in the PoC section.

## Edge cases

- The triager cannot reproduce. Respond within 24 hours with a
  clarified PoC or a video; most "cannot reproduce" is a missing step.
- The finding is a duplicate. Accept it gracefully; check
  duplicate-avoidance before the next submission, not after.
- The severity is downgraded. Argue once, with evidence, politely;
  then accept the decision and move on.
- The program goes silent. Follow up once after their stated SLA;
  then let it be.

## Escalation

- A critical finding needs immediate attention: use the program's
  priority channel if they have one; otherwise submit normally and
  note the urgency factually.
- The report was rejected unfairly: rewrite with tighter PoC and
  resubmit only if the policy allows; otherwise take the lesson.
- You need the report template improved: iterate it from triager
  feedback, not from theory.

## Detection and defender view

From the program's side, good reports are the cheapest security
investment: they convert external researcher time into fixed
vulnerabilities. Programs detect report quality problems by triage
time and reopen rates. The defender's action on a good report is the
fix plus the regression test; the report's remediation paragraph
should make that trivial.

## Key references

- Program-specific severity guides (read before submitting).
- OWASP Testing Guide (methodology backing for the PoC).
- CVSS calculator (for severity reasoning, where the program uses it).
