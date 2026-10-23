---
name: purple-team-exercises
description: Use when running purple team exercises that pair offense
  and defense on authorized systems. Covers exercise design, TTP
  selection, detection validation, and turning results into improved
  detections. Also use when red team findings need to become blue
  team capability.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [edr-evasion-detection, siem-detections, threat-hunting]
tools:
  - name: Python
    version: 3.12
---

Purple teaming puts red and blue at the same table: red runs a
technique, blue checks the detection, and together they close the
gap the same day. This skill covers running the exercises on systems
you are authorized to test: scoping, TTP selection, execution with
full telemetry, and converting results into detections.

## Quick Workflow

1. Scope the exercise: systems, techniques, and the detection stack
   under test, with written authorization.
2. Pick TTPs mapped to ATT&CK, prioritized by your threat profile.
3. Baseline: does a detection already exist for each TTP.
4. Execute red: run each technique with full logging and timestamps.
5. Validate blue: check every layer (EDR, SIEM, NDR) for the alert.
6. Tune together: write or fix the detection on the spot.
7. Retest: run the technique again and confirm the alert fires.
8. Report the before and after detection coverage.

## 1. Exercise plan

```bash
# Plan template (fill per exercise):
# objective: validate detection of credential dumping (T1003)
# scope: lab workstation WS-LAB-01, EDR + SIEM
# red steps: 1. run mimikatz variant 2. run comsvcs dump 3. ntdsutil
# blue checks: EDR alert? SIEM rule fired? timeline complete?
# success: alert within 5 min with correct technique ID
cat > /tmp/purple/plan_t1003.md << 'MD'
# Purple: T1003 OS Credential Dumping
## Red steps
## Blue expectations
## Tuning notes
## Retest result
MD
```

```python
#!/usr/bin/env python3
"""Coverage tracker: technique, layers, before/after."""
results = [
    {"ttp": "T1003.001 LSASS dump", "edr_before": "silent",
     "siem_before": "silent", "after": "alert in 2m"},
    {"ttp": "T1059.001 powershell", "edr_before": "alert",
     "siem_before": "silent", "after": "both alert"},
]
for r in results:
    print(f"{r['ttp']}: EDR was {r['edr_before']}, SIEM was {r['siem_before']} -> {r['after']}")
```

## 2. Running the loop

```bash
# During execution:
# - red announces each step before running it (no surprises)
# - blue watches the consoles live and calls out hits and misses
# - scribe logs: timestamp, technique, observed result per layer
# After each technique: tune immediately while context is fresh
# End of day: retest the tuned detections, record the evidence
echo "the retest is the point; untested tuning is a guess"
```

## Edge cases

- Production systems in scope. Limit to safe techniques or use the
  lab; purple teaming should not cause incidents.
- The EDR blocks everything. That is a result; shift to testing
  visibility (would you see it if it ran) via audit mode.
- Blue has no time to tune. Then the exercise produces a backlog;
  prioritize it like any security debt.

## Escalation

- Technique evades all layers: this becomes the top detection
  priority; consider the technique's likelihood for your threats.
- Exercise reveals systemic blindness: escalate to architecture
  (more telemetry) not just rules.

## Detection and defender view

Purple teaming is how detection matures: it replaces assumed
coverage with measured coverage. The output is not the report but
the tuned detections and the muscle memory of working together.
Run it regularly against your top threats, track coverage over
time, and feed the gaps into the detection engineering backlog.

## Key references

- MITRE ATT&CK: technique selection framework.
- Related skills: edr-evasion-detection, detection-as-code.
