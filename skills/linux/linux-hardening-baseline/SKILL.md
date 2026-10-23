---
name: linux-hardening-baseline
description: Use when building a defensive Linux hardening baseline for a
  server fleet, audit, or compliance review. Covers the baseline workflow
  (inventory, benchmark selection, apply, verify, monitor), SSH hardening
  with OpenSSH, filesystem permission hygiene, kernel parameter tuning with
  sysctl, and mapping controls to CIS benchmarks and MITRE ATT&CK
  mitigations. Purely defensive, with no exploitation content, covering how to make
  systems harder to break into and easier to audit.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening, linux-systemd-security, linux-log-intrusion-analysis]
tools:
  - name: OpenSSH
    version: 9.6
  - name: Python
    version: 3.12
  - name: auditd
    version: 3.1
---

A hardening baseline is the set of configuration decisions you make once and enforce everywhere: how SSH accepts connections, who can read and write what on disk, and how the kernel behaves under attack. This parent skill lays out the defensive workflow for building such a baseline on Linux servers, and points to the sub-skills for the three heaviest areas: SSH hardening, filesystem permissions, and kernel parameters. Everything here is defensive. There is no exploitation content: the goal is to shrink the attack surface, make misconfigurations visible, and give auditors a checklist they can verify with commands.

## Quick Workflow

1. Inventory the fleet: OS versions, roles (web, db, bastion), and which controls each role actually needs.
2. Pick a benchmark as your source of truth (CIS Benchmark for your distro, or your org's derived baseline) and record which version you follow.
3. Apply the baseline in layers: SSH first (remote access is the front door), then filesystem permissions, then kernel parameters, then services.
4. Verify every control with a check command, not by trusting the config file edit; capture the output as audit evidence.
5. Bake the baseline into provisioning (image build, Ansible/Puppet, cloud-init) so new hosts are born hardened.
6. Monitor drift: scheduled audits that diff live configuration against the baseline and alert on changes.
7. Review the baseline on a cadence (quarterly, or after each distro upgrade) because defaults and best practices move.

## 1. Choosing and scoping your benchmark

Do not invent controls from blog posts. Start from the CIS Benchmark for your distribution (CIS Debian, CIS Ubuntu, CIS RHEL), pick Level 1 for general servers and Level 2 only where the risk justifies the operational cost, and document every deviation with a reason. A baseline that nobody can explain is a baseline nobody will maintain.

```bash
cat /etc/os-release | head -3
uname -r
ss -tlnp | head -20
```

Example output shape: OS release plus kernel version tells you which benchmark applies; the listening sockets list tells you which services the baseline must cover (every open port needs a justification or a firewall rule). Record these three outputs as the baseline's scope statement.

## 2. The SSH layer: the front door

Remote access is where attackers knock first, so SSH hardening comes before everything else. The non-negotiables: key-only authentication, no root login, no password authentication, and a short list of allowed users. Protocol-level settings (strong ciphers, MACs, key exchange) close downgrade paths. Full detail lives in the ssh-hardening sub-skill.

```bash
sshd -T | grep -iE "permitrootlogin|passwordauthentication|pubkeyauthentication|allowusers"
```

Example output shape: `permitrootlogin no`, `passwordauthentication no`, `pubkeyauthentication yes` confirms the effective configuration (note: `sshd -T` shows effective values, which is what matters, not just what is written in the file). Run this after every sshd change; it is the verification command for the whole SSH layer.

## 3. The filesystem layer: who can touch what

Permissions are the second layer: correct ownership and modes on `/etc/passwd`, `/etc/shadow`, `/etc/ssh`, cron directories, and service configs; no unexpected SUID binaries; no world-writable files outside `/tmp` (and `/tmp` with the sticky bit); sane umasks. Full detail lives in the filesystem-permissions sub-skill.

```bash
find / -xdev -type f -perm -4000 2>/dev/null | head -20
find / -xdev -type f -perm -0002 ! -path "/proc/*" ! -path "/sys/*" 2>/dev/null | grep -v "^/tmp" | head -20
```

Example output shape: a short, known list of SUID binaries (passwd, sudo, su) and no world-writable files outside temporary directories. Any entry you cannot explain is a finding. Re-run these finds on a schedule; new SUID binaries appearing is one of the classic post-compromise indicators.

## 4. The kernel layer: behavior under attack

Sysctl parameters set kernel behavior: address space randomization, kernel pointer exposure, core dumps, module loading restrictions, and network stack hardening (SYN cookies, IP spoofing protection, ICMP redirects). Full detail lives in the kernel-parameters sub-skill.

```bash
sysctl -a 2>/dev/null | grep -E "kernel.randomize_va_space|kernel.kptr_restrict|kernel.dmesg_restrict|kernel.core_pattern" | head -10
```

Example output shape: `kernel.randomize_va_space = 2`, `kernel.kptr_restrict = 2`, `kernel.dmesg_restrict = 1` confirms the key exploit-mitigation knobs are on. Persist them in `/etc/sysctl.d/` files (never only via `sysctl -w`, which dies on reboot) and verify after reboot, because a baseline that does not survive a restart is decoration.

## 5. Services, firewall, and the rest of the surface

Beyond the three sub-skills: disable and mask unneeded services (`systemctl disable --now`, and `mask` for ones that must never start), default-deny firewall with explicit allows (nftables or firewalld), automatic security updates for the distro, and centralized logging so a compromised host cannot silently erase its trail. Each disabled service is attack surface removed; document the service list per role.

```bash
systemctl list-unit-files --state=enabled | head -20
nft list ruleset 2>/dev/null | head -30
```

Example output shape: a short enabled-services list matching the role's needs, and a firewall ruleset with a default drop or reject policy. If a service is enabled that the role does not need, that is a baseline deviation to fix or justify.

## 6. Baking it in and detecting drift

A baseline applied by hand to one server is a demo; a baseline enforced by automation is a control. Put the baseline in Ansible/Puppet/Chef or your image build pipeline, and run drift detection on a schedule: re-run the verification commands and diff against the expected values.

```bash
sshd -T | grep -iE "permitrootlogin|passwordauthentication" > /tmp/ssh-check.txt
diff /etc/baseline/expected-ssh.txt /tmp/ssh-check.txt && echo "SSH baseline OK"
```

Example output shape: silent diff means compliance; any diff lines are drift to investigate. Pair this with file integrity monitoring (AIDE) on baseline-controlled paths (`/etc/ssh/sshd_config`, `/etc/sysctl.d/`, unit files) so unauthorized changes generate alerts rather than sitting unnoticed.

## Edge cases

- Hardening baselines can break applications: disabling password auth locks out automation that uses passwords, and strict sysctl settings can break containers or databases, so test the full baseline on a staging host per role before fleet rollout.
- CIS Level 2 controls (like kernel module blacklisting or strict mount options) have real operational costs; apply them where the threat model justifies it and document where you deliberately chose Level 1.
- Cloud images and containers often reset or ignore parts of the baseline (cloud-init rewrites sshd_config, containers share the host kernel so sysctl is host-scoped); verify on the actual artifact that runs in production, not just on a reference VM.
- `sshd -T` must be run as root to show the effective configuration accurately; running it as an unprivileged user can hide Match-block effects and produce misleading verification.
- Some controls conflict across sub-skills: a strict umask can break service data directories, and `ProtectSystem=strict` in systemd units can conflict with applications writing to unexpected paths, so integration-test the combined baseline.
- Compliance frameworks (PCI DSS, ISO 27001) may demand specific settings that differ from CIS defaults; the benchmark is the starting point, the compliance requirement wins, and the deviation log records the difference.
- Baseline drift detection itself needs protection: if the checker script or expected-values file is writable by the wrong users, an attacker can silence the alarm, so protect the monitoring tooling with the same rigor as the baseline.

## Escalation

- If verification shows a control cannot be applied (legacy app requires password auth, vendor kernel module needs a blacklisted module), do not silently skip it: record a formal risk acceptance with owner, expiry, and compensating controls.
- If drift detection finds unauthorized changes to baseline files, treat it as a potential compromise indicator first and a config mistake second: investigate before reverting.
- If a new CVE or benchmark release changes a recommended setting, update the baseline through the normal change process (test, approve, roll out) rather than hand-editing production hosts.
- If different teams own different layers (network team owns firewall, app team owns service configs), assign each baseline section an explicit owner so failures have a name attached.

## Detection and defender view

A hardening baseline is itself a detection asset: every deviation from it is a signal. Defenders monitor the baseline through scheduled configuration audits, file integrity monitoring on controlled paths, and centralized logging of authentication and privilege events. MITRE ATT&CK maps here cleanly: hardening SSH and accounts mitigates T1110 (Brute Force) and T1078 (Valid Accounts); least-privilege permissions mitigate T1222 (File and Directory Permissions Modification); kernel mitigations blunt T1068 (Exploitation for Privilege Escalation). The audit evidence is the verification command output, stored centrally and reviewed, which is also what turns the baseline from good intentions into a compliance control.

## Key references

- CIS Benchmarks (Debian, Ubuntu, RHEL): https://www.cisecurity.org/cis-benchmarks/
- MITRE ATT&CK mitigations overview: https://attack.mitre.org/mitigations/
- OpenSSH sshd_config manual: https://man7.org/linux/man-pages/man5/sshd_config.5.html
- Arch Wiki security hardening guide: https://wiki.archlinux.org/title/Security
- Debian security hardening practices: https://www.debian.org/doc/manuals/securing-debian-manual/
- NIST SP 800-123 Guide to General Server Security: https://csrc.nist.gov/publications/detail/sp/800-123/final
