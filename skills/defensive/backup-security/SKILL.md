---
name: backup-security
description: Use when designing or auditing backup security. Covers
  the 3-2-1 rule, immutability against ransomware, encryption, and
  restore testing. Also use when ransomware readiness needs the
  recovery side verified, not just assumed.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ransomware-response, incident-response, linux-hardening]
tools:
  - name: Python
    version: 3.12
---

Backups are the last line against ransomware, and attackers know it:
they delete backups first. This skill covers making backups that
survive: the 3-2-1 rule, immutability, encryption, and restore
testing that proves recovery works. Design for the systems you own.

## Quick Workflow

1. Inventory what needs backing up: data, configs, and the
   procedures to rebuild.
2. Apply 3-2-1: three copies, two media types, one off site and
   offline or immutable.
3. Make backups immutable: object lock, air gap, or offline media
   the attacker cannot delete.
4. Encrypt backups with keys the production environment cannot
   reach.
5. Separate backup credentials: the backup admin is not the domain
   admin.
6. Test restores on a schedule: a backup you have not restored is
   a hope.
7. Monitor backup health: success, age, and integrity checks with
   alerts.
8. Document the recovery runbook with realistic time estimates.

## 1. Design checks

```bash
# Backup audit questions (answer per system):
# - where are the three copies, and which failures kill each?
# - can ransomware on the production network delete or encrypt them?
# - who holds the backup credentials, and are they separate?
# - when was the last successful restore test, and how long did it take?
echo "if the answer to 'can the attacker delete it' is yes, redesign"
```

```bash
# Immutability verification (example: S3 object lock)
# aws s3api get-object-lock-configuration --bucket backups
# Check: compliance mode, retention period, and that the backup role
# cannot override it
echo "verify: try deleting a locked object as the backup role -> must fail"
```

## 2. Restore testing

```bash
# Quarterly restore drill template:
# 1. pick a system at random (no warning to the restore team is better)
# 2. time the full restore to an isolated network
# 3. verify: data integrity, application starts, users can log in
# 4. record: time to restore, gaps found, runbook fixes
echo "track RTO vs actual; the gap is the finding"
```

```python
#!/usr/bin/env python3
"""Backup health dashboard sketch."""
backups = [
    {"system": "file server", "last_ok": "2026-10-22", "restore_test": "2026-07-15"},
    {"system": "database", "last_ok": "2026-10-23", "restore_test": "2026-10-01"},
    {"system": "configs", "last_ok": "2026-10-20", "restore_test": "never"},
]
for b in backups:
    flag = " <-- TEST RESTORE" if b["restore_test"] in ("never",) or b["restore_test"] < "2026-08-01" else ""
    print(f"{b['system']:12s} backup {b['last_ok']} restore {b['restore_test']}{flag}")
```

## Edge cases

- Backups are huge and immutable storage is costly. Tier: immutable
  for the critical set, standard for the rest, documented.
- The backup software itself is the target. Harden it like any
  privileged system and monitor its logs.
- Cloud backups in the same account as production. Separate
  account with no shared admin is the fix.

## Escalation

- Restore test fails: treat as an incident for the recovery
  capability; fix before the next test cycle.
- Ransomware active: protect the backup infrastructure first,
  then start recovery per the playbook.

## Detection and defender view

Backup attacks are detected through backup job failures, mass
deletion attempts on backup storage, and backup admin logins at odd
hours. Defenders alert on all of these and keep the backup network
isolated. The durable truth: ransomware defense is backup defense,
and untested backups are not backups.

## Key references

- NIST SP 800-34: contingency planning.
- 3-2-1 backup rule literature.
- Related skills: ransomware-response, incident-response.
