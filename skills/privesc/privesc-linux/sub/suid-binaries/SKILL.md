---
name: suid-binaries
description: Use when you have a low-privilege Linux shell on an authorized
  engagement and need to check SUID binaries for privilege escalation.
  Covers enumerating SUID and SGID files, checking each against GTFOBins
  techniques, testing exploitability safely, and distinguishing real paths
  from dead ends. Use when starting Linux privilege escalation, when LinPEAS
  flags SUID files, or when you need a quick root path without kernel
  exploits.
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
  - name: Sudo
    version: 1.9
---

SUID binaries run with the file owner's privileges, so a SUID root binary
with a shell escape is a direct path to root. This skill covers the SUID
enumeration and exploitation workflow on authorized engagements: finding
every SUID and SGID file, checking each against known techniques, and
testing safely. It is the highest-yield privesc check on Linux, and it
takes minutes, so it always comes early in the escalation order.

## Quick Workflow

1. Enumerate all SUID and SGID binaries on the system.
2. Filter out the standard, non-exploitable ones you recognize.
3. Look up each unusual binary in GTFOBins for SUID techniques.
4. Test the technique in a way that proves privilege without damage.
5. Confirm the elevated shell and record the exact binary and method.
6. Check for SUID scripts and writable SUID binaries as bonus paths.

## 1. Enumeration

```bash
# All SUID binaries, sorted for review
find / -perm -4000 -type f 2>/dev/null | sort

# SGID binaries too (group privilege, sometimes just as good)
find / -perm -2000 -type f 2>/dev/null | sort

# Focus on the unusual: exclude the standard system paths
find / -perm -4000 -type f 2>/dev/null | grep -v -E '^/(usr/bin|bin)/' | sort

# Check for SUID files writable by your user (misconfiguration gold)
find / -perm -4000 -writable -type f 2>/dev/null

# Capabilities are the modern SUID: check those too
getcap -r / 2>/dev/null | grep -v -E '^$'
```

Read the whole list before testing anything. The standard set (passwd,
sudo, su, mount) is noise; the custom or third-party binary in `/opt` or
the user's home is the signal.

## 2. Testing GTFOBins techniques

```bash
# Example pattern: check the binary's help for shell escapes first
/usr/local/bin/custom-tool --help 2>&1 | head -20

# Classic testable cases (verify against GTFOBins for the exact binary):
# vim-like SUID: escape to shell from inside the program
# find-like SUID: -exec /bin/sh
# less-like SUID: !/bin/sh from the pager
# python-like SUID: python -c 'import os; os.system("/bin/sh")'

# Safe proof: run id or whoami through the technique, not a full shell first
# then escalate to the shell only to confirm
```

Test with a read-only proof (`id` showing uid 0) before dropping into a
root shell. The finding is proven at `uid=0`; the interactive shell is
just confirmation.

## 3. Writable and script edge cases

```bash
# SUID shell scripts: the kernel ignores SUID on scripts on most
# systems, but check anyway (some configurations honor it)
/tmp/check.sh 2>/dev/null; file /usr/local/bin/*.sh 2>/dev/null | head

# SUID binary with a writable library or config it loads
strings /usr/local/bin/vuln-suid | grep -E '\.so|/etc/' | head -10
ldd /usr/local/bin/vuln-suid 2>/dev/null | grep 'not found'

# Relative path execution inside a SUID binary (PATH hijack)
strings /usr/local/bin/vuln-suid | grep -E 'system\(|popen|exec' | head -5
```

A SUID binary that calls `system("ls")` without a full path is exploitable
through PATH manipulation. A SUID binary loading a missing shared library
is exploitable by planting the library. Both are worth more in the report
than a plain GTFOBins hit because they show custom-code flaws.

## Edge cases

- The binary is SUID but drops privileges immediately. Some programs
  sanitize; test the actual technique rather than assuming SUID equals
  root.
- GTFOBins has no entry for the binary. Read its strings and help text;
  custom binaries with shell escapes are common in CTF and enterprise
  alike.
- The filesystem is mounted nosuid. Check `mount | grep nosuid`; SUID
  bits on nosuid mounts do nothing, which is a defensive finding.
- Containers confuse the picture. SUID inside a container escalates to
  container root, not host root; note which boundary you crossed.

## Escalation

- No SUID path works: move to sudo-misconfig, the next check in the
  privesc-linux order, then cron-abuse and kernel-exploits.
- You found a custom SUID binary with a memory corruption bug: that is a
  binary exploitation task; note it and time-box the exploit attempt.
- The SUID binary is exploitable but unstable: get the proof (`id`
  output) in one clean run and stop; repeated crashes look like
  instability in the report and risk the engagement.

## Detection and defender view

Defenders see SUID exploitation as a low-privilege process suddenly
running as root, which EDR and auditd can flag through parent-child
process anomalies. Unusual SUID binaries appear in file integrity
monitoring. Defenses are minimizing SUID binaries (remove the bit where
unneeded), mounting user-writable areas nosuid, using capabilities
instead of full SUID root, and monitoring for new SUID files.

## Key references

- MITRE ATT&CK T1548.001 (Abuse Elevation Control Mechanism: Setuid and
  Setgid).
- CWE-250 (Execution with Unnecessary Privileges).
- CWE-732 (Incorrect Permission Assignment for Critical Resource).
- GTFOBins: SUID techniques per binary.
