---
name: openapi-security-review
description: Use when reviewing an OpenAPI specification for security
  issues on an authorized engagement. Covers contract vs
  implementation drift, auth scheme review, schema validation gaps,
  and finding hidden endpoints. Also use when the API docs are the
  starting point for a test.
version: 1.0.0
domain: api
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [api-security-testing, rest-api-design, api-versioning]
tools:
  - name: Python
    version: 3.12
---

The OpenAPI spec is the API's blueprint: reviewing it finds auth
gaps, unvalidated schemas, and endpoints the testers would otherwise
miss. This skill covers the review method for specs you are
authorized to assess: structure checks, security scheme analysis,
and using the spec to drive testing. Review the spec, then verify
against the live API.

## Quick Workflow

1. Get the spec: openapi.json or yaml, all versions in use.
2. Validate it parses and check the version coverage.
3. Review security schemes: what auth is defined and where it is
   required.
4. Find endpoints with no security: the first findings.
5. Check schemas: required fields, types, and constraints the
   implementation may ignore.
6. Diff against the live API: hidden endpoints not in the spec.
7. Generate tests from the spec: fuzz per the schemas.
8. Report spec issues and implementation drift separately.

## 1. Spec analysis

```bash
# Validate and summarize the spec
python3 - << 'PY'
import json
spec = json.load(open("/tmp/api/openapi.json"))
paths = spec["paths"]
print("paths:", len(paths))
open_paths = [p for p, ops in paths.items()
              for m, op in ops.items()
              if isinstance(op, dict) and "security" not in op
              and "security" not in spec]
print("operations without security:", len(open_paths))
for p in open_paths[:10]:
    print("  OPEN:", p)
PY
```

```bash
# Security scheme review: what is defined and how strong
python3 - << 'PY'
import json
spec = json.load(open("/tmp/api/openapi.json"))
sec = spec.get("components", {}).get("securitySchemes", {})
for name, s in sec.items():
    print(name, "->", s.get("type"), s.get("scheme"), s.get("in"))
print("check: is the scheme applied globally, and are weak schemes")
print("(basic auth, apiKey in query) actually used?")
PY
```

## 2. Drift and test generation

```bash
# Find live endpoints missing from the spec (authorized target)
# 1. list spec paths, 2. fuzz for unlisted paths, 3. diff
python3 - << 'PY'
import json
spec_paths = set(json.load(open("/tmp/api/openapi.json"))["paths"])
print(f"{len(spec_paths)} documented paths")
print("fuzz common admin/debug paths and compare: undocumented = drift")
PY
```

```bash
# Schema based fuzzing: generate invalid bodies per the schema
# (schemathesis as tooling against the authorized target)
# schemathesis run --checks all --hypothesis-max-examples=50 \
#   --base-url https://target.example /tmp/api/openapi.json
echo "failures: 500s, auth bypasses, and validation gaps"
```

## Edge cases

- The spec is outdated. Then the drift findings multiply; note the
  spec age as a root cause.
- Multiple spec versions live. Review each; v1 often keeps old
  flaws.
- The spec is huge. Automate the checks above; manual review the
  auth and the sensitive endpoints.

## Escalation

- Undocumented admin endpoints found: test them as priority; they
  are often less hardened.
- Spec shows weak auth: verify live before reporting; specs lie.

## Detection and defender view

Spec review is preventive: it catches design flaws before code.
Defenders keep the spec as a security artifact: reviewed on change,
tested against in CI, and used to generate the allowlist for the
API gateway. Drift between spec and reality is itself a finding,
because undocumented endpoints escape every other control.

## Key references

- OWASP API Security Top 10.
- OpenAPI Specification: security scheme objects.
- Related skills: api-security-testing, rest-api-design.
