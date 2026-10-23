---
name: auditd-baseline
description: Use when setting up Linux audit logging with auditd for
  security monitoring. Covers the essential audit rules, log management,
  and verifying the rules capture what matters. Use when the server needs
  detective controls, when compliance requires audit trails, when
  investigating without logs today, or when setting the audit standard.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
parent: linux-hardening
requires: [linux-hardening]
extends: []
relates: [incident-response, threat-hunting]
tools:
  - name: Python
    version: 3.12
  - name: Audit
    version: 3.1
---

auditd watches what the kernel does: file accesses, privilege changes,
and system calls, with the detail incident response needs. This skill
covers the audit baseline: the rules worth having, log handling that
survives real volume, and verifying the rules actually fire. Audit logs
are the difference between "something happened" and "this is exactly
what happened."

## Quick Workflow

1. Install and enable auditd; check it is running.
2. Deploy the baseline rule set (below).
3. Verify each rule class fires with a test action.
4. Configure log rotation and remote shipping.
5. Set up alerting on the critical rule hits.
6. Review log volume after a week and tune.

## 1. Baseline rules

```bash
# Check auditd is running and the rules loaded
systemctl is-active auditd
auditctl -l | head -30

# Baseline /etc/audit/rules.d/hardening.rules:
# Identity and privilege:
# -w /etc/passwd -p wa -k identity
# -w /etc/shadow -p wa -k identity
# -w /etc/sudoers -p wa -k priv_esc
# -w /etc/sudoers.d/ -p wa -k priv_esc
# -a always,exit -F arch=b64 -S execve -k executions  (heavy: scope it)
# Authentication:
# -w /var/log/auth.log -p wa -k auth  (or the distro's auth log)
# -w /etc/ssh/sshd_config -p wa -k sshd
# Kernel and modules:
# -w /etc/sysctl.conf -p wa -k sysctl
# -a always,exit -F arch=b64 -S init_module -S delete_module -k modules
# Time:
# -a always,exit -F arch=b64 -S adjtimex -S settimeofday -k time_change

# Load and verify
augenrules --load
auditctl -l | wc -l
```

The execve rule is the most valuable and the noisiest: on busy servers,
scope it to interesting users or directories rather than everything.
Start broad, measure the volume, then narrow; the tuning week is part
of the deployment.

## 2. Testing the rules

```bash
# Each rule class gets a test action, then check the log
# Identity: touch /etc/passwd (as root, in maintenance) -> ausearch -k identity
sudo touch /etc/passwd && sudo ausearch -k identity --start recent 2>/dev/null | head -5

# Modules: modprobe a test module -> ausearch -k modules
# Time: check the time_change rule is loaded (do not actually change time)

# The test proves the pipeline: rule -> log -> searchable
# A rule that never fires in testing will not fire in the incident either
```

Test every rule class after deployment. Untested audit rules are
decorative; the ausearch output is the proof they work.

## 3. Log management

```bash
# /etc/audit/auditd.conf essentials:
# max_log_file = 100 (MB per file, tune to volume)
# max_log_file_action = rotate
# num_logs = 30 (retention in files; size to the policy)
# space_left_action = email (alert before the disk fills)
# admin_space_left_action = halt (stop rather than lose audit)

# Ship logs off the host: the local log is the attacker's first target
# (rsyslog forwarding, or the SIEM agent; test that it arrives)

# Verify remote arrival: generate a test event, confirm it lands centrally
logger -p authpriv.info "auditd pipeline test $(date -u +%FT%TZ)"
```

Audit logs that stay only on the host are evidence the attacker can
delete. Remote shipping is not optional for security-relevant audit;
the local copy is the buffer, the central copy is the record.

## Edge cases

- Log volume overwhelms the disk. Tune the execve scope first; then
  increase rotation; never solve it by disabling rules silently.
- Performance impact on busy servers. Measure before and after; the
  syscall rules cost the most, and scoping them is the fix.
- Container hosts: audit the host, not just the containers; the
  interesting events (module loads, host file writes) happen on the
  host.
- Compliance needs more. Layer the compliance rule set on top of this
  baseline; do not replace the baseline with it.

## Escalation

- An incident needs the audit data now: ausearch by key and time
  window is the fast path; the rules were built for this moment.
- The baseline is insufficient for the threat model: add the targeted
  rules (specific binaries, directories) with the same test discipline.
- Fleet rollout: config management deploys the rules, the scheduled
  audit verifies they are loaded everywhere.

## Detection and defender view

auditd IS the defender's host telemetry: the rules above feed the
detections for privesc, persistence, and tampering. The defender's work
is the tuning loop: rules fire, alerts get written, false positives get
scoped, and the audit trail gets better every quarter. An unmonitored
auditd is just disk usage; the alerting is what makes it a control.

## Key references

- CIS Benchmarks: auditing sections.
- Audit 3.1 documentation: auditctl, ausearch, augenrules.
- NIST SP 800-92 (log management).
