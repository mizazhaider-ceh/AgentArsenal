---
name: privesc-linux-vectors
description: Use when you hold a low-privilege Linux shell on an authorized
  penetration test, lab, or CTF and need a systematic map of every local
  privilege escalation vector before you exploit anything. Covers SUID and
  SGID binaries, sudo rule abuse, Linux capabilities, cron and systemd timer
  hijacking, PATH hijacking, writable scripts and libraries, NFS root
  squashing gaps, LD_PRELOAD tricks, and kernel attack surface triage. Built
  for authorized engagements only: enumerate first, verify each finding by
  hand, exploit the quietest reliable path, and capture evidence for the
  report.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [privesc-linux, privesc-kernel-triage]
tools:
  - name: linpeas
    version: 2.x
  - name: Python
    version: 3.12
  - name: findutils
    version: 4.9
  - name: sudo
    version: 1.9.x
---
Linux privilege escalation is won during enumeration, not during exploitation. This skill is the parent map of every major Linux escalation vector, and it exists for authorized penetration tests, lab exercises, and CTFs only. Never apply these techniques to systems you do not have explicit written permission to test. The method is always the same: stabilize the shell, enumerate every vector class systematically, verify each candidate finding by hand, exploit the lowest-noise reliable path, and capture evidence for the report. Most wins come from misconfigurations (sudo rules, SUID binaries, cron jobs, capabilities, writable files), which are quieter and safer than kernel exploits. Deep dives for each vector live in the sub-skills.

## Quick Workflow

1. Stabilize the shell and record the baseline: `whoami`, `id`, `uname -a`, distro, hostname, network position.
2. Run LinPEAS with full checks and exfiltrate the output for local analysis instead of reading it inside a fragile shell.
3. Work the vector classes in order of noise and reliability: sudo rules, SUID/SGID binaries, capabilities, cron and timers, writable files, PATH, NFS, kernel.
4. Verify every candidate by hand before exploiting: read the exact sudoers line, confirm the permission bits, inspect the cron script contents.
5. Exploit the quietest reliable vector first; misconfiguration abuse leaves less forensic trace and rarely crashes the host.
6. Confirm privilege with `id` and `hostname`, capture proof, and record exact commands and outputs for the report.
7. If `/.dockerenv` exists or cgroup paths show docker or kubepods, switch to the container escape checklist.

## 1. SUID and SGID binaries

Find every SUID and SGID binary, then filter out the standard ones. Any unusual SUID binary is a candidate.

```bash
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null
```

Example output shape: a long list of standard entries (`/usr/bin/sudo`, `/usr/bin/passwd`, `/usr/bin/su`) plus possibly one odd entry such as `/usr/local/bin/backup-tool` or `/opt/vuln/viewer`. Anything you do not recognize from a default install goes on the shortlist.

Check each shortlisted binary against GTFOBins for known escalation primitives, then check for shared library hijacking with `ldd` and `strings`. See the `privesc-linux-vectors-suid-binaries` sub-skill for the full technique.

## 2. Sudo rules and sudoers misconfigurations

`sudo -l` is the single highest-value command on a Linux privesc engagement. Read every line, including the `env_keep` and `secure_path` details.

```bash
sudo -l
```

Example output shape:

```
User app may run the following commands on web01:
    (ALL) NOPASSWD: /usr/bin/vim
    (root) /usr/bin/python3 /opt/scripts/*.py
```

NOPASSWD entries are immediate wins when the binary has a GTFOBins entry. Wildcards in the path invite argument injection. Binaries run as another user (not root) can still be stepping stones. The `privesc-linux-vectors-sudo-misconfigurations` sub-skill covers parsing, `sudoedit`, `LD_PRELOAD` via sudo, and `env_keep` abuse.

## 3. Linux capabilities

Capabilities split root's power into pieces, and several pieces are equivalent to root. Enumerate them on files and on your own processes.

```bash
getcap -r / 2>/dev/null
capsh --print | grep -i current
```

Dangerous capabilities include `cap_setuid` (become any UID), `cap_dac_read_search` and `cap_dac_override` (read or write any file), `cap_sys_ptrace` (inject into root processes), `cap_sys_module` (load a kernel module), and `cap_sys_admin` (broadly equivalent to root). A binary with `cap_setuid+ep` and a Python interpreter with `cap_dac_read_search+ep` are both classic wins.

## 4. Cron jobs and systemd timers

List system cron files, user crontabs, and systemd timers, then inspect every script a scheduled job executes for writability.

```bash
cat /etc/crontab; ls -la /etc/cron.d/ /etc/cron.hourly/ /var/spool/cron/crontabs/
systemctl list-timers --all
```

Example output shape: a root cron entry like `*/5 * * * * root /opt/backup.sh` where `/opt/backup.sh` is writable by your user means you own the box within five minutes. Wildcards in the cron command line (for example `tar cf /backup.tar *` run as root in a writable directory) enable wildcard injection. PATH hijacking applies when cron uses a relative command. Full coverage is in `privesc-linux-vectors-cron-and-path-hijacking`.

## 5. Writable files, PATH, and library hijacking

Writable scripts executed by root, writable directories in root's PATH, and missing shared libraries are all escalation paths.

```bash
find / -writable -type f 2>/dev/null | grep -v -E "^/(proc|sys|dev)" | head -30
echo $PATH
```

If root's PATH contains a directory you can write to, drop a malicious binary with the name of a command the root job calls. If an SUID binary links a library from a writable path (`ldd` shows `not found` or a writable directory), compile a hostile replacement. `LD_PRELOAD` works when a privileged binary preserves the environment variable.

## 6. NFS shares and other network vectors

Check for NFS mounts with `no_root_squash`, which lets a remote root act as root on the share.

```bash
cat /etc/exports
showmount -e 127.0.0.1 2>/dev/null
mount | grep nfs
```

With `no_root_squash`, mount the share from your attack box as root, drop an SUID binary onto it, and execute it on the target. Also check for writable NFS-mounted script directories and for credentials in `/etc/fstab` or automounter maps.

## 7. Kernel attack surface triage

Kernel exploits are the last resort: they can crash the target and burn the engagement. Triage the kernel version and patch level first, match against public exploits, and test safely.

```bash
uname -r; cat /proc/version; ls /boot 2>/dev/null
```

Record the exact version string, distribution kernel build, and compile date before matching anything. The `privesc-kernel-triage` skill and its sub-skills cover version enumeration, exploit matching, and safe testing discipline.

## Edge cases

- LinPEAS output can exceed shell scrollback; always redirect to a file and exfiltrate it, then grep locally instead of paging inside the reverse shell.
- `sudo -l` may prompt for a password; try the user's known passwords and check for cached credentials in history, config files, and environment variables first.
- SUID binaries that drop privileges or sanitize the environment defeat naive GTFOBins one-liners; verify the binary actually keeps euid 0 with a test like `id` before assuming the primitive works.
- Cron jobs may run in a minimal environment where your payload's dependencies (python3, PATH entries) do not exist; use absolute paths and static payloads.
- Capabilities on scripts are ignored by the kernel (capabilities only apply to binaries); a `cap_setuid` on a shell script is a dead end.
- NFS `root_squash` (the default) maps remote root to nobody, which kills the classic attack; confirm `no_root_squash` in the actual exports before investing time.
- Containers share the host kernel, so kernel exploits inside a container affect the host; treat container kernel exploitation as host exploitation with correspondingly higher authorization bar.

## Escalation

- If automated enumeration finds nothing, go fully manual: read `/etc/sudoers` and `/etc/sudoers.d/` directly, inspect every file in `/opt` and `/srv`, and review running processes with `ps aux` for custom services.
- When the shell is too fragile for enumeration, prioritize getting a stable reverse shell or SSH key access before continuing; half the failed privesc attempts fail on shell quality, not technique.
- If one vector class is hardened (no SUID oddities, tight sudoers), pivot to another class instead of forcing it: capabilities, timers, and NFS are frequently overlooked by defenders.
- When you find credentials (database passwords, API keys, reused passwords), try them against sudo and su before any exploit: credential reuse is the quietest escalation of all.

## Detection and defender view

Every vector in this skill has a defender counterpart: audit sudo usage with sudoreplay or centralized syslog, alert on new SUID binaries with file integrity monitoring, monitor cron file modifications, restrict capabilities with systemd sandboxing, and export NFS with `root_squash`. From the attacker's side, assume a mature target logs process execution (auditd execve rules) and file writes; prefer in-memory or single-command primitives over dropping persistent payloads where the rules of engagement require stealth. Kernel exploits are the noisiest option and the most likely to trigger EDR behavioral alerts or crash the host.

## Key references

- MITRE ATT&CK T1548 (Abuse Elevation Control Mechanism), T1053 (Scheduled Task/Job), T1068 (Exploitation for Privilege Escalation)
- GTFOBins: https://gtfobins.github.io (SUID and sudo binary primitives)
- LinPEAS: https://github.com/peass-ng/PEASS-ng (automated enumeration)
- sudoers manual: https://www.sudo.ws/docs/man/sudoers.man (sudo rule semantics)
- Linux capabilities manual: https://man7.org/linux/man-pages/man7/capabilities.7.html
- HackTricks Linux Privilege Escalation: https://book.hacktricks.xyz/linux-hardening/privilege-escalation (vector checklist)
