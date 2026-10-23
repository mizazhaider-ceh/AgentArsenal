---
name: authz-testing
description: Use when testing API authorization: whether users can access
  other users' data or admin functions on an authorized engagement. Covers
  IDOR testing, horizontal and vertical privilege escalation, function
  level access checks, and multi-account test methodology. Use when the API
  serves user-specific data, when roles exist, when object IDs are
  predictable, or when assessing broken object and function level
  authorization.
version: 1.0.0
domain: api
lifecycle: stable
last_verified: 2026-10-23
parent: api-security-testing
requires: [api-security-testing]
extends: []
relates: [auth-attacks, web-sqli]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
---

Broken authorization is the most common serious API flaw: the API checks
who you are but not whether you may touch this object or use this
function. This skill covers systematic authz testing on authorized
engagements: IDOR, horizontal and vertical escalation, and function-level
gaps, using two or three test accounts. It is methodical work; the
technique is simple, and thoroughness is the whole game.

## Quick Workflow

1. Get two low-privilege accounts (A and B) plus a high-privilege
   account if the scope provides one.
2. As user A, capture requests for A's own objects and note every ID.
3. Replay A's requests with B's token: horizontal test.
4. Replay low-privilege requests with the admin token and vice versa:
   vertical test.
5. Try admin endpoints with low-privilege tokens: function-level test.
6. Mutate IDs (increment, UUID swap, null) for IDOR variants.
7. Document each broken check with both requests side by side.

## 1. IDOR testing

```bash
# As user A: get your own order
curl -s 'https://target.example/api/orders/1001' \
  -H 'Authorization: Bearer TOKEN_A' -o /tmp/a_order.json
cat /tmp/a_order.json | head -5

# As user B: request A's order with B's token (horizontal IDOR)
curl -s 'https://target.example/api/orders/1001' \
  -H 'Authorization: Bearer TOKEN_B' -o /tmp/b_order.json -w '%{http_code}\n'
diff /tmp/a_order.json /tmp/b_order.json && echo "IDOR CONFIRMED: B read A's order"

# IDOR variants to try per endpoint:
# - Increment/decrement the ID (1001 -> 1002, 1000)
# - Swap UUIDs between your two accounts' objects
# - Try ID 0, -1, null, and very large numbers
# - Try the ID in a different parameter (body vs path vs query)
```

Test reads first, then writes: a read IDOR that also allows PUT or
DELETE is a bigger finding. But writes change other users' data, so get
the read proof first and clear write tests with the test lead.

## 2. Vertical and function-level tests

```bash
# Vertical: low-privilege token against admin endpoints
curl -s 'https://target.example/api/admin/users' \
  -H 'Authorization: Bearer TOKEN_A' -o /tmp/admin_try.json -w '%{http_code}\n'
head -c 300 /tmp/admin_try.json; echo

# Function-level: does the low role see admin functions in the UI/API docs
# that the API then allows?
for ep in /api/admin/config /api/admin/audit /api/users/all; do
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    -H 'Authorization: Bearer TOKEN_A' "https://target.example$ep")
  echo "$ep -> $code"
done

# Method-based: the GET is protected but the PUT is not (or vice versa)
curl -s -X PUT 'https://target.example/api/users/1002/role' \
  -H 'Authorization: Bearer TOKEN_A' -H 'Content-Type: application/json' \
  -d '{"role":"admin"}' -w '%{http_code}\n' -o /dev/null
```

Function-level gaps often hide behind UI hiding: the button is invisible
to low roles but the endpoint answers anyway. Enumerate endpoints from
the admin's traffic or the API docs, then test each with the low token.

## 3. Multi-account methodology

```bash
# Keep three token files and a helper for quick switching
# /tmp/token_low_a, /tmp/token_low_b, /tmp/token_admin
api() {  # usage: api <tokenfile> <method> <path> [data]
  local tok=$1 method=$2 path=$3 data=$4
  if [ -n "$data" ]; then
    curl -s -X "$method" "https://target.example$path" \
      -H "Authorization: Bearer $(cat $tok)" \
      -H 'Content-Type: application/json' -d "$data"
  else
    curl -s -X "$method" "https://target.example$path" \
      -H "Authorization: Bearer $(cat $tok)"
  fi
}
api /tmp/token_low_b GET /api/orders/1001 | head -c 300
```

The helper keeps the A/B/admin comparisons fast and consistent. Every
authz test is a comparison: same request, different token, different
result expected. When the results are the same, you have a finding.

## Edge cases

- IDs are unguessable UUIDs. IDOR still matters if UUIDs leak (in
  responses, exports, shared links); test with the leaked values, not
  brute force.
- The API returns 200 with an error body instead of 403. Read the body;
  a 200 that says "access denied" is still denied, but a 200 with the
  data is the finding.
- Authz differs between read and write. Test every method on every
  object endpoint; partial protection is common.
- Tenant isolation is the model. Test cross-tenant access with the same
  rigor; tenant IDOR is usually critical.

## Escalation

- IDOR confirmed with read access: demonstrate the data exposure
  clearly, then ask before testing writes on other users' objects.
- Mass IDOR (enumerate all objects): do not scrape the whole dataset;
  prove with two objects and describe the enumeration scenario.
- Authz is consistently broken: recommend the fix pattern (server-side
  ownership checks on every object access) once, and reference it from
  each finding instead of repeating it.

## Detection and defender view

Defenders see authz testing as odd access patterns: one token touching
many object IDs, low-privilege tokens hitting admin paths, and ID
sequences that no normal user would request. Good detection is
per-user access analytics. The defense is architectural: check
ownership and role on every request, server-side, with no exceptions;
deny by default; and test with multiple accounts in CI, not just in
pentests.

## Key references

- OWASP API Security Top 10 2023: API1 Broken Object Level
  Authorization, API5 Broken Function Level Authorization.
- CWE-639 (Authorization Bypass Through User-Controlled Key).
- CWE-862 (Missing Authorization).
- PortSwigger Web Security Academy: Access control labs.
