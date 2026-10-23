---
name: historian-security
description: Use when assessing a process historian on an authorized OT
  engagement. Covers historian architecture, the IT to OT data path,
  access control on trend and alarm data, and injection of false data.
  Also use when the historian replica in the DMZ is the bridge you need
  to review.
version: 1.0.0
domain: ics-scada
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [scada-network-seg, ics-incident-response, log-forensics]
tools:
  - name: Python
    version: 3.12
  - name: nmap
    version: 7.98
---

The historian records everything the process does: years of tag
values, alarms, and events. It usually sits at the OT to IT boundary,
which makes it both a high value target and the most attacked bridge.
This skill covers authorized assessment: mapping the historian data
flows, testing access controls, and checking the integrity of the data
everyone trusts for decisions and forensics.

## Quick Workflow

1. Map the historian architecture: collectors in OT, main historian,
   and the replica or interface node facing IT.
2. Trace every data flow across the boundary and check its direction.
3. Test authentication on historian interfaces: web, API, and database
   ports.
4. Check authorization: can a low privilege user read restricted tags
   or acknowledge alarms.
5. Assess data integrity: can values be backfilled or modified without
   an audit trail.
6. Review the replication path for bypasses around the DMZ design.
7. Check backup and retention: are they protected and sufficient for
   incident investigation.
8. Report with the exact paths data and users can take.

## 1. Architecture and access review

```bash
# Identify historian services on the authorized hosts (gentle)
sudo nmap -sV -p 5450,5457,1433,5432 -T2 --max-retries 1 \
  192.168.20.10 -oN /tmp/historian_svc.txt
cat /tmp/historian_svc.txt
# 5450/5457: common historian ports; 1433/5432: SQL backends
```

```bash
# Test the web/API interface authentication
curl -s -o /dev/null -w "%{http_code}\n" \
  'https://historian-dmz.example/api/tags'
# 200 without credentials = anonymous access to process data
curl -s -X POST 'https://historian-dmz.example/api/login' \
  -H 'Content-Type: application/json' \
  -d '{"user":"admin","password":"admin"}' | head -c 200
# Default credentials on historians are depressingly common
```

```python
#!/usr/bin/env python3
"""Tag authorization probe: can a low priv user read restricted tags?"""
import json, urllib.request

BASE = "https://historian-dmz.example/api"
TOKEN = "REPLACE_WITH_LOW_PRIV_TOKEN"
TAGS = ["plant/overview/production_rate", "plant/safety/esd_status",
        "plant/finance/cost_per_unit"]

def get(path):
    req = urllib.request.Request(BASE + path,
        headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, json.load(r)

for t in TAGS:
    try:
        status, data = get(f"/tags/{t}/current")
        print(f"{t}: HTTP {status} -> {'VISIBLE' if status == 200 else 'blocked'}")
    except Exception as e:  # noqa: BLE001
        print(f"{t}: error {e}")
```

## 2. Data integrity checks

```bash
# Can values be backfilled or edited? Check the audit trail design
# Ask operations or test on a lab tag:
# 1. write a test value with a past timestamp
# 2. check whether the historian flags it as manual/backfilled
# 3. check who can delete tag history
echo "integrity questions: backfill allowed? edits audited? deletes restricted?"
```

```bash
# Verify replication direction: the DMZ replica should never write to OT
# Check firewall rules for the replica host: established outbound from
# OT to DMZ is fine; DMZ initiated inbound to OT is a finding
sudo iptables -L -n -v | grep -E "192.168.10|192.168.20" | head -20
```

## Edge cases

- The historian is also the alarm manager. Alarm suppression or
  acknowledgment by unauthorized users is a safety relevant finding;
  handle it with operations, not just IT.
- Tag names reveal process details. Even read only anonymous access
  leaks the plant's layout; treat it as information disclosure.
- The database backend has its own credentials. Test those separately;
  the app layer auth may not cover direct DB access.
- Cloud historian sync exists. Review what leaves the site and under
  whose credentials.

## Escalation

- Anonymous access confirmed: demonstrate with a non sensitive tag,
  then stop; do not scrape the tag database.
- Write access found: test only a lab tag, announce it, and revert
  immediately.
- Replication bypass suspected: trace the actual packets rather than
  trusting the diagram.

## Detection and defender view

Defenders watch the historian for unusual read patterns (bulk tag
exports), logins from unexpected hosts, and backfill or edit
operations outside maintenance windows. They protect it with strong
authentication on every interface, role based tag authorization,
immutable audit trails for edits, and a replication design that cannot
be reversed. The historian is often the best forensic source in OT, so
its own integrity is worth defending.

## Key references

- NIST SP 800-82r3: historian placement and protection.
- IEC 62443-3-3: system security requirements for zones.
- MITRE ATT&CK ICS T0802 (Automated Collection): historian targeting.
