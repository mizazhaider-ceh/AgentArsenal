---
name: ssh-pivoting
description: Use when you have SSH access to a foothold host on an
  authorized engagement and need to pivot through it. Covers dynamic
  forwarding, local and remote port forwards, ProxyJump chains, and
  keeping tunnels stable. Use when reaching internal networks through a
  jump host, when accessing internal services from your machine, or when
  exposing a local tool to the internal network.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
parent: network-pivoting
requires: [network-pivoting]
extends: []
relates: [recon-active, c2-fundamentals]
tools:
  - name: OpenSSH
    version: 9.6
  - name: Python
    version: 3.12
---

SSH pivoting turns a foothold with SSH into a gateway: your traffic flows
through it to networks you cannot reach directly. This skill covers the
SSH forwarding toolkit on authorized engagements: dynamic SOCKS proxies,
port forwards in both directions, jump host chains, and tunnel hygiene.
It is the most common pivoting method because SSH is already there and
the traffic is encrypted.

## Quick Workflow

1. Confirm SSH access to the foothold and note its network view.
2. Choose the forward type for the job: dynamic, local, or remote.
3. Establish the tunnel with keepalives and backgrounding.
4. Verify the pivot reaches the intended targets.
5. Run the internal enumeration through the tunnel.
6. Tear the tunnels down at engagement end.

## 1. Dynamic forwarding (SOCKS proxy)

```bash
# SOCKS proxy on localhost:1080 through the foothold
ssh -D 1080 -C -N -f user@foothold.example
# -D dynamic forward, -C compression, -N no shell, -f background

# Use it: proxychains for tools without native SOCKS support
# /etc/proxychains.conf: socks5 127.0.0.1 1080
proxychains nmap -sT -T4 --top-ports 100 10.1.0.23

# curl with native SOCKS support (cleaner than proxychains)
curl -s --socks5 127.0.0.1:1080 http://10.1.0.23/ | head -20

# Keepalive so idle tunnels do not die
ssh -D 1080 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 \
  -C -N -f user@foothold.example
```

Dynamic forwarding is the general answer: any tool that speaks SOCKS (or
runs under proxychains) reaches the internal network. Note that nmap
through proxychains is limited to connect scans (`-sT`); SYN scans do not
work through SOCKS.

## 2. Local and remote forwards

```bash
# Local forward: internal service appears on your localhost
ssh -L 8080:10.1.0.23:80 -N -f user@foothold.example
curl -s http://127.0.0.1:8080/ | head -10

# Remote forward: your local tool appears on the foothold's network
ssh -R 4444:127.0.0.1:4444 -N -f user@foothold.example
# Now the internal host can reach your listener via foothold:4444

# Multiple forwards in one command
ssh -L 8080:10.1.0.23:80 -L 3389:10.1.0.24:3389 -N -f user@foothold.example
```

Local forwards are precise (one service, one port); dynamic forwards are
general. Use local forwards for the services you touch constantly and
dynamic for exploration.

## 3. Jump chains

```bash
# ProxyJump: hop through footholds to the deep target in one command
ssh -J user@foothold1.example user@10.1.0.23

# Chain: your machine -> foothold -> internal host -> deeper host
ssh -J user@foothold1.example,user@10.1.0.23 user@10.2.0.5

# Persistent config for a complex engagement (~/.ssh/config)
# Host internal-*
#   ProxyJump user@foothold1.example
#   ServerAliveInterval 60
```

Chains get fragile fast: each hop adds failure modes. Test each hop
individually before chaining, and keep the chain as short as the network
allows.

## Edge cases

- The foothold's SSH config forbids forwarding. Check
  `AllowTcpForwarding` on the foothold; if disabled, you need another
  pivot method (see socks-proxies).
- Idle tunnels drop through NAT. ServerAliveInterval plus autossh
  (`autossh -M 0`) keeps them up across flaky networks.
- DNS does not resolve through the tunnel. SOCKS5 with remote DNS
  (`socks5h`) fixes curl; for other tools, resolve names on the
  foothold first and use IPs.
- Too many forwards collide. Keep a port map in your notes; forwarded
  port collisions cause confusing failures.

## Escalation

- SSH is unavailable on the foothold: switch to socks-proxies for
  tool-based pivoting without SSH.
- You need the whole subnet, not single ports: dynamic forwarding plus
  proxychains covers it; full VPN-style pivoting is rarely needed.
- Tunnels must survive the engagement: document every forward with its
  purpose so teardown is complete.

## Detection and defender view

Defenders see SSH pivoting as long-lived SSH sessions with forwarding
channels, traffic to internal hosts that never touched the foothold's
normal profile, and port forwards in firewall logs. EDR on the foothold
sees the forwarded connections' process tree. Defenses are restricting
forwarding in sshd_config where unneeded, monitoring for forwarding
channel opens, and alerting on SSH sessions that spawn unusual internal
traffic.

## Key references

- MITRE ATT&CK T1090 (Proxy).
- MITRE ATT&CK T1572 (Protocol Tunneling).
- MITRE ATT&CK T1021.004 (Remote Services: SSH).
- OpenSSH 9.6 manual: ssh_config and sshd_config.
