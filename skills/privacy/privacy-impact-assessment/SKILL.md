---
name: privacy-impact-assessment
description: Use when running a privacy impact assessment (DPIA) for a
  new feature or system. Covers when a DPIA is required, the assessment
  steps, risk scoring, mitigation planning, and getting sign off. Also
  use when a launch is blocked pending privacy review.
version: 1.0.0
domain: privacy
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [privacy-threat-model, gdpr-engineering, data-minimization]
tools:
  - name: Python
    version: 3.12
---

A DPIA is the structured review before high risk processing starts:
describe it, assess necessity, find the risks, mitigate them, and get
sign off. This skill gives the practical method engineering teams can
actually run: the screening questions, the assessment template, and
how to reach a defensible decision without six months of process.

## Quick Workflow

1. Screen: does this need a DPIA (new tech, large scale, sensitive
   data, systematic monitoring, vulnerable subjects).
2. Describe the processing: purposes, data, flows, retention, and
   recipients, with a diagram.
3. Assess necessity and proportionality: is each element needed for
   the purpose.
4. Identify risks to subjects: use the privacy threat model output.
5. Score likelihood and severity per risk, from the subject's view.
6. Define mitigations with owners and dates; re score residual risk.
7. Consult: DPO always, subjects or their representatives where
   appropriate.
8. Get sign off, publish the summary where required, and schedule the
   review.

## 1. Screening and template

```bash
# Screening questions (yes to any likely means DPIA):
# - new technology with unclear privacy effects?
# - large scale processing of personal data?
# - special category or criminal data?
# - systematic evaluation or scoring of people?
# - monitoring of public areas?
# - vulnerable subjects (children, employees)?
echo "record the screening decision either way; 'no DPIA needed' needs reasons"
```

```python
#!/usr/bin/env python3
"""DPIA risk register with residual scoring."""
risks = [
    {"risk": "location history enables stalking by abusive partner",
     "likelihood": 3, "severity": 5,
     "mitigation": "coarse location only, 30 day retention, no sharing",
     "residual_l": 1, "residual_s": 4},
    {"risk": "support agents see full profiles unnecessarily",
     "likelihood": 4, "severity": 3,
     "mitigation": "scoped ticket view, access logging",
     "residual_l": 2, "residual_s": 2},
]
for r in risks:
    before, after = r["likelihood"] * r["severity"], r["residual_l"] * r["residual_s"]
    print(f"{r['risk']}\n  before: {before}, after mitigation: {after}")
    print(f"  mitigation: {r['mitigation']}\n")
```

## 2. Sign off and review

```bash
# Sign off checklist:
# - DPO advice recorded (and followed or formally overruled with reasons)
# - residual risks accepted by the accountable owner, in writing
# - mitigations have tickets with dates, not just intentions
# - review date set: launch + 6 months, or on material change
echo "a DPIA without tracked mitigations is a creative writing exercise"
```

## Edge cases

- High residual risk remains after mitigation. Consult the regulator
  before proceeding where the law requires it; do not launch and hope.
- The feature changes after sign off. Material changes reopen the
  DPIA; define "material" in advance.
- Multiple teams touch the processing. One DPIA with clear section
  owners beats five overlapping ones.

## Escalation

- DPO and product disagree: the accountable executive decides, with
  both positions recorded.
- Timeline pressure to skip: skipping a required DPIA is a
  compliance breach, not a shortcut; escalate in writing.

## Detection and defender view

Detect DPIA process failures with launch gates: no DPIA number, no
launch for in scope features. Audit a sample of past DPIAs for
mitigation completion. The durable practice is embedding the
screening in the design doc template so assessments start early,
when changes are cheap.

## Key references

- GDPR Article 35: DPIA requirements.
- EDPB/ICO DPIA templates and guidance.
- Related skills: privacy-threat-model, gdpr-engineering.
