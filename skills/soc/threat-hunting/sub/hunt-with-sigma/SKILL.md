---
name: hunt-with-sigma
description: Use when writing Sigma rules to hunt threats across SIEM
  platforms on a repeatable basis. Covers Sigma rule structure, writing
  hunt rules from hypotheses, testing rules safely, and converting hunts
  to detections. Use when the hunt needs to run on a schedule, when
  sharing hunts across tools, when building the detection backlog, or
  when the team standardizes on Sigma.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
parent: threat-hunting
requires: [threat-hunting]
extends: []
relates: [sigma-rules, siem-detections]
tools:
  - name: Python
    version: 3.12
  - name: Wazuh
    version: 4.8
---

Sigma is the shared language for detections: write once, run on any
SIEM. This skill covers using Sigma for threat hunting: writing hunt
rules from hypotheses, testing them without alert fatigue, and promoting
the good ones to permanent detections. It makes hunts repeatable,
shareable, and schedulable instead of one-off queries.

## Quick Workflow

1. Take the hunt hypothesis or deviation signal.
2. Write the Sigma rule: title, logsource, detection, condition.
3. Test against historical data first (backtest).
4. Tune thresholds and filters from the backtest results.
5. Run as a scheduled hunt; review the hits.
6. Promote validated rules to detection status.
7. Share and version the rule library.

## 1. Rule structure

```yaml
# Example: hunt for suspicious encoded PowerShell (Windows event logs)
title: Hunt Encoded PowerShell Execution
id: 11111111-2222-3333-4444-555555555555
status: experimental
description: Finds powershell.exe with encoded command flags for triage
author: SOC Hunt Team
date: 2026/10/23
logsource:
  product: windows
  category: process_creation
detection:
  selection:
    Image|endswith: '\powershell.exe'
    CommandLine|contains:
      - '-EncodedCommand'
      - '-enc '
      - 'FromBase64String'
  filter_known_good:
    CommandLine|contains: 'known_admin_tooling_string'
  condition: selection and not filter_known_good
level: medium
```

The `filter_known_good` is what separates a hunt rule from an alert
rule: hunts tolerate reviewing hits, alerts must not fire on normal
activity. Write the filter from the baseline work in baseline-deviation.

## 2. Backtesting and tuning

```bash
# Backtest: run the rule's logic against 30 days of history
# (in the SIEM's Sigma backend or with sigma-cli conversion)
# Measure: total hits, hits per day, known-good ratio

# Tuning targets:
# - A hunt rule: < 20 hits/day reviewable, or scoped narrower
# - A detection rule: near-zero false positives (much stricter)
# - If the backtest explodes: add filters (host roles, known goods)
#   before narrowing the detection logic itself

# Convert and deploy per platform (example: Wazuh/SIEM backend)
# sigma convert -t <backend> -p <pipeline> rule.yml
```

Backtest every rule before scheduling: the historical hit count predicts
the operational load. A rule that would have fired 500 times last month
is a tuning task, not a detection.

## 3. Hunt-to-detection pipeline

```bash
# Pipeline stages per rule:
# experimental (hunt): scheduled, hits reviewed manually
#   -> test: narrowed, filtered, reviewed for two cycles
#   -> stable (detection): alerting, in the SOC runbook
#   -> deprecated: technique obsolete or covered better elsewhere

# Rule library discipline:
# - Versioned in git, one file per rule
# - Every rule has: hypothesis link, backtest results, owner
# - Quarterly review: still relevant? still firing correctly?
```

The pipeline prevents the two failure modes: hunts that never become
detections (knowledge evaporates) and detections that were never hunts
(alerts nobody understands). Every detection should trace back to the
hunt that proved it.

## Edge cases

- The log source does not exist yet. The rule becomes the logging
  requirement; hunt value justifies the collection cost.
- Sigma backend differences change semantics. Test the converted
  query on the actual platform; converters are good but not perfect.
- The rule needs enrichment (asset roles, user context). Build the
  enrichment first; context-free rules stay noisy.
- Threat intel feeds the rule. Cite the intel in the rule's
  references; intel ages, and the rule should show its source.

## Escalation

- A hunt rule confirms malicious activity: hand to ir-scoping with
  the rule hits as evidence.
- The library is growing unmanaged: assign rule owners and run the
  quarterly review; detection debt is real.
- Cross-platform sharing needed: Sigma's portability is the answer;
  test the conversion per target platform.

## Detection and defender view

Sigma-based hunting is the defender's detection engineering practice:
hunts become rules, rules become alerts, alerts get runbooks. The
maturity signal is the pipeline flowing: hypotheses in, detections
out, with the library as the institutional memory. Attackers evolve;
the rule library is how the defense remembers.

## Key references

- SigmaHQ rule specification and taxonomy.
- MITRE ATT&CK (technique tags on rules).
- pySigma backend documentation (conversion).
