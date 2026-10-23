---
name: consent-management
description: Use when implementing or auditing consent for data
  processing: cookie banners, app permissions, and marketing opt ins.
  Covers consent records, withdrawal handling, dark pattern avoidance,
  and verifying that backend processing respects the choice. Also use
  when a consent banner needs to be more than theater.
version: 1.0.0
domain: privacy
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [gdpr-engineering, privacy-threat-model]
tools:
  - name: Python
    version: 3.12
---

Consent is only valid if it is freely given, specific, informed, and
revocable: a pre ticked banner that ignores "reject" fails all four.
This skill covers the engineering of real consent: capturing the
choice, storing the record, enforcing it in every processing path,
and honoring withdrawal promptly. It applies to cookies, app
permissions, and marketing opt ins alike.

## Quick Workflow

1. List every processing purpose that relies on consent, separately.
2. Design the choice: granular per purpose, accept and reject equally
   easy, no dark patterns.
3. Store a consent record: who, when, what text version, which
   purposes, and the proof.
4. Gate every processing path on the record: no consent, no
   processing, including third party SDKs.
5. Make withdrawal as easy as giving: one click, immediate effect.
6. Propagate withdrawal to processors and delete or stop the data.
7. Re prompt when purposes change; old consent does not cover new
   uses.
8. Audit regularly: synthetic users accepting, rejecting, and
   withdrawing.

## 1. Consent record and gating

```python
#!/usr/bin/env python3
"""Consent record model and request gating (illustrative)."""
import datetime

record = {
    "subject_id": "user_123",
    "purposes": {"analytics": True, "marketing": False, "personalization": True},
    "policy_version": "2026-09",
    "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "method": "banner_v3",
}

def allowed(record, purpose):
    return bool(record["purposes"].get(purpose, False))

# Gate in the request path, not just the UI
for purpose in ["analytics", "marketing"]:
    print(purpose, "->", "process" if allowed(record, purpose) else "BLOCK")
```

```bash
# Verify the banner actually blocks: reject all, then check network
# 1. fresh profile, open the site, click "reject all"
# 2. capture requests for 60 seconds
# 3. fail if any analytics or ad request fired
echo "test: tcpdump or devtools, filter the vendor domains, expect silence"
```

## 2. Withdrawal propagation

```bash
# Withdrawal must reach every processor, not just your database
# Checklist per processor: API to delete/suppress, confirmation receipt,
# documented SLA, and a retry queue for failures
python3 - << 'PY'
processors = ["email_vendor", "analytics_vendor", "ad_platform"]
for p in processors:
    print(f"[ ] {p}: suppression API wired, tested, monitored")
PY
```

## Edge cases

- Legitimate interest is claimed instead of consent. That is a legal
  call; engineering still needs the per purpose flag either way.
- The app ships with SDKs that phone home on launch. Consent cannot
  be valid if collection starts before the choice; delay SDK init.
- Children or special category data. Higher bar; get legal involved
  before designing the flow.
- Consent records are personal data too. Minimize what the record
  holds and protect it like any PII.

## Escalation

- Vendor has no suppression API: escalate to procurement and legal;
  you cannot honor withdrawal without it.
- Dark patterns mandated by growth: document the regulatory risk in
  writing; patterns like roach motel consent are enforcement bait.
- Cross device consent: define the identity resolution carefully or
  keep consent per device.

## Detection and defender view

Detect consent failures with synthetic tests (reject all then sniff),
SDK inventories that flag new network calls, and record audits that
check coverage. Regulators detect the same way: they click reject and
watch the traffic. The durable design treats consent as a distributed
systems problem: one record, enforced everywhere, with withdrawal
propagated like any other critical state change.

## Key references

- GDPR Article 7: conditions for consent.
- EDPB guidance on consent and dark patterns.
- Related skills: gdpr-engineering, dsr-automation.
