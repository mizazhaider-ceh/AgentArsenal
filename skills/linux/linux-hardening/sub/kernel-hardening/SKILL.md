---
name: kernel-hardening
description: Use when hardening the Linux kernel's runtime parameters
  via sysctl on a server. Covers the key sysctl settings, applying them
  persistently, and verifying the running values. Use when hardening a
  new server, when auditing kernel settings, when the privesc review
  found kernel weaknesses, or when setting the sysctl standard.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
parent: linux-hardening
requires: [linux-hardening]
extends: []
relates: [privesc-linux]
tools:
  - name: Python
    version: 3.12
---

Kernel runtime parameters shape what the system allows: IP forwarding,
core dumps, ASLR strength, and module loading. This skill covers the
sysctl hardening baseline: which settings matter, what values to set,
and how to make them persist and verified. It is a small file with
outsized effect; misconfigured kernel parameters enable entire privesc
classes.

## Quick Workflow

1. Read the current values of the baseline parameters.
2. Write the hardened values to a sysctl.d file.
3. Apply and verify the running values match.
4. Test server functionality after the change.
5. Confirm persistence across reboot.
6. Document the baseline as the standard.

## 1. The baseline parameters

```bash
# Read current values first (know before you change)
sysctl -a 2>/dev/null | grep -E \
  'ip_forward|rp_filter|accept_source_route|core_pattern|randomize_va_space|kptr_restrict|dmesg_restrict|perf_event_paranoid|unprivileged_bpf_disabled|kernel.modules_disabled|userns_clone' | head -20

# Baseline /etc/sysctl.d/99-hardening.conf:
# net.ipv4.ip_forward = 0                    (unless the box routes)
# net.ipv4.conf.all.rp_filter = 1
# net.ipv4.conf.all.accept_source_route = 0
# net.ipv4.conf.all.accept_redirects = 0
# net.ipv4.icmp_echo_ignore_broadcasts = 1
# kernel.randomize_va_space = 2              (full ASLR)
# kernel.kptr_restrict = 2                   (hide kernel pointers)
# kernel.dmesg_restrict = 1                  (dmesg needs privilege)
# kernel.perf_event_paranoid = 2             (perf needs privilege)
# kernel.unprivileged_bpf_disabled = 2       (no unprivileged BPF)
# kernel.kexec_load_disabled = 1             (no kexec after boot)
# fs.suid_dumpable = 0                      (no core dumps of SUID)
# kernel.core_pattern = |/bin/false          (no core dumps at all, if acceptable)
# kernel.unprivileged_userns_clone = 0       (where supported; breaks some containers)
```

Each setting has a reason: ASLR and pointer hiding raise exploit cost,
dmesg and perf restrictions close info leaks, and the network settings
kill spoofing and redirection attacks. Comment each line with its reason
in the file.

## 2. Apply and verify

```bash
# Apply the file
sysctl --system 2>&1 | grep -i error | head -5

# Verify the RUNNING values (the file is intent, the kernel is truth)
sysctl net.ipv4.ip_forward kernel.randomize_va_space kernel.kptr_restrict kernel.dmesg_restrict

# Functionality test: the server's normal operations must still work
# (pay attention to: containers need userns, monitoring needs dmesg/perf)

# Persistence: the file in sysctl.d survives reboot; verify after one
```

Some settings break legitimate workloads: unprivileged user namespaces
break rootless containers and some sandboxes; disabling core dumps
hinders debugging. Test the workload, then decide per setting with the
tradeoff documented, not globally.

## 3. Module and boot hardening

```bash
# Disable automatic module loading for unneeded protocols
# /etc/modprobe.d/hardening.conf:
# install dccp /bin/true
# install sctp /bin/true
# install rds /bin/true
# install tipc /bin/true
# install cramfs /bin/true
# install freevxfs /bin/true

# Verify a module cannot load
modprobe dccp 2>&1 | head -2

# Bootloader: set a grub password so kernel parameters cannot be
# edited at boot (physical/console access scenario)
```

Rare protocols and filesystems are exploit surface with no legitimate
use on most servers. Disabling their autoloading is pure win; the
modprobe test proves it.

## Edge cases

- A setting breaks the application. Revert that one setting,
  document the exception with its risk acceptance, keep the rest.
- The value reverts after reboot. Another sysctl file overrides it;
  check the full `sysctl --system` order and fix the conflict.
- Containers share the host kernel. Container sysctls are limited;
  the hardening belongs on the host, and the container gets what the
  runtime allows.
- Compliance mandates specific values. The compliance baseline wins
  ties; document where hardening exceeds it.

## Escalation

- The privesc review found kernel info leaks: prioritize kptr_restrict,
  dmesg_restrict, and perf_event_paranoid; verify with the privesc
  checks afterward.
- Fleet-wide rollout: encode in the image or config management with
  the verification as a scheduled audit.
- A setting needs tuning per role: keep the common baseline plus
  per-role overrides, each documented.

## Detection and defender view

For defenders, sysctl drift is a configuration finding: the scheduled
audit diffs running values against the baseline, and unexpected changes
(including attacker changes like enabling ip_forward for pivoting)
alert. Some of these settings ARE the detection: dmesg_restrict and
perf restrictions close the info leaks attackers use for recon.

## Key references

- CIS Benchmarks: kernel and sysctl sections.
- Linux kernel sysctl documentation.
- NIST SP 800-123 (server security).
