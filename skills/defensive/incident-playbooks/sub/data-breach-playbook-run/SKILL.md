---
name: data-breach-playbook-run
description: Use when data theft is confirmed or suspected and the data
  breach playbook must be executed. Covers determining what was taken,
  legal and notification obligations, evidence preservation, and
  customer communication support. Use when exfiltration is detected, when
  an attacker had database access, when a third party reports your data,
  or when running the tabletop version.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
parent: incident-playbooks
requires: [incident-response]
extends: []
relates: [incident-response, forensics-fundamentals]
tools:
  - name: Python
    version: 3.12
---

A data breach playbook runs alongside the technical response but answers
different questions: what was taken, who must be told, and by when. This
skill is the executable playbook: scoping the theft, preserving the
evidence lawyers need, meeting notification obligations, and supporting
honest communication. Legal drives the timeline here; technical findings
feed it.

## Quick Workflow

1. Confirm the theft: what evidence shows data left the environment.
2. Determine WHAT: data types, whose data, how many records.
3. Preserve evidence with legal hold in mind from the start.
4. Engage legal immediately: notification obligations depend on
   jurisdiction and data type.
5. Scope the access: how the attacker reached the data, for how long.
6. Support notification: factual content for the messages.
7. Run lessons learned with the breach lens.

## 1. Confirming and scoping the theft

```bash
# Evidence of exfiltration to gather:
# - Firewall/proxy logs: large transfers to external hosts
# - Database audit logs: bulk queries, dumps
# - Endpoint: archive tools (rar, 7z) run before transfer
# - Cloud: unusual download volumes from storage

# WHAT was taken (the question everything else depends on):
# - Data types: PII, credentials, financial, health, IP
# - Whose: customers, employees, which regions
# - How many: record counts, with the query that produced them
# - Sensitivity: encrypted? hashed? plaintext?

# Document the theft evidence like forensics: hashes, logs, queries,
# all preserved with chain of custody
```

"What was taken" is the hardest question and the most important: every
notification decision flows from it. Invest the analysis time here;
guessing wrong in either direction (over or under) has real costs.

## 2. Legal and notification track

```bash
# Engage legal BEFORE drafting any notification or public statement.
# Legal determines:
# - Which jurisdictions' breach laws apply (residence of the data subjects)
# - Notification deadlines (they vary: 72 hours is common in the EU)
# - What must be notified: regulators, individuals, both
# - Privilege: which investigation work product stays privileged

# Technical support to legal:
# - Factual timeline of the theft (no speculation in writing)
# - Record counts with methodology
# - Remediation status (what is fixed, what is in progress)

# Do NOT: notify customers without legal, discuss the breach on
# unprivileged channels, or speculate about attribution in writing
```

The notification clock starts at discovery or confirmation depending on
the jurisdiction; know which applies. Missing a deadline turns a breach
into a compliance failure too.

## 3. Communication support

```bash
# The technical team provides facts; comms and legal own the message.
# Facts to prepare:
# - What happened, in plain language, without jargon
# - What data was involved, specifically
# - What the organization did about it (containment, fixes)
# - What affected people should do (concrete steps)
# - Where to get help (dedicated contact, not the general line)

# Prepare for the questions: how, how many, why us, is it over,
# what are you doing to prevent repeats
```

Honest, specific communication beats vague reassurance: people forgive
breaches better than they forgive evasions. The technical team's job is
making sure every factual claim in the message is true.

## Edge cases

- The theft is suspected but unproven. Investigate as a breach (legal
  hold, scoping) while stating the status honestly; downgrade only on
  evidence.
- A third party reports your data (ransomware leak site, researcher).
  Treat the report as the detection; verify independently before
  acting on it.
- The data was encrypted by the attacker (ransomware). Theft plus
  encryption is the double extortion case; run both playbooks.
- The breach involves a processor or vendor. Their notification duties
  and yours interact; legal coordinates, technical verifies their
  claims.

## Escalation

- Regulators must be notified: legal files, technical provides the
  factual annex; keep the annex updated as the investigation refines
  the numbers.
- Law enforcement involvement: preserve evidence to their standard
  and coordinate through legal.
- The playbook timeline conflicts with the investigation: legal sets
  the notification deadline; the investigation prioritizes answering
  the notification questions first.

## Detection and defender view

The defender's preparation for this playbook: data inventory (knowing
what sensitive data lives where), egress monitoring that can answer
"what left," database audit logging, and practiced legal engagement.
The organizations that handle breaches well knew their data before the
incident; the ones that struggle discover their data during it.

## Key references

- NIST SP 800-61 (incident handling).
- GDPR Articles 33-34 (notification duties, EU reference point).
- Sector breach notification laws (jurisdiction-specific, via legal).
