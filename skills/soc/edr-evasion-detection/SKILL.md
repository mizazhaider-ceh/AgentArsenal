---
name: edr-evasion-detection
description: Use when reviewing whether attacker techniques evade the
  deployed EDR on an authorized assessment. Covers common evasion
  classes, detection gap testing with atomic tests, and tuning
  recommendations. Also use when a red team bypassed the EDR and you
  need to close the gap.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [edr-basics, threat-hunting, siem-detections, purple-team-exercises]
tools:
  - name: Python
    version: 3.12
---

EDR evasion is the attacker's craft: unhooking, AMSI bypass, LOLBins,
and direct syscalls. This skill covers authorized gap testing: running
atomic technique tests in the lab, seeing what the EDR catches, and
tuning the detections. Test only on lab systems or with written
authorization; evasion testing on production endpoints is disruptive.

## Quick Workflow

1. Baseline the EDR: version, policy, and what it claims to detect.
2. Pick evasion classes to test: unhooking, AMSI, ETW, LOLBins, and
   syscalls.
3. Run atomic tests in the lab, one technique at a time, with full
   logging.
4. Record: blocked, alerted, or silent, with the exact telemetry.
5. Tune: write or enable the detection for each silent technique.
6. Retest after tuning to confirm the gap closed.
7. Check for tampering protection: can the EDR itself be disabled.
8. Report the residual gaps honestly with the test evidence.

## 1. Atomic testing (lab)

```bash
# Atomic Red Team style: one technique, one test, full logging
# Example: LOLBin execution test (lab Windows host)
# powershell -c "rundll32.exe javascript:..."
echo "run each atomic, then check the EDR console within 5 minutes"
```

```bash
# AMSI bypass class test (lab): does the EDR see the bypass attempt
# or only the payload after? Both matter for the gap analysis
# Record: which stage alerted, with what severity
```

```python
#!/usr/bin/env python3
"""Gap register: technique, expected detection, observed result."""
tests = [
    ("T1055 process injection", "alert", "silent"),
    ("T1059.001 powershell download", "block", "alert"),
    ("T1218 rundll32", "alert", "alert"),
    ("direct syscalls", "alert", "silent"),
]
for tech, want, got in tests:
    status = "GAP" if got == "silent" else ("TUNE" if got != want else "OK")
    print(f"[{status}] {tech}: want={want} got={got}")
```

## 2. Tamper protection check

```bash
# Can the EDR be disabled from an elevated lab prompt?
# - service stop attempts (should be blocked or alerted)
# - driver unload attempts
# - exclusion abuse: adding attacker paths to exclusions
# Test the exclusion path especially: overly broad exclusions are the
# most common "evasion" and need no malware at all
echo "review: who can edit exclusions, and what is excluded now"
```

## Edge cases

- The EDR alerts but the SOC ignores the rule. The gap is process,
  not product; fix the triage, not just the rule.
- Tests are blocked by policy, not detected. Blocking is fine;
  record it as blocked, not as a detection gap.
- Cloud managed EDR with delayed telemetry. Account for the delay
  in the test window or you will mislabel.

## Escalation

- EDR disabled by the test: the tamper finding outranks technique
  gaps; report it first.
- Systemic blindness (e.g. no script logging): recommend the
  platform change (enable AMSI, script block logging) before rule
  tuning.

## Detection and defender view

This skill is defensive: it finds where the EDR is blind so you can
fix it. Attackers use the same knowledge offensively, which is why
testing stays in the lab with authorization. The durable program is
purple: red runs the techniques, blue tunes the detections, and the
gap register trends down over time. Assume breach: the EDR is one
layer, and its gaps are known and tracked.

## Key references

- MITRE ATT&CK T1562 (Impair Defenses), T1055, T1218.
- MITRE Engenuity ATT&CK Evaluations: EDR test methodology.
- Related skills: edr-basics, purple-team-exercises.
