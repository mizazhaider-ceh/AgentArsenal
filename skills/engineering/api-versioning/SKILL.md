---
name: api-versioning
description: Use when designing or reviewing API versioning strategy.
  Covers URL vs header versioning, breaking change policy,
  deprecation process, and contract testing. Also use when an API
  change risks breaking clients or when version sprawl needs cleanup.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [rest-api-design, api-security-testing, openapi-security-review]
tools:
  - name: Python
    version: 3.12
---

API versioning is a promise to clients: what you built against keeps
working. This skill covers doing it well: choosing the versioning
scheme, defining what breaks a version, running deprecation properly,
and testing contracts. It prevents the slow breakage that erodes
trust in a platform.

## Quick Workflow

1. Pick one scheme and document it: URL path (/v1) or header based.
2. Define breaking vs non breaking changes in writing.
3. Version the OpenAPI contract alongside the code.
4. Run contract tests in CI: the implementation must match the
   published version.
5. Deprecate with notice: headers, docs, and a sunset date, never
   silent removal.
6. Monitor version usage: know who is on what before you retire.
7. Support N and N-1 during transitions; plan the capacity.
8. Sunset cleanly: remove the code after the date, confirm no
   traffic.

## 1. Scheme and breaking rules

```bash
# Document the scheme in the API guide:
# - URL versioning: /api/v1/orders (simple, visible, cache friendly)
# - header versioning: Accept: application/vnd.api.v2+json (clean URLs)
# Pick one per API; mixing confuses clients and tooling
echo "record the choice and the rationale in the API standards doc"
```

```python
#!/usr/bin/env python3
"""Breaking change classifier for API diffs."""
BREAKING = ["remove field", "rename field", "change type",
            "remove endpoint", "require new header", "change auth"]
SAFE = ["add optional field", "add endpoint", "add enum value",
        "loosen validation"]

def classify(change):
    c = change.lower()
    if any(b in c for b in BREAKING):
        return "BREAKING -> new version"
    if any(s in c for s in SAFE):
        return "safe -> same version"
    return "unclear -> review"

for ch in ["remove field 'nickname'", "add optional field 'avatar'",
           "change type of 'id' to string"]:
    print(f"{ch:35s} {classify(ch)}")
```

## 2. Deprecation and contract tests

```bash
# Deprecation headers on old versions (inform, do not just log)
# Sunset: <http-date>; Deprecation: true; Link: <successor>
curl -s -i 'https://api.example/v1/orders' | grep -i -E "deprecation|sunset" | head -5
```

```bash
# Contract test in CI: does /v1 still match openapi-v1.yaml
# (schemathesis or dredd as tooling; fail the build on drift)
echo "gate: contract test runs on every PR touching the API"
```

## Edge cases

- Internal clients break anyway. Versioning does not replace
  communication; announce to internal consumers too.
- The version is in the URL but auth differs per version. Keep
  security policy version independent or document the matrix.
- GraphQL or gRPC instead of REST. The principles transfer:
  deprecate fields, evolve schemas, test contracts.

## Escalation

- Breaking change shipped without a version bump: assess client
  impact, consider a rollback, and fix the CI gate that missed it.
- Version sprawl (v1 through v7 live): measure usage per version
  and run a retirement program with dates.

## Detection and defender view

Versioning misuse looks like clients pinned to ancient versions
with known vulnerabilities, and sunset dates that pass without
removal. Security teams care because old versions keep old flaws
alive: each supported version is attack surface. The durable
practice is few versions, enforced sunsets, and security patches
that reach every live version.

## Key references

- Semantic Versioning (semver.org) adapted for APIs.
- IETF draft on API deprecation headers.
- Related skills: rest-api-design, openapi-security-review.
