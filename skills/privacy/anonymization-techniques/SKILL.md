---
name: anonymization-techniques
description: Use when you need to anonymize a dataset for sharing or
  analysis. Covers k-anonymity, l-diversity, generalization and
  suppression, re identification risk assessment, and why naive
  masking fails. Also use when someone proposes "just removing names"
  and you need to show why that is not enough.
version: 1.0.0
domain: privacy
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [differential-privacy, data-minimization, privacy-threat-model]
tools:
  - name: Python
    version: 3.12
---

Removing names does not anonymize: ZIP code plus birth date plus
gender uniquely identifies most Americans, and attackers join your
"anonymous" data with public records. This skill covers doing it
properly: k-anonymity and l-diversity, generalization hierarchies,
and measuring re identification risk. Treat the output as high effort
pseudonymization unless a proper risk analysis says otherwise.

## Quick Workflow

1. Classify attributes: direct identifiers, quasi identifiers, and
   sensitive attributes.
2. Drop direct identifiers completely.
3. Generalize quasi identifiers up hierarchies (age to range, ZIP to
   region) until k-anonymity holds.
4. Suppress the outliers that cannot be generalized without ruining
   utility.
5. Check l-diversity: each group must have diverse sensitive values,
   not just k members.
6. Run a re identification risk assessment against plausible attacker
   knowledge.
7. Document the method, parameters, and residual risk honestly.
8. If the risk is still high, use differential privacy or do not
   share.

## 1. k-anonymity implementation

```python
#!/usr/bin/env python3
"""k-anonymity check on quasi identifiers (illustrative)."""
import collections

# rows: (age, zip, gender, diagnosis)
rows = [
    (25, "10001", "F", "flu"), (27, "10001", "F", "cold"),
    (26, "10002", "F", "flu"), (45, "20001", "M", "fracture"),
    (47, "20001", "M", "cold"),
]

def generalize_age(a):
    return f"{a // 10 * 10}-{a // 10 * 10 + 9}"

def generalize_zip(z):
    return z[:3] + "**"

groups = collections.defaultdict(list)
for age, zipc, gender, diag in rows:
    key = (generalize_age(age), generalize_zip(zipc), gender)
    groups[key].append(diag)

k = 2
for key, diags in groups.items():
    ok = "OK " if len(diags) >= k else "FAIL"
    print(f"{ok} group {key}: {len(diags)} rows, diagnoses={set(diags)}")
# Then check l-diversity: groups where all diagnoses are equal still leak
```

## 2. Re identification risk assessment

```bash
# Attacker model questions (answer before sharing):
# - what public datasets could join with these quasi identifiers?
# - what is the smallest group size after generalization?
# - are there unique combinations left (outliers)?
# - does the recipient have motive and means to re identify?
python3 - << 'PY'
print("risk = f(uniqueness, attacker knowledge, data sensitivity)")
print("document: method, k, hierarchies, suppression rate, residual risk")
print("rule: if you cannot defend the risk analysis, do not release")
PY
```

## Edge cases

- Longitudinal data (multiple releases). Each release must be
  analyzed together; composition breaks naive per release k.
- High dimensional data (location traces, genomes). k-anonymity
  destroys utility before it gives safety; use DP or synthetic data.
- The recipient is trusted. Trust is not a technique; contracts help
  but do not change the math.

## Escalation

- Utility collapses before k is reached: switch to synthetic data
  generation or differential privacy for the statistics.
- Legal needs "anonymous" status: only counsel decides; your job is
  the risk analysis they decide on.

## Detection and defender view

Detect anonymization failures with re identification drills: have a
red team try to re identify records using public data. Monitor for
dataset combinations (two "anonymous" releases that join
trivially). The durable lesson from research is humility: famous
datasets thought anonymous were re identified, so the analysis must
assume a motivated attacker with public data.

## Key references

- Sweeney (k-anonymity) and Machanavajjhala (l-diversity) papers.
- NIST SP 800-188: de-identification guidance.
- Related skills: differential-privacy, data-minimization.
