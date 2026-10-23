---
name: privesc-kernel-triage
description: Use when authorized privilege escalation has exhausted
  misconfiguration vectors and the kernel is the remaining path, or when
  you need to rule the kernel out quickly. Covers precise kernel version
  and patch level enumeration on Linux and Windows, matching versions
  against public exploit databases, reading exploit code for constraints
  before running it, safe testing discipline (snapshots, one-shot payloads,
  crash risk assessment), and documenting kernel findings for the report.
  Kernel exploits can crash targets, so this skill treats them as the last
  resort with explicit warnings. For authorized pentests, labs, and CTFs
  only.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [privesc-linux, privesc-windows, privesc-linux-vectors]
tools:
  - name: Python
    version: 3.12
  - name: gcc
    version: 13.2.0
  - name: nmap
    version: 7.98
---
Kernel exploits are the highest-risk privilege escalation path: they can crash the target, corrupt data, and burn an engagement. This skill exists for authorized penetration tests, labs, and CTFs to impose discipline on kernel work: enumerate the kernel precisely, match it against public exploits with skepticism, read every line of exploit code before compiling it, test safely with snapshots and one-shot payloads, and document everything. The rule is simple: misconfigurations first, kernel last, and never a kernel exploit without explicit authorization and a recovery plan. The sub-skills break the workflow into version enumeration, exploit matching, and safe testing.

## Quick Workflow

1. Enumerate the kernel precisely: version string, distribution build, compile date, architecture, and loaded modules or drivers.
2. Determine the patch level: distribution kernel builds backport fixes, so the upstream version number alone is not enough.
3. Search public exploit databases for the exact version and read the exploit's header comments for supported ranges and constraints.
4. Read the full exploit source before compiling: understand what it touches, what it assumes, and how it can fail.
5. Assess crash risk and get explicit authorization; confirm snapshots or a rebuild path exist.
6. Test with a one-shot, minimal payload first; confirm privilege, capture evidence, and clean up artifacts.
7. If the kernel is patched or the risk is unacceptable, document the finding as informational and move on.

## 1. Why kernel version alone misleads

Distribution kernels backport security fixes without bumping the upstream version number. A target reporting `5.15.0` may be fully patched against a CVE that affects upstream 5.15.0, because the distro applied the fix to its `5.15.0-91` build.

```bash
uname -r
cat /proc/version
```

Example output shape: `5.15.0-91-generic` plus a build string with a distribution tag and compile date. The `-91` and the date are what you match against the distro's security tracker, not just `5.15.0`. On Windows the equivalent is the exact build number from `systeminfo`, since Microsoft patches per build. The `privesc-kernel-triage-version-enumeration` sub-skill covers extracting every relevant field.

## 2. Matching against public exploits

Search by exact version and by subsystem, then filter ruthlessly. Most search results will not apply.

```bash
searchsploit "Linux Kernel 5.15" | head -20
```

Read the exploit's comments for the supported version range, required configuration (for example `CONFIG_USER_NS` for userns exploits, or a specific loaded driver), and architecture. An exploit for `5.15.0` on x86_64 with user namespaces does not apply to an ARM target without them. Check the CVE's patch commit date against the target's kernel compile date: if the kernel was built after the fix was committed upstream and the distro tracks upstream closely, it is probably patched. Details are in `privesc-kernel-triage-exploit-db-matching`.

## 3. Reading exploit code before running it

Never compile and run exploit code you have not read. Read for: hardcoded offsets that assume a specific build, cleanup behavior on failure, whether it writes to disk, and what happens when the vulnerable path is absent.

```bash
head -60 exploit.c
grep -n -iE "offset|cleanup|exit|system\(|shell" exploit.c | head -20
```

Red flags: exploits that `panic()` the kernel on failure, that assume a single hardcoded kernel base, that fork-bomb on retry, or that were written for a different distribution's memory layout. Prefer exploits with explicit version checks that exit cleanly when the target does not match.

## 4. Safe testing discipline

Kernel testing on an authorized engagement follows a strict protocol.

- Snapshot or image the target before any kernel exploit attempt; on a CTF or lab, confirm you can reset the box.
- Get explicit authorization for kernel exploitation in the rules of engagement; many clients forbid it on production.
- Run the exploit exactly once with a minimal payload (spawn a shell or write a marker), not a reverse shell that retries forever.
- Have a recovery plan: who reboots the box, how long recovery takes, and what to do if it does not come back.
- Capture `dmesg` output after the attempt; oops messages confirm whether the vulnerable path was even reached.

The `privesc-kernel-triage-safe-testing` sub-skill expands this into a full checklist.

## 5. When not to run the exploit

Common stop conditions: the kernel build postdates the fix, the required subsystem or driver is absent, the exploit's constraints do not match the target architecture, the rules of engagement forbid kernel exploits, or no snapshot exists. In all these cases, document the kernel version, the CVEs you evaluated, and why each was ruled out. A well-reasoned negative finding is valuable report content.

## Edge cases

- Container kernels are host kernels: a kernel exploit inside a container escapes to the host, which raises the authorization bar to host-level approval.
- Some exploits need specific sysctls (for example `kernel.unprivileged_userns_clone`) or mounted filesystems; verify prerequisites instead of assuming defaults.
- Exploit code from old blog posts may target compilers or libc versions that no longer exist; build failures are common and do not prove the target is patched.
- Windows kernel exploits often depend on a vulnerable third-party driver being installed; `driverquery` tells you whether the prerequisite exists.
- A successful exploit that spawns a shell may still leave the kernel in an unstable state; treat the box as fragile afterward and finish evidence capture promptly.
- Time-based race exploits may need many attempts; each attempt is a crash opportunity, so weigh the retry count against the engagement's tolerance.

## Escalation

- If the kernel path is blocked, re-audit misconfigurations from a fresh angle: capabilities, NFS, and backup files are the vectors most often missed on the first pass.
- When one CVE does not fit, check adjacent CVEs in the same subsystem; kernel bugs cluster, and the patch level that blocks one may not block its neighbor.
- If kernel exploitation is authorized but no public exploit fits, consider whether a vulnerable driver or eBPF-adjacent feature offers a more targeted path than a core kernel bug.
- Document everything as informational findings even when you do not exploit: exact versions, evaluated CVEs, and the reasoning are report-grade content.

## Detection and defender view

Kernel exploitation is noisy: oops messages in `dmesg`, auditd anomalies, EDR kernel callbacks, and often a crash. Defenders prevent it with timely patching, livepatch services, and minimizing attack surface (disabling unneeded subsystems, restricting user namespaces and eBPF for unprivileged users). From the authorized tester side, kernel exploits are the most detectable technique in the privesc set and the most likely to cause an outage; this is precisely why they sit behind explicit authorization, snapshots, and a recovery plan.

## Key references

- MITRE ATT&CK T1068 (Exploitation for Privilege Escalation)
- Exploit-DB: https://www.exploit-db.com (searchsploit for local searching)
- Linux kernel CVE tracking per distro: https://ubuntu.com/security/cves, https://access.redhat.com/security/updates/cve
- Microsoft Security Update Guide (build-level patch mapping): https://msrc.microsoft.com/update-guide
- Kernel version enumeration: https://man7.org/linux/man-pages/man1/uname.1.html, /proc/version documentation
- Google Project Zero kernel exploit writeups (technique background): https://googleprojectzero.blogspot.com
