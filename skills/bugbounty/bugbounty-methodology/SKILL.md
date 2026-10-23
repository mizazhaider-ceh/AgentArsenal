---
name: bugbounty-methodology
description: Use when hunting on an in-scope bug bounty program and you need a complete, repeatable methodology that takes you from scope reading to payout. Covers the five phases of a professional hunt (scope and rules of engagement, reconnaissance, application mapping, systematic exploitation per bug class, and reporting), per-bug-class testing sequences for IDOR, XSS, SQLi, SSRF, authentication flaws, file uploads, and business logic, evidence collection habits, severity triage, and when to stop and move on. Authorized targets only, strictly inside program scope.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [bug-bounty-workflow, bugbounty-scope-recon, bugbounty-report-writing, bugbounty-duplicate-avoidance, recon-subdomain-enumeration]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
  - name: ffuf
    version: 2.1
  - name: nuclei
    version: 3.3
  - name: httpx
    version: 1.6
---

Methodology is what separates hunters who get paid from hunters who get lucky once. A bug bounty program rewards repeatable, thorough testing inside its stated scope: read the policy, map the surface, work each bug class systematically across the whole target, validate every finding, and report it cleanly. This skill gives you that end-to-end methodology, the order of operations, and the habits that keep you in good standing with programs. Only test targets the program explicitly lists in scope, and stop the moment you step outside it.

## Quick Workflow

1. Read the program policy end to end: scope, exclusions, forbidden test types, safe harbor, bounty table, SLA.
2. Create a program workspace: SCOPE.txt, target list, credentials for two test accounts, and a notes file.
3. Run recon in order: passive sources first, then active enumeration, then content discovery on live hosts.
4. Map the application through Burp: every endpoint, parameter, role, and state-changing action before testing anything.
5. Test one bug class at a time across the full mapped surface (access control first, then auth, injection, SSRF, file handling, business logic, APIs).
6. Validate each candidate finding from a clean session with a second account; discard false positives before they become reports.
7. Check for duplicates against disclosed reports and your own notes before writing.
8. Write one report per vulnerability: title, severity, reproduction steps, impact, remediation, evidence.
9. Track the report through triage; retest fixes politely and confirm.

## 1. Phase one: scope and rules of engagement

Scope is the contract that makes your testing legal. Before any tool runs:

- Copy the exact in-scope list into SCOPE.txt: domains, wildcards, IP ranges, mobile apps, APIs. Note what a wildcard really covers (usually only subdomains of the named domain).
- Copy the exclusions too: staging, third-party services, anything named explicitly. Out-of-scope means do not touch, not "test quietly."
- Note forbidden test types (commonly DoS, social engineering, physical attacks, high-intensity automated scanning) and the safe harbor terms.
- Record the bounty table and any severity guidance so your severity claims match what the program pays for.

Re-read the policy when the program updates it (they do, often). If you find something in an asset you are unsure about, report it to the program as a question, not as a finding, and stop probing until they confirm.

## 2. Phase two: reconnaissance

Recon builds your target list. Work in increasing intensity:

```bash
# Passive subdomain collection
subfinder -d target.com -silent -o subfinder.txt
amass enum -passive -d target.com -o amass-passive.txt

# Resolve and probe for live web hosts
cat subfinder.txt amass-passive.txt | sort -u | dnsx -silent -o resolved.txt
httpx -l resolved.txt -silent -o live.txt -title -tech-detect -status-code
```

Example output shape from httpx:

```
https://app.target.com [200] [Login Portal] [nginx,React]
https://api.target.com [403] [Forbidden] [cloudflare]
https://old.target.com [200] [Welcome] [Apache/2.4.41]
```

Content discovery on live hosts, paced politely:

```bash
ffuf -u https://app.target.com/FUZZ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -mc 200,301,302,403 -o ffuf-app.json
```

Collect every JavaScript file and grep for API endpoints, keys, and hidden parameters. JS files are scope-authorized source code review; endpoints found there are in-scope endpoints.

## 3. Phase three: application mapping

Proxy everything through Burp and use the application like a thorough user before attacking it:

- Build the site map: every endpoint with its parameters. Tag each parameter: ID, action, search, upload, redirect, URL-fetch.
- Register two accounts (different roles if possible). Diff what each role can see and do; access control bugs live in the differences.
- List every state-changing request and note its CSRF protection or absence.
- Find the API surface: Swagger or OpenAPI docs, GraphQL endpoints, mobile app traffic. Mobile traffic often exposes more than the web UI.

Nuclei assists with known-vulnerability and misconfiguration checks:

```bash
nuclei -l live.txt -t ~/nuclei-templates/http/misconfiguration/ -o nuclei-misconfig.txt
```

Treat every scanner hit as a lead, not a finding. Validate manually before it becomes a report.

## 4. Phase four: exploitation per bug class

Work one class across the whole surface before moving on. Depth per class beats shallow coverage of everything.

Access control and IDOR: for every object reference (user IDs, order IDs, document UUIDs), substitute another user's ID and a sequential neighbor. Test direct references and indirect ones (search filters, export functions, API parameters). Test function-level access: can a low-privilege role call admin endpoints directly.

Authentication: registration, login, password reset, session handling. Reset tokens must be random, single-use, and short-lived. Check for user enumeration via response differences, missing rate limits, OAuth redirect URI validation, and the state parameter.

Injection: XSS in every reflected and stored input, then template injection, then SQLi where inputs reach queries. For stored XSS, confirm it fires in another user's session.

```bash
# Quick reflected XSS probe pattern (manual, in Burp Repeater)
# Inject: "><svg onload=alert(document.domain)>  then observe reflection context
```

SSRF: every place the server fetches a URL (webhooks, avatars, PDF generators, importers) gets internal addresses and cloud metadata endpoints. Confirm with a collaborator callback, then show what internal data is reachable.

File upload: test extension, MIME type, and magic byte validation independently. A file that uploads is not a finding; execution or disclosure from the uploaded file is.

Business logic: price and quantity tampering, workflow skipping (steps out of order), race conditions on limited resources, coupon or credit abuse. Scanners cannot find these, so they pay well.

APIs: mass assignment (extra JSON fields), excessive data exposure (fields the UI never shows), missing object-level authorization per endpoint, shadow endpoints (v1, internal, debug).

## 5. Phase five: validation and reporting

Triage before writing: reproduce from a clean session, confirm real impact, check duplicates. Then write one report per vulnerability with title, justified severity, summary, numbered reproduction steps with raw HTTP requests, concrete impact, remediation, and evidence attachments. See bugbounty-report-writing for the full reporting standard and bugbounty-duplicate-avoidance before you submit.

## Edge cases

- The scope is ambiguous: ask the program in writing before testing. A "quick check" outside scope is still outside scope.
- Recon finds nothing new: go deeper on the application instead of wider. Business logic and access control bugs hide where scanners stop.
- You hit a duplicate: note the pattern and hunt its siblings. One disclosed IDOR often means the same broken pattern on five more endpoints.
- The program goes quiet: one polite follow-up after their stated SLA, then move on. Never threaten disclosure to speed triage.
- Rate limiting or WAF blocks you: slow down and never try to evade aggressively. Evasion attempts look like attacks because they are.
- You accidentally touch out-of-scope: stop immediately, document it, and disclose honestly to the program. Honesty preserves safe harbor.

## Escalation

- One bug class is exhausted on a target: rotate to a different asset class in the program (API instead of web, mobile instead of API). Fresh surface, fresh bugs.
- Low-severity findings accumulate: chain them. Information disclosure plus a weak reset flow can become account takeover; programs pay for chains.
- Stuck on validation: reproduce with a second account and a clean browser profile to rule out session confusion, the most common false positive in access control testing.
- Bounty disputes: stay factual, cite the policy and bounty table, and accept the program's final call gracefully.

## Detection and defender view

- Programs are a defensive investment: scope them to the real attack surface, keep the policy current, and triage quickly. Slow triage trains hunters to leave.
- Every bug class in section 4 maps to defenses: object-level authorization checks, output encoding, parameterized queries, SSRF allowlists with DNS pinning, strict file validation, server-side business logic enforcement.
- Monitor telemetry for hunter behavior: repeated 403s on admin paths, ID enumeration patterns, and collaborator callbacks show what attackers try first. It is free adversary emulation.
- Fix classes, not instances: one IDOR report should trigger an authorization review across the codebase, not a single endpoint patch.

## Key references

- HackerOne hunter documentation: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- OWASP Top 10 (2021): https://owasp.org/Top10/
- OWASP API Security Top 10: https://owasp.org/API-Security/
- PortSwigger Web Security Academy: https://portswigger.net/web-security
- nuclei-templates project: https://github.com/projectdiscovery/nuclei-templates
