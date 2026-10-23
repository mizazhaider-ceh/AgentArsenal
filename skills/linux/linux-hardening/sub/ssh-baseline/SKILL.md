---
name: ssh-baseline
description: Use when hardening SSH on a Linux server or auditing its
  configuration. Covers sshd_config hardening, key-only authentication,
  MFA options, and verifying the effective configuration. Use when
  building a new server, when auditing existing SSH, when the privesc
  review found weak SSH, or when setting the team's SSH standard.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
parent: linux-hardening
requires: [linux-hardening]
extends: []
relates: [privesc-linux, auth-attacks]
tools:
  - name: OpenSSH
    version: 9.6
  - name: Python
    version: 3.12
---

SSH is the front door of every Linux server: harden it and the most
attacked service becomes the strongest. This skill covers the SSH
hardening baseline: the sshd_config settings that matter, key-only
authentication, and verifying what is actually running. Apply it to new
builds and audit it on existing ones; SSH misconfigurations are
privesc-linux's favorite finding.

## Quick Workflow

1. Read the current effective configuration (`sshd -T`).
2. Apply the baseline: key-only auth, no root, protocol hygiene.
3. Verify the settings took effect (not just the file).
4. Test authentication as a normal user and as root (must fail).
5. Set up fail2ban or equivalent rate limiting.
6. Document the baseline as the team's standard.

## 1. The baseline configuration

```bash
# Read the EFFECTIVE config (includes defaults and includes)
sshd -T | grep -i -E 'permitrootlogin|passwordauth|pubkeyauth|port|permitTunnel|maxauthtries|logingracetime'

# Baseline /etc/ssh/sshd_config.d/hardening.conf:
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes
# ChallengeResponseAuthentication no
# UsePAM yes (for account/session, not for password auth)
# MaxAuthTries 3
# LoginGraceTime 30
# PermitEmptyPasswords no
# X11Forwarding no
# AllowTcpForwarding no (unless the role needs it)
# AllowAgentForwarding no
# ClientAliveInterval 300
# ClientAliveCountMax 2
# LogLevel VERBOSE

# Apply and verify: restart, then re-read the effective config
systemctl restart sshd
sshd -T | grep -i -E 'permitrootlogin|passwordauth'
```

`sshd -T` is the truth; the config file is the intent. Includes,
defaults, and distro overrides mean the file can lie. Always verify
with `-T` after changes.

## 2. Key management

```bash
# Key-only means the keys are now the credential: manage them
# - Ed25519 keys, no RSA-1024 or DSA anywhere
# - Authorized keys reviewed: who has access, remove the departed
for u in $(ls /home); do
  echo "== $u"
  cat /home/$u/.ssh/authorized_keys 2>/dev/null | cut -d' ' -f3 | head -5
done

# Permissions that SSH enforces (wrong perms = key ignored = lockout risk)
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys

# Check for weak keys still accepted
ssh-keygen -l -f /home/*/.ssh/authorized_keys 2>/dev/null | grep -v -E 'ED25519|ECDSA|RSA \(2048|3072|4096' | head -10
```

Key sprawl is the silent failure of key-only auth: fifty keys, nobody
knows whose. The authorized_keys audit is part of the baseline, not an
extra.

## 3. Rate limiting and monitoring

```bash
# fail2ban for SSH: slows password guessing to irrelevance
# (with key-only auth, guessing is already dead; this is defense in depth)
# jail.local: [sshd] enabled=true, maxretry=3, bantime=1h

# Monitor SSH auth logs for the patterns that matter
grep -E 'Failed|Invalid user' /var/log/auth.log | tail -10
# Alert on: root login attempts, many failures from one IP, logins at odd hours

# Verify root login is actually refused (test, do not assume)
ssh -o BatchMode=yes root@127.0.0.1 2>&1 | head -2
# Expect: Permission denied (publickey) -- and root has no key
```

With key-only auth plus no-root plus rate limiting, SSH brute force is
a non-issue and the logs prove it. The monitoring stays because the
logs also catch the misconfigurations (a sudden password-auth success
means someone changed the config).

## Edge cases

- Legacy automation needs password auth. Isolate it: Match blocks for
  specific users or sources, with a migration deadline, not a global
  exception.
- The change locks everyone out. Test from a second session before
  closing the first; keep console access until the new config is
  proven.
- FIPS or compliance modes restrict algorithms. Align the baseline
  with the compliance requirement; document the deviations.
- Jump host versus direct: the baseline applies to both, but the jump
  host gets the stricter forwarding settings.

## Escalation

- The audit finds SSH as the privesc path (weak keys, agent
  forwarding): fix per this baseline and re-run the privesc checks.
- MFA for SSH is required: add it via PAM (TOTP) on top of keys, and
  test the full login flow including automation accounts.
- Fleet-wide rollout: bake the baseline into the image or config
  management, and audit with the `sshd -T` check on a schedule.

## Detection and defender view

Hardened SSH is monitored SSH: the auth logs become high-signal
because legitimate failures drop to near zero. Alert on any root
attempt, any password-auth success (config drift), and key usage from
new sources. The defender's win is that SSH stops being the incident
source and starts being the incident evidence.

## Key references

- CIS Benchmark: SSH server configuration sections.
- OpenSSH 9.6 sshd_config manual.
- NIST SP 800-123 (server security, SSH guidance).
