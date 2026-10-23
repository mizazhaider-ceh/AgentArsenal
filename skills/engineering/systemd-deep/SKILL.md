---
name: systemd-deep
description: Use when working deeply with systemd 256 on Linux: writing and
  debugging service, timer, socket, and target units, using systemctl and
  journalctl effectively, replacing cron jobs with systemd timers, analyzing
  boot time with systemd-analyze, creating drop-in overrides without editing
  vendor units, applying service sandboxing directives (ProtectSystem,
  PrivateTmp, NoNewPrivileges), managing dependencies and ordering, or
  diagnosing failed units and boot hangs. Use when the task mentions systemd
  services, timers, journald, unit files, or Linux service management.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening]
tools:
  - name: systemd
    version: 256
  - name: systemctl
    version: 256
  - name: journalctl
    version: 256
---

systemd is the init system and service manager on nearly every modern Linux
distribution: it starts the system, supervises services, schedules timers,
manages sockets, and collects logs in the journal. This skill covers
operating systemd 256 like a professional: unit anatomy, systemctl and
journalctl fluency, timers, drop-in overrides, dependency ordering,
service sandboxing, and boot and failure diagnosis.

## Quick Workflow

1. Identify the unit: `systemctl status <name>` shows state, recent logs,
   and the loaded unit file path.
2. Read the unit file (`systemctl cat <name>`) before changing anything.
3. Never edit vendor units in `/lib/systemd/system`; use drop-in
   overrides in `/etc/systemd/system/<name>.d/`.
4. After any unit change, run `systemctl daemon-reload`, then restart and
   verify.
5. Prefer timers over cron for scheduled work: they log to the journal,
   support dependencies, and survive reboots predictably.
6. Apply sandboxing directives to services that face the network or parse
   untrusted input.
7. Use `systemd-analyze` to find what slows the boot.
8. Diagnose failures with `journalctl -u`, `systemctl --failed`, and the
   service exit code.

## 1. systemctl fluency

```bash
# State of one service: loaded path, active state, recent log lines
systemctl status nginx --no-pager

# Full unit file as systemd sees it (includes drop-ins merged)
systemctl cat nginx

# Where a unit file lives and whether it is enabled
systemctl is-enabled nginx
systemctl show nginx -p FragmentPath,UnitFileState

# List all units, filter by state
systemctl list-units --type=service --state=running
systemctl list-units --type=service --state=failed
systemctl --failed

# Enable now and at boot in one command
sudo systemctl enable --now redis-server

# Mask a unit so nothing can start it (stronger than disable)
sudo systemctl mask telnet.socket
```

Reload vs restart: `reload` asks the daemon to re-read its own config
(nginx, sshd support it); `restart` kills and starts the process. For
systemd unit file changes you always need `daemon-reload` first:

```bash
sudo systemctl daemon-reload
sudo systemctl restart myapp.service
systemctl is-active myapp.service
```

## 2. Unit file anatomy

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My application API
Documentation=https://example.com/docs
Wants=network-online.target
After=network-online.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/bin/server --config /etc/myapp/config.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5s
# Resource limits
MemoryMax=1G
CPUQuota=150%
# Timeouts: fail fast instead of hanging the boot
TimeoutStartSec=30s
TimeoutStopSec=15s

[Install]
WantedBy=multi-user.target
```

Key choices: `Type=simple` for foreground processes (the common case);
`Type=forking` only for daemons that background themselves;
`Type=oneshot` for jobs that run and exit (used with timers).
`Restart=on-failure` restarts on crashes but not on clean exits; use
`Restart=always` for services that must never stop.

Enable and verify:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myapp.service
systemctl show myapp.service -p ActiveState,SubState,MainPID
```

## 3. Drop-in overrides (never edit vendor units)

Package updates overwrite `/lib/systemd/system/`. Put local changes in a
drop-in:

```bash
# Override the restart policy and add an env var for nginx
sudo systemctl edit nginx
```

That opens `/etc/systemd/system/nginx.service.d/override.conf`:

```ini
[Service]
Restart=on-failure
Environment="WORKER_PROCESSES=4"
# Clear a vendor list directive before replacing it:
# ExecStart=
# ExecStart=/usr/sbin/nginx -g 'daemon off;'
```

Rules: to replace a directive that accepts multiple values (like
`ExecStart`), first clear it with an empty assignment (`ExecStart=`),
then set the new value. Verify the merged result:

```bash
sudo systemctl daemon-reload
systemctl cat nginx | tail -20
sudo systemctl restart nginx
```

## 4. journalctl: reading the journal

```bash
# Logs for one unit, newest last, with pager
journalctl -u myapp.service

# Follow live, like tail -f
journalctl -u myapp.service -f

# Since the last boot, or a time window
journalctl -u myapp.service -b
journalctl --since "2026-10-23 06:00" --until "2026-10-23 07:00"

# Errors and worse across all units
journalctl -p err -b

# JSON output for parsing with jq
journalctl -u myapp.service -o json | jq -r '.MESSAGE' | tail -20

# Who is spamming the journal (disk pressure diagnosis)
journalctl --disk-usage
sudo journalctl --vacuum-size=500M
```

Persistent journal storage lives in `/var/log/journal/`; without it, logs
vanish on reboot. Set `Storage=persistent` in `/etc/systemd/journald.conf`
on servers.

## 5. Timers instead of cron

A timer needs two files: the `.service` (what to run) and the `.timer`
(when to run it).

```ini
# /etc/systemd/system/backup.service
[Unit]
Description=Nightly backup job

[Service]
Type=oneshot
User=backup
ExecStart=/usr/local/bin/backup.sh
```

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Run backup nightly

[Timer]
OnCalendar=02:30
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now backup.timer

# List timers with next run time and last result
systemctl list-timers --all

# Run the job right now without waiting for the schedule
sudo systemctl start backup.service
journalctl -u backup.service -n 30
```

`Persistent=true` runs missed jobs after downtime; `OnCalendar=` accepts
expressions like `Mon *-*-* 03:00:00` or `hourly`. Check the next elapse
with `systemd-analyze calendar "Mon *-*-* 03:00:00"`.

## 6. Dependencies and ordering

`Wants=` / `Requires=` control what gets pulled in; `After=` / `Before=`
control ordering only. A service can be ordered after something without
requiring it. Common mistake: using `After=` alone and assuming the
dependency starts too; add `Wants=` or `Requires=` for that.

Targets group units: `multi-user.target` is the normal server state,
`graphical.target` adds a desktop.

```bash
# Inspect the dependency tree of a service
systemctl list-dependencies myapp.service

# What target are we in, and what is the default
systemctl get-default
systemctl isolate multi-user.target   # drop out of graphical mode
```

## 7. Service sandboxing directives

These directives cut what a compromised service can touch. Apply
incrementally and test after each one, because over-strict settings break
legitimate services.

```ini
# /etc/systemd/system/myapp.service.d/sandbox.conf
[Service]
# Process cannot gain new privileges (breaks setuid helpers inside)
NoNewPrivileges=true
# Private /tmp invisible to other processes
PrivateTmp=true
# Mount /usr and /boot read-only; /etc read-only too with ProtectSystem=strict
ProtectSystem=strict
# Hide home directories
ProtectHome=true
# No write access anywhere except the listed paths
ReadWritePaths=/var/lib/myapp /var/log/myapp
# Restrict which syscalls the service may use
SystemCallFilter=@system-service
SystemCallArchitectures=native
# Private network namespace (for services needing no network at all)
# PrivateNetwork=true
```

Test sandboxing without breaking production:

```bash
# Dry-run: shows which syscalls would be denied
sudo systemd-run --pipe -p SystemCallFilter='~@clock' /bin/true
# Check the service still starts and functions
sudo systemctl restart myapp.service
journalctl -u myapp.service -n 20 | grep -iE 'denied|failed|error'
```

Verify what a running service is confined with:

```bash
systemctl show myapp.service -p NoNewPrivileges,PrivateTmp,ProtectSystem,ProtectHome
```

## 8. Boot analysis

```bash
# Total boot time and where it went
systemd-analyze
systemd-analyze blame | head -20

# Critical chain: what actually delayed the boot target
systemd-analyze critical-chain

# Visual SVG timeline (open in a browser)
systemd-analyze plot > /tmp/boot.svg

# Check for ordering cycles and unit file problems
systemd-analyze verify /etc/systemd/system/myapp.service
```

## 9. Diagnosing failed units

```bash
# Which units failed
systemctl --failed

# Full story: status, exit code, recent logs
systemctl status myapp.service --no-pager -l
journalctl -u myapp.service -b -n 50

# Decode the exit code (143 = SIGTERM, 137 = SIGKILL/OOM)
systemctl show myapp.service -p ExecMainStatus,ExecMainCode

# Was it the OOM killer? Check the kernel log
dmesg | grep -i 'killed process' | tail -5
journalctl -k | grep -i 'out of memory' | tail -5

# Start manually in the foreground to see the raw error
sudo -u appuser /opt/myapp/bin/server --config /etc/myapp/config.yaml
```

## Edge cases

- Unit file changed but behavior did not: you forgot
  `daemon-reload`. systemd reads unit files once at load; always reload
  after edits.
- Service starts then immediately stops with success: usually
  `Type=forking` on a program that does not fork, or `Type=simple` on a
  program that daemonizes itself. Match Type to reality; prefer simple.
- Timer exists but never fires: the `.timer` is not enabled
  (`systemctl is-enabled backup.timer`), or `Persistent=true` is missing
  and the machine was off at the scheduled time.
- `systemctl edit` opens an empty file and changes seem lost: you edited
  the wrong unit name; check `systemctl cat <name>` for the drop-in path.
- Sandboxing breaks the app at 3 AM: `ProtectSystem=strict` without the
  right `ReadWritePaths`, or `PrivateTmp=true` hiding a socket the app
  shares. Test restarts after every sandboxing change.
- Journal logs missing after reboot: `/var/log/journal/` does not exist;
  create it or set `Storage=persistent`.
- Boot hangs on a network mount: use `nofail` and `x-systemd.device-timeout=10s`
  in fstab for non-critical mounts so boot continues.

## Escalation

- `daemon-reload` hangs: a stuck unit can block it; find it with
  `systemctl list-jobs`, cancel with `systemctl cancel <job-id>`.
- System will not reach multi-user.target: boot with
  `systemd.unit=rescue.target` on the kernel command line, then inspect
  `journalctl -b -p err`.
- Suspected unit file syntax error: `systemd-analyze verify` on the file
  prints the offending line.
- Service killed instantly with no logs: run it via
  `systemd-run --pty --wait --collect` to capture stdout/stderr directly.
- Journal corruption: `journalctl --verify` checks files;
  `--vacuum-time=1s` plus restart clears a corrupt journal (logs are
  lost, so export first if they matter).

## Detection and defender view

For engineering operators, the defender view is about catching malicious
or careless unit changes: persistence via systemd is a top attacker
technique, and a misconfigured service is an outage waiting to happen.
Watch for:

```bash
# Recently changed or new unit files (possible persistence)
sudo find /etc/systemd/system -name '*.service' -mtime -7 -ls
sudo find /etc/systemd/system -name '*.timer' -mtime -7 -ls

# Units that are enabled but should not be
systemctl list-unit-files --state=enabled | grep -vE '^(sshd|nginx|cron)'

# Masked or suspicious: services running as root that do not need it
systemctl show -p User,ExecStart --value '*'

# Unexpected timers (common persistence mechanism)
systemctl list-timers --all
```

Red flags: a new service with `ExecStart` pointing at `/tmp` or a hidden
directory, timers with random-looking names, `WantedBy=multi-user.target`
units added outside package management, and journal gaps suggesting log
wiping (`journalctl --verify` failures). Baseline: keep unit files in
version control or a config management system and alert on drift.

## Key references

- systemd 256 documentation: https://www.freedesktop.org/software/systemd/man/latest/
- systemctl man page: https://www.freedesktop.org/software/systemd/man/latest/systemctl.html
- systemd.service man page: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- systemd.timer man page: https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html
- systemd.exec sandboxing: https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- MITRE ATT&CK T1543.002 (Systemd Service): persistence via services.
- MITRE ATT&CK T1053.006 (Systemd Timers): persistence via timers.
- CWE-732 (Incorrect Permission Assignment): world-writable unit files.
