---
name: recon-for-bounty
description: Use when doing reconnaissance for a bug bounty program to
  maximize coverage within the program scope. Covers scope parsing,
  subdomain and endpoint discovery at bounty speed, prioritizing targets,
  and continuous monitoring for new assets. Use when starting on a new
  program, when the scope updates, when hunting for the widest attack
  surface, or when building the automation that watches for changes.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
parent: bug-bounty-workflow
requires: [bug-bounty-workflow]
extends: []
relates: [recon-passive, recon-active]
tools:
  - name: Amass
    version: 4.2
  - name: ffuf
    version: 2.1
  - name: Python
    version: 3.12
---

Bounty recon is a coverage game: the widest in-scope asset map wins,
because every asset is a chance at a finding. This skill covers the
bounty recon workflow: parsing scope precisely, discovering assets fast,
prioritizing by bounty potential, and monitoring for new assets over
time. It runs continuously, not once; programs change, and new assets
are the freshest targets.

## Quick Workflow

1. Parse the scope: read every line, note wildcards and exclusions.
2. Build the initial asset map: subdomains, IPs, web apps, APIs.
3. Fingerprint everything: technologies, interesting endpoints.
4. Prioritize: new assets, complex apps, and forgotten subdomains first.
5. Set up monitoring: alert on new subdomains and changed assets.
6. Feed prioritized targets to the testing workflow.
7. Re-run on scope updates and on a schedule.

## 1. Scope parsing

```bash
# Scope checklist per program (fill before any scanning):
cat > /tmp/bounty_scope.txt <<'EOF'
Program: <name>
In scope: <domains, wildcards, IPs, apps>
Out of scope: <explicit exclusions>
Bounty table: <critical/high/medium/low payouts>
Rules: <rate limits, forbidden techniques, disclosure terms>
Notes: <acquisitions, subdomains of subdomains, etc.>
EOF

# Scope traps to check:
# - "*.example.com" includes deep subdomains; "example.com" may not
# - Out-of-scope third parties embedded in scope (mark, do not test)
# - "Anything not listed is out of scope" versus "in scope" defaults
```

Scope misunderstandings get researchers banned: when in doubt, ask the
program before testing the gray area. The question is cheap; the ban is
not.

## 2. Asset discovery at bounty speed

```bash
# Subdomains: passive first (fast, quiet), then active on the wildcards
# Passive: certificate transparency, Amass passive mode
amass enum -passive -d example.com -o /tmp/subs_passive.txt 2>/dev/null | head -20

# Active brute-force on the in-scope wildcard only
# (respect the program's rate expectations)

# Merge, resolve, and fingerprint
sort -u /tmp/subs_*.txt > /tmp/subs_all.txt
wc -l /tmp/subs_all.txt

# Quick web fingerprint per live host (status, title, tech hints)
python3 - <<'EOF'
print("For each live host: fetch /, record status/title/headers")
print("Flag: login pages, admin panels, API docs, staging/dev hosts")
print("Staging and dev subdomains are historically the richest targets")
EOF
```

Prioritize the unusual: the subdomain with the 2015 CMS, the API with
no docs, the staging host with debug on. The main app gets everyone's
attention; the forgotten assets get none, which is why they pay.

## 3. Continuous monitoring

```bash
# New assets are fresh targets: monitor for them
# Daily: re-run passive subdomain enumeration, diff against yesterday
# Alert on: new subdomains, new IPs, changed certificates, new ports

# Simple diff-based monitor
# comm -13 /tmp/subs_yesterday.txt /tmp/subs_today.txt > /tmp/subs_new.txt
# Any line in subs_new.txt is a same-day testing target

# Also watch: certificate transparency logs for the scope domains,
# program scope updates (new in-scope assets announced)
```

The researcher who tests a new subdomain on day one beats the researcher
who finds it on day thirty. Monitoring is the highest-ROI automation in
bounty hunting; build it before you need it.

## Edge cases

- The scope is huge (wildcard on a tech giant). Narrow by
  fingerprinting: test the interesting 5 percent deeply rather than
  the 100 percent shallowly.
- The program forbids automated scanning. Respect it absolutely;
  manual recon and passive sources still build a strong map.
- Duplicates are likely on popular targets. That is what
  duplicate-avoidance is for; recon still comes first.
- Rate limits are strict. Slow down, prioritize harder, and let the
  monitoring run quietly in the background.

## Escalation

- You need the asset map shared with a team: version it, note the
  discovery dates, and mark who is testing what to avoid collisions.
- Scope ambiguity blocks testing: ask the program publicly or
  privately per their preference; document the answer.
- The program ends or the scope shrinks: archive the map; scopes
  often return.

## Detection and defender view

From the program's side, bounty recon looks like broad internet
scanning with security-tool fingerprints: it is expected and (within
the rules) welcome. Programs detect abuse by the rules: out-of-scope
probing, aggressive rates, and disruptive techniques. The defender's
view of good bounty recon is that it finds the assets the internal
team forgot; the asset inventory gap is the real finding.

## Key references

- OWASP Testing Guide: information gathering.
- Program policy pages (scope is the contract).
- Amass 4.2 documentation.
