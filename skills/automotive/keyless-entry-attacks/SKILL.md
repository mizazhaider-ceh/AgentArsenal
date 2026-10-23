---
name: keyless-entry-attacks
description: Use when assessing keyless entry and immobilizer systems
  on vehicles you own or have authorization to test, in a lab setting.
  Covers relay attack concepts, rolling code analysis, and defensive
  review of key fob protocols. Also use when advising on theft
  resistant parking and storage practices.
version: 1.0.0
domain: automotive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [bluetooth-le, automotive-threat-model]
tools:
  - name: Python
    version: 3.12
---

Keyless entry theft is mostly relay attacks: amplify the fob's signal
from inside the house to the car outside, and the car thinks the key
is present. This skill covers authorized assessment concepts and
defensive review on your own vehicles: how the attacks work, how to
test defenses in the lab, and what actually stops them. Only test on
vehicles you own, parked securely, and never as a how to for theft.

## Quick Workflow

1. Identify the system: passive keyless entry, remote fob, or phone
   as key, and the frequency bands used.
2. Understand the protocol: challenge response, rolling codes, and
   distance bounding if present.
3. Assess relay exposure in the lab: does the car unlock when the fob
   signal is relayed from another room.
4. Review rolling code implementations for reuse and desync issues.
5. Check the immobilizer separately: starting the car is a higher bar
   than unlocking it.
6. Test the mitigations: motion sensors in fobs, UWB ranging, and PIN
   to drive.
7. Advise on storage: signal blocking pouches and parking practices.
8. Report the theft scenarios honestly with the tested mitigations.

## 1. Relay attack concept and lab test

```text
Relay attack: two radios bridge the distance.
  [fob in house] <---> [relay box A] <---> [relay box B] <---> [car]
  The car measures a valid response and unlocks; distance is not checked.
Defenses: ultra wideband (UWB) distance bounding, fob motion sensors
that sleep when still, PIN to drive.
```

```bash
# Lab assessment (your own vehicle, your own equipment):
# 1. place fob far from the car, confirm the car stays locked
# 2. with a lab relay setup, bridge the signal per your test plan
# 3. record: does it unlock? does it allow start? does the alarm trigger?
# 4. repeat with the fob in a signal blocking pouch (expect: stays locked)
echo "document each scenario; never test on other people's vehicles"
```

## 2. Rolling code review

```python
#!/usr/bin/env python3
"""Rolling code properties to check (protocol review, not capture)."""
checks = [
    "code never repeats within the window",
    "receiver resyncs within a bounded window only",
    "codes are not derived from a short predictable counter",
    "each button has independent sequence state",
    "jamming + record + replay (rolljam class) is mitigated",
]
for c in checks:
    print("[ ]", c)
```

## Edge cases

- The car uses UWB ranging. Relay is much harder; verify the UWB
  cannot be downgraded to plain RSSI.
- Phone as key over Bluetooth. Review the Bluetooth pairing and the
  app's key storage (see bluetooth-le).
- Aftermarket alarms and trackers add their own bypasses. Assess the
  whole system, not just the factory fob.

## Escalation

- Relay works including start: recommend PIN to drive, UWB upgrade
  path, and immediate storage mitigations.
- Cryptographic break suspected: this needs specialist RF and crypto
  review; do not publish attack details.

## Detection and defender view

Owners detect relay theft only after the fact, which is why
prevention matters: signal blocking storage, disabled keyless entry
where the car allows it, and PIN to drive. Manufacturers defend with
UWB distance bounding, sleeping fobs, and immobilizers that need
more than a relayed unlock. Insurers and police track theft
patterns to warn about vulnerable models.

## Key references

- Relay attack research literature (authorized lab studies).
- UWB distance bounding standards (IEEE 802.15.4z).
- CWE-294 (Authentication Bypass by Capture-replay).
