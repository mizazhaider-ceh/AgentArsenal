---
name: api-discovery
description: Use when mapping an API's full attack surface before security
  testing on an authorized engagement. Covers finding undocumented
  endpoints, version enumeration, GraphQL introspection, and documentation
  discovery. Use when starting API testing, when the provided docs look
  incomplete, when hunting shadow or deprecated endpoints, or when
  building the endpoint inventory for fuzzing and authz phases.
version: 1.0.0
domain: api
lifecycle: stable
last_verified: 2026-10-23
parent: api-security-testing
requires: [api-security-testing]
extends: []
relates: [recon-active, web-sqli]
tools:
  - name: ffuf
    version: 2.1
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
---

API discovery finds the endpoints the documentation forgot: old versions,
debug routes, shadow APIs, and the methods nobody admitted to. This skill
covers systematic discovery on authorized engagements: documentation
hunting, wordlist fuzzing, version enumeration, and GraphQL
introspection. The inventory it produces feeds rest-fuzzing and
authz-testing; undiscovered endpoints are untested endpoints.

## Quick Workflow

1. Collect every documented endpoint and the API versioning scheme.
2. Hunt for documentation: OpenAPI specs, GraphQL schemas, Postman
   collections left exposed.
3. Fuzz for undocumented paths with API-focused wordlists.
4. Enumerate versions: v1, v2, beta, internal, legacy.
5. Introspect GraphQL where present.
6. Merge everything into one endpoint inventory with methods.
7. Hand the inventory to the fuzzing and authz phases.

## 1. Documentation hunting

```bash
# Common documentation locations
for p in /openapi.json /swagger.json /swagger.yaml /api-docs \
         /graphql /graphiql /playground /api/swagger.json; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://target.example$p")
  [ "$code" = "200" ] && echo "FOUND: $p"
done

# Save any spec found; it becomes the test plan
curl -s https://target.example/openapi.json -o /tmp/openapi.json
python3 -c "
import json
spec = json.load(open('/tmp/openapi.json'))
print('endpoints:', len(spec.get('paths', {})))
for p in list(spec.get('paths', {}))[:10]: print(' ', p)
"

# JavaScript bundles reference endpoints the docs omit
curl -s https://target.example/static/app.js | grep -o -E '\"/api/[^\"]*\"' \
  | sort -u > /tmp/js_endpoints.txt
wc -l /tmp/js_endpoints.txt
```

An exposed spec in production is a finding by itself (information
disclosure), and it is also your test plan. Save it before it gets
removed mid-test.

## 2. Path and version fuzzing

```bash
# API-focused wordlist fuzzing
ffuf -u 'https://target.example/api/FUZZ' \
  -H 'Authorization: Bearer TOKEN' \
  -w /usr/share/wordlists/seclists/Discovery/Web-Content/api-actions.txt \
  -mc 200,201,204,301,302,400,401,403 -o /tmp/api_fuzz.json

# Version enumeration: old versions keep old vulnerabilities
for v in v1 v2 v3 beta internal legacy test dev; do
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    -H 'Authorization: Bearer TOKEN' "https://target.example/api/$v/users")
  echo "/api/$v/users -> $code"
done

# Method discovery per endpoint (documented GET may hide a working DELETE)
```

Old versions are the prize: v1 often lacks the authz checks v2 added.
Test every live version with the same rigor; "deprecated" without
removal is still attack surface.

## 3. GraphQL introspection

```bash
# Introspection query: dumps the whole schema when enabled
curl -s -X POST 'https://target.example/graphql' \
  -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
  -d '{"query":"{__schema{queryType{name}mutationType{name}}}"}' \
  | head -c 500; echo

# Full schema dump for offline review (when introspection is on)
python3 - <<'EOF'
import json, urllib.request
q = {"query": "{__schema{types{name fields{name}}}}"}
req = urllib.request.Request("https://target.example/graphql",
    data=json.dumps(q).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer TOKEN"})
print(urllib.request.urlopen(req, timeout=15).read()[:300])
EOF
```

Introspection enabled in production is both a finding and a test plan:
it lists every query and mutation. When it is disabled, fall back to
suggestions, error messages, and JS bundle greps for field names.

## Edge cases

- The API needs signed requests. Fuzz through Burp with the signing
  handled, or discovery stalls at 401s.
- Everything returns 200 with the same body. The API may route unknown
  paths to a default handler; compare body hashes, not status codes.
- The inventory keeps growing. Time-box discovery, freeze the list,
  and let testing findings reopen it.
- WebSocket or gRPC endpoints exist. They need their own discovery
  (protocol-aware tools); note them and schedule the follow-up.

## Escalation

- Shadow endpoints found serving production data: report them as a
  priority finding; undocumented plus production is the worst
  combination.
- You need the backend source view: ask the client for the route table
  to diff against your discovered list; the diff is the shadow API.
- Discovery is blocked by aggressive WAF: note the coverage gap and
  work from the documented surface plus JS references.

## Detection and defender view

Defenders see API discovery as fuzzing bursts against /api paths, 404
storms with API wordlists, and introspection queries. It is
distinguishable from normal use and worth alerting on. Defenses are not
exposing specs and introspection in production, removing dead versions,
and monitoring for enumeration patterns. The durable fix is knowing
your own API inventory better than the attacker does.

## Key references

- OWASP API Security Top 10 2023: API9 Improper Inventory Management.
- CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- OWASP Testing Guide: API testing sections.
