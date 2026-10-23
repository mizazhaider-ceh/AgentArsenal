---
name: ssh-hardening
description: "Use when hardening OpenSSH 9.8 servers and clients: writing a secure sshd_config (key-only auth, no root login, modern ciphers and key exchange), auditing the effective config with sshd -T, managing host keys, deploying fail2ban or rate limits against brute force, configuring jump hosts and ProxyJump, understanding agent forwarding risks, using SSH certificates, or reviewing authorized_keys hygiene. Use when the task mentions SSH hardening, sshd_config, key-only authentication, brute force protection, or bastion hosts."
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening]
tools:
  - name: OpenSSH
    version: 9.8
  - name: ssh-audit
    version: 3.4
---
SSH is the front door of every server, and it is scanned constantly: any
SSH port on the internet receives brute-force attempts within minutes.
Hardening it is one of the highest-leverage security tasks there is. This
skill covers OpenSSH 9.8 server hardening (sshd_config done right),
client-side hygiene, key management, brute-force defenses, jump hosts,
certificates, and auditing with sshd -T and ssh-audit.

## Quick Workflow

1. Audit first: `sshd -T` shows the effective config; ssh-audit grades
   the algorithms.
2. Enforce key-only auth: disable passwords, disable root login.
3. Restrict who can connect: AllowUsers/AllowGroups, and listen only
   where needed.
4. Select modern ciphers, MACs, and key exchange; disable legacy ones.
5. Harden the handshake: MaxAuthTries, LoginGraceTime, MaxSessions.
6. Add brute-force protection: fail2ban or firewall rate limiting.
7. Fix permissions on host keys, ~/.ssh, and authorized_keys.
8. Use jump hosts (ProxyJump) instead of exposing every box.
9. Re-audit after changes and watch the auth logs for a week.

## 1. Audit the current state

```bash
# Effective config with defaults applied (run as root)
sudo sshd -T | sort

# Focus on the security-relevant knobs
sudo sshd -T | grep -iE 'permitrootlogin|passwordauthentication|pubkeyauthentication|ciphers|macs|kexalgorithms|maxauthtries|permit.*forward|allowusers|allowgroups'

# Grade the algorithms from outside (install ssh-audit via pip)
ssh-audit example.com

# What auth methods does the server actually offer?
ssh -v -o PreferredAuthentications=none example.com 2>&1 | grep -i 'authentications that can continue'
```

## 2. The hardened sshd_config

```bash
# /etc/ssh/sshd_config.d/10-hardening.conf  (drop-in, survives upgrades)
# Authentication: keys only, no root
PermitRootLogin no
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes
PubkeyAuthentication yes

# Who may connect (principle of least privilege)
AllowUsers deploy backup
# AllowGroups ssh-users   (alternative)

# Modern algorithms only
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes128-ctr
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256

# Handshake limits
MaxAuthTries 3
LoginGraceTime 30
MaxSessions 4
MaxStartups 10:30:60

# Forwarding: disable what you do not use
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
# AllowAgentForwarding no   (set explicitly; see section 6)

# Logging and banners
LogLevel VERBOSE
Banner /etc/ssh/banner.txt
```

Apply and verify:

```bash
sudo sshd -t && sudo systemctl reload sshd
sudo sshd -T | grep -iE 'permitrootlogin|passwordauthentication'
# Keep your current session open and test a NEW connection before closing it
ssh -o PreferredAuthentications=publickey deploy@example.com
```

The golden rule: never close your working SSH session until a new
login succeeds with the new config. One typo in sshd_config plus a
closed session equals a drive to the datacenter.

## 3. Host keys and file permissions

```bash
# Generate missing host key types (ed25519 + rsa); remove weak ones
sudo ssh-keygen -A
sudo rm -f /etc/ssh/ssh_host_dsa_key* /etc/ssh/ssh_host_ecdsa_key*

# Show host key fingerprints (compare on first connect)
sudo ssh-keygen -l -f /etc/ssh/ssh_host_ed25519_key.pub

# Permissions: root-owned, tight
sudo chown root:root /etc/ssh/ssh_host_*_key
sudo chmod 600 /etc/ssh/ssh_host_*_key
sudo chmod 644 /etc/ssh/ssh_host_*_key.pub
```

Client side, per user:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub ~/.ssh/known_hosts

# authorized_keys hygiene: one key per line, comment says who/where
cat ~/.ssh/authorized_keys
# ssh-ed25519 AAAA... deploy@laptop-2026
```

Restrict what a key can do with options in authorized_keys:

```bash
# Backup key: only rsync, only from the backup host, no forwarding
from="10.0.0.5",command="/usr/bin/rsync --server --sender -vlogDtpr . /data/",no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 AAAA... backup@backup-1
```

## 4. Brute-force protection

fail2ban is the standard: ban IPs after N failed logins.

```bash
sudo apt install -y fail2ban

# /etc/fail2ban/jail.d/sshd.local
# [sshd]
# enabled = true
# maxretry = 4
# findtime = 10m
# bantime = 1h

sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
sudo fail2ban-client get sshd banip --with-time | head
```

Firewall-level rate limiting as a second layer (nftables example):

```bash
# Allow 3 new SSH connections per minute per IP, then drop
sudo nft add rule inet filter input tcp dport 22 ct state new \
  limit rate over 3/minute burst 5 packets log prefix '"ssh-flood: "' drop
```

Reality check on "change the port": moving SSH off port 22 cuts log
noise by 99 percent but adds zero real security; do it for quiet logs,
not as a control, and never as the only control.

## 5. Jump hosts instead of exposed fleets

```bash
# ~/.ssh/config: one bastion, everything else behind it
Host bastion
    HostName bastion.example.com
    User ops
    IdentityFile ~/.ssh/id_ed25519

Host db-1 app-1
    ProxyJump bastion
    User deploy
    IdentityFile ~/.ssh/id_ed25519

# Now this goes through the bastion transparently, end-to-end encrypted
ssh db-1
scp backup.sql db-1:/tmp/
```

The private servers need no public SSH at all: firewall port 22 to the
bastion's IP only. Audit who can reach what with one config file instead
of scattered firewall rules.

## 6. Agent forwarding: convenient and dangerous

`ssh -A` lets the remote host use your local keys. A compromised remote
host can then use your agent to hop further as you, for as long as you
stay connected.

```bash
# Prefer ProxyJump (no keys ever leave your laptop)
ssh -J bastion db-1

# If you must forward, confirm what's loaded and lock it
ssh-add -l
ssh-add -c ~/.ssh/id_ed25519   # confirm each use

# Server side: default deny, allow per need
# AllowAgentForwarding no   (global default in the hardening drop-in)
```

Rule: ProxyJump by default; agent forwarding only for the rare case a
remote host must authenticate outward, with `-c` confirmation, and
never to hosts you do not fully trust.

## 7. SSH certificates (beyond keys)

Certificates remove authorized_keys management: a CA signs short-lived
user certificates, servers trust the CA.

```bash
# CA setup (on the CA host, once)
ssh-keygen -f /etc/ssh/ca -N ''
# On each server: trust the CA for user certs
# /etc/ssh/sshd_config.d/20-ca.conf:
# TrustedUserCAKeys /etc/ssh/ca.pub

# Issue a 8-hour certificate for an engineer
ssh-keygen -s /etc/ssh/ca -I izaz-laptop -n deploy \
  -V -5m:+8h -z 1 id_ed25519.pub
# Produces id_ed25519-cert.pub; ssh offers it automatically
ssh -i id_ed25519 db-1
```

Certificates give expiry, principals (usernames), and instant
revocation via serial lists: the grown-up answer to "who still has
access".

## 8. Ongoing monitoring

```bash
# Failed logins by IP (tune the window)
sudo journalctl -u ssh --since "24 hours ago" \
  | grep -oP 'Failed password.*from \K[0-9.]+' | sort | uniq -c | sort -rn | head

# Successful logins: every one should be expected
sudo journalctl -u ssh --since "24 hours ago" | grep 'Accepted' | tail -20

# Keys offered vs accepted (VERBOSE LogLevel gives fingerprints)
sudo journalctl -u ssh --since "1 hour ago" | grep -i 'publickey' | tail -10
```

Alert on: logins at unusual hours, new source IPs for privileged
users, `Accepted` for users outside AllowUsers (config drift), and
fail2ban bans spiking (targeted campaign, not background noise).

## Edge cases

- Locked out after hardening: use console access (cloud provider
  console, IPMI) to fix sshd_config; this is why you test a new
  session before closing the old one.
- `AllowUsers` silently blocks everyone not listed, including
  automation accounts; audit the full user list before enabling.
- `sshd -T` shows a value you did not set: another drop-in or the
  main file sets it; `sshd -T` merges all, check
  `/etc/ssh/sshd_config.d/` for conflicts (first-obtained value
  wins in sshd, opposite of most tools).
- Legacy clients cannot connect after cipher hardening: identify
  them from the logs (`no matching cipher found`) and upgrade the
  client; do not re-enable weak ciphers for one old script.
- fail2ban bans you during testing: whitelist your IP with
  `ignoreip` in jail.local.
- ProxyJump chains break scp/rsync scripts: they honor
  `~/.ssh/config`, so define the Host blocks once and scripts work
  unchanged.

## Escalation

- `sshd -t` fails: it prints the file and line; fix and retest,
  never restart on a failed test.
- Authentication fails with keys after hardening: check server
  `LogLevel VERBOSE` output for the fingerprint offered, verify
  `~/.ssh` permissions (700/600), and confirm SELinux/AppArmor
  contexts on non-standard home directories (`restorecon -R`).
- Need to allow one legacy device: use a `Match` block scoped to
  its IP with weaker settings, never weaken the global config:
  `Match Address 10.0.0.99` then the overrides, and document why.
- Suspected compromised key: remove it from all authorized_keys,
  rotate the host keys if the server was breached, and move to
  certificates to make the next rotation instant.

## Detection and defender view

SSH is the most attacked service on the internet; the defender view is
brute force, key sprawl, and persistence via authorized_keys. Detect
with:

```bash
# Brute force in progress right now
sudo journalctl -u ssh -f | grep -E 'Failed|Invalid user'

# authorized_keys files changed recently (persistence!)
sudo find /home /root -name authorized_keys -mtime -30 -ls

# Keys with dangerous options or unknown owners
sudo grep -h -v '^#' /home/*/.ssh/authorized_keys /root/.ssh/authorized_keys \
  2>/dev/null | awk '{print $NF}' | sort | uniq -c | sort -rn | head -20

# Logins from never-before-seen IPs (baseline first, then alert)
sudo journalctl -u ssh --since "7 days ago" | grep Accepted \
  | grep -oP 'from \K[0-9.]+' | sort -u
```

Red flags: `command=` keys you did not create, world-readable private
keys, password auth re-enabled after hardening (drift), and successful
logins for users who should be key-only from unexpected countries.
Treat any unknown entry in root's authorized_keys as an incident.

## Key references

- OpenSSH 9.8 release notes: https://www.openssh.com/releasenotes.html
- sshd_config man page: https://man.openbsd.org/sshd_config
- ssh-audit 3.4: https://github.com/jtesta/ssh-audit
- Mozilla OpenSSH guidelines: https://infosec.mozilla.org/guidelines/openssh
- MITRE ATT&CK T1021.004 (SSH): lateral movement over SSH.
- MITRE ATT&CK T1136: account creation/persistence via keys.
- CWE-798 (Hard-coded Credentials): passwords in scripts instead of keys.
- CWE-287 (Improper Authentication): password auth left enabled.
