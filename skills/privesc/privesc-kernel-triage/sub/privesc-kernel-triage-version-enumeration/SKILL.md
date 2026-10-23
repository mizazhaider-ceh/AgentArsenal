---
name: privesc-kernel-triage-version-enumeration
description: Use when authorized kernel privilege escalation triage needs
  exact kernel facts, not guesses. Covers uname fields and what each one
  tells you, /proc/version and distribution build strings, compile dates
  versus patch dates, loaded module and driver enumeration on Linux and
  Windows, enabled kernel subsystems (user namespaces, eBPF, io_uring),
  sysctl values that gate exploit prerequisites, and recording a kernel
  fingerprint for exploit matching. For authorized pentests, labs, and
  CTFs only.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-kernel-triage]
extends: []
parent: privesc-kernel-triage
relates: [privesc-linux, privesc-windows, privesc-kernel-triage-exploit-db-matching]
tools:
  - name: Python
    version: 3.12
  - name: nmap
    version: 7.98
---
Exploit matching lives or dies on precision: an exploit for upstream 5.15.0 may not apply to distribution build 5.15.0-91, and a user-namespace exploit is dead when user namespaces are disabled. This sub-skill covers extracting a complete kernel fingerprint on Linux and Windows: version strings, build metadata, compile dates, loaded modules and drivers, and the subsystem and sysctl prerequisites that exploits require. Authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Collect the full version identity: `uname -a`, `/proc/version`, distro release files, and on Windows the exact build from `systeminfo`.
2. Record the compile or build date and compare it against the CVE fix dates you will check later.
3. Enumerate loaded modules (`lsmod`) on Linux and drivers (`driverquery /v`) on Windows; note third-party or unusual entries.
4. Check exploit-gating subsystems: user namespaces, eBPF availability, io_uring, and related sysctls.
5. Record CPU architecture and any virtualization or container indicators.
6. Save the fingerprint to a file; every later matching step references it instead of re-running enumeration.

## 1. Linux version identity

Collect every version field; each answers a different matching question.

```bash
uname -a
uname -r; uname -v; uname -m
cat /proc/version
cat /etc/os-release
```

Example output shape:

```
Linux web01 5.15.0-91-generic #101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux
```

Read it as: upstream `5.15.0`, Ubuntu build `-91`, SMP build compiled Nov 14 2023, x86_64. The compile date is your first patch heuristic: a CVE fixed upstream in October 2023 is likely included in a November 2023 distro build, but confirm against the distro's CVE tracker rather than assuming. Also check `/boot` for available kernel images and `dpkg -l | grep linux-image` or `rpm -qa | grep kernel` for the installed package version.

## 2. Compile date versus patch date reasoning

Backported fixes mean the version number lies; the build date and the distro tracker tell the truth.

```bash
stat -c %y /boot/vmlinuz-$(uname -r) 2>/dev/null
```

Workflow: note the CVE's upstream fix commit date, then check the distro security tracker (Ubuntu CVE pages, Red Hat CVE database) for whether that fix landed in the installed build. If the tracker says the build is patched, stop; if it says vulnerable or the package predates the fix, the CVE stays on the candidate list. Record the tracker URL and verdict for each CVE in your notes.

## 3. Loaded modules and drivers

Exploits frequently target specific modules or third-party drivers rather than core kernel code.

```bash
lsmod | head -30
ls -la /lib/modules/$(uname -r)/ 2>/dev/null | head
```

Example output shape: standard modules (ext4, nvme, x86 stuff) plus possibly unusual entries like `vboxguest`, a vendor driver, or an out-of-tree module. Unusual or third-party modules are prime suspects: search exploit databases by module name. On Windows:

```powershell
driverquery /v | findstr /i /v "Microsoft"
systeminfo | findstr /i "OS Version"
```

Non-Microsoft drivers with known CVEs are the Windows equivalent of the third-party module path. Record driver names and versions exactly.

## 4. Subsystem and sysctl prerequisites

Many modern Linux exploits need a subsystem that hardening guides disable. Check before matching.

```bash
sysctl kernel.unprivileged_userns_clone 2>/dev/null
cat /proc/sys/kernel/unprivileged_bpf_disabled 2>/dev/null
grep -i io_uring /boot/config-$(uname -r) 2>/dev/null
unshare --user --map-root-user id 2>&1 | head -2
```

Example output shape: `unshare` succeeding with `uid=0(root)` inside the namespace proves unprivileged user namespaces work, which keeps userns exploit candidates alive. `unprivileged_bpf_disabled=2` kills unprivileged eBPF exploit paths. `io_uring` in the kernel config keeps io_uring CVE candidates alive. Each prerequisite you verify narrows the exploit list honestly instead of by hope.

## 5. Architecture and environment indicators

Record architecture and whether the target is virtualized or containerized, because exploits are architecture-specific and container kernels are host kernels.

```bash
uname -m; lscpu | grep -i "model name" | head -1
ls -la /.dockerenv 2>/dev/null; cat /proc/1/cgroup 2>/dev/null | head -5
systemd-detect-virt 2>/dev/null
```

An aarch64 target needs ARM exploit builds; an x86_64 exploit will not run. A container indicator changes the risk calculus entirely: kernel exploitation inside a container affects the host, which needs host-level authorization.

## Edge cases

- Some minimal containers lack `uname` full output or `/boot`; fall back to `/proc/version` and `/proc/sys/kernel/*` which are almost always present.
- Distro trackers sometimes mark a CVE as not-affected for reasons unrelated to patching (configuration not present); read the notes, not just the status word.
- `lsmod` can be empty in containers that share the host's module set without visibility; the host kernel version still governs exploitability.
- Windows build numbers from `systeminfo` lag behind actual patch state when updates are pending reboot; check `wmic qfe list` for installed KBs.
- Custom-compiled kernels (common in CTFs) have no distro tracker; match purely on upstream version plus the config file if exposed.
- Kernel headers may be absent, which blocks compiling exploits on target; plan to cross-compile on your attack box for the exact architecture.

## Escalation

- If version enumeration shows a fully patched kernel, close the kernel path quickly and return to misconfiguration vectors; do not burn hours on patched kernels.
- When the distro tracker is ambiguous, test exploit prerequisites empirically (unshare, bpf checks) rather than debating the tracker.
- If one subsystem is disabled (userns off), pivot the matching to CVEs in subsystems that are enabled; the fingerprint tells you which lists to search.
- Combine with the exploit-db-matching sub-skill: the fingerprint file you saved is its required input.

## Detection and defender view

Version enumeration itself is low-noise (reading files and sysctls), which is why it should always precede any exploit attempt. Defenders make this triage harder for attackers by patching promptly, using livepatch to shrink reboot windows, and disabling unneeded subsystems, which removes whole exploit classes regardless of version. From the authorized tester side, a precise fingerprint demonstrates methodology in the report: it shows you ruled candidates in and out on evidence, not on version-number guessing.

## Key references

- MITRE ATT&CK T1068 (Exploitation for Privilege Escalation)
- uname manual: https://man7.org/linux/man-pages/man1/uname.1.html
- Ubuntu CVE tracker: https://ubuntu.com/security/cves
- Red Hat CVE database: https://access.redhat.com/security/updates/cve
- Microsoft Security Update Guide: https://msrc.microsoft.com/update-guide
- Kernel config documentation: https://www.kernel.org/doc/html/latest/admin-guide/sysctl/kernel.html
