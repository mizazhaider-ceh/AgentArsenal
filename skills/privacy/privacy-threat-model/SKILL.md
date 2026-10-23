---
name: privacy-threat-model
description: Use when building a privacy threat model for a system you
  design or review. Covers LINDDUN methodology, attacker profiling for
  privacy, linkability and identifiability analysis, and turning the
  model into engineering requirements. Also use when a security threat
  model misses the privacy harms.
version: 1.0.0
domain: privacy
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [privacy-impact-assessment, data-minimization, gdpr-engineering]
tools:
  - name: Python
    version: 3.12
---

Security threat models ask who breaks in; privacy threat models ask
who learns what about whom, including insiders and the system itself.
This skill gives the method: LINDDUN categories, privacy attacker
profiles, and data flow analysis that surfaces linkability and
identifiability risks a security review misses.

## Quick Workflow

1. Draw the data flow diagram: subjects, processes, data stores, and
   every flow of personal data.
2. Walk each element against LINDDUN: Linkability, Identifiability,
   Non-repudiation, Detectability, Disclosure, Unawareness, Non
   compliance.
3. Profile privacy attackers: the curious insider, the data broker,
   the state actor, and the system operator itself.
4. For each threat, name the harmed party: it is the data subject,
   not the company.
5. Rate by severity to the subject and likelihood given the
   architecture.
6. Turn threats into requirements: PETs, minimization, or process
   changes.
7. Assign owners and verify at implementation, not just on paper.
8. Revisit when data flows change; the model rots fast.

## 1. LINDDUN walkthrough

```bash
# LINDDUN categories with the question each asks:
# Linkability:      can two actions be tied to the same person?
# Identifiability:  can the person be named from this data?
# Non-repudiation:  can the subject deny it later (logs as evidence)?
# Detectability:    can an observer tell the subject did something?
# Disclosure:       is personal data exposed where it should not be?
# Unawareness:      does the subject know this processing happens?
# Non-compliance:   does this violate policy or law?
echo "walk every data flow and store against all seven"
```

```python
#!/usr/bin/env python3
"""Threat register: one row per (element, LINDDUN category) finding."""
threats = [
    ("analytics pipeline", "Linkability",
     "pseudonymous IDs stable across sessions allow profiling",
     "rotate IDs per session or add noise"),
    ("support tickets", "Identifiability",
     "agents see full history including unrelated past tickets",
     "scope ticket view to the current issue"),
    ("mobile SDK", "Unawareness",
     "location collected though the feature never shows a map",
     "remove collection or disclose and get consent"),
]
for el, cat, desc, mitigation in threats:
    print(f"[{cat}] {el}\n  threat: {desc}\n  fix: {mitigation}\n")
```

## 2. Data flow diagram essentials

```bash
# Minimum viable DFD for privacy:
# - every datastore labeled with whose data and how long
# - every flow labeled with the data categories it carries
# - trust boundaries where the operator changes (your backend vs vendor)
# - the subject's view: what they think happens vs what actually happens
echo "the gap between subject expectation and reality is where threats hide"
```

## Edge cases

- The system is internal only. Insiders are still privacy attackers;
  internal tools need the same analysis.
- Machine learning on the data. Models memorize; add extraction and
  membership inference to the threats.
- The threat model is done once and filed. Schedule the revisit with
  the data flow owner, or it becomes fiction.

## Escalation

- High severity threat with no cheap fix: propose the PET
  (differential-privacy, anonymization-techniques) or a product
  scope change, with the tradeoff explicit.
- Legal classification needed (is this personal data): involve
  counsel; engineers should not make that call alone.

## Detection and defender view

Privacy threats are detected by design review, not by SIEM: data
flow audits, schema change gates, and periodic re modeling. The
"defender" here is the design itself plus the DPO's oversight.
Durable practice: make the threat model a living doc owned by the
team, reviewed on every architecture change, with mitigations
tracked like security bugs.

## Key references

- LINDDUN methodology (linddun.org): categories and process.
- NIST Privacy Framework: threat modeling context.
- Related skills: privacy-impact-assessment, differential-privacy.
