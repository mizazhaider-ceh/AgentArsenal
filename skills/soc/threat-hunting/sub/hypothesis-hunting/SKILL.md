---
name: hypothesis-hunting
description: Use when hunting threats from an idea about attacker
  behavior rather than an alert. Covers writing testable hypotheses,
  scoping the hunt, executing with analytics, and concluding with
  evidence. Use when starting a hunt cycle, when threat intel suggests a
  technique, when alerts are quiet but risk is not, or when building the
  team's hunting discipline.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
parent: threat-hunting
requires: [threat-hunting]
extends: []
relates: [incident-response]
tools:
  - name: Python
    version: 3.12
  - name: Velociraptor
    version: 0.72
  - name: osquery
    version: 5.12
---

Hypothesis hunting starts from an idea: "attackers are using WMI for
persistence in our estate," then proves or disproves it with data. This
skill covers the hypothesis-driven hunt: writing hypotheses that are
testable, scoping them to the data you have, executing efficiently, and
concluding with evidence either way. A hunt without a hypothesis is
just browsing logs; the hypothesis is what makes it hunting.

## Quick Workflow

1. Write the hypothesis: actor, technique, expected evidence.
2. Check data availability: do the logs exist to test it.
3. Scope: which hosts, what time window, what data sources.
4. Execute: query for the expected evidence, then for its absence.
5. Conclude: confirmed, refuted, or inconclusive, with the evidence.
6. Convert confirmed hunts into detections; log refuted ones too.
7. Feed lessons into the next hypothesis.

## 1. Writing testable hypotheses

```bash
cat > /tmp/hunt_hypothesis.txt <<'EOF'
Hypothesis: Attackers are maintaining persistence via WMI event
subscriptions on our Windows workstations.

Expected evidence if TRUE:
- WMI event consumers not created by our management tooling
- Recent creation timestamps on suspicious subscriptions
- Associated event filters querying process creation

Data needed: WMI repository (via Velociraptor), EDR process data
Scope: all Windows workstations, last 90 days
Falsifiable: a clean inventory of WMI subscriptions refutes it
EOF
```

A good hypothesis names the technique, the expected evidence, and what
would disprove it. "APT is in our network" is not a hypothesis; "WMI
persistence exists on workstations" is. Write it before touching the
data; the hypothesis disciplines the hunt.

## 2. Executing the hunt

```bash
# Example: hunt WMI persistence with Velociraptor across the fleet
# Artifact: Windows.Persistence.WMI or custom WMI enumeration query
# Collect, then review for non-standard consumers

# osquery alternative for the same question on enrolled hosts
osqueryi "SELECT name, query FROM wmi_event_filters;" 2>/dev/null | head -10

# Analysis discipline:
# 1. Baseline first: what does NORMAL look like? (management tooling,
#    known-good subscriptions)
# 2. Anomalies: everything not in the baseline gets reviewed
# 3. Validate: each anomaly checked against change records before
#    verdicting
```

Baseline before anomaly: the hunt that skips the baseline verdicts
the management tooling as malicious and wastes the cycle. Spend the
first third of the hunt learning normal for the specific question.

## 3. Concluding and converting

```bash
# Conclusion template:
cat > /tmp/hunt_conclusion.txt <<'EOF'
Hypothesis: <text>
Verdict: CONFIRMED / REFUTED / INCONCLUSIVE
Evidence: <what was found, with queries and counts>
Scope covered: <hosts, window, sources>
Gaps: <what could not be checked>

If CONFIRMED: incident declared, handed to ir-scoping with this evidence
If REFUTED: detection opportunity logged (see below)
EOF

# Every hunt produces a detection, even refuted ones:
# the queries become the scheduled check that keeps the answer fresh
```

Refuted hypotheses are wins: they are answered questions, and their
queries become the monitoring that keeps them answered. The hunt
program's output is detections, not just incidents; track both.

## Edge cases

- The data does not exist. The hunt becomes a logging gap finding;
  that is a valid and valuable conclusion, not a failure.
- The scope is too big for the time. Narrow the hypothesis (one
  business unit, one technique variant) rather than skimming everything.
- The hypothesis is confirmed everywhere (widespread). Escalate to
  incident response; the hunt did its job, now the response runs.
- Threat intel is vague. Sharpen it into the testable form above
  before hunting; vague intel produces vague hunts.

## Escalation

- Confirmation: hand to ir-scoping immediately with the hunt evidence;
  do not keep hunting while the incident waits.
- You need better data: the hunt's data gaps become the logging
  improvement backlog, prioritized by hunt value.
- The hunt program needs structure: run hypotheses in cycles (weekly),
  track them, and review the detection conversions quarterly.

## Detection and defender view

Hypothesis hunting IS the defender's proactive detection: it finds what
the alerts missed and turns the findings into new alerts. The program
matures from alert-driven to hunt-driven to detection-engineered, where
every hunt's queries become permanent coverage. The defender's metric
is hunts per quarter and the detection conversion rate, not just
incidents found.

## Key references

- MITRE ATT&CK (hypotheses map to techniques; use the framework).
- Sqrrl/Threat hunting methodology references.
- NIST SP 800-61 (hunt-to-incident handoff).
