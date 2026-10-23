---
name: gdpr-engineering
description: Use when building or reviewing systems for GDPR compliance
  from the engineering side. Covers data mapping, lawful basis in code,
  retention automation, and data subject rights implementation. Also use
  when an audit asks how the codebase enforces privacy requirements, or
  when designing a new service that handles EU personal data.
version: 1.0.0
domain: privacy
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding, dsr-automation, privacy-impact-assessment]
tools:
  - name: Python
    version: 3.12
  - name: PostgreSQL
    version: 17
---

GDPR is not just legal text; it compiles into engineering work: data
inventories, retention jobs, export and deletion endpoints, and consent
checks in request paths. This skill covers the engineering
implementation for teams building or reviewing systems that handle EU
personal data: what to build, how to verify it, and the common gaps
audits find.

## Quick Workflow

1. Map personal data: what you store, where, why, and under which
   lawful basis, as a living inventory.
2. Encode the lawful basis per processing purpose in config, not in
   developers' heads.
3. Implement retention: automatic deletion or anonymization when the
   purpose expires.
4. Build data subject rights: access, rectification, erasure,
   portability, and objection, as working endpoints.
5. Add consent checks to the request path where consent is the basis.
6. Handle cross border transfers: know where data lives and under
   what mechanism it moves.
7. Log processing activities in a way the DPO can actually query.
8. Test the whole loop with a synthetic subject before the audit.

## 1. Data inventory

```bash
# Start the inventory as code: a registry every service reports to
cat > /tmp/privacy/data_registry.yaml << 'YAML'
datasets:
  - name: users
    store: postgres://db:5432/app.users
    fields: [email, name, created_at]
    basis: contract
    retention_days: 2555   # 7 years for tax records
  - name: analytics_events
    store: clickhouse.events
    fields: [user_id, page, ts]
    basis: consent
    retention_days: 395
YAML
python3 -c "import yaml,sys; print('registry loads:', bool(yaml.safe_load(open('/tmp/privacy/data_registry.yaml'))))" 2>/dev/null || echo "keep the registry in version control and review it quarterly"
```

```bash
# Find personal data the registry missed: scan schemas for PII patterns
psql "$DB_URL" -c "\d users" | grep -i -E "email|phone|name|address|dob" | head -20
# Every match needs a registry entry with basis and retention
```

## 2. Retention automation

```python
#!/usr/bin/env python3
"""Retention job: deletes or anonymizes expired personal data (dry run first)."""
import datetime

REGISTRY = {
    "analytics_events": {"retention_days": 395, "action": "delete"},
    "marketing_contacts": {"retention_days": 730, "action": "anonymize"},
}

def expired(table, retention_days):
    cutoff = datetime.date.today() - datetime.timedelta(days=retention_days)
    return f"DELETE FROM {table} WHERE created_at < '{cutoff}'  -- DRY RUN"

for table, cfg in REGISTRY.items():
    print(expired(table, cfg["retention_days"]))
# Run for real only with: reviewed SQL, backups, and an audit log entry
```

```bash
# Verify retention actually ran: count rows older than the cutoff
psql "$DB_URL" -c "SELECT count(*) FROM analytics_events WHERE created_at < now() - interval '395 days';"
# Non zero means the job failed; alert, do not silently retry forever
```

## 3. Rights endpoints (see dsr-automation for depth)

```bash
# Smoke test the access and deletion endpoints with a synthetic user
curl -s 'https://app.example/api/privacy/export' \
  -H "Authorization: Bearer $SYNTH_TOKEN" | head -c 300
curl -s -X POST 'https://app.example/api/privacy/erase' \
  -H "Authorization: Bearer $SYNTH_TOKEN" \
  -H 'Content-Type: application/json' -d '{"confirm":true}' | head -c 200
# Then verify: export contains the user's data, erase removes it everywhere
# including backups within the documented window
```

## Edge cases

- Backups contain data the user asked to delete. Document the backup
  retention window and the process that purges on restore; regulators
  accept this if it is real and documented.
- Legal holds conflict with erasure. Keep the hold register; a hold
  overrides erasure but must be specific and time boxed.
- Third party processors hold copies. Erasure must propagate via
  contract and API; verify, do not assume.
- The lawful basis changes (consent withdrawn). The system must stop
  the processing, not just record the withdrawal.

## Escalation

- Inventory incomplete: run the PII scan across all stores and treat
  unknown data as in scope until classified.
- Retention job failing silently: page the owning team; every day of
  failure is over retention.
- Cross border transfer without a mechanism: escalate to legal
  immediately; engineering cannot fix this with code.

## Detection and defender view

For privacy engineering, "detection" means the controls that catch
non compliance: retention job monitors, registry drift alerts (new
table with email column but no registry entry), and synthetic subject
tests that exercise rights end to end. Auditors look for exactly
these: a registry that matches reality, retention that provably
runs, and rights that work. The durable practice is privacy as code:
reviewed, tested, and monitored like any other correctness property.

## Key references

- GDPR Articles 5, 6, 17, 25: principles, basis, erasure, by design.
- EDPB guidance on data subject rights.
- Related skills: dsr-automation, privacy-impact-assessment.
