---
name: linux-hardening-baseline-ssh-hardening
description: Use when hardening OpenSSH on a Linux server or auditing an
  existing sshd configuration. Covers key-only authentication, disabling
  root login and password auth, AllowUsers and AllowGroups scoping, strong
  ciphers MACs and key exchange selection, idle timeouts and login attempt
  limits, verifying effective config with sshd -T, and brute force defenses
  with fail2ban. Defensive hardening mapped to MITRE ATT&CK mitigations for
  T1110 Brute Force and T1078 Valid Accounts.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-hardening-baseline]
extends: []
parent: linux-hardening-baseline
relates: [linux-hardening-baseline, linux-hardening, linux-log-intrusion-analysis]
tools:
  - name: OpenSSH
    version: 9.6
  - name: fail2ban
    version: 1.0.2
  - name: auditd
    version: 3.1
---

SSH is the remote front door of nearly every Linux server, which makes its configuration the highest-leverage hardening work you can do. This sub-skill covers the complete defensive SSH baseline: authentication policy, user scoping, cryptographic algorithm selection, session limits, verification of the effective configuration, and brute force defenses. Everything here is defensive hardening for systems you own or administer. The parent skill places SSH in the wider baseline; this file is the deep, command-level reference.

## Quick Workflow

1. Back up the current config: `cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak-$(date +%F)`.
2. Set the authentication policy: key-only, no root login, no password or challenge-response auth.
3. Scope who may connect with `AllowUsers` or `AllowGroups`; deny everyone else by default.
4. Pin strong ciphers, MACs, and key exchange algorithms; disable weak and legacy ones.
5. Set session hygiene: idle timeouts, max auth tries, max sessions, disabled tunneling features you do not use.
6. Validate syntax with `sshd -t`, restart carefully (keep one existing session open), and verify effective settings with `sshd -T`.
7. Add brute force defense (fail2ban or equivalent) and confirm it is banning with a controlled test.

## 1. Authentication policy: keys only, no root

The core of SSH hardening is removing the password guessing surface entirely. Public key authentication plus disabled root login eliminates the two most attacked vectors.

```bash
grep -iE "^(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|ChallengeResponseAuthentication|UsePAM)" /etc/ssh/sshd_config
```

Set in `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
UsePAM yes
```

`UsePAM yes` stays on because PAM provides session setup and account checks even without password auth. After changing, verify the effective configuration as root with `sshd -T | grep -iE "permitrootlogin|passwordauthentication|pubkeyauthentication"`, which resolves includes and Match blocks. Expected: `permitrootlogin no`, `passwordauthentication no`, `pubkeyauthentication yes`.

## 2. Scoping access with AllowUsers and AllowGroups

Even with keys only, restrict which accounts can use SSH at all. An allowlist means a compromised or forgotten account without a key still cannot get a shell.

```
AllowGroups ssh-users
```

Then ensure every human and automation account that needs SSH is in `ssh-users`, and nothing else is. Verify with `sshd -T | grep -i allowusers` and by attempting a login as a non-listed user (it must fail before authentication). Prefer groups over users: group membership is managed centrally and survives staff changes better than editing sshd_config per person.

## 3. Cryptographic algorithm selection

Defaults in modern OpenSSH are good, but explicit pinning protects against downgrade pressure and documents intent. Disable CBC ciphers, weak MACs, and SHA1 key exchange.

```
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes128-ctr
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256
```

Generate and prefer ed25519 host keys (`ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key`) and remove DSA host keys entirely. Verify the negotiated algorithms for a real connection with `ssh -vv user@host 2>&1 | grep -iE "kex|cipher|mac"`. Note: pinning too aggressively can lock out old automation clients; check client versions before deploying the strict list.

## 4. Session hygiene and feature lockdown

Limit what an authenticated session can do, and kill idle sessions before they become forgotten open doors.

```
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 3
LoginGraceTime 60
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
PermitEmptyPasswords no
```

Disable `X11Forwarding` and `AllowTcpForwarding` unless a documented use case needs them; forwarding turns an SSH account into a network pivot. `ClientAliveInterval 300` with count 2 drops idle sessions after about 10 minutes. Verify with `sshd -T | grep -iE "clientalive|maxauthtries|x11forwarding|allowtcpforwarding"`.

## 5. Brute force defense with fail2ban

Key-only auth already defeats password guessing, but fail2ban still adds value: it slows reconnaissance, reduces log noise, and protects any remaining password surface (or other services).

```bash
systemctl enable --now fail2ban
fail2ban-client status sshd
fail2ban-client get sshd banip --with-time 2>/dev/null | head -5
```

Example output shape: `Status for the jail: sshd` with current bans listed. Tune `maxretry` and `bantime` in `/etc/fail2ban/jail.local` (never edit `jail.conf` directly), and set `ignoreip` for your management networks and bastion hosts so you cannot lock yourself out. Test from a controlled source with intentional failures and confirm the ban appears; an untested jail is a hope, not a control.

## 6. Safe restart and rollback

The classic SSH hardening outage is locking yourself out with a bad config. The procedure: validate syntax, keep one session open, restart, test a new session, and only then close the old one.

```bash
sshd -t && echo "syntax OK"
systemctl restart sshd
sleep 2; systemctl is-active sshd
ssh -o PreferredAuthentications=publickey user@localhost "echo login-ok"
```

Example output shape: `syntax OK`, `active`, `login-ok`. If the test login fails, `cp` the backup back and restart again. For fleet rollouts, do this host by host with automation that verifies the new session before closing the old (Ansible's `wait_for` plus a test task), never a blind mass restart.

## Edge cases

- `sshd_config` supports `Include` directives and `Match` blocks that override global settings; always verify with `sshd -T` (effective config) rather than grepping the file, because a Match block can silently re-enable password auth for a subnet.
- Distro defaults differ: Debian enables `KbdInteractiveAuthentication` via PAM in ways that can surprise, and RHEL ships different default ciphers; read your distro's default config before assuming upstream OpenSSH defaults.
- Changing the SSH port is obscurity, not security; it reduces log noise but must never be presented as a control, and it complicates firewall rules and monitoring, so only do it for noise reduction with eyes open.
- Automation accounts (Ansible, backups, monitoring) need their keys deployed before you disable password auth; coordinate the key rollout first or you will break every scheduled job at once.
- `AllowUsers`/`AllowGroups` with a typo locks out everyone including you; test the exact spelling with `sshd -T` and a real login attempt before closing your safety session.
- Old embedded devices or vendor appliances may only support legacy algorithms; inventory SSH clients before pinning the strict cipher list, and isolate legacy clients behind a bastion instead of weakening the whole fleet.
- fail2ban on IPv6 needs the jail to handle v6 addresses, and aggressive bantimes on NAT-heavy networks can ban whole offices; tune `maxretry` upward and `bantime` downward where many users share source IPs.

## Escalation

- If the server must keep password authentication for a legacy integration, escalate to a formal risk acceptance: document the business reason, add fail2ban with strict limits, enforce strong password policy, and set a removal date.
- If you discover existing brute force campaigns in the logs during hardening, preserve the log evidence and check for successful logins before assuming the hardening fixed an already-compromised host.
- If a config change breaks production access, roll back immediately from the backup, then root-cause in staging; never debug sshd_config on a production box you are locked out of.
- If compliance requires specific algorithms or settings that conflict with your baseline, the compliance requirement wins; record the deviation and its justification in the baseline log.

## Detection and defender view

Hardened SSH is monitored SSH. Defenders watch `/var/log/auth.log` (Debian) or `/var/log/secure` (RHEL) for `Failed password`, `Invalid user`, and `Accepted` lines; a spike in failures is reconnaissance, and any `Accepted` outside expected users or hours is an incident. MITRE ATT&CK T1110 (Brute Force) is mitigated by key-only auth plus fail2ban, and T1078 (Valid Accounts) by AllowGroups scoping and key hygiene. Auditd rules on `/etc/ssh/sshd_config` detect unauthorized config changes, and periodic `sshd -T` diffs against the baseline catch drift. Centralize the logs: an attacker who gains access will try to clean local logs first.

## Key references

- MITRE ATT&CK T1110 Brute Force: https://attack.mitre.org/techniques/T1110/
- MITRE ATT&CK T1078 Valid Accounts: https://attack.mitre.org/techniques/T1078/
- OpenSSH sshd_config manual: https://man7.org/linux/man-pages/man5/sshd_config.5.html
- Mozilla OpenSSH security guidelines: https://infosec.mozilla.org/guidelines/openssh
- fail2ban manual: https://fail2ban.readthedocs.io/
- CIS distribution benchmarks (SSH sections): https://www.cisecurity.org/cis-benchmarks/
