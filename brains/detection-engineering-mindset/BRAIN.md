---
name: detection-engineering-mindset
kind: brain
description: Use when an agent must build or improve detections: writing detection rules for a SIEM, deciding what to alert on, tuning noisy alerts, hunting for attacker techniques, or measuring whether the SOC actually sees attacks. Provides detection engineering reasoning: detect the technique not the tool, climb the pyramid of pain, prefer high-fidelity over high-volume, treat detections as code, and measure mean time to detect. Load this brain when the task is to see the attacker, not just to collect logs.
version: 1.0.0
provides:
  - Technique-based detection design
  - Pyramid of pain prioritization
  - High-fidelity alert tuning
  - Detections-as-code discipline
  - Detection coverage measurement
  - Alert fatigue countermeasures
used_by: []
---

Most organizations collect logs and call it detection. Then the SOC drowns in five thousand alerts a day, tunes out, and misses the real one. Detection engineering is the discipline of building detections that fire when it matters and stay quiet when it does not. It treats each detection as a small product: designed against a specific attacker technique, tested, tuned, and measured. It matters because an undetected attacker is just a future breach report. Visibility you cannot act on is expensive storage.

## Core mental models

**Detect the technique, not the tool.** Attackers change tools constantly; they change techniques rarely. A detection for "mimikatz.exe running" dies the day the attacker renames the binary. A detection for "a process opening LSASS with read access to dump credentials" survives renames, recompiles, and new tools. Anchor every detection to the underlying technique (credential access, lateral movement, persistence) and let the tool names be details.

**Climb the pyramid of pain.** The pyramid of pain ranks what you detect by how much it hurts the attacker to change: hashes at the bottom (trivial to change), then IPs, domains, artifacts, tools, and techniques at the top (painful to change). Detections at the bottom are cheap to build and cheap to evade. Spend your engineering time climbing: every detection should sit as high on the pyramid as your telemetry allows.

**High fidelity beats high volume.** One alert that fires ten times a year and is right nine times is worth more than a thousand alerts that are right half the time. Every false positive trains analysts to ignore the rule, which silently deletes your detection. Tune ruthlessly: baseline normal, exclude the known-good, and set thresholds from data. An alert nobody trusts is an alert that does not exist.

**Detections are code.** Version them, test them, review them, and retire them. A detection rule should live in a repository with tests (does it fire on the attack? does it stay quiet on normal?), a named owner, and a review date. Detections rot as systems change: the rule that was perfect last year fires on the new backup tool today. Treat the detection backlog like a software backlog.

## Operating checklist

1. Pick the technique to detect, mapped to MITRE ATT&CK if possible. Name the adversary behavior precisely.
2. Check telemetry: do you have the logs to see this technique? If not, get the telemetry first.
3. Write the detection against the technique's invariant behavior, not tool names or hashes.
4. Baseline normal: run it against a week of real data and count the noise before it goes live.
5. Tune: exclude known-good patterns, set thresholds from the baseline, document each exclusion's reason.
6. Test both directions: does it fire on a simulated attack? Does it stay quiet on normal activity?
7. Define the response: what does the analyst do when this fires? A detection without a runbook is a notification.
8. Ship it as code: versioned, reviewed, with an owner and a review date.
9. Measure: true positives, false positives, time from attack to alert. Track the trend.
10. Retire or fix detections that go noisy, stale, or untrusted. A dead rule is worse than no rule.

## Heuristics

- If the detection names a filename, it is already half dead. Name the behavior.
- Baseline before you alert. Unknown noise is just future false positives.
- Every exclusion needs a reason and an expiry. Exclusions are where attackers hide.
- One detection, one technique, one runbook. Bundled mega-rules are untunable.
- Test with real attack simulations, not just imagination. Atomic-style tests are cheap.
- If analysts mute it, believe them and fix the rule. They are the customer.
- Measure mean time to detect per technique, not alerts per day.
- Retire detections that have not fired truly in a year. They are archaeology.

## Anti-patterns

- **IOC-only detection.** Alerting on hashes and IPs the attacker changes before lunch.
- **Alert spam.** Hundreds of untuned rules producing thousands of alerts nobody reads.
- **Tool-name anchoring.** Detecting "psexec" instead of detecting lateral movement via service creation.
- **No runbook.** Alerts that fire with no documented next step, so each analyst improvises.
- **Write-once rules.** Detections deployed and never reviewed, slowly rotting into noise or silence.

## Worked example

Goal: detect credential dumping. Bad detection: alert on `mimikatz.exe`. The attacker renames it and walks past. Detection engineering pass: technique is "OS Credential Dumping" (T1003), invariant behavior is a non-system process opening LSASS with process-memory read rights. Telemetry check: Sysmon or EDR gives process-access events with granted rights. Rule: alert when a process outside the signed-system baseline requests 0x1010/0x1410 rights on lsass.exe. Baseline week: the backup agent triggers it twice (legitimate, documented exclusion with reason). Test: run a renamed dumping tool in the lab, rule fires. Runbook: isolate host, check for lateral movement, rotate potentially exposed credentials. Result: a detection that survives tool changes, fires rarely, and is trusted. That is the difference between logging and detection engineering.
