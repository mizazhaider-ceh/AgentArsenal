---
name: ir-eradication
description: Use when the attacker is contained and their presence must be
  removed from the environment completely. Covers finding all persistence,
  removing attacker artifacts, validating clean systems, and planning
  recovery. Use after containment holds, when hunting remaining footholds,
  when rebuilding versus cleaning decisions arise, or when preparing
  systems to return to production.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-response
requires: [incident-response]
extends: []
relates: [forensics-fundamentals, malware-in-memory]
tools:
  - name: Python
    version: 3.12
  - name: YARA
    version: 4.5
---

Eradication removes the attacker completely: every persistence
mechanism, every backdoor account, every planted tool. This skill covers
the eradication discipline: hunting all footholds systematically,
removing them safely, and validating that clean means clean. Incomplete
eradication is how incidents recur; the checklist below exists because
"we got it all" needs proof.

## Quick Workflow

1. List every known attacker artifact from the investigation.
2. Hunt for unknown persistence across the scope: the checklist below.
3. Remove artifacts in an order that does not alert remaining pieces.
4. Decide rebuild versus clean per host (rebuild wins ties).
5. Validate: rescan, re-hunt, and monitor for reappearance.
6. Document every removal with before and after evidence.
7. Hand clean systems to recovery with the validation record.

## 1. Persistence hunt checklist

```bash
# Run across every in-scope host (adapt paths per OS):
# Windows:
# - Registry Run keys, Services, Scheduled Tasks, WMI subscriptions
# - Startup folders, Winlogon entries, LSA providers
# Linux:
# - cron (system and users), systemd units and timers
# - rc.local, profile.d, authorized_keys, LD_PRELOAD
# Both:
# - New user accounts and group memberships (compare to baseline)
# - Modified system binaries (compare hashes to known-good)
# - Web shells in web roots (YARA scan for webshell patterns)

# Account review: list all privileged accounts, justify each one
# Compare against the pre-incident baseline or a known-good host
```

Hunt beyond what the investigation found: the attacker planted what you
saw plus what you have not seen yet. The checklist is the minimum; the
threat intel for the specific actor extends it.

## 2. Removal and rebuild decisions

```bash
# Removal order: remove the quiet pieces first, C2 last, so nothing
# phones home about the cleanup in progress
# 1. Persistence mechanisms (they re-establish the rest)
# 2. Dropped tools and web shells
# 3. Backdoor accounts
# 4. C2 configurations (after confirming no new beacons)

# Rebuild versus clean:
# - Domain controllers, critical servers: rebuild from known-good media
# - Workstations with full disk encryption and good baselines: clean may do
# - Any doubt: rebuild. The cost of rebuild is known; the cost of a
#   missed backdoor is not.
```

Rebuilding is not admitting defeat; it is the only way to be sure about
kernel-level or firmware-level persistence. When the investigation found
sophisticated tooling, rebuild is the default answer.

## 3. Validation

```bash
# Post-eradication validation per host:
# - Full AV/EDR scan clean
# - YARA scan with the incident's rules: no hits
# - Persistence checklist re-run: no findings
# - 72 hours of enhanced monitoring: no reappearance

# The 72-hour watch is part of eradication, not an afterthought:
# attackers who kept one foothold reveal it when they check in
```

Validation without the monitoring window is incomplete. Schedule the
watch, staff it, and define the re-escalation trigger before declaring
eradication done.

## Edge cases

- The attacker used legitimate tools (living off the land). Removal
  means configuration review, not file deletion; document the intended
  state for each tool.
- Firmware or bootkit persistence is suspected. Rebuild does not reach
  firmware; this needs specialist handling and vendor involvement.
- Backups contain the attacker. Validate backup contents before
  restoring, or the recovery reintroduces the incident.
- The business cannot tolerate rebuild downtime. Phase the rebuilds,
  keep enhanced monitoring on the waiting hosts, and document the
  accepted risk.

## Escalation

- Eradication keeps finding new artifacts: the scope was wrong;
  re-scope and consider that the attacker is still active.
- You need the environment declared clean for regulators or customers:
  the validation record (checklist results plus the 72-hour watch) is
  the evidence; do not declare it early.
- Recovery planning starts: hand over the validated-clean inventory
  with the rebuild log.

## Detection and defender view

Eradication is where the defender's preparation pays compound interest:
known-good baselines, gold images, and configuration management make
"remove everything unknown" a tractable operation. Without baselines,
eradication is guesswork. The defender's lasting win from this phase is
the hardened build that replaces what the attacker touched.

## Key references

- NIST SP 800-61 (Computer Security Incident Handling Guide).
- MITRE ATT&CK persistence techniques (the hunt checklist source).
- SANS Incident Handler's Handbook.
