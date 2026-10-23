---
name: linux-hardening-baseline-kernel-parameters
description: Use when tuning Linux kernel parameters with sysctl as part of
  a defensive hardening baseline. Covers exploit mitigations (ASLR,
  kptr_restrict, dmesg_restrict, core dumps, module loading), network stack
  hardening (SYN cookies, IP spoofing protection, redirects, source routing),
  persisting settings in /etc/sysctl.d, verifying after reboot, and
  documenting deviations. Defensive hardening mapped to MITRE ATT&CK
  mitigations for T1068 Exploitation for Privilege Escalation.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-hardening-baseline]
extends: []
parent: linux-hardening-baseline
relates: [linux-hardening-baseline, linux-hardening, linux-systemd-security]
tools:
  - name: sysctl
    version: 4.0
  - name: systemd
    version: 255
  - name: Python
    version: 3.12
---

Sysctl parameters are the kernel's configuration knobs: they control exploit mitigations, information exposure, and network stack behavior. Set correctly, they raise the cost of exploitation and close entire classes of misconfiguration. This sub-skill covers the defensive sysctl baseline: which parameters matter, what values to set, how to persist them so they survive reboot, and how to verify. Purely defensive, for systems you own or administer. The parent skill places kernel tuning in the wider baseline; this file is the parameter-level reference.

## Quick Workflow

1. Record the current values of every parameter you plan to change, so you can roll back.
2. Write the baseline to a file in `/etc/sysctl.d/` (e.g. `99-hardening.conf`), never rely on `sysctl -w` alone.
3. Apply with `sysctl --system` and verify each value took effect.
4. Test workload behavior on a staging host per role before fleet rollout.
5. Reboot the staging host and re-verify: persistence is part of the control.
6. Roll out via automation, then add the verification commands to drift detection.
7. Review after each kernel or distro upgrade, because parameter names and defaults change.

## 1. Exploit mitigation parameters

These knobs make memory corruption and local privilege escalation harder, and they hide kernel internals from unprivileged users.

```bash
cat >> /etc/sysctl.d/99-hardening.conf <<'EOF'
kernel.randomize_va_space = 2
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.perf_event_paranoid = 2
kernel.kexec_load_disabled = 1
kernel.core_uses_pid = 1
fs.suid_dumpable = 0
EOF
sysctl --system
sysctl kernel.randomize_va_space kernel.kptr_restrict kernel.dmesg_restrict
```

What these do: full ASLR (`randomize_va_space=2`), no kernel pointer leaks to unprivileged users (`kptr_restrict=2`, `dmesg_restrict=1`), restricted perf events (which have been an exploit vector), disabled kexec (prevents booting a hostile kernel), and no core dumps from SUID programs (`suid_dumpable=0`, because core dumps of privileged processes leak memory contents). Verify each with `sysctl <name>` after applying; a typo in the key name is silently ignored unless you check.

## 2. Module loading and kernel attack surface

Loadable kernel modules are powerful and historically exploited. Restrict who can load them and disable dangerous module autoloading.

```bash
cat >> /etc/sysctl.d/99-hardening.conf <<'EOF'
kernel.modules_disabled = 0
kernel.unprivileged_bpf_disabled = 2
net.core.bpf_jit_harden = 2
EOF
echo "install dccp /bin/false" >> /etc/modprobe.d/hardening.conf
echo "install sctp /bin/false" >> /etc/modprobe.d/hardening.conf
echo "install bluetooth /bin/false" >> /etc/modprobe.d/hardening.conf
```

`modules_disabled=1` is the strongest option but irreversible until reboot and breaks anything that loads modules later (including some drivers and security tools), so most baselines leave it 0 and instead blacklist unneeded protocols via modprobe. `unprivileged_bpf_disabled=2` blocks unprivileged eBPF entirely (value 1 blocks it without the bpf() syscall, 2 is the strictest). Verify blacklists with `lsmod | grep -E "dccp|sctp"` returning nothing.

## 3. Network stack hardening

The network sysctls close spoofing, redirection, and ancient-protocol abuse at the kernel level, complementing the firewall.

```bash
cat >> /etc/sysctl.d/99-hardening.conf <<'EOF'
net.ipv4.tcp_syncookies = 1
net.ipv4.ip_forward = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_rfc1337 = 1
EOF
sysctl --system
```

What these do: SYN cookies blunt SYN floods, disabled forwarding stops the host becoming a router by accident (enable only on actual routers), no ICMP redirects sent or accepted (prevents route manipulation), no source-routed packets (a classic spoofing vector), reverse path filtering drops spoofed packets, martian logging records impossible addresses, and broadcast ping is ignored (Smurf protection). Verify with `sysctl -a | grep -E "ip_forward|accept_redirects|rp_filter"` and confirm forwarding-dependent roles (VPN gateways, container hosts) are exempted deliberately.

## 4. Core dumps and crash data

Core dumps capture process memory, which for privileged or secret-handling processes means credentials on disk. Control where dumps go and who can trigger them.

```bash
grep -E "core" /etc/sysctl.d/99-hardening.conf
sysctl kernel.core_pattern fs.suid_dumpable
ulimit -c
```

Set `kernel.core_pattern` to a controlled path or to `|/bin/false` to discard, keep `fs.suid_dumpable=0`, and set `ulimit -c 0` in `/etc/security/limits.conf` (`* hard core 0`) for defense in depth. If you run a crash-reporting pipeline (systemd-coredump, apport), route dumps there with strict permissions instead of disabling entirely, and document the decision: debugging needs sometimes outweigh the hardening preference.

## 5. Persistence, verification, and drift detection

A sysctl baseline only counts if it survives reboot and is monitored. The persistence chain is: file in `/etc/sysctl.d/`, applied by `systemd-sysctl.service` at boot, verified after reboot, watched for drift.

```bash
systemd-sysctl --cat-config | grep -E "kptr_restrict|ip_forward" | head -10
sysctl --system 2>&1 | grep -i error | head -5
```

`systemd-sysctl --cat-config` shows the merged effective configuration with file sources, which is what you audit. Check for errors on apply: unknown keys on older kernels fail loudly here, which is how you catch parameters your kernel does not support. For drift detection, store expected `sysctl -a` output for the baseline keys and diff on a schedule; any change to a security sysctl outside change control is investigated.

## Edge cases

- Container hosts share the host kernel: sysctl set inside a container mostly does nothing (network and some kernel keys are namespaced, most are not), so apply the baseline on the host, not in container images, and document which keys are per-namespace.
- `kernel.modules_disabled=1` cannot be undone without reboot and breaks DKMS-style driver installs, livepatch, and some security agents; test thoroughly or leave it 0 with modprobe blacklists instead.
- Some parameters are per-interface (`conf.all` vs `conf.default` vs `conf.eth0`): new interfaces inherit `default`, so set both `all` and `default` to cover interfaces created later, and verify on the actual interface names in use.
- Older kernels lack newer keys (`unprivileged_bpf_disabled`, `bpf_jit_harden`); `sysctl --system` errors on unknown keys, so gate version-specific keys by kernel version in your automation rather than shipping one file everywhere.
- Strict `rp_filter=1` breaks asymmetric routing setups common in multi-homed servers and some cloud topologies; use loose mode (2) or per-interface exceptions where the network design requires it, and document why.
- Disabling IPv6-related or uncommon-protocol sysctls does not remove the code; prefer modprobe blacklists plus firewall rules for protocols you truly want gone, since sysctl only tunes behavior.
- Performance-sensitive workloads (high-throughput networking, databases) can be affected by settings like `tcp_syncookies` behavior under load or perf restrictions; benchmark before and after on representative load.

## Escalation

- If a required application breaks under the baseline (database needing perf events, router needing forwarding), do not silently drop the control: record a scoped exception with the exact parameter, the business justification, compensating controls, and a review date.
- If verification after reboot shows values reverted, escalate to the provisioning team: something in the boot chain (cloud-init, a conflicting sysctl file with higher sort priority) is overriding the baseline, and hand-editing will not stick.
- If a kernel upgrade introduces new security parameters (or deprecates old ones), schedule a baseline review; running a stale baseline on a new kernel means missing new mitigations.
- If drift detection reports sysctl changes with no matching change ticket, treat it as a potential compromise indicator (attackers do tune the kernel) and investigate before re-applying.

## Detection and defender view

Sysctl hardening is verified, not assumed: defenders diff live values against the baseline on a schedule and alert on changes to security-relevant keys. MITRE ATT&CK T1068 (Exploitation for Privilege Escalation) is the technique these mitigations blunt: ASLR, kptr_restrict, and module restrictions each remove or narrow an exploitation primitive. Auditd can watch `/etc/sysctl.d/` for unauthorized modifications, and the `sysctl` syscall itself is auditable for runtime changes. The detection story is simple: the baseline values are known, any deviation is an event, and unexplained deviation is investigated as hostile until proven otherwise.

## Key references

- MITRE ATT&CK T1068 Exploitation for Privilege Escalation: https://attack.mitre.org/techniques/T1068/
- Kernel sysctl documentation: https://www.kernel.org/doc/html/latest/admin-guide/sysctl/kernel.html
- CIS distribution benchmarks (system maintenance and kernel sections): https://www.cisecurity.org/cis-benchmarks/
- systemd-sysctl.service manual: https://www.freedesktop.org/software/systemd/man/systemd-sysctl.service.html
- sysctl.d manual: https://www.freedesktop.org/software/systemd/man/sysctl.d.html
- NIST SP 800-123 Guide to General Server Security: https://csrc.nist.gov/publications/detail/sp/800-123/final
