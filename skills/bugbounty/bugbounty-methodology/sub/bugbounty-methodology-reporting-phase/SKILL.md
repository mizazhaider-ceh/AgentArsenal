---
name: bugbounty-methodology-reporting-phase
parent: bugbounty-methodology
description: Use when a finding is validated on an in-scope bug bounty target and needs to become a payout-ready report. Covers the triage-before-writing checklist (clean-session reproduction, impact confirmation, duplicate search), the report structure triagers reward (specific title, justified severity, numbered reproduction steps with raw HTTP, concrete impact, remediation), evidence habits (screenshots and video as support, never as substitute), one-vulnerability-per-report discipline, and polite retest etiquette after fixes. Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-methodology]
extends: []
relates: [bug-bounty-workflow, bugbounty-report-writing, bugbounty-duplicate-avoidance, bugbounty-methodology-exploitation-phase]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

A validated finding earns nothing until a tired triager understands it at midnight. The reporting phase converts exploitation output into reports that get triaged fast and paid fairly: triage before writing, one vulnerability per report, exact reproduction steps, concrete impact, and polite retests. This sub-skill covers only the reporting phase of bugbounty-methodology. Report only vulnerabilities found on targets the program lists in scope.

## Quick Workflow

1. Triage the candidate: reproduce from a clean session with fresh accounts before writing anything.
2. Confirm the impact is real and concrete (whose data, which privilege, what an attacker gains).
3. Search for duplicates: disclosed reports, your own notes, the program's known-issues list.
4. Write one report per vulnerability with the structure in section 2.
5. Attach evidence: screenshots or short video of the key step, supporting the written steps, never replacing them.
6. Submit, then track: answer triager questions promptly and precisely.
7. After a fix is marked, retest the exact steps plus close variants, politely and once.
8. Confirm the fix or demonstrate the bypass with the same quality as the original report, then move on.

## 1. Triage before writing

Never write a report from a single observation. The triage checklist:

- Reproduce from a clean browser profile and fresh test accounts. Session confusion is the most common false positive in access control testing.
- Confirm the impact with the least privilege that demonstrates it. Reading one other user's invoice proves IDOR; dumping the table does not add value and looks hostile.
- Check it is in scope: the exact host, and the exact test type, must both be allowed by the policy.
- Search duplicates first (see bugbounty-duplicate-avoidance): the program's disclosed reports, HackerOne Hacktivity or Bugcrowd disclosures for that program, and your own submission history.
- Severity sanity check: does the impact match the bounty table, or are you inflating it. Overstated severity slows triage and costs credibility.

If any check fails, the finding goes back to validation or gets dropped. A dropped false positive costs nothing; a submitted one costs reputation.

## 2. Report structure that gets paid

Write for a tired triager at midnight: short sentences, exact steps, no hype.

1. Title: specific and searchable. "Stored XSS in support ticket subject executes in admin panel" beats "XSS vulnerability found."
2. Severity: justified against the bounty table with one sentence of reasoning. Cite CVSS only if the program uses it.
3. Summary: two sentences on what is broken and why it matters.
4. Reproduction steps: numbered, starting from a clean state, with exact requests. Include raw HTTP requests, not just screenshots:

```http
POST /api/v1/tickets HTTP/1.1
Host: support.target.com
Authorization: Bearer <attacker-token>
Content-Type: application/json

{"subject": "<svg onload=alert(document.domain)>", "body": "help"}
```

5. Impact: what an attacker gains, concretely. "I read another user's invoices including names and amounts" beats "IDOR vulnerability."
6. Remediation: one paragraph on the fix (server-side authorization check on the object, output encoding at render, parameterized query).
7. Attachments: screenshots or video of the key step. Screenshots support the written steps; they never replace them.

One vulnerability per report. Bundling distinct bugs into one report costs you money and confuses remediation. Chained issues that only matter together are one report; independent issues are separate reports.

## 3. Evidence habits

Collect evidence during exploitation, not after:

- Save the raw request and response for the proving step (Burp: save item, or copy as curl).
- Screenshot the moment of impact: the other user's data rendered, the alert firing in the victim session, the admin action completed as a low-privilege user.
- For stored XSS or multi-step flows, a short screen recording is worth ten screenshots. Narrate nothing; let the steps speak.
- Redact other users' real data if you touched any. Blur names, emails, and amounts that are not yours.
- Keep a per-finding evidence folder: `findings/2026-10-23-idor-invoices/` with request.txt, response.txt, screenshots, and notes.md.

## 4. Retest etiquette

After the program marks a report fixed, retest promptly and politely:

- Run the exact reproduction steps first, then close variants (encoding bypasses, neighboring IDs, the same flaw on a sibling endpoint).
- Confirm the fix with the same evidence quality as the original, or demonstrate the bypass just as clearly.
- Thank the triager and close the loop. Do not keep hammering a fixed endpoint to find new ways in; that is a new hunt, not a retest.
- If the fix is incomplete, say exactly which variant still works and stop there. One clear bypass note beats five angry comments.

## Edge cases

- The triager asks for clarification: answer within a day, precisely, with the exact step they asked about. Do not resend the whole report.
- Severity is set lower than you claimed: stay factual, cite the policy and bounty table once, and accept the final call gracefully. Arguing burns the relationship that brings the next invite.
- The report is marked duplicate: note the pattern, hunt its siblings on other endpoints, and check the disclosure timeline so your next similar find lands first.
- The program goes quiet past its SLA: one polite follow-up, then move on. Never threaten disclosure to speed triage.
- You realize after submitting that the finding is weaker than claimed: update the report honestly before triage finishes. Corrections build trust; discovered exaggerations destroy it.

## Escalation

- A report is rejected as intended behavior: ask for the reasoning, learn the program's risk appetite, and adjust what you submit there next time. Different programs pay for different things.
- Repeated rejections on one program: rotate to a different program rather than grinding. Your methodology transfers; the program's appetite does not.
- A fix bypass turns into a new variant class: after confirming the bypass, sweep the sibling endpoints once, then report the pattern to the program as a follow-up note on the original report.

## Detection and defender view

- Good reports teach the defender: the remediation paragraph and the attack class turn one report into a codebase-wide fix. Write remediation for the developer who will implement it.
- Evidence with raw HTTP requests lets defenders replay the issue in staging without guessing, which shortens fix time.
- Honest severity helps defenders prioritize correctly; inflated severity trains them to discount your future reports.
- Polite retests confirm the fix actually landed, which is a defensive win, not just a payout step.

## Key references

- HackerOne report writing guidance: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- OWASP Testing Guide reporting section: https://owasp.org/www-project-web-security-testing-guide/
- CVSS v3.1 specification: https://www.first.org/cvss/
- CWE-639 Authorization Bypass Through User-Controlled Key: https://cwe.mitre.org/data/definitions/639.html
