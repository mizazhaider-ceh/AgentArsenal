---
name: os-fingerprinting
description: Use when you need to identify the operating system of target
  hosts during authorized active reconnaissance. Covers TCP/IP stack
  fingerprinting with nmap, passive banner and behavior clues, SMB and SNMP
  based identification, and resolving conflicting results. Use when
  planning OS-specific attacks, when prioritizing exploits by platform, when
  banners are hidden, or when building an accurate asset inventory.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
parent: recon-active
requires: [recon-active]
extends: []
relates: [nmap-methodology, privesc-linux, privesc-windows]
tools:
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.2
---

Operating system fingerprinting identifies what runs on a target host so
later phases pick the right exploits, payloads, and privilege escalation
paths. This skill covers authorized OS identification: active TCP/IP stack
fingerprinting, service-level clues, and resolving the conflicts that
middleboxes create. It produces a best-guess OS per host with a confidence
note, not a certainty; report it that way.

## Quick Workflow

1. Collect OS hints passively first: banners, TTL values, TCP window
   sizes from existing scan traffic.
2. Run nmap OS detection against hosts with at least one open TCP port.
3. Corroborate with service-level clues: SMB, SNMP, SSH, HTTP headers.
4. Resolve conflicts (nmap says Linux, SMB says Windows) by weighing the
   evidence.
5. Record OS, version guess, and confidence for each host.
6. Feed OS-specific targets to the right follow-on phases.

## 1. Active stack fingerprinting

```bash
# nmap OS detection needs at least one open and one closed port
nmap -O --osscan-guess -oN /tmp/os.txt 10.0.5.23

# Combine with service scan in one pass for small scopes
nmap -A -T4 --top-ports 100 -oN /tmp/aggr.txt 10.0.5.0/24

# TTL heuristic from a single ping (rough, but fast)
ping -c1 10.0.5.23 | grep ttl
# ttl=64 suggests Linux, ttl=128 suggests Windows, ttl=255 suggests
# network gear; each hop decrements, so adjust for distance
```

nmap prints a confidence percentage and the matching fingerprints. Below
90 percent, treat the guess as a hint and corroborate before acting on it.

## 2. Service-level corroboration

```bash
# SMB: Windows version and hostname in one query
nmap --script smb-os-discovery -p445 -oN /tmp/smb.txt 10.0.5.23

# SSH banner: OpenSSH version strings map to OS families loosely
(echo; sleep 1) | timeout 5 nc 10.0.5.23 22 | head -1
# SSH-2.0-OpenSSH_8.9p1 Ubuntu-3 -> Ubuntu host

# SNMP system description (when community strings are in scope)
snmpwalk -v2c -c public 10.0.5.23 1.3.6.1.2.1.1.1.0 2>&1 | head -2

# HTTP Server header and error pages
curl -s -I http://10.0.5.23/ | grep -i '^server:'
curl -s http://10.0.5.23/nonexistent-404-test | head -20
```

One strong service clue beats a weak stack guess. An SMB response naming
the Windows build is more reliable than a 85 percent nmap guess.

## 3. Resolving conflicts

```bash
# Capture the handshake yourself when tools disagree
tcpdump -i eth0 -w /tmp/hs.pcap host 10.0.5.23 &
curl -s http://10.0.5.23/ -o /dev/null
kill %1
tshark -r /tmp/hs.pcap -T fields -e ip.ttl -e tcp.window_size | head -5
# Compare TTL and window size against known OS defaults
```

Common conflict causes: load balancers (the fingerprint is the balancer,
not the backend), NAT (TTL decremented), honeypots (deliberately odd
stacks), and containers (host kernel, container userland). Note the likely
cause next to the guess instead of forcing one answer.

## Edge cases

- nmap reports no OS match. New or hardened stacks do this; fall back to
  service clues and report the OS as unknown with the evidence listed.
- The target is behind a VPN or jump host. Fingerprint from the closest
  vantage point; each middlebox degrades accuracy.
- OS detection needs closed ports and the firewall drops everything.
  Without a closed-port response, nmap cannot fingerprint; note the
  limitation.
- Containers share the host kernel. The stack says Linux with the host's
  kernel version while the services say otherwise; check for container
  markers in HTTP headers or error pages.

## Escalation

- You need the exact version for exploit targeting: combine the OS guess
  with application versions (web server, database) since exploits usually
  key off those, not the kernel.
- Passive-only engagement: skip active fingerprinting entirely and build
  the OS picture from banners and behaviors already captured.
- The inventory must be defensible: keep the raw nmap output and the
  corroborating evidence per host so the finding survives review.

## Detection and defender view

Defenders see OS fingerprinting as nmap's distinctive probe sequence
(multiple packets to open and closed ports with odd flag combinations),
which IDS signatures catch easily. Service probes for SMB and SNMP also
log. Defenses are the standard ones: IDS coverage, firewall rules that
limit probe responses, and banner minimization. Note that hiding the OS
rarely stops a determined tester; it only slows inventory.

## Key references

- MITRE ATT&CK T1592 (Gather Victim Host Information).
- MITRE ATT&CK T1082 (System Information Discovery).
- nmap 7.98 documentation: OS detection.
- "Remote OS detection via TCP/IP Stack FingerPrinting" (classic paper).
