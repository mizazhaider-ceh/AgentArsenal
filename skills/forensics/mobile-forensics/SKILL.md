---
name: mobile-forensics
description: Use when doing forensics on mobile devices in an
  authorized investigation. Covers acquisition methods, iOS and
  Android artifacts, app data analysis, and handling encryption.
  Also use when a case involves a phone and the evidence needs
  proper handling.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [forensics-fundamentals, disk-forensics, ios-basics, android-static]
tools:
  - name: Python
    version: 3.12
---

Mobile forensics recovers evidence from phones: messages, locations,
app data, and deleted content, within the limits of encryption and
authorization. This skill covers the method for authorized cases:
acquisition options, artifact locations, and analysis. Work only with
proper legal authority and handle the device to preserve evidence.

## Quick Workflow

1. Confirm legal authority and scope before touching the device.
2. Isolate the device: Faraday bag, airplane mode, do not power
   off a running encrypted phone lightly.
3. Choose acquisition: logical, file system, or physical, per
   device and authority.
4. Hash and document everything acquired.
5. Analyze system artifacts: calls, messages, locations, and
   network.
6. Analyze app data: the apps relevant to the case.
7. Recover deleted data where the method supports it.
8. Report with the method's limits stated.

## 1. Acquisition decisions

```bash
# Decision factors (no single tool does everything):
# - iOS: checkra1n devices allow physical; modern need agent based
# - Android: depends on model, patch level, and bootloader state
# - encrypted and locked: logical may be all you get; do not guess passcodes
#   beyond policy (attempt limits can wipe)
echo "record: method, tool version, hashes, and what was NOT captured"
```

```bash
# After acquisition, verify integrity immediately
sha256sum /evidence/phone_image.bin > /tmp/mf/hash.txt
# Work on copies; the original stays sealed
```

## 2. Artifact analysis

```bash
# iOS key artifacts (from a file system acquisition):
# - SMS: /private/var/mobile/Library/SMS/sms.db
# - calls: CallHistory.storedata
# - locations: /private/var/mobile/Library/Caches/com.apple.routined/
# - Safari: History.db, WhatsApp: ChatStorage.sqlite
find /tmp/mf/ios -name "sms.db" -o -name "History.db" 2>/dev/null | head
```

```bash
# Android key artifacts:
# - SMS: /data/data/com.android.providers.telephony/databases/mmssms.db
# - calls: calllog.db, contacts: contacts2.db
# - WhatsApp: msgstore.db (needs key), location: cached cells
find /tmp/mf/android -name "mmssms.db" -o -name "contacts2.db" 2>/dev/null | head
```

```bash
# Quick triage queries (SQLite)
sqlite3 /tmp/mf/ios/sms.db \
  "SELECT datetime(date/1000000000,'unixepoch'), address, text FROM message LIMIT 5;"
```

## Edge cases

- The phone is locked and encrypted. Without the passcode and
  legal authority to compel, acquisition stops; document it.
- Cloud backups exist. They are a separate source with separate
  authority; do not mix them silently.
- The device is damaged. Chip off is specialized lab work; scope
  it separately.

## Escalation

- Time sensitive (kidnapping, imminent threat): follow the
  emergency procedures; speed changes the method choice.
- Need app specific deep dive: analyze the app's database schema
  per the case needs.

## Detection and defender view

This skill is investigative; the defensive side is for device
owners: encryption on, strong passcodes, remote wipe, and backup
awareness. For investigators, the durable practices are legal
authority first, Faraday isolation, and honest reporting of what
each method can and cannot recover.

## Key references

- NIST SP 800-101: mobile forensics guidelines.
- Related skills: forensics-fundamentals, disk-forensics.
