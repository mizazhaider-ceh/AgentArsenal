---
name: rest-api-design
description: "Use when designing a REST API from scratch or reviewing an existing one: naming resources and URIs, choosing HTTP methods and status codes correctly, versioning the API, designing pagination, filtering, and sorting, writing consistent error envelopes, making operations idempotent, documenting with OpenAPI 3.1, adding rate limit headers, or choosing an authentication scheme. Use when the task mentions REST API design, endpoint naming, API versioning, pagination, error responses, or OpenAPI specs."
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [api-security-testing, secure-coding]
tools:
  - name: OpenAPI
    version: 3.1
  - name: curl
    version: 8.9
  - name: Python
    version: 3.12
---
A REST API is a contract: clients program against your URIs, methods, and
status codes for years, so design mistakes calcify fast. This skill covers
designing clean, predictable, secure REST APIs: resource modeling, method
and status code semantics, versioning, pagination and filtering, error
formats, idempotency, authentication, rate limiting, and documenting the
result in OpenAPI 3.1. Scope is HTTP API design; transport security and
auth internals live in api-security-testing.

## Quick Workflow

1. Model the domain as resources (nouns), not actions; nest only one
   level deep.
2. Assign each operation the correct HTTP method (GET/POST/PUT/PATCH/
   DELETE) and make safe methods truly safe.
3. Return the right status code for every outcome; never 200-with-error.
4. Version from day one (URL path is the pragmatic default).
5. Paginate every list endpoint with cursor or offset plus total counts.
6. Return errors in one consistent envelope with a machine-readable code.
7. Make retries safe with idempotency keys on mutating endpoints.
8. Require authentication on everything except explicit public routes;
   document the scheme.
9. Document the whole API in OpenAPI 3.1 and keep the spec in version
   control.
10. Review the design against the security checklist before shipping.

## 1. Resource naming

Nouns, plural, lowercase, hyphens for multi-word. No verbs in URIs (the
method is the verb). No trailing slashes as distinct resources.

```text
GET    /v1/users                 list users
POST   /v1/users                 create a user
GET    /v1/users/42              get user 42
PUT    /v1/users/42              replace user 42
PATCH  /v1/users/42              update fields of user 42
DELETE /v1/users/42              delete user 42

GET    /v1/users/42/orders       orders of user 42 (one nesting level)
POST   /v1/users/42/orders       create an order for user 42

# Actions that are not CRUD go under a sub-resource or a verb-noun RPC
POST   /v1/users/42/password-reset
POST   /v1/orders/99/cancel
```

```bash
# Smoke-test the naming with curl: predictable patterns should work
curl -s https://api.example.com/v1/users | head -c 200
curl -s -o /dev/null -w '%{http_code}\n' https://api.example.com/v1/users/42
```

## 2. Method semantics

- GET: read, safe (no side effects), idempotent, cacheable.
- POST: create, or trigger a non-idempotent action. Not safe, not
  idempotent by default.
- PUT: full replace of a resource at a known URI. Idempotent.
- PATCH: partial update. Idempotent if the patch document is.
- DELETE: remove. Idempotent (deleting twice has the same effect).
- HEAD/OPTIONS: metadata and CORS preflight.

```bash
# PUT is idempotent: sending it twice must not create two resources
curl -s -X PUT https://api.example.com/v1/users/42 \
  -H 'Content-Type: application/json' \
  -d '{"name":"Izaz","role":"student"}' | head -c 200

# PATCH for a partial update
curl -s -X PATCH https://api.example.com/v1/users/42 \
  -H 'Content-Type: application/json' \
  -d '{"role":"admin"}' | head -c 200
```

## 3. Status codes that mean what they say

```text
200 OK                    GET/PUT/PATCH/DELETE succeeded with a body
201 Created               POST created a resource (return it + Location header)
202 Accepted              async job queued (return a status URL)
204 No Content            success with nothing to return
400 Bad Request           client sent invalid data (validate first)
401 Unauthorized          missing or bad credentials
403 Forbidden             authenticated but not allowed
404 Not Found             resource does not exist (or must look that way)
405 Method Not Allowed    wrong method for this URI
409 Conflict              state conflict (duplicate unique key, version clash)
412 Precondition Failed   If-Match version check failed
415 Unsupported Media Type wrong Content-Type
422 Unprocessable Entity  valid JSON, failed business rules
429 Too Many Requests     rate limited (include Retry-After)
500 Internal Server Error server bug (log it, never leak internals)
503 Service Unavailable   overloaded or down (include Retry-After)
```

Rules: 401 means "who are you", 403 means "I know who you are, and no".
404 vs 403 on private resources: return 404 to avoid confirming existence
to attackers. Never return 200 with an error body; clients and monitors
key on the code.

## 4. Versioning

URL path versioning is the most debuggable and cache-friendly:

```text
https://api.example.com/v1/users
https://api.example.com/v2/users
```

Rules: never break v1 to fix v2; add fields freely (clients must ignore
unknown fields); remove or rename only in a new major version; announce
deprecation with a `Deprecation` header and a sunset date, and keep the
old version running through it.

```bash
curl -sI https://api.example.com/v1/users | grep -i '^deprecation:'
```

## 5. Pagination, filtering, sorting

Every list endpoint paginates. Cursor pagination for large or
real-time datasets; offset for small admin lists.

```text
# Cursor pagination (stable under inserts)
GET /v1/orders?limit=50&cursor=eyJpZCI6OTl9

# Response envelope
{
  "data": [ ... ],
  "pagination": {
    "limit": 50,
    "next_cursor": "eyJpZCI6NTB9",
    "has_more": true
  }
}

# Offset pagination (simple, fine under ~10k rows)
GET /v1/users?limit=20&offset=40
```

Filtering and sorting use query params with a documented allowlist:

```text
GET /v1/orders?status=shipped&status=paid&sort=-created_at&fields=id,total
```

Validate `sort` and `fields` against an allowlist; never interpolate
them into SQL. Cap `limit` (for example max 100) and default it (for
example 20).

## 6. Error envelope

One shape for every error, machine-readable code plus human message:

```json
{
  "error": {
    "code": "order_not_found",
    "message": "No order with id 99.",
    "details": { "order_id": 99 },
    "request_id": "req_8f3a2c",
    "documentation": "https://docs.example.com/errors#order_not_found"
  }
}
```

```bash
# Errors must carry the right status AND the envelope
curl -s -w '\nHTTP %{http_code}\n' https://api.example.com/v1/orders/99
```

Validation errors return 422 with per-field details:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "2 fields are invalid.",
    "details": {
      "fields": {
        "email": ["must be a valid email address"],
        "age": ["must be 13 or older"]
      }
    }
  }
}
```

Never leak stack traces, SQL, or internal paths in production errors.

## 7. Idempotency

Network retries must not double-charge or double-create. Accept an
`Idempotency-Key` header on POST/PUT/PATCH: store the key with the
response for 24 hours and replay the stored response on repeats.

```bash
KEY=$(uuidgen)
curl -s -X POST https://api.example.com/v1/orders \
  -H "Idempotency-Key: $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"item":"book","qty":1}'
# Retry with the SAME key after a timeout: must return the original
# order, not a second one
curl -s -X POST https://api.example.com/v1/orders \
  -H "Idempotency-Key: $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"item":"book","qty":1}'
```

Also support conditional writes with ETags to prevent lost updates:

```bash
# Get the version tag
curl -sI https://api.example.com/v1/users/42 | grep -i '^etag:'
# Update only if unchanged
curl -s -X PUT https://api.example.com/v1/users/42 \
  -H 'If-Match: "v7"' -H 'Content-Type: application/json' \
  -d '{"name":"Izaz"}'
# -> 412 Precondition Failed if someone else changed it first
```

## 8. Authentication and authorization

Default-deny: every endpoint requires auth unless explicitly public.
Bearer tokens over HTTPS are the standard for APIs:

```bash
curl -s https://api.example.com/v1/users/me \
  -H "Authorization: Bearer $TOKEN"
```

Design rules: short-lived access tokens plus refresh tokens (OAuth2) for
user-facing APIs; scoped API keys for service-to-service; scopes like
`orders:read` and `orders:write` so a leaked key has limited blast
radius; never accept credentials in query strings (they land in logs);
hash API keys at rest and show them only once at creation. Full auth
testing methodology lives in api-security-testing.

## 9. Rate limiting and headers

```text
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1750000060
```

Limit by authenticated identity, not just IP, so one bad tenant cannot
starve others. Document the limits; clients cannot back off correctly
against undocumented 429s.

## 10. OpenAPI 3.1 documentation

Keep the spec next to the code and generate clients and mocks from it:

```yaml
# openapi.yaml (excerpt)
openapi: 3.1.0
info:
  title: Example API
  version: 1.4.0
servers:
  - url: https://api.example.com/v1
paths:
  /users/{id}:
    get:
      operationId: getUser
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: integer }
      responses:
        '200':
          description: The user
          content:
            application/json:
              schema: { $ref: '#/components/schemas/User' }
        '404':
          description: Not found
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
```

```bash
# Validate the spec loads and is the right OpenAPI major version
python3 - <<'EOF'
import json
spec = json.load(open('openapi.json'))
assert spec['openapi'].startswith('3.1'), 'must be OpenAPI 3.1'
print('paths:', len(spec['paths']), '| version:', spec['info']['version'])
EOF
```

## Edge cases

- PATCH with JSON Merge Patch (`application/merge-patch+json`) vs JSON
  Patch (`application/json-patch+json`): pick one, document it, and set
  the right Content-Type; they behave differently on nulls and arrays.
- `204 No Content` must have no body; some frameworks sneak one in and
  break strict clients.
- Trailing slashes: decide once (`/users` canonical, `/users/` redirects
  with 301) and enforce it; two URIs for one resource splits caches.
- Timezones: accept and return ISO 8601 UTC only
  (`2026-10-23T07:00:00Z`); never local times without offsets.
- Large file uploads do not belong in JSON bodies; use multipart upload
  or signed-URL direct-to-storage flows with a completion callback.
- Enum values: document the full set; adding a value is backward
  compatible, removing one is a breaking change.
- Boolean query params (`?active=true`): define the accepted spellings
  once and reject the rest with 400.

## Escalation

- Clients report "random" 400s: log the raw request body on validation
  failure (server side, debug only) and compare against the documented
  schema; usually a Content-Type or charset mismatch.
- Pagination duplicates or skips rows: offset pagination on a table with
  concurrent inserts; switch to cursor pagination on a stable key.
- Version sprawl (v1 through v5 live): publish a sunset calendar, add
  `Deprecation` headers, and migrate internal clients first to prove the
  new version.
- Idempotency keys colliding across tenants: scope stored keys by tenant
  id, not just the key string.
- Still inconsistent: generate a contract test suite from the OpenAPI
  spec and run it in CI so drift fails the build, not the customer.

## Detection and defender view

For API designers, the defender view is abuse detection: an API that is
easy to enumerate or retry is easy to attack. Design in these signals:

```bash
# Enumeration probing: sequential IDs with high 404 rate from one client
grep -oP 'GET /v1/users/\d+.*?" 404' /var/log/nginx/access.log | wc -l

# Credential stuffing shape: bursts of 401/403 on auth endpoints
awk '$9 ~ /^401$/ {print $1}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head

# Clients ignoring rate limits: repeated 429s from the same key
grep ' 429 ' /var/log/nginx/access.log | grep -oP 'apikey=\K[^ ]+' \
  | sort | uniq -c | sort -rn | head
```

Design defenses: per-key rate limits, request quotas per plan, anomaly
alerts on 4xx spikes per client, audit logging of auth failures and
privilege changes, and never expose internal IDs that are enumerable
across tenants (use UUIDs or scoped IDs). Misuse signal: a client that
pages to the end of every collection daily is probably scraping.

## Key references

- OpenAPI 3.1 specification: https://spec.openapis.org/oas/v3.1.0
- RFC 9110 (HTTP Semantics): https://www.rfc-editor.org/rfc/rfc9110.html
- RFC 6585 (429 status): https://www.rfc-editor.org/rfc/rfc6585.html
- IETF Idempotency-Key draft: https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/
- OWASP API Security Top 10: https://owasp.org/API-Security/
- CWE-200 (Exposure of Sensitive Information): verbose errors, IDOR.
- CWE-770 (Allocation of Resources Without Limits): unpaginated lists,
  missing rate limits.
