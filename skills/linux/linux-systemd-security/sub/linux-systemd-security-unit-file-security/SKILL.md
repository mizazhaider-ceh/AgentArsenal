---
name: linux-systemd-security-unit-file-security
description: Use when auditing or hardening systemd unit files on a Linux
  server you administer. Covers unit file ownership and writability checks,
  auditing drop-in overrides, safe privilege settings (User, Group,
  NoNewPrivileges, CapabilityBoundingSet), ExecStart path hygiene, timer
  unit auditing for persistence abuse, and masking unneeded services.
  Defensive hardening mapped to MITRE ATT&CK T1543 Create or Modify System
  Process; no exploitation content.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-systemd-security]
extends: []
parent: linux-systemd-security
relates: [linux-systemd-security, linux-hardening-baseline, linux-log-intrusion-analysis]
tools:
  - name: systemd
    version: 255
  - name: AIDE
    version: 0.18
  - name: auditd
    version: 3.1
---

A unit file is a recipe for running code as a chosen user at boot, on a timer, or on demand. Whoever can write one (or a drop-in that modifies one) can get persistent privileged execution, which is why unit files are security-sensitive configuration and a favorite persistence mechanism (MITRE T1543). This sub-skill covers the defensive side: auditing unit trust, setting safe privilege options in your own units, keeping ExecStart paths clean, auditing timers, and disabling what you do not need. For systems you own or administer; no exploitation content. The parent skill sets the strategy; this file is the unit-level reference.

## Quick Workflow

1. List all enabled units and timers; justify each against the host's role.
2. Audit ownership and writability of unit files and every `.d` drop-in directory.
3. Review privilege settings in enabled units: User, Group, NoNewPrivileges, CapabilityBoundingSet, AmbientCapabilities.
4. Check ExecStart and ExecStartPre paths: absolute, root-owned, non-writable by service users.
5. Audit timer units like cron jobs: command, user, and writability of everything they touch.
6. Mask or disable unneeded services; verify they stay down after reboot.
7. Add unit paths to integrity monitoring and re-audit on a schedule.

## 1. Unit file trust: ownership, writability, drop-ins

The trust chain is: package files in `/usr/lib/systemd/system` (do not hand-edit), admin config in `/etc/systemd/system`, ephemeral in `/run/systemd/system`. Drop-ins in `/etc/systemd/system/<name>.d/*.conf` merge silently, so auditing the unit without its drop-ins is auditing half the configuration.

```bash
find /etc/systemd/system /run/systemd/system -type f -name "*.conf" -o -type f -name "*.service" -o -type f -name "*.timer" 2>/dev/null | head -30
find /etc/systemd/system -type f ! -user root -o -type f -perm -0002 2>/dev/null | head -10
systemctl cat cron.service 2>/dev/null | head -30
```

Expected: all unit files and drop-ins root-owned and non-world-writable; `systemctl cat` shows the merged result you expect, with no surprise drop-ins. Any non-root-writable unit file or unknown drop-in is investigated as potential persistence before anything else. After any change, run `systemctl daemon-reload` and verify the merged view again.

## 2. Privilege settings in your own units

When you write or override a unit, set the privilege floor explicitly. Run as a dedicated unprivileged user, forbid privilege gains, and bound capabilities to the minimum.

```ini
[Service]
User=appsvc
Group=appsvc
NoNewPrivileges=true
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
ProtectSystem=strict
ReadWritePaths=/var/lib/myapp
```

`NoNewPrivileges=true` is the single highest-value line: it prevents the service and its children from ever gaining new privileges (via setuid, file capabilities, or LSM transitions). `User=`/`Group=` drop root at start; `CapabilityBoundingSet` limits which capabilities can ever be held. Verify with `systemctl show <unit> -p User,NoNewPrivileges,CapabilityBoundingSet` and confirm the process actually runs as the intended user with `ps -o user= -p <pid>`.

## 3. ExecStart path hygiene

Every path a unit executes must be absolute, root-owned, and writable only by root. A relative path, a PATH lookup, or a writable script in ExecStart is a privilege escalation waiting for the next boot.

```bash
systemctl show myapp.service -p ExecStart,ExecStartPre,ExecReload | tr ';' '\n' | head -10
stat -c "%a %U %n" /usr/local/bin/myapp /opt/myapp/start.sh 2>/dev/null
```

Expected: absolute paths only, each binary and its parent directories root-owned and non-writable by the service user. Check parent directories too: a root-owned script in a world-writable directory is still hijackable. Never use bare command names in ExecStart (no PATH lookup happens, but reviewers and future editors assume safety that is not enforced); always spell out the full path.

## 4. Timer auditing: the systemd cron

Timers are cron with better logging and the same abuse potential. Audit every timer's command line, user, and the writability of the executed paths, exactly as you would audit cron.

```bash
systemctl list-timers --all --no-pager --no-legend | awk '{print $NF}' | while read t; do
  echo "== $t"; systemctl show "$t" -p Unit 2>/dev/null
done | head -20
for s in $(systemctl list-timers --all --no-legend --no-pager | awk '{print $NF}' | sed 's/.timer$/.service/'); do
  systemctl show "$s" -p ExecStart,User 2>/dev/null | grep -q . && echo "$s: $(systemctl show "$s" -p ExecStart,User 2>/dev/null)"
done | head -20
```

Example output shape: each timer mapped to its service, ExecStart, and User. Flag any timer whose service runs as root and executes a path writable by non-root users. Also check `Persistent=true` timers that catch up after downtime (an attacker can use these to guarantee execution) and timers with randomized delays used to hide in noise. Unknown timers follow the incident-response-first rule: preserve, investigate, then disable.

## 5. Disabling and masking unneeded services

Every enabled service is attack surface and a potential persistence slot. Disable what the role does not need; mask what must never run.

```bash
systemctl list-unit-files --type=service --state=enabled | head -30
systemctl disable --now avahi-daemon.service 2>/dev/null
systemctl mask telnet.socket 2>/dev/null
systemctl list-unit-files --type=service | grep -E "masked|enabled" | wc -l
```

`disable` stops autostart; `mask` symlinks to `/dev/null` so nothing (including dependencies) can start it. Verify after reboot that masked units stayed down. Keep a per-role allowed-services list; anything enabled that is not on the list is a finding. Remember masking is a guardrail, not a boundary: it stops accidental and dependency starts, not direct binary execution by an attacker who already has shell.

## Edge cases

- Package upgrades replace files in `/usr/lib/systemd/system` but preserve `/etc/systemd/system` overrides and drop-ins; always customize via drop-ins so upgrades do not silently revert your hardening.
- `systemctl cat` shows the merged configuration, but `systemctl show` shows runtime properties; use `cat` for auditing what is configured and `show` for verifying privilege settings took effect.
- User units (`~/.config/systemd/user/`) run as the user and are a persistence vector that system-level audits miss; include user units in the audit on multi-user systems, especially for service accounts.
- Transient units created via the D-Bus API (`systemd-run --scope`, API calls) do not live in unit files at all; auditd rules on the systemd D-Bus interface and `systemctl list-units --all` catch these where file audits cannot.
- `NoNewPrivileges=true` breaks services that legitimately need setuid helpers or capability transitions (some container runtimes, `ping` wrappers); test per service and document exceptions rather than dropping the directive fleet-wide.
- Timer accuracy (`AccuracySec`) and randomized delays mean a malicious timer may not fire on a predictable schedule; when hunting, look at the unit definition, not at whether you observed it fire.
- On systems with SELinux, unit file contexts matter: a correctly written unit with the wrong SELinux label may fail or behave unexpectedly, so check `ls -Z` on custom units when troubleshooting denials.

## Escalation

- If audit finds an unknown unit, drop-in, or timer, escalate to incident response workflow: preserve the files and journal entries, determine how they arrived, and check for related indicators before disabling.
- If a vendor or package unit requires dangerous settings (root user, writable ExecStart path), escalate to the vendor as a security issue and apply a drop-in mitigation in the meantime; do not hand-edit package files.
- If disabling a service breaks a hidden dependency (monitoring agent, backup client), re-enable with documentation rather than leaving the host unmonitored; the allowed-services list gets updated, not silently violated.
- If user units or D-Bus transient units are outside your monitoring coverage, escalate the gap to the security team: file-only integrity monitoring has a blind spot that needs a runtime control.

## Detection and defender view

Unit file security is monitored through integrity and behavior. AIDE or auditd watches on `/etc/systemd/system` (including `.d` directories) alert on any unit modification; `systemctl list-timers` and enabled-unit diffs on a schedule catch new persistence; journal entries for unit starts (`systemd[1]: Started ...`) give a timeline. MITRE T1543 (Create or Modify System Process) is the technique this counters, and unexpected unit changes are treated as compromise indicators until proven otherwise. Centralize the journal so that an attacker who modifies units cannot erase the record of the service starts that followed.

## Key references

- MITRE ATT&CK T1543 Create or Modify System Process: https://attack.mitre.org/techniques/T1543/
- MITRE ATT&CK T1053 Scheduled Task/Job: https://attack.mitre.org/techniques/T1053/
- systemd.unit manual: https://www.freedesktop.org/software/systemd/man/systemd.unit.html
- systemd.service manual: https://www.freedesktop.org/software/systemd/man/systemd.service.html
- systemd.timer manual: https://www.freedesktop.org/software/systemd/man/systemd.timer.html
- CIS distribution benchmarks (service and cron-equivalent sections): https://www.cisecurity.org/cis-benchmarks/
