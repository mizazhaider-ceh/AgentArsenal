---
name: bugbounty-scope-recon
description: Use when starting a new in-scope bug bounty program and you need reconnaissance that stays strictly inside the authorized scope. Covers reading the policy into a machine-usable scope file, asset discovery from the stated scope (domains, wildcards, IP ranges, mobile apps, APIs), mapping scope boundaries and gray areas, identifying out-of-scope assets before you touch them, and the discipline of stopping at the boundary. Authorized targets only, only test assets the program explicitly lists in scope.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [bug-bounty-workflow, bugbounty-methodology, recon-subdomain-enumeration, recon-asn-netblock, domain-osint]
tools:
  - name: subfinder
    version: 2.6
  - name: amass
    version: 4.2
  - name: httpx
    version: 1.6
  - name: Python
    version: 3.12
---

Scope reconnaissance is the discipline of knowing exactly what you are allowed to touch before you touch anything. Programs ban hunters who scan out of scope, and safe harbor only covers testing inside the policy. This skill turns a program's scope statement into an enforced target list: discover the assets the scope implies, map the boundaries and gray areas, and build habits that keep every packet inside the lines. Only test targets the program explicitly lists in scope.

## Quick Workflow

1. Read the program policy end to end and copy the scope, exclusions, and forbidden test types verbatim into SCOPE.txt.
2. Normalize the scope into a target list: expand wildcards to discovered subdomains, expand CIDR ranges to IPs, list mobile apps and APIs separately.
3. Run asset discovery only against the normalized list, passive sources first.
4. Map the boundaries: for each discovered asset, decide in-scope, out-of-scope, or gray area, and record the reasoning.
5. For gray areas, ask the program in writing before testing. A "quick check" outside scope is still outside scope.
6. Build an explicit out-of-scope blocklist and enforce it in your tooling (exclusion files, proxy rules).
7. Re-read the policy on every program update; scopes change and new assets appear.
8. If you touch out-of-scope by accident, stop immediately, document it, and disclose it honestly to the program.

## 1. From policy to scope file

The scope file is the single source of truth for the engagement. Copy, do not paraphrase:

```
PROGRAM: Example Corp (HackerOne)
SCOPE IN:
  - *.example.com
  - 203.0.113.0/24
  - Example Corp Android app (com.example.app, v2.4+)
SCOPE OUT:
  - staging.example.com
  - third-party integrations (status.example.net)
  - *.example.org
FORBIDDEN: DoS, social engineering, physical, automated scanners at high rate
SAFE HARBOR: yes, good-faith testing within this policy
BOUNTY TABLE: critical 5000, high 2000, medium 500, low 100
UPDATED: 2026-10-23
```

Keep this file at the root of the program workspace and re-read it before every session. When the program updates the policy, diff the new scope against this file.

## 2. Asset discovery from stated scope

Expand each scope line into concrete targets:

```bash
# Wildcard domain: enumerate subdomains, then keep only what is under it
subfinder -d example.com -silent | sort -u > subs.txt
# CIDR range: expand to IPs, then check which are live
python3 -c "import ipaddress; print('\n'.join(str(h) for h in ipaddress.ip_network('203.0.113.0/24').hosts()))" > ips.txt
# Mobile app: pull the APK, list domains and API endpoints from strings and traffic
# API: collect base URLs from the web app JS and the mobile app
```

Then verify each discovered asset resolves and belongs to the scope:

```bash
cat subs.txt | dnsx -silent -resp -o resolved-subs.txt
# Drop anything that does not end in the scoped domain
grep -E '\.example\.com$' resolved-subs.txt > in-scope-subs.txt
```

A subdomain that resolves to a third-party IP (a CDN, a SaaS provider) is still in scope if the name is in scope, but the underlying third-party infrastructure is not yours to test directly. Test the application, not the provider.

## 3. Scope boundary mapping

For every discovered asset, assign one of three verdicts and record why:

- In-scope: the name or IP is explicitly listed, or a wildcard clearly covers it. Test normally.
- Out-of-scope: explicitly excluded, or belongs to a third party, or is outside the named domains and ranges. Do not touch.
- Gray area: plausible but ambiguous (an acquired company domain not yet listed, a subdomain pointing at a partner, a shared staging environment). Ask the program in writing before testing.

```bash
# Example boundary decision log (decisions.md)
# api.example.com -> IN SCOPE (wildcard *.example.com)
# staging.example.com -> OUT (explicitly excluded)
# legacy-acquired.io -> GRAY (not listed; acquired 2024; asked program 2026-10-23, awaiting reply)
```

Gray areas stay untouched until the program answers. Most programs answer scope questions quickly because it protects them too.

## 4. Out-of-scope avoidance in tooling

Enforce the boundary mechanically, not by memory:

- Keep an `exclude.txt` blocklist and pass it to every scanner that supports exclusions.
- In Burp, set Target scope to the in-scope list and enable "drop out-of-scope requests" so stray clicks do not generate traffic.
- For wildcard-heavy scopes, add a pre-flight check script that verifies a target matches the scope regex before any active tool runs.
- Never follow a redirect or a pivot from an in-scope host to an out-of-scope one. The vulnerability does not become in scope because you arrived from inside.

## Edge cases

- The scope lists a wildcard but the program clearly only operates some subdomains: the wildcard is the authority, but partner-looking subdomains go in the gray list until confirmed.
- An in-scope domain CNAMEd to an out-of-scope third party: test the application behavior on the in-scope name; do not attack the third-party infrastructure behind it.
- IP range scope with unassigned or reassigned IPs: verify current ownership with whois before testing an IP; ranges get reallocated.
- The mobile app talks to API hosts not listed in scope: those hosts are gray until the program confirms, even though the app is in scope.
- Scope updated mid-hunt: diff immediately, move newly excluded assets to the blocklist, and stop any running scans against them.
- You accidentally scanned out-of-scope: stop, record exactly what was sent, and disclose it to the program honestly. Honesty preserves safe harbor; hiding it destroys it.

## Escalation

- Gray area with no program answer after the stated SLA: treat it as out-of-scope and move on. Silence is not permission.
- Asset discovery stalls inside a narrow scope: go deeper on the listed assets (more endpoints, more roles, more logic) instead of wider outside them.
- The program's scope contradicts its actual infrastructure (acquisitions, rebrands): report the mismatch as a scope question; programs often expand scope when hunters ask precisely.
- You find a critical issue in an out-of-scope asset: do not probe it further. Report its existence to the program as a good-faith note with no exploitation detail, and let them decide.

## Detection and defender view

- Scope discipline is what makes bounty hunting a defensive asset instead of a liability: the policy plus your scope file is the audit trail that your testing was authorized.
- Defenders should keep scope current: stale scopes with unlisted acquisitions are where hunters either waste time asking or cross lines by accident.
- Monitor for out-of-scope probing from hunters as a signal: it usually means your scope statement is ambiguous, not that the hunter is malicious. Clarify the policy.
- Safe harbor works both ways: it protects good-faith hunters inside the policy and gives you clear grounds against anyone outside it.

## Key references

- HackerOne program scope documentation: https://docs.hackerone.com
- Bugcrowd scope and safe harbor docs: https://docs.bugcrowd.com
- OWASP Amass documentation: https://github.com/owasp-amass/amass
- subfinder documentation: https://github.com/projectdiscovery/subfinder
- dnsx documentation: https://github.com/projectdiscovery/dnsx
- MITRE ATT&CK T1590 Gather Victim Network Information: https://attack.mitre.org/techniques/T1590/
