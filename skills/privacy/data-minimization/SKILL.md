---
name: data-minimization
description: Use when reducing personal data collection and storage in
  a system you build or review. Covers purpose mapping, field level
  audits, replacing identifiers with pseudonyms, and safe defaults.
  Also use when a feature asks for more data than it needs, or when
  preparing for a privacy review.
version: 1.0.0
domain: privacy
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [gdpr-engineering, secure-coding, privacy-threat-model]
tools:
  - name: Python
    version: 3.12
  - name: PostgreSQL
    version: 17
---

Data minimization means collecting only what the purpose needs, and
keeping it only as long as needed. It is the cheapest privacy control
there is: data you never collect cannot leak. This skill covers the
engineering practice: auditing what you collect, challenging each
field, and replacing identifying data with less risky alternatives.

## Quick Workflow

1. List every personal data field the feature collects, with the
   purpose each serves.
2. Challenge each field: what breaks if we do not collect it.
3. Drop or make optional everything without a solid answer.
4. Replace direct identifiers with pseudonyms where identity is not
   needed.
5. Reduce precision: coarse location instead of GPS, birth year
   instead of full date.
6. Set the shortest retention the purpose allows, with automatic
   deletion.
7. Review logs and analytics for accidental PII collection.
8. Re audit on every feature change; minimization rots without
   maintenance.

## 1. Field audit

```bash
# Dump the fields a form or API actually collects
curl -s 'https://app.example/api/signup/schema' | python3 -m json.tool | head -40
# For each field ask: purpose? basis? who decided? when reviewed?
```

```python
#!/usr/bin/env python3
"""Field audit report: flags fields without a documented purpose."""
FIELDS = [
    ("email", "account identity", True),
    ("phone", "2FA delivery", True),
    ("date_of_birth", "none documented", False),
    ("full_address", "none documented", False),
    ("device_model", "debugging", True),
]
for name, purpose, ok in FIELDS:
    status = "KEEP" if ok else "DROP OR JUSTIFY"
    print(f"{name:15s} purpose: {purpose:20s} -> {status}")
```

## 2. Pseudonymization and precision reduction

```python
#!/usr/bin/env python3
"""Replace direct identifiers with pseudonyms (one way, keyed)."""
import hmac, hashlib

PEPPER = b"server-side-secret-from-vault"  # never hardcode in real code

def pseudonym(value: str) -> str:
    return hmac.new(PEPPER, value.encode(), hashlib.sha256).hexdigest()[:32]

print(pseudonym("user@example.com"))
# Store the pseudonym where identity is not needed (analytics, logs)
# Keep the mapping only where the purpose requires re identification
```

```bash
# Precision reduction examples in SQL migrations
# GPS (lat/lon float) -> city level: store geohash prefix only
# full DOB -> birth year for age gating
# exact timestamp -> hour bucket for analytics
echo "each reduction is a migration; plan backfill carefully"
```

```bash
# Hunt accidental PII in logs: the classic minimization failure
grep -rhoE "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" /var/log/app/ 2>/dev/null | sort -u | head -10
# Any hit means emails are logged; fix the logging, then purge
```

## Edge cases

- Product insists the data "might be useful later". Future use is not
  a purpose; collect it when the purpose exists.
- Pseudonymized data plus auxiliary data re identifies people.
  Treat pseudonymous data as personal data, because legally it is.
- Logs need some detail for debugging. Sample, redact, and shorten
  retention instead of logging everything.
- ML features want raw data. Use the minimized features; model
  quality rarely needs the full PII.

## Escalation

- A field is legally required (tax, KYC). Document the requirement;
  minimization does not override law.
- Deleting historical data breaks analytics. Aggregate first, then
  delete the raw rows; keep the aggregates.
- The audit finds systemic over collection. Propose a phased
  reduction plan with dates, not a big bang.

## Detection and defender view

Detect minimization drift with schema change reviews (new PII column
needs a purpose note), log scanners for PII patterns, and periodic
field audits against the registry. The privacy review gate on new
features is the human control; the scanners are the safety net. The
durable habit is asking "why do we need this" at design time, when
saying no is cheap.

## Key references

- GDPR Article 5(1)(c): data minimization principle.
- NIST SP 800-122: PII handling guidance.
- Related skills: gdpr-engineering, anonymization-techniques.
