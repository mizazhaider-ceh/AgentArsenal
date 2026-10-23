---
name: bugbounty-duplicate-avoidance-search-techniques
parent: bugbounty-duplicate-avoidance
description: Use when you have fingerprinted an in-scope finding and need to search thoroughly for prior reports before submitting. Covers building search queries from the finding fingerprint, searching HackerOne Hacktivity and Bugcrowd disclosures effectively, grepping your own per-program history, using search engines for hunter write-ups, and varying terminology so differently-titled duplicates still surface. Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-duplicate-avoidance]
extends: []
relates: [bugbounty-duplicate-avoidance-disclosure-timelines, bugbounty-duplicate-avoidance-program-specific-dupes, bug-bounty-workflow]
tools:
  - name: Python
    version: 3.12
---

Searching is a skill: the duplicate you miss is the payout you lose. Different hunters title the same bug differently, disclosures get redacted, and your own history is the fastest check you have. This sub-skill covers the search techniques for the duplicate check step of bugbounty-duplicate-avoidance: query construction, where to look, terminology variation, and searching your own records. Search only for findings on in-scope targets.

## Quick Workflow

1. Write the fingerprint: bug class, component, endpoint, effect, one line.
2. Generate query variants: formal terms, slang terms, component names, endpoint paths.
3. Search your own history first: submissions.log and findings folders for this program (fastest, highest hit rate for self-dupes).
4. Search HackerOne Hacktivity filtered to the program with each query variant.
5. Search Bugcrowd disclosures and the program brief page.
6. Search web engines for hunter write-ups naming the program and bug class.
7. Record the search: queries run, hits reviewed, verdict (clear or duplicate).

## 1. Building queries from the fingerprint

From the fingerprint, generate at least six queries by varying each axis:

```
Fingerprint: stored-xss | support.example.com | /api/v1/tickets subject | admin queue

Queries:
1. "Example Corp" stored XSS
2. "Example Corp" "cross-site scripting"
3. "Example Corp" ticket XSS
4. "Example Corp" "support portal" XSS
5. site:hackerone.com "Example Corp" XSS
6. "example.com" XSS writeup
```

Vary the bug class terms: "XSS," "cross-site scripting," "script injection," "HTML injection." Vary the component: "ticket," "support portal," "helpdesk." Vary the program name: legal name, brand name, domain. One axis fixed while others vary catches the reports titled differently from yours.

## 2. Searching your own history first

Your own submissions are the duplicates you can prevent in ten seconds:

```bash
# Per-program log: fingerprint, date, status
cat ~/bb/example.com/submissions.log
# Example line: 2026-09-14 | stored-xss | tickets subject | submitted | triaged-medium

# Grep findings and notes for the class and the endpoint
grep -ril "xss" ~/bb/example.com/findings/ | head
grep -ri "ticket" ~/bb/example.com/submissions.log
```

Keep the log format fixed: date, bug class, component, endpoint, status. Fixed format makes grep reliable. Log every submission the day you submit it, including the fingerprint; memory of what you submitted six months ago is unreliable.

## 3. Platform disclosure search

HackerOne Hacktivity: filter to the program first, then search. Read titles and the disclosed summaries; note the vulnerable area each names. Sort by recent: a two-year-old disclosure about rewritten code is weaker evidence of duplication than last month's.

Bugcrowd: check disclosed submissions and the program brief. Some briefs list "commonly reported issues" which function as a pre-announced duplicate list; treat those classes as submit-only-with-a-twist.

The program's own channels: changelog, status page, security.txt history, release notes. A fixed version number next to your component is a strong duplicate signal; a rewrite of the component since disclosure weakens it.

## 4. Web search for write-ups

Hunters publish write-ups after disclosure, often with more technical detail than the platform disclosure:

```
"example.com" bug bounty writeup XSS
"Example Corp" hackerone XSS
"support.example.com" vulnerability
```

Write-ups name exact endpoints and payloads, which lets you compare precisely against your fingerprint. They also reveal the program's triage behavior: what they paid, what they marked duplicate, how they worded the fix.

## Edge cases

- No disclosed reports exist for the program: search your history and the program's changelog only, then submit. New or private programs have thin disclosure trails; that is normal.
- Disclosures are heavily redacted: compare on bug class plus component; when you cannot rule it out, note the possibly-related disclosure in your report and let triage decide.
- The same hunter discloses the same class repeatedly: read their write-ups; they are effectively publishing the program's duplicate map for free.
- Search results are polluted by other companies with similar names: add the domain to every query to disambiguate.

## Escalation

- Searches keep coming back ambiguous: timebox the search to 30 minutes. Beyond that, the expected value of more searching drops below the expected value of submitting with a clear fingerprint and a note.
- You find a write-up describing your exact bug on a different program: not a duplicate, but a strong hint the pattern is common. Check the siblings on your program extra carefully before submitting.

## Detection and defender view

- Hunters who search well submit fewer duplicates, which directly shrinks your triage queue. Encourage it: keep disclosures searchable and specific.
- Publish write-up-friendly disclosures: specific component names and fixed versions let the next hunter self-check instead of submitting blind.
- Monitor which of your disclosures get cited in hunter write-ups; those are the patterns the community now knows, so expect sibling-hunting there.

## Key references

- HackerOne Hacktivity: https://hackerone.com/hacktivity
- HackerOne disclosure guidelines: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- MITRE ATT&CK T1596 Search Open Websites/Domains: https://attack.mitre.org/techniques/T1596/
