---
name: baseline-deviation
description: Use when hunting by comparing current activity against
  established baselines of normal. Covers building baselines, choosing
  deviation signals, investigating outliers, and tuning to reduce noise.
  Use when the environment is well-instrumented, when hunting without a
  specific hypothesis, when looking for novel attacker behavior, or when
  building anomaly-based detections.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
parent: threat-hunting
requires: [threat-hunting]
extends: []
relates: [siem-detections]
tools:
  - name: Python
    version: 3.12
  - name: osquery
    version: 5.12
---

Baseline deviation hunting assumes the attacker looks different from
normal: new processes, odd logon times, unusual network patterns. This
skill covers the approach: building honest baselines, picking deviation
signals worth investigating, and working the outliers down to verdicts.
It complements hypothesis hunting; where that skill tests an idea, this
one listens for the unusual.

## Quick Workflow

1. Pick the behavior domain: logons, processes, network, or data access.
2. Build the baseline from 30+ days of clean data.
3. Define deviation signals: first-seen, rare, off-hours, impossible.
4. Query the recent window for deviations.
5. Investigate each outlier: benign explanation or malicious.
6. Tune: whitelist the benign, alert on the rest.
7. Re-baseline on a schedule; environments drift.

## 1. Building baselines

```bash
# Example: process baseline per host role
# Collect 30 days of process executions, aggregate by (host_role, process_path)
python3 - <<'EOF'
# Baseline table concept:
# role=webserver: nginx, php-fpm, cron, logrotate  (expected set)
# role=workstation: explorer, chrome, outlook, ...  (larger expected set)
# Anything not in the role's set is a deviation candidate
print("Build per-role expected sets from the 30-day history")
print("New binaries, new paths, and new parents are the signals")
EOF

# osquery for the current process picture (compare against baseline)
osqueryi "SELECT name, path, parent FROM processes;" 2>/dev/null | head -20
```

Baselines are per role, not global: what is normal on a web server is
anomalous on a workstation. Role-based baselines cut the noise by an
order of magnitude versus one global "normal."

## 2. Deviation signals

```bash
# High-value deviation signals (tune per environment):
# - First-seen binary on a host role (new malware or new software)
# - Logons at 3 AM for a 9-to-5 user (compromise or travel)
# - Impossible travel: two logons, distant locations, short interval
# - Rare external destination: first-seen IP/domain per host
# - Privilege use outside the admin's pattern (new admin activity)

# Investigation order: rare + privileged + external first
# (a first-seen binary phoning a first-seen IP as SYSTEM: investigate now)
```

Stack the signals: one deviation is a lead, three stacked deviations
are an incident. The scoring is what makes this huntable at scale;
individual anomalies are too noisy alone.

## 3. Investigation and tuning

```bash
# Per outlier, answer in order:
# 1. Is it change-controlled? (ticket, deployment, known admin action)
# 2. Is it the user's normal? (check their history, ask if needed)
# 3. Is it malicious? (technique match, IOC match, behavior analysis)

# Tuning loop (weekly at first):
# - Whitelist the benign with expiry dates (whitelists rot too)
# - Tighten the signals that only produce noise
# - Promote the signals that found real issues to permanent detections
```

The tuning loop is the job: unturned anomaly hunting drowns in false
positives within weeks. Every benign verdict should improve the
baseline; every missed malicious one should tighten a signal.

## Edge cases

- The environment changes fast (devops, cloud). Shorten the baseline
  window and automate the re-baselining; manual baselines cannot keep
  up.
- The baseline period contained the attacker. Baselines learn
  malicious as normal; re-baseline from a known-clean period after
  incidents.
- Too many outliers to investigate. Raise the stacking threshold
  (require 2+ signals) rather than sampling randomly.
- Privacy constraints limit the data. Hunt on metadata (counts, times,
  patterns) rather than content where policy requires it.

## Escalation

- Stacked deviations indicate compromise: hand to ir-scoping with the
  deviation evidence and the baseline comparison.
- The baseline approach is failing (all noise): switch to hypothesis
  hunting for a cycle; the environment may need the targeted approach.
- You need the detections permanent: the tuned signals become SIEM
  rules with the baseline as the reference data.

## Detection and defender view

Baseline deviation is the defender's anomaly detection program: it
catches the novel attacker that signatures miss. Its maturity path is
manual hunts to tuned signals to automated detections, with the
baseline maintained as living documentation. The defender's investment
is the data (30+ days, per role) and the tuning discipline; without
both, it is either blind or noisy.

## Key references

- MITRE ATT&CK (techniques the deviations map to).
- NIST SP 800-94 (intrusion detection guidance).
- SANS hunting references (baseline methodologies).
