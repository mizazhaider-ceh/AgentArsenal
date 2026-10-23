---
name: bugbounty-duplicate-avoidance
description: Use when a finding is validated on an in-scope bug bounty target and you need to check it is not already known before writing the report. Covers searching disclosed reports (HackerOne Hacktivity, Bugcrowd disclosures, program changelogs), searching your own submission history, reading disclosure timelines to judge who reported first, program-specific duplicate patterns (same bug class across sibling endpoints), and what to do when you land a duplicate (hunt siblings, note the pattern). Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [bug-bounty-workflow, bugbounty-methodology, bugbounty-report-writing, bugbounty-methodology-reporting-phase]
tools:
  - name: Python
    version: 3.12
---

Duplicates are the most expensive non-finding in bug bounty: all the work, none of the payout. Every validated finding gets a duplicate check before it becomes a report, against disclosed reports, the program's own history, and your notes. This skill gives you the search techniques, the timeline reading, and the program-specific patterns that keep your submissions original. Check duplicates only for vulnerabilities found inside program scope.

## Quick Workflow

1. Write a one-line fingerprint of your finding: bug class, component, endpoint, effect.
2. Search disclosed reports for the program: HackerOne Hacktivity, Bugcrowd disclosures, the program's changelog or known-issues page.
3. Search your own submission history and notes for the same pattern on this program.
4. Search broader: same bug class disclosed on similar programs, which hints the pattern is well known.
5. Read disclosure timelines to judge whether an existing report covers your exact finding or just a sibling.
6. If it is a duplicate: do not submit. Hunt the sibling endpoints for the same pattern instead.
7. If it is original: submit promptly. Speed matters once validation is done.
8. Log the finding's fingerprint in your notes regardless of outcome, so future checks are fast.

## 1. The fingerprint

Before searching, compress the finding to one searchable line:

```
stored-xss | support.example.com | /api/v1/tickets subject | fires in admin queue
```

Search each element separately and together: the bug class alone ("stored XSS" + program name), the component ("ticket subject"), and the endpoint. Different hunters title differently, so vary the terms: "XSS," "cross-site scripting," "script injection" all get a pass.

## 2. Where to search

- HackerOne Hacktivity: filter by the program, then search the bug class and component. Disclosed reports show titles and often the vulnerable area.
- Bugcrowd: disclosed submissions and the program's brief page, which sometimes lists out-of-scope-by-duplicate patterns.
- The program's own changelog, status page, or known-issues list: fixed versions and release notes reveal what was already reported.
- Your notes: grep your per-program finding logs for the bug class and endpoint. Your own past submissions are the duplicates you control.
- Search engines: `"program name" "bug class"` occasionally surfaces write-ups hunters published after disclosure.

```bash
# Example: grep your own history before submitting
grep -ri "stored.xss" ~/bb/example.com/findings/ | head -20
grep -ri "tickets" ~/bb/example.com/submissions.log | head -20
```

## 3. Reading disclosure timelines

A disclosed report is a duplicate of yours only if it covers the same vulnerability, not just the same class:

- Same endpoint and same parameter: duplicate. Move on.
- Same bug class, different endpoint: usually not a duplicate. Programs pay per vulnerable location unless their policy says otherwise. Hunt the siblings.
- Same endpoint, different bug class: not a duplicate. An XSS on a page with a known IDOR is a separate report.
- Vague disclosed title ("XSS in support portal"): treat as possibly covering yours. Weigh the risk: submitting into a likely duplicate costs triage goodwill; skipping a possibly-original finding costs a payout. When the title is vague and your endpoint is specific, many hunters submit with a note referencing the disclosed report.

Check dates: a report disclosed last month about code that changed since may mean your finding is a regression, which is a fresh report, not a duplicate.

## 4. Program-specific duplicate patterns

Programs develop duplicate personalities. Learn each program's:

- Known-duplicate classes: some programs have received 200 reflected XSS reports; the 201st needs a twist (stored, admin context, chained impact) to be worth submitting.
- Sibling policies: some programs mark the second IDOR on a sibling endpoint as a duplicate of the first; others pay per endpoint. Their past triage decisions, visible in disclosed reports, tell you which.
- Auto-duplicate tooling: some programs run scanners and auto-close known patterns. Check whether your finding's class appears in their "commonly reported, auto-closed" list before investing in the write-up.

When you do hit a duplicate, the pattern is the prize: one disclosed IDOR means the same broken authorization pattern probably exists on five more endpoints. Hunt the siblings immediately; the original reporter's fix may not have covered them.

## Edge cases

- The finding is a duplicate but the original was never fixed: still a duplicate for payout, but a polite note to the program that it regressed or persists can earn goodwill and sometimes a re-open.
- You and another hunter submit nearly simultaneously: the earlier submission wins. This is why validated findings get submitted promptly, not batched for weeks.
- The disclosed report is redacted heavily: you cannot tell if it covers your endpoint. Submit with a clear fingerprint and let triage decide; note the possibly-related disclosure in your report.
- Internal duplicates (your own past submissions): keep a submissions.log per program with fingerprints and dates. Checking it takes ten seconds and saves the embarrassment of self-duplicating.

## Escalation

- Duplicate rate is high on a program: shift from common classes (reflected XSS, missing headers) to business logic and access control, where duplicates are rarer and payouts higher.
- A sibling of a disclosed finding looks fixed but bypassable: that is a new finding (fix bypass), not a duplicate. Report it as a follow-up with the bypass evidence.
- You suspect the program marks valid findings as duplicates to avoid payout: document everything, stay professional, and take your hunting to programs with better reputations. Do not accuse; just leave.

## Detection and defender view

- Publish disclosed reports with specific-enough titles that hunters can self-check duplicates; vague titles waste everyone's time.
- Maintain a known-issues list: hunters who can check it will, and your triage queue shrinks.
- When you fix a bug class, fix the siblings too, then disclose the pattern. Each undisclosed sibling is a future duplicate report you will triage for free.
- Track duplicate rates per bug class as a signal: classes with 90 percent duplicates are classes your scanners or your disclosure clarity should handle before humans do.

## Key references

- HackerOne Hacktivity: https://hackerone.com/hacktivity
- HackerOne disclosure guidelines: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- CVSS v3.1 specification: https://www.first.org/cvss/
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
