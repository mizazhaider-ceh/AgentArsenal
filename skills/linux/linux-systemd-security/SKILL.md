---
name: linux-systemd-security
description: Use when securing systemd on a Linux server from a defensive
  posture across unit files, sandboxing, and logging. Covers auditing unit file
  permissions and privilege settings, applying sandboxing directives
  (ProtectSystem, PrivateTmp, SystemCallFilter), securing the journal with
  journald configuration and tamper-evident logging, and mapping controls to
  MITRE ATT&CK mitigations for persistence techniques like T1543 and T1053.
  Defensive hardening for systems you administer; no exploitation content.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening, linux-hardening-baseline, linux-log-intrusion-analysis]
tools:
  - name: systemd
    version: 255
  - name: auditd
    version: 3.1
  - name: Python
    version: 3.12
---

Systemd is the init system, the service manager, and the logging pipeline on most Linux servers, which makes it both a prime persistence target for attackers and the best lever defenders have for containing services. This parent skill covers the defensive systemd security posture in three parts: keeping unit files themselves trustworthy, sandboxing what services can do, and securing the journal so logs survive an incident. Everything here is defensive hardening for systems you own or administer. The sub-skills go deep on unit file security, sandboxing directives, and journal security; this file is the strategy and the cross-cutting workflow.

## Quick Workflow

1. Inventory units: list enabled services and timers, and justify each one for the host's role.
2. Audit unit file trust: ownership, writability, and drop-in overrides for every enabled unit.
3. Apply sandboxing directives per service, starting with the network-exposed ones (web, mail, dns, ssh-adjacent tooling).
4. Harden the journal: persistent storage, sane retention, forwarding to a central collector, and access controls.
5. Verify with `systemd-analyze security` per unit and re-run after every change.
6. Bake the hardened units into provisioning so new hosts inherit them.
7. Monitor: alert on unit file changes, new timers, and journal gaps.

## 1. Why systemd is a security boundary

Attackers love systemd because persistence is one `systemctl enable` away (MITRE T1543, T1053), and defenders love it because a few unit directives can sandbox a service better than most hand-rolled wrappers. Treat every unit file as security-sensitive configuration: who can write it decides who can get root at next boot.

```bash
systemctl list-unit-files --state=enabled --type=service | wc -l
systemctl list-timers --all --no-pager | head -20
systemd-analyze security sshd.service | tail -5
```

Example output shape: the enabled service count (know your number per role; growth without a change ticket is a signal), the timer list (attackers hide in timers), and the `systemd-analyze security` exposure score for a key service. Run the timer list regularly: it is the cheapest persistence audit on the system.

## 2. Unit file trust: ownership and overrides

Unit files live in `/lib/systemd/system` (package-owned, do not edit), `/etc/systemd/system` (admin overrides), and `/run/systemd/system` (ephemeral). Only root should write any of them, and drop-ins in `/etc/systemd/system/<unit>.d/` deserve the same scrutiny as the unit itself because they silently modify behavior.

```bash
find /etc/systemd/system -type f ! -user root 2>/dev/null | head -10
find /etc/systemd/system /lib/systemd/system -type f -perm -0002 2>/dev/null | head -10
systemctl cat sshd.service | head -40
```

Expected: everything root-owned, nothing world-writable, and `systemctl cat` showing exactly the unit plus drop-ins you expect. An unexpected drop-in (for example one adding `ExecStartPre=/tmp/evil.sh`) is a persistence finding; treat unknown unit modifications as compromise indicators first.

## 3. Sandboxing: the directive toolkit

Systemd's sandboxing directives (`ProtectSystem`, `PrivateTmp`, `ProtectHome`, `CapabilityBoundingSet`, `SystemCallFilter`, `DynamicUser`, and more) constrain a compromised service's blast radius. The strategy: start with filesystem protections (cheap, rarely break things), then capabilities and syscall filters (test carefully), and measure with `systemd-analyze security` before and after. Full directive reference lives in the sandboxing sub-skill.

```bash
systemd-analyze security nginx.service 2>/dev/null | grep -E "Overall|EXPOSURE" | head -3
grep -E "^(ProtectSystem|PrivateTmp|NoNewPrivileges)" /lib/systemd/system/nginx.service 2>/dev/null
```

Example output shape: an exposure level (the analyzer rates 0-10) plus the directives present. Aim to move network-exposed services from the red zone toward green, one directive at a time, testing the service after each change. Sandboxing that breaks the service gets reverted; sandboxing is risk reduction, not a purity test.

## 4. Journal security: logs that survive incidents

Systemd's journal is the local log store, and attackers target it (MITRE T1070, Indicator Removal). Harden it: persistent storage so logs survive reboot, rate limiting so a flood cannot DoS logging, forwarding to an off-host collector so local tampering does not erase the trail, and restricted read access. Full detail lives in the journal-security sub-skill.

```bash
grep -E "^(Storage|SystemMaxUse|ForwardToSyslog|RateLimit)" /etc/systemd/journald.conf
journalctl --disk-usage
ls -ld /var/log/journal
```

Expected: `Storage=persistent`, bounded disk use, forwarding enabled to your collector, and `/var/log/journal` owned by root with group `systemd-journal` at 2755. Verify forwarding actually arrives at the collector; a forwarding directive that silently fails is worse than none because it creates false confidence.

## 5. Timers as the new cron: audit them like cron

Systemd timers replaced cron for many tasks, and they inherit cron's abuse potential with better logging. Audit them with the same rigor: who created them, what they run, and whether the executed paths are writable by non-root.

```bash
systemctl list-timers --all --no-pager
for t in $(systemctl list-timers --all --no-legend --no-pager | awk '{print $NF}'); do systemctl cat "$t" 2>/dev/null | grep -E "ExecStart|User="; done | head -20
```

Example output shape: each timer's command line and user. Any timer running a writable script as root is the systemd equivalent of the classic cron privesc, so check script ownership exactly as you would for cron. Unknown timers get the same incident-response-first treatment as unknown cron jobs.

## Edge cases

- `systemd-analyze security` scores are heuristic, not gospel: a 9.6 "unsafe" rating on a database that legitimately needs raw disk access is expected, so use the score as a prioritization aid and document justified exceptions.
- Sandboxing directives interact: `ProtectSystem=strict` with `ReadWritePaths` needs every write path listed or the service fails in confusing ways, so add directives incrementally and test rather than copying a maximal template blindly.
- Drop-in overrides in `/etc/systemd/system/<unit>.d/` survive package upgrades that replace the main unit file, which is both the correct way to customize and a persistence mechanism attackers abuse; audit the `.d` directories, not just the units.
- Container environments often run systemd incompletely or not at all; the journal and unit hardening here applies to the host and full VMs, while containers need the container-hardening approach instead.
- `DynamicUser=yes` breaks services that need stable UIDs, persistent state keyed by user, or supplementary group memberships; it is excellent for stateless services and wrong for databases, so apply per-service.
- Journal rate limiting (`RateLimitIntervalSec`, `RateLimitBurst`) can drop log lines during genuine traffic spikes; tune against real peak load or you will lose the exact logs you need during an incident.
- Masked units (`systemctl mask`) can still be started via direct binary execution; masking is a guardrail against accidental or dependency-triggered starts, not a security boundary against a determined local attacker.

## Escalation

- If you find an unknown enabled service, timer, or unit drop-in, treat it as potential persistence: preserve the unit files and journal entries first, then investigate, and only then disable.
- If sandboxing breaks a production service, revert the last directive, document the incompatibility, and apply the remaining directives; partial sandboxing with a documented gap beats a reverted-everything rollback.
- If journal forwarding to the collector fails, escalate to the logging team immediately: silent log loss during normal operations means zero visibility during an incident.
- If a vendor unit file ships dangerously permissive settings, prefer a drop-in override in `/etc` over editing the package file (which upgrades will clobber), and file the issue with the vendor.

## Detection and defender view

Systemd is both the thing being defended and a detection source. Defenders monitor unit file integrity (AIDE watches on `/etc/systemd/system`), alert on new timers and newly enabled services, and centralize the journal so local tampering is visible as a gap. MITRE mappings: T1543 (Create or Modify System Process) and T1053 (Scheduled Task/Job) are the persistence techniques systemd enables and that unit auditing counters; T1070 (Indicator Removal) is what journal hardening counters; sandboxing directives are mitigations across execution and privilege escalation techniques. The `systemd-analyze security` score per service, tracked over time, is a simple metric for the hardening program's progress.

## Key references

- MITRE ATT&CK T1543 Create or Modify System Process: https://attack.mitre.org/techniques/T1543/
- MITRE ATT&CK T1053 Scheduled Task/Job: https://attack.mitre.org/techniques/T1053/
- systemd.exec manual (sandboxing directives): https://www.freedesktop.org/software/systemd/man/systemd.exec.html
- systemd.unit manual: https://www.freedesktop.org/software/systemd/man/systemd.unit.html
- systemd-analyze manual: https://www.freedesktop.org/software/systemd/man/systemd-analyze.html
- CIS distribution benchmarks (systemd and service sections): https://www.cisecurity.org/cis-benchmarks/
