---
name: bugbounty-report-writing-impact-statements
parent: bugbounty-report-writing
description: Use when you have a working proof of concept on an in-scope target and need to write the impact section that justifies your severity. Covers translating technical bugs into concrete attacker gains (whose data, which privilege, what action), the impact ladder from informational to critical with examples per bug class, avoiding hype and theoretical impact, and matching the impact claim to the program's bounty table. Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-report-writing]
extends: []
relates: [bugbounty-report-writing-proof-of-concept-format, bugbounty-report-writing-cvss-scoring, bug-bounty-workflow]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

Impact is the sentence that decides your severity. Triagers do not pay for bug classes; they pay for what an attacker concretely gains: whose data, which privilege, what action. This sub-skill teaches the translation from technical finding to impact statement, the impact ladder with per-class examples, and how to keep claims honest and matched to the bounty table. Write impact only for vulnerabilities found inside program scope.

## Quick Workflow

1. State the primitive: what the bug lets you do in one clause (read, write, execute, escalate).
2. Name the victim and the asset: which user's data, which role's privilege, which system.
3. Remove prerequisites honestly: does it need user interaction, a second bug, or special conditions.
4. Place it on the impact ladder to sanity-check your severity.
5. Write the impact paragraph: primitive plus victim plus scale, in two to three sentences.
6. Cross-check against the program's bounty table before submitting.

## 1. The translation method

Every impact statement follows one shape: attacker action plus victim plus asset plus scale.

- Weak: "IDOR vulnerability in the invoice endpoint."
- Strong: "Any authenticated user can read any other user's invoices, including names, addresses, and amounts, by changing the invoice ID. I confirmed this with two test accounts."

The strong version names the primitive (read), the victim (any other user), the asset (invoices with PII), and the proof (two test accounts). Write yours the same way, then delete any adjective that is not doing work ("critical," "severe," "dangerous" add nothing; the facts set the severity).

## 2. The impact ladder with examples

Use the ladder to check your severity claim before the triager does:

- Informational: version disclosure, verbose errors with no sensitive data. Impact: helps an attacker fingerprint, nothing more.
- Low: reflected XSS requiring heavy user interaction, verbose errors leaking internal paths, missing security headers alone. Impact: limited, conditional, or preparatory.
- Medium: stored XSS in a low-traffic area, IDOR exposing non-sensitive data, CSRF on low-value actions, user enumeration. Impact: real but bounded, or needing significant interaction.
- High: stored XSS in an admin panel, IDOR exposing PII or financial data, authentication bypass on accounts, SSRF reaching internal services, SQLi with data extraction. Impact: direct compromise of users, data, or privilege.
- Critical: remote code execution, full authentication bypass at scale, SSRF to cloud metadata leading to infrastructure keys, mass account takeover (password reset flaw affecting all users). Impact: system-level or population-level compromise.

Per-class examples:

- XSS: reflected with one click (low to medium); stored firing for every admin (high); stored in a signup field firing for all users (critical).
- IDOR: reading your own data with another ID (not a finding); reading another user's non-sensitive preferences (low to medium); reading PII or financial records (high); modifying or deleting another user's data (high).
- SSRF: callback to your collaborator only (low, unproven); reading cloud metadata (high to critical depending on what the credentials unlock).
- Business logic: a coupon reusable twice (low to medium); price set to zero at checkout (high); mass creation of paid resources for free (high).

## 3. Honesty rules

- Claim only what you demonstrated. "Could lead to RCE" without the shell is not RCE impact; it is the impact of the step you proved, plus a clearly labeled next step.
- State prerequisites plainly: "requires the victim to click a link while logged in" or "requires an admin to view the ticket queue." Hidden prerequisites discovered by the triager read as exaggeration.
- Do not stack hypothetical chains: one demonstrated link is a chain; three imagined links are fiction. Programs pay for the demonstrated part.
- Match the bounty table: if the program pays medium for user enumeration, do not argue it is high. Learn their appetite and aim your hunting where it pays.

## Edge cases

- The impact is real but the program's table underpays the class: report it anyway with honest severity. Reputation compounds; one underpaid report is cheap tuition.
- Two impacts from one bug (XSS that also leaks CSRF tokens): state the primary impact and note the secondary in one sentence. Do not double-claim severity.
- The impact depends on data you must not touch (real user PII): prove with your own test accounts' data and describe the rest by field names, not contents. Never exfiltrate real user data to prove a point.
- The program asks "what is the worst case": give the realistic worst case you can defend, labeled as such, separate from the demonstrated impact.

## Escalation

- Triager downgrades severity: cite the demonstrated impact and the bounty table once, factually, then accept the call. One calm pushback is professional; two is arguing.
- You discover a bigger impact after submitting: update the report with new evidence before triage closes. Upgrades with proof are welcome.
- Impact is unclear because the data classification is unknown: describe the fields exposed and let the program classify. "Exposes full names, emails, and order histories" is enough.

## Detection and defender view

- Impact statements tell defenders what to prioritize: a precise impact paragraph routes the fix to the right team faster than a severity label alone.
- Honest impact trains correct risk models; inflated impact trains alert fatigue. The defender's backlog is real and your honesty shapes it.
- The ladder in section 2 doubles as a defender triage rubric: map incoming reports to it before assigning.
- Fix the class the impact reveals: an IDOR exposing PII means an authorization review, not a single endpoint patch.

## Key references

- CVSS v3.1 specification: https://www.first.org/cvss/
- HackerOne severity guidance: https://docs.hackerone.com
- Bugcrowd vulnerability rating taxonomy: https://docs.bugcrowd.com
- CWE database: https://cwe.mitre.org/
- OWASP Risk Rating Methodology: https://owasp.org/www-community/OWASP_Risk_Rating_Methodology
