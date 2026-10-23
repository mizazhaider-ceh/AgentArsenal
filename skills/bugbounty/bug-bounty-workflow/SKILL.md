---
name: bug-bounty-workflow
description: Use when hunting on a bug bounty program and you need a repeatable, professional methodology from scope to payout. Covers scope discipline and rules of engagement, a repeatable recon pipeline (subdomain enumeration with amass, port scanning with nmap, content discovery, JavaScript analysis), application mapping, methodology per bug class (IDOR and broken access control, XSS, SQLi, SSRF, authentication flaws, file upload, business logic, API issues), nuclei-assisted checks, report writing that gets paid (clear impact, reproduction steps, severity justification), duplicate avoidance, and polite retest etiquette. Requires recon-passive and webapp-pentest-methodology. Authorized targets only, strictly inside program scope.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-passive, webapp-pentest-methodology]
extends: []
relates: []
tools:
  - name: nmap
    version: 7.98
  - name: amass
    version: 4.2.0
  - name: nuclei
    version: 3.x
  - name: burp
    version: 2024.x
---

Bug bounty hunting rewards methodology, not luck. Programs pay for real, in-scope vulnerabilities with clear impact and reproducible reports, and they ban hunters who scan out of scope or submit noise. This skill gives you the full workflow: scope discipline, a repeatable recon pipeline, per-bug-class methodology, report writing that gets paid, and retest etiquette that keeps you in good standing. It builds on recon-passive for open-source intelligence and webapp-pentest-methodology for the core testing techniques. Only test targets the program explicitly authorizes.

## Quick Workflow

1. Read the program policy end to end: scope, out-of-scope assets, forbidden test types, safe harbor terms, bounty table.
2. Define your target list strictly from the stated scope. When in doubt, ask the program before testing.
3. Run passive recon first (no packets to the target), then active recon in increasing intensity.
4. Map the application: every endpoint, parameter, role, and state-changing action, in Burp.
5. Work each bug class methodically: access control, auth, injection, SSRF, file handling, business logic, APIs.
6. Validate impact and check for duplicates before writing anything.
7. Write the report: title, severity, reproduction steps, impact, remediation.
8. Retest politely after the fix, confirm, and move on. Never re-exploit aggressively.

## Phase 1: Scope discipline and rules of engagement

Scope is the contract. Read it before any tool runs:

- In-scope: exact domains, wildcards, IP ranges, mobile apps, APIs. Note what "wildcard" really covers (often only subdomains of the named domain, not acquired properties).
- Out-of-scope: commonly staging, third-party services, and anything the program names explicitly. Out-of-scope means do not touch, not "test quietly."
- Forbidden: usually DoS, social engineering, physical attacks, and automated scanners at high intensity. Rate-limit everything.
- Safe harbor: confirms good-faith research inside the policy is authorized. Staying inside the policy is what makes it apply to you.

Keep a scope file per program and re-read it when the program updates (they do, often). If you find a vulnerability in an asset you are unsure about, report it as a question to the program, not as a finding, and do not probe further until they confirm.

## Phase 2: Recon pipeline

Recon finds the attack surface. Go passive first, then active, then deep.

Passive (no direct contact with the target):

```bash
amass enum -passive -d target.com -o amass-passive.txt
```

Combine with certificate transparency logs, DNS datasets, and the techniques in recon-passive. Deduplicate and resolve:

```bash
sort -u amass-passive.txt -o subs.txt
```

Active enumeration, paced and polite:

```bash
nmap -sV --top-ports 1000 -iL live-hosts.txt -oA nmap-top1000
```

Content discovery on web hosts:

```bash
ffuf -u https://target.com/FUZZ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -o ffuf.json
```

JavaScript analysis: collect every JS file the application loads, then grep for API endpoints, keys, and hidden parameters. Endpoints in JS are endpoints in scope.

Takeover checks on dangling DNS (CNAMEs pointing at unclaimed services) are high-value and low-noise. Screenshot and document everything; recon output becomes the appendix of your reports.

## Phase 3: Application mapping

Proxy everything through Burp and use the application like a thorough user first. Build the site map, then annotate:

- Every endpoint with its parameters, noting which are IDs, which are actions, and which change state.
- Every user role: register two accounts and compare what each can see and do. Access control bugs live in the differences.
- Every state-changing request: note the CSRF protection, or its absence.
- API documentation: Swagger, OpenAPI, GraphQL introspection, and mobile app traffic, which often expose more than the web UI.

Nuclei assists with known-vulnerability and misconfiguration checks across the mapped surface:

```bash
nuclei -l urls.txt -t ~/nuclei-templates/http/misconfiguration/ -o nuclei-misconfig.txt
```

Treat scanner output as leads. Every nuclei hit gets manual validation before it becomes a report; scanners are wrong often enough that unvalidated submissions burn your reputation.

## Phase 4: Methodology per bug class

Work each class across the whole mapped surface before moving to the next. Depth per class beats shallow coverage of everything.

Access control and IDOR: for every object reference (user IDs, order IDs, document UUIDs), swap in another user's ID and a sequential neighbor. Test both direct references and indirect ones (search filters, export functions, API parameters). Check function-level access too: can a low-privilege role hit admin endpoints directly.

Authentication: test registration, login, password reset, and session handling. Reset tokens must be random, single-use, and expiring. Test for user enumeration via response differences, missing rate limits, and OAuth misconfigurations (redirect URI validation, state parameter).

Injection: XSS first in every reflected and stored input, then template injection, then SQLi where inputs reach queries. For stored XSS, verify it fires in another user's session. See web-sqli for the SQL injection methodology this skill relates to.

SSRF: every place the server fetches a URL (webhooks, avatars, PDF generators, importers) gets internal addresses, cloud metadata endpoints, and DNS rebinding payloads. Confirm with a collaborator or request-bin interaction, then show what internal data is reachable.

File upload: test extension, MIME type, and magic byte validation independently. A file that uploads is not a finding; execution or sensitive disclosure from the uploaded file is.

Business logic: price manipulation, quantity tampering, workflow skipping (do steps out of order), race conditions on limited resources, and coupon or credit abuse. These pay well because scanners cannot find them.

APIs: test mass assignment (extra JSON fields), excessive data exposure (fields the UI never shows), missing object-level authorization on every endpoint, and versioned or shadow endpoints (v1, internal, debug).

## Phase 5: Report writing that gets paid

Triage before writing: reproduce from a clean session, confirm the impact is real, and search the program's disclosed reports and your own notes for duplicates. A duplicate is not a payout; check first.

Report structure that triagers love:

1. Title: specific and searchable ("Stored XSS in support ticket subject executes as admin").
2. Severity: justified against the bounty table, not inflated. Overstated severity slows triage.
3. Summary: two sentences on what is broken and why it matters.
4. Reproduction steps: numbered, starting from a clean state, with exact requests. Include raw HTTP requests, not just screenshots.
5. Impact: what an attacker gains, concretely (account takeover, data access, privilege escalation). "I could read other users' invoices" beats "IDOR vulnerability."
6. Remediation: one paragraph on the fix (authorization check on the object, output encoding, parameterized query).
7. Attachments: screenshots or video of the key step, never as a substitute for written steps.

Write for a tired triager at midnight: short sentences, exact steps, no hype. One vulnerability per report; bundling distinct bugs into one report costs you money and confuses remediation.

## Phase 6: Retest etiquette and program citizenship

After the program marks a fix, retest promptly and politely:

- Test the exact reproduction steps, plus close variants (bypass attempts are fair game on a retest).
- Confirm the fix or clearly demonstrate the bypass with the same report quality as the original.
- Thank the triager, close the loop, and move on. Do not keep hammering a fixed endpoint.

Program citizenship: stay in scope, respect rate limits, never pivot from an in-scope host to an out-of-scope one, disclose your testing when asked, and keep vulnerability details private until the program discloses. Hunters who behave well get private invites; hunters who do not get banned.

## Edge cases

- The scope is ambiguous: ask the program in writing before testing. A "quick check" outside scope is still outside scope.
- Recon finds nothing new: go deeper on the application instead of wider on the internet. Business logic and access control bugs hide where scanners stop.
- You hit a duplicate: note the pattern and hunt its siblings. One disclosed IDOR often means the same broken pattern on five more endpoints.
- The program goes quiet: one polite follow-up after their stated SLA, then move on. Do not threaten disclosure to speed triage.
- Rate limiting or WAF blocks you: slow down, distribute politely, and never try to evade the WAF aggressively. Evasion attempts look like attacks because they are.
- You accidentally touch out-of-scope: stop immediately, document what happened, and disclose it to the program honestly. Honesty preserves safe harbor; hiding it destroys it.

## Escalation

- Methodology per class is exhausted on one target: rotate to a different asset class in the program (API instead of web, mobile instead of API). Fresh surface, fresh bugs.
- Low-severity findings accumulate: chain them. A low-severity information disclosure plus a weak reset flow can become account takeover; programs pay for chains.
- Stuck on validation: reproduce with a second account and a clean browser profile to rule out session confusion, which is the most common false positive in access control testing.
- Bounty disputes: stay factual, cite the policy and the bounty table, and accept the program's final call gracefully. Arguing burns the relationship that brings the next invite.

## Detection and defender view

- Bug bounty programs are a defensive investment: scope them to the real attack surface, keep the policy current, and triage quickly. Slow triage trains hunters to leave.
- Every bug class in Phase 4 maps to defenses: object-level authorization checks, output encoding, parameterized queries, SSRF allowlists with DNS pinning, strict file validation, and server-side business logic enforcement.
- Monitor your own telemetry for hunter behavior: it is free adversary emulation. Repeated 403s on admin paths, ID enumeration patterns, and collaborator callbacks show you what attackers try first.
- Fix classes, not instances: one IDOR report should trigger an authorization review across the codebase, not a single endpoint patch.

## Key references

- MITRE ATT&CK: T1595.001 (Scanning IP Blocks), T1595.002 (Vulnerability Scanning), T1190 (Exploit Public-Facing Application), T1552.001 (Credentials In Files, for exposed secrets in JS), T1552.005 (Cloud Instance Metadata API, for SSRF impact).
- CWE: CWE-862 (Missing Authorization), CWE-863 (Incorrect Authorization), CWE-639 (Authorization Bypass Through User-Controlled Key), CWE-79 (Cross-site Scripting), CWE-89 (SQL Injection), CWE-918 (Server-Side Request Forgery), CWE-352 (Cross-Site Request Forgery), CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- Standards and docs: OWASP Top 10 (2021), OWASP Testing Guide, OWASP API Security Top 10, nuclei-templates project documentation, amass documentation.
