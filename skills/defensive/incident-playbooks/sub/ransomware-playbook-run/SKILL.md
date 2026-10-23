---
name: ransomware-playbook-run
description: Use when ransomware is detected or suspected and the
  ransomware playbook must be executed. Covers immediate isolation,
  identifying the variant, protecting backups, and the recovery decision
  path. Use when files are being encrypted, when a ransom note appears,
  when EDR flags ransomware behavior, or when running the tabletop
  version of this scenario.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
parent: incident-playbooks
requires: [incident-playbooks]
extends: []
relates: [incident-response, forensics-fundamentals]
tools:
  - name: Python
    version: 3.12
  - name: YARA
    version: 4.5
---

Ransomware is the incident where minutes matter: every minute of spread
is more encrypted data. This skill is the executable playbook: the
ordered actions from detection through recovery, with the decisions
marked. Run it when ransomware is suspected; adapt the tempo to the
situation, but do not skip the order. Isolate first, think second,
recover third.

## Quick Workflow

1. Confirm it is ransomware: ransom note, mass file renames, or EDR
   verdict (do not wait for certainty if encryption is spreading).
2. Isolate affected hosts immediately: network quarantine, do not shut
   down yet.
3. Protect backups: disconnect and verify them before the attacker
   reaches them.
4. Identify the variant from the note, extensions, and EDR data.
5. Scope the spread: which hosts, which shares, which data.
6. Decide the recovery path: clean backups, rebuild, or decryptor.
7. Execute recovery and validate before reconnecting anything.

## 1. First 15 minutes

```bash
# 1. ISOLATE: EDR network quarantine on every affected host NOW
#    (one click per host; do all known-affected before investigating)

# 2. Do NOT shut down yet: memory holds keys and evidence
#    Exception: encryption spreading faster than you can quarantine ->
#    then shutdown is the lesser evil

# 3. Protect backups immediately:
#    - Disconnect backup storage from the network
#    - Verify backup integrity from an isolated console
#    - Check backup logs for attacker access in the last 30 days

# 4. Photograph/document the ransom note (it identifies the variant)
```

The ransom note is evidence and intelligence: it names the variant,
which determines whether a free decryptor exists and what the actor's
pattern is. Save it before anything overwrites it.

## 2. Variant identification and scoping

```bash
# Identify from: ransom note text, encrypted file extensions,
# EDR/AV verdict, and dropped tool names
# Check decryptor availability: No More Ransom project (nomoreransom.org)

# Scope the spread fast:
# - Query EDR for the ransomware process name across all hosts
# - Check file shares for fresh .encrypted extensions (or variant's)
# - Review backup logs: when did the attacker first touch backups?

# Preserve one encrypted sample plus the note for the investigation
# (and for decryptor testing later)
```

Variant identification changes the recovery math completely: a variant
with a free decryptor, a variant with flawed crypto, and a variant with
neither are three different incidents. Identify before deciding.

## 3. Recovery decision

```bash
# Decision tree:
# 1. Clean, tested, isolated backups exist -> restore (verify first)
# 2. Free decryptor exists for the variant -> test on samples, then run
# 3. Neither -> rebuild from gold images + data from clean sources
# 4. Ransom payment: leadership + legal decision ONLY; note that payment
#    funds crime, may be sanctioned, and often does not recover data

# Recovery order: domain controllers and identity first, then
# critical services, then the rest; validate each tier before the next
```

Never reconnect a recovered host to a network that still has infected
hosts. Recovery happens in an isolated recovery network, validated,
then reconnected in tiers. Re-infection during recovery is the classic
second disaster.

## Edge cases

- The ransomware is still spreading during recovery. Stop recovery,
  re-isolate, re-scope; the eradication was incomplete.
- Backups are encrypted too. The attacker did their homework; fall to
  decryptor or rebuild, and treat backup protection as the top lessons
  learned item.
- The variant is new with no decryptor. Focus on clean rebuild and the
  investigation; do not pay without the leadership and legal process.
- Data theft accompanied encryption (double extortion). The incident
  now includes a data breach playbook run in parallel.

## Escalation

- Leadership must decide on ransom: prepare the facts (recovery cost,
  downtime cost, decryptor status, legal constraints) and let them
  decide; never decide alone.
- Law enforcement notification: follow the jurisdiction's requirements
  and the organization's policy; preserve evidence accordingly.
- The playbook does not fit (novel variant): fall back to the general
  incident-response phases and update this playbook afterward.

## Detection and defender view

This playbook exists because prevention sometimes fails; the defender's
real investment is in the pieces that make this playbook short: tested
offline backups, network segmentation that slows spread, EDR with
behavioral ransomware detection, and practiced isolation drills. Every
ransomware incident should end with the question: which of these failed,
and what fixes it before next time.

## Key references

- NIST SP 800-61 (incident handling).
- CISA ransomware guide (variant and recovery guidance).
- No More Ransom project (decryptor availability).
