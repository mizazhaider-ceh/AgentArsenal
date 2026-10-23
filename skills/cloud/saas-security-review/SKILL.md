---
name: saas-security-review
description: Use when reviewing the security of a SaaS application your
  organization uses or builds. Covers SSO and SCIM, data residency,
  tenant isolation, admin controls, and offboarding. Also use when
  procurement asks for a security review before buying.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [cloud-security-basics, api-security-testing, oauth2-deep-dive]
tools:
  - name: Python
    version: 3.12
---

SaaS sprawl means your data lives in dozens of vendors' hands: the
review checks who can access it, how it is isolated, and what happens
when you leave. This skill covers the assessment for SaaS you buy or
build: authentication, tenant isolation, admin controls, and exit.
Review with a test tenant, never production data.

## Quick Workflow

1. Inventory the SaaS: what data it holds, who uses it, and the
   contract terms.
2. Check authentication: SSO enforced, MFA available, and password
   policies sane.
3. Test authorization: can one tenant's user see another tenant's
   data (test tenants only).
4. Review admin controls: role granularity and admin activity logs.
5. Check data handling: residency options, encryption, and backup.
6. Test offboarding: does deprovisioning actually revoke access.
7. Review integrations: OAuth grants and API keys the SaaS holds.
8. Assess exit: data export format and deletion on termination.

## 1. Auth and tenant isolation tests

```bash
# SSO enforcement check (test tenant)
# 1. try logging in with password when SSO is required -> must fail
# 2. check MFA enrollment options for admins
# 3. review session lifetimes and idle timeouts
echo "record: SSO enforced? MFA for admins? session timeout?"
```

```python
#!/usr/bin/env python3
"""Tenant isolation probe: two test tenants, cross access attempts."""
import urllib.request, json

def api(tenant_token, path):
    req = urllib.request.Request(
        f"https://saas.example/api/{path}",
        headers={"Authorization": f"Bearer {tenant_token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read()[:200]
    except Exception as e:  # noqa: BLE001
        return "error", str(e)[:100]

# Tenant B tries to read tenant A's object by guessing the ID
status, body = api("TENANT_B_TOKEN", "documents/doc_owned_by_tenant_a")
print("cross tenant read:", status, body[:100])
# 200 with data = broken tenant isolation (test tenants only)
```

## 2. Admin and lifecycle review

```bash
# Admin role granularity: can you make a billing-only admin, or is
# every admin a super admin?
# Offboarding test: disable a test user, then verify:
# - login fails immediately (not after token expiry)
# - API keys revoked
# - SCIM deprovisioning if configured
echo "test: disable user, then attempt login + API call within 5 minutes"
```

```bash
# Integration review: OAuth grants the SaaS holds to your other systems
# List authorized apps per user and per tenant; revoke the stale ones
echo "checklist: least privilege scopes, expiry, unused grant cleanup"
```

## Edge cases

- The vendor will not give a test tenant. Review docs and contracts;
  mark untested areas explicitly.
- SSO is "on the roadmap". Price the risk of password only auth in
  the meantime, especially for admins.
- Data residency cannot be guaranteed. Document where data actually
  lives vs where the contract says.

## Escalation

- Tenant isolation failure: emergency report to the vendor with
  the test tenant proof.
- No admin logs: you cannot detect misuse; recommend a vendor that
  provides them or compensating monitoring.

## Detection and defender view

Defenders monitor SaaS through SSO logs (impossible travel, new
devices), admin activity exports, and CASB alerts on unusual data
volumes. They defend with SSO plus MFA everywhere, least privilege
admin roles, and quarterly access reviews. The durable practice is
treating SaaS like your own infrastructure for identity and
offboarding, because to the attacker it is.

## Key references

- CWE-862 (Missing Authorization): tenant isolation gaps.
- CAIQ (Cloud Security Alliance): SaaS assessment questionnaire.
- OWASP API Security Top 10: integration review.
