---
name: ir-containment
description: Use when an incident's scope is known and attacker activity
  must be stopped without destroying evidence. Covers short-term and
  long-term containment, isolation techniques, credential resets, and the
  evidence versus disruption tradeoff. Use when the attacker is active,
  when lateral movement is suspected, when deciding what to isolate first,
  or when balancing business continuity against security.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-response
requires: [incident-response]
extends: []
relates: [forensics-fundamentals, memory-forensics]
tools:
  - name: Python
    version: 3.12
---

Containment stops the bleeding: isolate the attacker, keep the business
running where possible, and preserve the evidence the later phases need.
This skill covers the containment decisions and techniques: what to
isolate first, how to isolate without tipping off or destroying evidence,
and when short-term containment becomes long-term. Every containment
action is a tradeoff; this skill makes the tradeoffs explicit.

## Quick Workflow

1. Prioritize containment targets: active C2 hosts first, then lateral
   movement paths, then the rest of the scope.
2. Capture volatile evidence from each target before isolating it.
3. Isolate: network first (least destructive), host second.
4. Reset credentials in the right order: attacker-controlled last.
5. Verify the attacker is actually cut off (watch for re-entry).
6. Document every action with timestamps for the timeline.
7. Transition to eradication when containment holds.

## 1. Isolation techniques

```bash
# Least destructive first:
# 1. Network isolation at the switch/firewall: host keeps running,
#    memory stays alive, attacker loses C2
# 2. Host firewall block of C2 destinations (surgical, keeps business traffic)
# 3. EDR network quarantine (one click, preserves the host state)
# 4. Full host isolation (last resort before shutdown)

# Before ANY isolation, capture volatiles (see evidence-handling):
# memory dump, netstat, process list, in that order

# Blocking the C2 at the perimeter as the first move:
# - Add the IOC IPs/domains to the firewall block list
# - Watch for the attacker switching infrastructure (new IOCs)
```

Network isolation beats host shutdown in almost every case: it stops the
attacker while preserving memory and disk state. Shutdown is for
ransomware actively encrypting, where seconds matter more than memory.

## 2. Credential reset order

```bash
# Reset order matters: reset in the wrong order and the attacker
# harvests the new credentials too.
# 1. Contain the hosts first (attacker cannot observe the resets)
# 2. Reset service accounts the attacker touched
# 3. Reset compromised user accounts
# 4. Reset krbtgt twice (invalidates all Kerberos tickets) ONLY for
#    domain compromise, with leadership approval: it is disruptive
# 5. Reset remaining privileged accounts

# Verify each reset: the old credential must fail, the new one must work
```

krbtgt reset is the nuclear option for domain compromise: it kills every
ticket including the attacker's, at the cost of disrupting the domain.
It needs explicit approval and a maintenance window, and it is done
twice (the two-password history means one reset is not enough).

## 3. Verifying containment

```bash
# Containment is not done when you act; it is done when verified:
# - Watch the blocked C2 destinations for new connection attempts
# - Watch for new hosts showing the IOCs (lateral movement continuing)
# - Check that isolated hosts stay isolated (no shadow IT reconnects)
# - Monitor the attacker's known accounts for new logons

# Re-entry indicators to alert on:
# - New external connections from the contained VLAN
# - Logons with reset credentials from odd sources
# - Fresh persistence mechanisms (the attacker re-establishing)
```

An attacker who notices containment often moves faster, not slower.
The 24 hours after containment are the highest-risk period; staff the
monitoring accordingly.

## Edge cases

- Business critical hosts cannot be isolated. Use surgical blocks (C2
  destinations only) and enhanced monitoring; document the accepted
  risk with leadership sign-off.
- The attacker is in the backups too. Note it for eradication; do not
  trust restores until verified.
- Cloud workloads complicate isolation. Use security groups and
  service controls rather than reaching for host power controls.
- Containment tips off the attacker before evidence is captured. That
  is why volatiles come first; when ransomware is encrypting, accept
  the tradeoff and isolate immediately.

## Escalation

- Containment fails (attacker re-enters): escalate severity, widen the
  scope investigation, and consider that the initial scope was wrong.
- You need to keep the attacker contained but observable: that is a
  deliberate deception decision needing leadership approval, not a
  default.
- Eradication is ready to start: hand over the contained, documented
  scope with the evidence inventory.

## Detection and defender view

Containment is the defender's active phase: every action should be
visible in the monitoring (isolation events, block list changes,
credential resets) so the team can verify effect. The defender's
preparation is the tooling that makes containment fast: EDR quarantine,
network segmentation that actually segments, and practiced credential
reset runbooks. Speed of containment is the metric that matters.

## Key references

- NIST SP 800-61 (Computer Security Incident Handling Guide).
- SANS Incident Handler's Handbook.
- MITRE ATT&CK (map the contained techniques for the report).
