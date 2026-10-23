---
name: bugbounty-duplicate-avoidance-program-specific-dupes
parent: bugbounty-duplicate-avoidance
description: Use when hunting a specific in-scope program repeatedly and you need to learn its duplicate personality. Covers building a per-program duplicate profile (known-duplicate classes, sibling payout policy, auto-closed patterns), learning from the program's triage history in disclosed reports, adapting your hunting to low-duplicate classes like business logic and access control, and turning a duplicate hit into a sibling-hunting session. Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-duplicate-avoidance]
extends: []
relates: [bugbounty-duplicate-avoidance-search-techniques, bugbounty-duplicate-avoidance-disclosure-timelines, bugbounty-methodology]
tools:
  - name: Python
    version: 3.12
---

Every program has a duplicate personality: the classes everyone reports, the sibling policy they actually enforce, the patterns their tooling auto-closes. Hunters who learn it stop wasting submissions and start aiming where duplicates are rare. This sub-skill covers building and using a per-program duplicate profile. Profile only programs whose scope authorizes your testing.

## Quick Workflow

1. Create a per-program profile file: program-duplicates.md in the program workspace.
2. Mine disclosed reports for the program: list bug classes, endpoints, payouts, and duplicate-marked reports.
3. Record the sibling policy as observed: per-endpoint payouts versus marked-duplicate siblings.
4. List auto-closed or commonly-reported classes from the program brief and triage behavior.
5. Aim hunting time at low-duplicate classes: business logic, access control chains, SSRF, second-order issues.
6. When you hit a duplicate, log the pattern and immediately hunt its siblings.
7. Update the profile after every submission outcome.

## 1. Building the duplicate profile

One file per program, updated after every triage outcome:

```markdown
# Example Corp - duplicate profile (updated 2026-10-23)

## Known-duplicate classes (submit only with a twist)
- Reflected XSS on marketing pages (12 disclosed, all low or duplicate)
- Missing security headers alone (brief lists as commonly reported)
- Verbose server banners

## Sibling policy (observed)
- IDOR: paid per endpoint (3 disclosed, distinct endpoints, all paid)
- XSS: second report on sibling page marked duplicate once (2026-08)

## Auto-closed / scanner-handled
- Open S3 buckets (program runs own scanning, auto-duplicates)

## Low-duplicate hunting grounds
- Business logic in checkout (0 disclosed)
- API mass assignment (1 disclosed, 2025)
- SSRF in webhook features (0 disclosed)
```

Build it from disclosed reports, the program brief, and your own submission outcomes. Ten minutes of profiling saves hours of duplicate write-ups.

## 2. Reading triage behavior

Disclosed reports are the program's revealed preferences:

- Payout per class and per endpoint: shows what they value and whether siblings pay.
- Reports marked duplicate with visible originals: shows exactly where their duplicate line sits.
- Time from report to triage per class: fast triage on a class means they care about it; slow triage means it is noise to them.
- Comments from the program: occasionally state the duplicate policy explicitly ("we treat sibling endpoints as one issue").

When the brief says "we have received many XSS reports," believe it: your reflected XSS needs stored impact, an admin context, or a chain to be worth the write-up.

## 3. Aiming where duplicates are rare

Duplicate rates are lowest where scanners and casual hunters cannot go:

- Business logic: price, quantity, workflow order, race conditions. Zero disclosed in most programs because each needs manual reasoning.
- Access control chains: two low-severity issues composed into account takeover. The components are known; the composition is original.
- SSRF in specific features: webhooks, importers, PDF generators. Each feature is a fresh attack surface.
- Second-order issues: stored data rendered in a different component (admin panel, export, email template). The injection point is known; the sink is not.
- Mobile-only or API-only endpoints: fewer hunters look there, so disclosure trails are thin.

This is not about avoiding work; it is about aiming effort where originality lives.

## 4. Turning a duplicate into sibling hunts

A duplicate verdict is a map, not a loss:

1. Log the duplicate pattern: class, component, endpoint, why it was known.
2. List every sibling: same component on other endpoints, same endpoint pattern on other components, same bug class in adjacent features.
3. Test the siblings in one focused session, fastest-first.
4. For each sibling, run the duplicate check again: some siblings are known, some are not.
5. Submit the original ones promptly, referencing the pattern but not the duplicate report's details.

One disclosed IDOR has repeatedly meant five more on sibling endpoints. The hunters who profit from disclosures are the ones who read them as hunting guides.

## Edge cases

- The program's sibling policy is unwritten and inconsistent: default to submitting clearly distinct endpoints with a note, and let triage teach you. Log every outcome to sharpen the profile.
- A class is known-duplicate but you found a genuinely novel variant (new sink, new privilege boundary): submit it as the variant it is, with the novelty stated up front so triage does not reflex-mark it.
- The program changes its duplicate policy: re-profile. Policies tighten as programs mature; what paid per-endpoint last year may be one-issue-now.

## Escalation

- Duplicate rate stays high despite profiling: the program may be over-hunted for your style. Rotate to a newer or less popular program where your methodology is fresher.
- You suspect valid findings are marked duplicate to avoid payout: document, stay professional, leave quietly. Reputation markets punish bad programs without your help.

## Detection and defender view

- Publish your duplicate policy explicitly: per-endpoint or per-issue, which classes are auto-handled. Explicit policy cuts duplicate submissions more than any tooling.
- When you fix a reported bug, fix and disclose the sibling sweep: every undisclosed sibling is a future report you triage for free.
- Track duplicate rate per class per quarter: rising duplicates in a class mean your disclosure or your automated handling needs work, not that hunters are lazy.
- New programs should expect high duplicate rates early; it decays as the disclosure trail grows. Plan triage capacity accordingly.

## Key references

- HackerOne Hacktivity: https://hackerone.com/hacktivity
- HackerOne disclosure guidelines: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- MITRE ATT&CK T1596 Search Open Websites/Domains: https://attack.mitre.org/techniques/T1596/
