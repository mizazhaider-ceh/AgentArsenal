---
name: rest-fuzzing
description: Use when fuzzing REST API endpoints for injection, parsing,
  and logic flaws on an authorized engagement. Covers parameter and body
  fuzzing, type confusion, HTTP method and verb tampering, and response
  differential analysis. Use when the API map is ready, when testing input
  handling at scale, when hunting for 500 errors and stack traces, or when
  you need systematic coverage of many endpoints.
version: 1.0.0
domain: api
lifecycle: stable
last_verified: 2026-10-23
parent: api-security-testing
requires: [api-security-testing]
extends: []
relates: [web-sqli, web-xss]
tools:
  - name: ffuf
    version: 2.1
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

REST fuzzing throws unexpected input at every API parameter and watches
for the cracks: 500 errors, stack traces, type confusion, and logic
bypasses. This skill covers systematic API fuzzing on authorized
engagements: building the fuzz plan from the API map, running body and
parameter fuzzing, and triaging the anomalies. Fuzzing finds the flaws
that careful manual testing misses and the flaws that manual testing
would take weeks to find.

## Quick Workflow

1. Take the endpoint inventory from api-discovery.
2. Baseline each endpoint: normal request, normal response shape.
3. Fuzz parameters: inject special characters, types, and lengths.
4. Fuzz bodies: malformed JSON, type swaps, nested objects, arrays.
5. Tamper methods and content types per endpoint.
6. Triage anomalies: reproduce each one by hand.
7. Report confirmed issues with the minimal reproducing request.

## 1. Parameter fuzzing

```bash
# Baseline first: record the normal response size and shape
curl -s -X GET 'https://target.example/api/users/123' \
  -H 'Authorization: Bearer TOKEN' -o /tmp/base.json
wc -c /tmp/base.json

# Fuzz the path parameter with special characters
ffuf -u 'https://target.example/api/users/FUZZ' \
  -H 'Authorization: Bearer TOKEN' \
  -w /tmp/special_chars.txt -mc 500 -o /tmp/fuzz_path.json

# Fuzz query parameters for injection signals
for p in "'\"<>" '%00' '../../etc/passwd' '1 OR 1=1'; do
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$p")
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    -H 'Authorization: Bearer TOKEN' "https://target.example/api/search?q=${enc}")
  echo "$p -> $code"
done
```

500 responses are leads, not findings: reproduce each one manually,
read the error body for stack traces or SQL text, and only then decide
what the anomaly means.

## 2. Body fuzzing and type confusion

```bash
# Type confusion: the API expects a string, send other types
for body in '{"id":123}' '{"id":true}' '{"id":[]}' '{"id":{}}' '{"id":null}'; do
  echo "== $body"
  curl -s -X POST 'https://target.example/api/users' \
    -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
    -d "$body" -o /tmp/tc.json -w '%{http_code}\n'
  head -c 200 /tmp/tc.json; echo
done

# Malformed JSON and deep nesting (parser stress, stay gentle)
curl -s -X POST 'https://target.example/api/users' \
  -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
  -d '{"id":}' -w '%{http_code}\n' -o /dev/null
python3 -c "print('{\"a\":' * 500 + '1' + '}' * 500)" > /tmp/deep.json
curl -s -X POST 'https://target.example/api/users' \
  -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
  -d @/tmp/deep.json -w '%{http_code}\n' -o /dev/null

# Wrong content type: form data to a JSON endpoint and vice versa
curl -s -X POST 'https://target.example/api/users' \
  -H 'Authorization: Bearer TOKEN' \
  -d 'id=123' -w '%{http_code}\n' -o /dev/null
```

Type confusion breaks authorization and validation logic regularly: an
array where a string was expected can bypass length checks, regexes, and
comparisons. Test every typed field, not just the obvious ones.

## 3. Method and content-type tampering

```bash
# Try every method on each endpoint; document what each allows
for m in GET POST PUT PATCH DELETE OPTIONS HEAD; do
  code=$(curl -s -X $m 'https://target.example/api/users/123' \
    -H 'Authorization: Bearer TOKEN' -o /dev/null -w '%{http_code}')
  echo "$m -> $code"
done

# Method override headers (some frameworks honor these)
curl -s -X POST 'https://target.example/api/users/123' \
  -H 'Authorization: Bearer TOKEN' -H 'X-HTTP-Method-Override: DELETE' \
  -o /dev/null -w '%{http_code}\n'
```

A DELETE that works where only GET was documented is a finding. Method
handling inconsistencies are also authz bugs in disguise: the
authorization check may only cover the documented method.

## Edge cases

- Rate limiting kills the fuzz run. Slow down, narrow the wordlists,
  and note the limit; the anomalies you find at low rate are the same.
- The API needs request signing. Fuzz through Burp with the signing
  extension so every fuzzed request is validly signed.
- Responses are identical for all inputs. The anomaly signal may be
  timing or a side effect (check the created objects); adapt the
  oracle to the API.
- Fuzzing creates junk data. Use a dedicated test tenant or clean up
  created objects; note the cleanup in your test log.

## Escalation

- A 500 reveals a stack trace with SQL: hand the endpoint to web-sqli
  with the exact reproducing request.
- Fuzzing suggests an authz flaw: hand it to authz-testing for the
  systematic check.
- The API is too large to fuzz fully: prioritize by data sensitivity
  and write the coverage decision into the test notes.

## Detection and defender view

Defenders see REST fuzzing as bursts of malformed requests from one
source, 500-error spikes in application monitoring, and WAF blocks on
injection patterns. It is noisy by nature. Defenses are input validation
with strict schemas, generic 500 pages that leak nothing, rate limiting,
and alerting on error-rate anomalies. Every 500 in the logs is a free
hint about where the parsers are weak.

## Key references

- OWASP API Security Top 10 2023.
- CWE-20 (Improper Input Validation).
- CWE-89 (SQL Injection), CWE-79 (XSS) via API inputs.
- ffuf 2.1 documentation.
