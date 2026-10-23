---
name: bugbounty-report-writing
description: Use when a validated in-scope finding needs to become a report that gets triaged fast and paid fairly. Covers the full report standard triagers reward (specific title, justified severity, two-sentence summary, numbered reproduction steps with raw HTTP requests, concrete impact, remediation paragraph), one-vulnerability-per-report discipline, evidence collection habits during testing, writing for a tired triager, handling triager questions, and polite retest etiquette. Authorized targets only, report only vulnerabilities found inside program scope.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [bug-bounty-workflow, bugbounty-methodology, bugbounty-methodology-reporting-phase, bugbounty-report-writing-impact-statements, bugbounty-report-writing-proof-of-concept-format, bugbounty-report-writing-cvss-scoring]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

Reports are the product. Programs pay for clear, reproducible, honestly-severed reports on real in-scope vulnerabilities, and they remember hunters who waste triage time. This skill is the complete reporting standard: what to include, how to structure it, how to write impact that justifies the severity, how to present proof of concept, and how to behave through triage and retest. Report only vulnerabilities found on targets the program lists in scope.

## Quick Workflow

1. Triage the finding first: clean-session reproduction, real impact confirmed, duplicate search done.
2. Write a specific, searchable title naming the bug class, location, and effect.
3. State severity with one sentence of justification tied to the program's bounty table.
4. Summarize in two sentences: what is broken, why it matters.
5. Give numbered reproduction steps from a clean state, with exact raw HTTP requests.
6. State the impact concretely: what an attacker gains, whose data, which privilege.
7. Add a one-paragraph remediation aimed at the developer who will fix it.
8. Attach evidence (screenshots, short video) supporting the written steps, never replacing them.
9. Submit one vulnerability per report, track it, answer questions fast, retest fixes politely.

## 1. The report template

Use this structure for every report. Triagers scan for these headings:

```
TITLE: Stored XSS in support ticket subject executes in admin panel

SEVERITY: High. Stored script executes in the session of any admin
viewing the ticket queue, enabling admin session theft.

SUMMARY:
The support ticket subject field stores unsanitized HTML and renders it
in the admin ticket queue. Any admin viewing the queue executes attacker
JavaScript in their session.

REPRODUCTION:
1. Log in as attacker@example.com / <password>.
2. POST /api/v1/tickets with subject: <svg onload=alert(document.domain)>
   (full request below).
3. Log in as admin in a separate browser profile.
4. Open Admin > Ticket queue. The alert fires.

RAW REQUEST:
POST /api/v1/tickets HTTP/1.1
Host: support.example.com
...

IMPACT:
An attacker who submits a ticket can execute JavaScript in any admin
session that views the queue, stealing admin session tokens and taking
over the admin panel, including user PII visible there.

REMEDIATION:
Encode ticket subject output in the admin queue template (context-aware
output encoding), and validate the subject server-side against an
allowlist of safe characters on submission.
```

## 2. Titles and summaries

The title is searchable: future duplicate checks and your own records depend on it. Formula: bug class + location + effect. "Stored XSS in support ticket subject executes in admin panel." Not "XSS vulnerability" and not "Critical security issue in your app."

The summary is two sentences: what is broken, why it matters. If the triager reads only the title and summary, they should know whether to keep reading. Write it last, after the reproduction steps are solid.

## 3. Reproduction steps

Numbered, from a clean state, with exact values:

- State the starting point: which account, which browser profile, which URL.
- Include the raw HTTP request for the proving step, with real headers and body. Screenshots of requests are not a substitute; triagers copy text, not images.
- Note any prerequisites: "requires two accounts," "requires the admin to view the queue," "fires within 60 seconds."
- End with the observable proof: what you saw that demonstrates the impact (the other user's data, the alert in the victim session).

Test your own steps once more before submitting, following them literally as written. If you cannot follow them cold, neither can the triager.

## 4. Impact and remediation

Impact answers: what does an attacker gain, concretely. Name the data, the privilege, the action. "Read any user's invoices including names and amounts" beats "IDOR vulnerability." See bugbounty-report-writing-impact-statements for the full method.

Remediation is one paragraph for the developer: the fix class, where to apply it, and what to verify. "Add a server-side ownership check on invoice_id against the session user in the invoice controller, and audit the other /api/v1/* endpoints for the same pattern." Avoid prescribing exact code unless you are sure; describe the control.

## 5. Evidence and attachments

Collect during testing, not after: raw request and response for the proving step, a screenshot of the moment of impact, and a short screen recording for multi-step or stored flows. Redact other users' real data. Keep a per-finding folder: `findings/2026-10-23-idor-invoices/` with request.txt, response.txt, screenshots, notes.md. See bugbounty-report-writing-proof-of-concept-format for the evidence standard.

## 6. Triage behavior and retests

Answer triager questions within a day, precisely, about the exact step they asked. If severity comes back lower than claimed, cite the policy once, stay factual, and accept the call. After a fix is marked, retest the exact steps plus close variants promptly and politely, confirm or demonstrate the bypass with equal quality, thank the triager, and move on.

## Edge cases

- The finding needs chaining to matter: document each link's evidence separately, then the chain, as one report. Programs pay for demonstrated chains.
- The impact depends on user interaction (phishing an admin): say so plainly and price the severity accordingly. Do not imply it is worse than it is.
- You realize post-submit the finding is weaker: update the report honestly before triage finishes. Corrections build trust.
- The program marks it duplicate: note the pattern, hunt siblings, and check the disclosure timeline so your next similar find lands first.
- The program goes quiet past SLA: one polite follow-up, then move on. Never threaten disclosure.

## Escalation

- Repeated rejections on one program: rotate programs. Your reporting skill transfers; their risk appetite does not.
- A fix bypass becomes a variant class: confirm the bypass, sweep sibling endpoints once, and report the pattern as a follow-up on the original report.
- A report is rejected as intended behavior: learn that program's appetite and adjust what you submit there. Different programs pay for different things.

## Detection and defender view

- Good reports are defensive assets: the remediation paragraph turns one report into a codebase-wide fix. Write it for the implementing developer.
- Raw HTTP in reports lets defenders replay issues in staging without guessing, which shortens fix time measurably.
- Honest severity trains correct prioritization; inflated severity trains defenders to discount you.
- Polite, fast retests confirm fixes actually landed, which is a defensive win beyond the payout.

## Key references

- HackerOne report guidance: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- CVSS v3.1 specification: https://www.first.org/cvss/
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- CWE database: https://cwe.mitre.org/
- PortSwigger Web Security Academy: https://portswigger.net/web-security
