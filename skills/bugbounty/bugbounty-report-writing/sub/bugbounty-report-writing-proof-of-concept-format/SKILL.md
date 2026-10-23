---
name: bugbounty-report-writing-proof-of-concept-format
parent: bugbounty-report-writing
description: Use when you need to present the proof of concept for an in-scope bug bounty finding in the format triagers can replay. Covers the PoC evidence standard (raw HTTP requests over screenshots, clean-state numbered steps, exact values), per-bug-class PoC patterns (XSS, IDOR, SSRF, SQLi, auth flaws, file upload, business logic), screen recording for multi-step flows, redacting other users' data, and the per-finding evidence folder layout. Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-report-writing]
extends: []
relates: [bugbounty-report-writing-impact-statements, bugbounty-report-writing-cvss-scoring, bug-bounty-workflow]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

The proof of concept is the part of the report the triager actually replays. A PoC they can copy, paste, and run gets triaged in minutes; a PoC made of screenshots and prose gets queued behind everything else. This sub-skill sets the evidence standard: raw HTTP first, numbered steps from a clean state, exact values, per-class patterns, and recordings for flows that need them. Present PoCs only for vulnerabilities found inside program scope.

## Quick Workflow

1. During testing, save the raw request and response of the proving step (Burp save item, or copy as curl).
2. Reproduce the finding once more from a clean browser profile, following your own notes literally.
3. Write numbered steps from that clean state, with exact URLs, accounts, and payloads.
4. Paste the raw HTTP request for the proving step into the report as text.
5. Screenshot the moment of impact (the other user's data, the alert in the victim session).
6. For multi-step or stored flows, record a short screen capture walking the steps.
7. Redact any real third-party data, then file everything in the per-finding evidence folder.

## 1. The PoC evidence standard

Every PoC has three layers, in this order of importance:

1. Replayable text: the raw HTTP request, exact commands, exact payload strings. This is what the triager copies.
2. Numbered steps: the narrative that turns the request into a scenario (which account, which profile, what to click, what you should see).
3. Visual proof: screenshots or video of the impact moment. This confirms, it does not replace layers 1 and 2.

```http
POST /api/v1/tickets HTTP/1.1
Host: support.example.com
Authorization: Bearer eyJhbGciOi...<attacker-token>
Content-Type: application/json
Content-Length: 68

{"subject":"<svg onload=alert(document.domain)>","body":"help"}
```

Steps that reference it: "1. Log in as attacker@example.com. 2. Send the request above (Repeater or curl). 3. In a separate profile logged in as admin@example.com, open Admin > Ticket queue. 4. The alert fires, proving script execution in the admin session."

## 2. Per-bug-class PoC patterns

- XSS (reflected): the exact URL with payload, plus the reflection context noted ("reflected unencoded inside a double-quoted attribute"). One URL the triager can open.
- XSS (stored): the submission request, then the trigger location and the victim session that fires it. Include the recording; stored flows confuse in text alone.
- IDOR: two requests side by side, yours and the victim's object, showing the 200 with another user's data. State both account names.
- SSRF: the request that makes the server fetch, plus the collaborator or request-bin log showing the incoming connection with timestamp. Then the internal target and what it returned, redacted as needed.
- SQLi: the boolean or time-based proof (two requests, true versus false condition, with response difference or timing), not a full dump. Minimal proof, e.g. the output of a single `SELECT user()` style query.
- Authentication flaws: the reset or login flow steps with the token values (yours, expiring, test accounts only) and the exact point where the check fails.
- File upload: the upload request, the storage location, and the fetch proving execution or disclosure. Use a harmless marker file, never a real shell on a production target.
- Business logic: the sequence of requests with the manipulated values highlighted (price 0, quantity -1, steps out of order) and the resulting state (order confirmed at 0.00).

## 3. Recordings and screenshots

- Screenshot the impact moment only: the alert dialog, the other user's data on screen, the admin action completed. Three good screenshots beat thirty.
- Record multi-step flows (stored XSS trigger, checkout manipulation, OAuth dance) as short silent screen captures. No narration needed; the steps speak.
- Keep recordings under two minutes. Trim ruthlessly; triagers watch at 2x or not at all.
- Redact: blur other users' names, emails, amounts, and anything that is not your test data. Redaction is part of the PoC, not an afterthought.

## 4. The evidence folder

One folder per finding, created during testing:

```
findings/2026-10-23-stored-xss-tickets/
  notes.md        # what you tried, what failed, timestamps
  request.txt     # raw proving request
  response.txt    # raw proving response
  impact.png      # screenshot of the impact moment
  walkthrough.mp4 # short recording for multi-step flows
```

When the triager asks a follow-up in two weeks, this folder has the answer. When you hunt the same pattern next month, it is your template.

## Edge cases

- The PoC needs timing (race conditions): include the script or Turbo Intruder config, the parallelism used, and how many attempts it took. "Won 3 of 10 runs" is honest and triageable.
- The PoC only works in your session: it is not a PoC yet. Rebuild from a clean profile until it works cold, then write it up.
- The proving step touches real user data: stop at the field names. "Returns full name, email, and order history of user 8842" proves it; the contents do not need to leave the target.
- Video files are too large for the platform: host per the program's guidance or link a trimmed version; never let size be the reason the PoC is missing.
- The triager cannot reproduce: check your steps against a truly clean state (new profile, fresh accounts), and ask what differs on their side before assuming they are wrong.

## Escalation

- A PoC the triager cannot replay after two honest attempts: rebuild it from scratch in a fresh environment. The bug is usually session state you forgot to document.
- The platform mangles your raw HTTP (smart quotes, line endings): attach request.txt as a file as well as pasting it, so there is always a byte-exact copy.
- Complex chains: split the PoC into labeled phases (Phase 1: get token, Phase 2: escalate) with a checkpoint observable after each.

## Detection and defender view

- Replayable PoCs let defenders reproduce in staging in minutes, which is the single biggest accelerator of fix time. Text beats video for this.
- The per-class patterns in section 2 double as defender test cases: run them against staging after the fix to confirm remediation.
- Redaction discipline in PoCs models how the program should handle reporter-submitted data containing user information.
- Evidence folders are audit trails: they show exactly what the hunter did, which supports both payout decisions and safe harbor reviews.

## Key references

- HackerOne report guidance: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- PortSwigger Web Security Academy: https://portswigger.net/web-security
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- CWE database: https://cwe.mitre.org/
