---
name: endpoint-hardening-baseline
description: Use when building or auditing endpoint hardening
  baselines for Windows, macOS, or Linux fleets. Covers CIS benchmark
  adaptation, practical control selection, compliance checking, and
  exception handling. Also use when a fleet needs a defensible
  standard configuration.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening, ssh-hardening, edr-basics]
tools:
  - name: Python
    version: 3.12
---

A hardening baseline is the fleet's standard secure configuration:
what is on, what is off, and what is monitored, applied to every
endpoint. This skill covers building one that is actually adopted:
adapting CIS benchmarks, choosing controls with user impact in mind,
checking compliance, and handling exceptions. It is for fleets you
manage.

## Quick Workflow

1. Pick the starting benchmark: CIS level 1 for the OS in use.
2. Adapt to your environment: remove what breaks business apps,
   document why.
3. Prioritize the controls that stop real attacks: attack surface
   reduction first.
4. Implement via configuration management, not manual tweaks.
5. Check compliance continuously: drift alerts, not annual audits.
6. Handle exceptions formally: ticket, expiry, compensating control.
7. Measure: compliance percentage per control, trending up.
8. Review the baseline yearly or after major OS changes.

## 1. Control selection

```bash
# Priority controls (the ones that earn their user impact):
# - firewall on, inbound default deny
# - automatic updates on, reboot policy defined
# - no local admin for daily use
# - USB mass storage restricted or monitored
# - EDR installed, tamper protected, reporting
# - disk encryption on
# - screen lock <= 5 min, password required
# - unnecessary services disabled (telnet, SMBv1, LLMNR where possible)
echo "each control: setting, enforcement method, exception process"
```

```python
#!/usr/bin/env python3
"""Baseline compliance sketch: control, expected, found, status."""
checks = [
    ("firewall enabled", True, True),
    ("disk encrypted", True, True),
    ("local admins <= 2", True, False),
    ("EDR reporting", True, True),
]
for name, want, got in checks:
    print(f"[{'OK' if want == got else 'FAIL'}] {name}")
print("trend the pass rate; investigate new FAILs within a day")
```

## 2. Compliance checking

```bash
# Linux example checks (adapt per OS):
# firewall: ufw status | firewall-cmd --state
# encryption: lsblk -o NAME,FSTYPE | grep crypto
# updates: unattended-upgrades status or last patch date
# EDR: service status and last check in
echo "automate: config management enforces, scanner verifies, SIEM alerts"
```

## Edge cases

- Developers need local admin. Give just in time elevation with
  logging, not standing admin.
- Legacy apps need old protocols. Isolate those machines and
  document the risk acceptance.
- BYOD in scope. Then the baseline is MDM enforced minimums, not
  full control; be honest about the difference.

## Escalation

- Compliance dropping: find whether it is drift, exceptions, or
  new devices; fix the process, not just the machines.
- Control breaks business: the exception process exists for this;
  undocumented workarounds are the real risk.

## Detection and defender view

Hardening is prevention; its detection side is compliance
monitoring: drift from the baseline is the alert. Attackers look
for the non compliant machines, which is why coverage matters more
than perfection on a few. The durable program measures compliance
like uptime and treats exceptions as temporary by default.

## Key references

- CIS Benchmarks: per OS hardening guides.
- NIST SP 800-53: control catalog.
- Related skills: linux-hardening, ssh-hardening.
