---
name: iso21434-basics
description: Use when you need working knowledge of ISO/SAE 21434 for
  automotive cybersecurity work. Covers the standard's structure, TARA
  (threat analysis and risk assessment), cybersecurity planning, and
  how assessments map to its clauses. Also use when an automotive
  client asks what 21434 expects from their engineering process.
version: 1.0.0
domain: automotive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [automotive-threat-model, secure-coding]
tools:
  - name: Python
    version: 3.12
---

ISO/SAE 21434 is the automotive cybersecurity engineering standard:
it tells manufacturers how to build security in, from concept to
decommissioning. This skill gives the working knowledge assessors and
engineers need: the clause structure, the TARA method, and how
technical testing maps to process requirements. It is foundations for
security work in automotive, not a certification course.

## Quick Workflow

1. Learn the structure: the standard's clauses from management to
   operations.
2. Understand TARA: asset identification, threat scenarios, attack
   paths, and risk rating.
3. Map your technical testing to TARA attack paths: each finding is
   evidence for a path's feasibility.
4. Review the cybersecurity plan artifacts: what 21434 expects to
   exist.
5. Check the lifecycle coverage: production, operations, maintenance,
   and decommissioning.
6. Assess incident response expectations for vehicle fleets.
7. Note the supply chain clauses: what OEMs must require of suppliers.
8. Use the vocabulary correctly in reports: damage scenarios, threat
   scenarios, attack paths.

## 1. TARA essentials

```text
TARA flow:
  1. Item definition: what the system is and its boundaries
  2. Asset identification: what needs protection (safety, financial, data)
  3. Threat scenarios: what could go wrong (STRIDE style brainstorming)
  4. Attack paths: step by step how an attacker gets there
  5. Feasibility rating: how hard each path is (time, expertise, access)
  6. Impact rating: safety, financial, operational, privacy
  7. Risk value: impact x feasibility -> treatment decision
```

```bash
# Turn assessment findings into attack path evidence
python3 - << 'PY'
paths = [
    ("OBD injection -> gateway -> powertrain CAN", "medium", "safety: high"),
    ("telematics API IDOR -> remote unlock", "low", "theft: high"),
    ("infotainment USB -> code exec -> CAN bridge", "high", "safety: medium"),
]
for p, feas, impact in paths:
    print(f"path: {p}\n  feasibility: {feas}, impact: {impact}\n")
PY
```

## 2. Clause map for assessors

```bash
# Where technical work maps to the standard:
# Clause 8: TARA -> your threat model feeds this
# Clause 9: product development -> your code and design review
# Clause 10: verification and validation -> your penetration tests
# Clause 11: production -> your supply chain and flashing review
# Clause 12: operations and maintenance -> your update and IR review
# Clause 13: end of life -> your decommissioning checks
echo "cite the clause your finding violates for maximum client impact"
```

## Edge cases

- The client confuses 21434 with UN R155. 21434 is the engineering
  standard; R155 is the regulation requiring a certified management
  system. Know which one the client means.
- TARA exists but attack paths are vague. Your testing makes them
  concrete; feed results back to the TARA owner.
- Suppliers claim 21434 compliance without evidence. Ask for the
  work products, not the claim.

## Escalation

- Need a full TARA: this skill gives the method; a full TARA is a
  multi week engineering activity with the item team.
- Regulatory questions: involve compliance specialists; assessors
  test, they do not certify.

## Detection and defender view

In the 21434 world, "detection" is organizational: continuous
monitoring of the fleet, vulnerability management, and incident
response per the cybersecurity plan. Technical monitoring (SOC for
vehicles, anomaly detection on telematics) feeds the process. The
durable value of the standard is that security becomes a lifecycle
activity with owners, not a test before launch.

## Key references

- ISO/SAE 21434:2021: Road vehicles, cybersecurity engineering.
- UN R155: cybersecurity management system regulation.
- Related skill: automotive-threat-model.
