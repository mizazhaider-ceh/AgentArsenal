---
name: duplicate-avoidance
description: Use when hunting bugs on crowded programs to avoid
  submitting duplicates. Covers checking known issues, targeting
  uncommon areas, timing strategies, and validating novelty before
  submitting. Use when choosing what to test, when a finding feels
  familiar, when the program is old and crowded, or when deciding
  whether a variant is worth submitting.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
parent: bug-bounty-workflow
requires: [bug-bounty-workflow]
extends: []
relates: [recon-for-bounty]
tools:
  - name: Python
    version: 3.12
---

Duplicates are the tax on crowded programs: the same XSS found by ten
researchers pays the first one. This skill covers avoiding them:
researching what is known, hunting where others do not, and validating
novelty before you write the report. It does not guarantee uniqueness;
it shifts the odds toward targets with fewer hunters.

## Quick Workflow

1. Research the program: disclosed reports, known issue lists, common
   findings.
2. Hunt away from the crowd: new assets, odd features, deep logic.
3. Before submitting, check the finding against known patterns.
4. Assess variant novelty honestly: same root cause is a duplicate.
5. Submit fast once validated; speed matters after novelty.
6. Learn from duplicates: log why, adjust the hunting.

## 1. Researching the program

```bash
# Before testing a program, gather:
# - Disclosed HackerOne/Bugcrowd reports for the program (techniques used)
# - The program's changelog and scope history (what is new)
# - Common findings for the tech stack (what everyone finds first)

# Build the "probably already found" list:
# - Reflected XSS on the search box
# - Missing security headers
# - Verbose errors on the main app
# Then hunt everything EXCEPT that list first
```

Programs disclose to teach; read the disclosures as a map of where
not to start. The disclosed XSS in the search box means the search box
is picked clean; the undisclosed admin import feature is not.

## 2. Hunting where others do not

```bash
# Low-competition targets (historically):
# - Newly added scope (test within days of the announcement)
# - Mobile app APIs (fewer web hunters look here)
# - Business logic flaws (need understanding, not just scanning)
# - Chained vulnerabilities (each link is known; the chain is not)
# - Old, forgotten subdomains (from recon-for-bounty monitoring)
# - File handling: uploads, exports, imports, parsers

# Depth beats breadth on crowded programs:
# one feature understood completely > ten features scanned shallowly
```

Business logic is the durable edge: it cannot be found by scanners,
it needs the application's context, and most hunters skip it for the
faster injection wins. Learn the application's purpose and abuse its
rules; that is where the unique findings live.

## 3. Novelty validation

```bash
# Before writing the report, ask:
# 1. Is this the same root cause as a known finding? (duplicate)
# 2. Is it the same vuln class in a different parameter? (likely duplicate
#    unless the program pays per instance: check the policy)
# 3. Does it need a genuinely different exploit path? (probably novel)
# 4. Would the fix for the known issue also fix mine? (duplicate if yes)

# The fix test is the best heuristic: if one patch kills both,
# they are the same finding.
```

When in doubt about a variant, submit with a clear note explaining
how it differs; triagers decide, and a well-argued variant sometimes
pays. But do not spam variants of your own duplicate hoping one
sticks; programs notice and remember.

## Edge cases

- The program pays per instance. Then variants are submissions, not
  duplicates; read the policy carefully because most programs do not.
- The duplicate window is unclear. Ask the program; some dupes expire
  after fixes, some do not.
- Your finding is a bypass of a known fix. That is novel (the fix
  failed); document the original fix and your bypass clearly.
- Everything you find is a duplicate. Move programs or move target
  areas; the hunting strategy needs the change, not the effort.

## Escalation

- A duplicate teaches you the program's patterns: log it (what, why
  duped, what you missed) and adjust the target list.
- The program is saturated: rotate to newer programs or private
  invites where the hunter density is lower.
- You need a second opinion on novelty: ask a trusted hunter, not
  the program; the program's answer is the submission itself.

## Detection and defender view

From the program's side, duplicates are signal: ten duplicate XSS
reports mean the finding class is systemic and the fix should be
systemic (framework-level encoding, not per-page patches). Programs
reduce duplicates with good scope docs, disclosed reports, and clear
variant policies. The defender's win from the duplicate pile is the
pattern it reveals.

## Key references

- Program disclosure pages (HackerOne Hacktivity, Bugcrowd disclosures).
- OWASP Testing Guide (for the systematic coverage that avoids
  shallow duplicates).
