---
name: privesc-kernel-triage-safe-testing
description: Use when an authorized engagement has a shortlisted kernel
  exploit and you need to test it without crashing the target or breaking
  the rules of engagement. Covers authorization checkpoints, snapshot and
  recovery planning, reading exploit failure modes, one-shot minimal
  payloads, compiling for the exact target architecture, monitoring dmesg
  for oops confirmation, post-exploit stability handling, cleanup, and
  documenting the attempt for the report whether it succeeds or fails.
  For authorized pentests, labs, and CTFs only.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-kernel-triage]
extends: []
parent: privesc-kernel-triage
relates: [privesc-linux, privesc-windows, privesc-kernel-triage-exploit-db-matching]
tools:
  - name: gcc
    version: 13.2.0
  - name: Python
    version: 3.12
---
Running a kernel exploit is the point of no return in privilege escalation: success gives you the highest privilege on the box, failure can crash it. This sub-skill imposes a testing protocol for authorized engagements: authorization checkpoints, snapshots and recovery plans, exploit failure-mode analysis, one-shot minimal payloads, careful compilation, post-attempt monitoring, and honest documentation of both success and failure. Kernel exploits without this discipline are how engagements lose targets. Authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Confirm explicit authorization for kernel exploitation in the rules of engagement; if it is forbidden, stop here.
2. Verify the snapshot, image, or reset path and the recovery procedure with whoever owns the target.
3. Re-read the shortlisted exploit source end to end, mapping its failure modes and cleanup behavior.
4. Compile for the exact target architecture on your attack box when target tooling is missing.
5. Deploy a one-shot minimal payload: prove privilege with `id` or a marker file, not a retrying reverse shell.
6. Monitor `dmesg` and system responsiveness during and after the attempt.
7. Confirm or rule out, stabilize, clean up artifacts, and document the attempt with timestamps.

## 1. Authorization and recovery checkpoints

These are gates, not suggestions. Do not proceed past a failed gate.

- Written authorization: the rules of engagement or lab instructions explicitly permit kernel exploitation on this target. Verbal permission gets confirmed in writing.
- Recovery path: a VM snapshot, disk image, or lab reset button exists, and you have tested or confirmed it restores the box.
- Recovery owner: you know who reboots or restores the target and how long it takes, so a crash becomes an incident with a plan, not a surprise.
- Container check: if the target is a container, kernel exploitation affects the host and needs host-level authorization, which is a separate, higher gate.

Record each gate's status in your notes with a timestamp before compiling anything.

## 2. Reading failure modes in exploit source

Before running, map exactly how the exploit can fail by reading the code.

```bash
grep -n -iE "panic|oops|die\(|exit\(|fork\(|while *\(1\)" exploit.c | head -20
```

Classify what you find: clean exit on version mismatch (safe), infinite retry loops (noisy, crash-prone), writes to arbitrary kernel memory without validation (corruption risk), and missing cleanup of modified kernel structures (instability after success). Prefer exploits that check the target version first and exit quietly on mismatch. If the code modifies kernel function pointers or credentials structures, understand what it restores afterward; exploits that leave the kernel in a half-patched state cause delayed crashes.

## 3. Compiling for the target

Match the toolchain output to the target architecture and kernel expectations.

```bash
gcc -o exploit exploit.c -static 2>&1 | head -20
file exploit
```

Example output shape: `exploit: ELF 64-bit LSB executable, x86-64` must match `uname -m` on the target. Static linking avoids missing-library failures on minimal targets but inflates size; dynamic linking is fine when the target has a standard libc. Cross-compile when the target lacks gcc: `x86_64-linux-gnu-gcc` or `aarch64-linux-gnu-gcc` on your attack box. Transfer the binary and verify its integrity with a checksum before executing.

## 4. One-shot minimal payloads

The first run proves the primitive with the smallest possible blast radius.

```bash
./exploit id > /tmp/kout.txt 2>&1; echo "exit: $?" >> /tmp/kout.txt
cat /tmp/kout.txt
```

Example success shape: `uid=0(root) gid=0(root) groups=0(root)` in the output. A minimal payload does one thing: demonstrate uid 0. Do not start with a reverse shell that retries connections in a loop; if the primitive works, escalate to your operational payload afterward. Run exactly once, then evaluate before any retry: check `dmesg` for oops messages, check that the system still responds, and only then decide whether a second attempt is justified.

## 5. Monitoring during and after the attempt

Watch the kernel's own diagnostics for confirmation of what happened.

```bash
dmesg | tail -30
uptime
```

Example output shape on a triggered bug: oops traces naming the subsystem, register dumps, or `BUG:` lines. An oops naming the exact function the exploit targets confirms you reached the vulnerable path even if the exploit failed, which is valuable triage data. `uptime` and a simple command round-trip confirm the box survived. If the box stops responding, execute the recovery plan immediately and note the exact time of the crash for the report.

## 6. Post-success stability and cleanup

A successful kernel exploit may leave the kernel unstable; treat the box as fragile.

- Capture evidence immediately: `id`, `hostname`, and the exact exploit command with timestamps.
- Avoid heavy post-exploitation on a box you just exploited at the kernel level; finish the required evidence and stabilize.
- Remove the exploit binary and any marker files unless the rules of engagement require leaving them for the blue team to find.
- Note any lingering effects (disabled mitigations, modified sysctls the exploit changed) and restore them where possible.

## Edge cases

- Race-condition exploits may need specific system load or timing; a failed first attempt does not always mean the target is patched, but each retry multiplies crash risk, so cap retries explicitly.
- Some exploits require running as a particular user or with specific resource limits; check `ulimit -a` against the exploit's assumptions.
- Kernel address space layout randomization means exploits that defeat KASLR need an info leak first; verify the leak step works before the write step.
- On Windows, driver-based exploits need the vulnerable driver loaded; a reboot or driver update between enumeration and testing invalidates the plan.
- Exploit binaries transferred as text or through shells can corrupt; always checksum after transfer and before execution.
- Timezone and clock skew do not matter for most exploits, but certificate or token based payloads after success might care; keep it in mind for post-exploitation.

## Escalation

- If the exploit fails cleanly with a version mismatch message, trust it: the target is not vulnerable to this candidate, so document and move to the next shortlisted item.
- When dmesg shows you reached the vulnerable path but the exploit failed, the bug may be real with a broken exploit; weigh writing a targeted fix against the engagement's time budget.
- If the box crashes, execute the recovery plan, document the crash honestly, and do not retry the same exploit without understanding the failure.
- When all shortlisted candidates are exhausted, close the kernel path with written verdicts and return to misconfiguration vectors or credential attacks.

## Detection and defender view

Kernel exploitation is the noisiest technique in the privesc set: oops messages, auditd gaps during crashes, EDR kernel telemetry, and often a full outage. Defenders detect it through kernel log monitoring, crash analysis, and behavioral alerts on exploit-like process patterns. From the authorized tester side, this noise is expected and accepted within the authorization: the protocol in this sub-skill exists to keep the noise bounded (one-shot payloads, no retry storms) and to give the blue team exact timestamps and artifacts for their detection validation.

## Key references

- MITRE ATT&CK T1068 (Exploitation for Privilege Escalation)
- Exploit-DB: https://www.exploit-db.com
- Google Project Zero writeups (exploit reliability analysis): https://googleprojectzero.blogspot.com
- Linux kernel oops documentation: https://www.kernel.org/doc/html/latest/admin-guide/bug-hunting.html
- GCC cross-compilation docs: https://gcc.gnu.org/onlinedocs/gcc/Cross-Compiler.html
- Microsoft driver signing and verification: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/driver-signing
