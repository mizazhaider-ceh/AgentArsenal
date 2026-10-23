---
name: nmap-port-scanning
description: Use when you need to scan ports across live hosts with nmap on
  an authorized engagement. Covers SYN, connect, and UDP scan types, timing
  templates and rate control, full versus top-port strategies, and reading
  open, closed, and filtered states correctly. Use when mapping the attack
  surface of confirmed hosts, when choosing scan speed versus stealth, when
  UDP services matter, or when filtered results need interpretation.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
parent: nmap-methodology
requires: [nmap-methodology]
extends: []
relates: [recon-active, firewall-evasion]
tools:
  - name: nmap
    version: 7.98
  - name: masscan
    version: 1.3.2
---

Port scanning is nmap's core job: testing which ports accept connections on
each live host. This skill covers scan-type selection and execution on
authorized engagements: SYN scans as the default, connect scans where raw
sockets are unavailable, UDP scans for connectionless services, and timing
control for fragile or monitored networks. Service identification is a
separate sub-skill; this one is about accurate port states.

## Quick Workflow

1. Start from the live host list produced by nmap-host-discovery.
2. Run a top-ports SYN sweep for the quick picture.
3. Run a full-port SYN sweep on hosts that matter.
4. Run targeted UDP scans for DNS, SNMP, and other UDP services.
5. Interpret filtered versus closed correctly; re-probe ambiguities.
6. Save machine-readable output for the service detection phase.

## 1. SYN scanning

```bash
# Default workhorse: SYN scan, top 1000 ports, fast timing
nmap -sS -T4 --top-ports 1000 -iL /tmp/live.txt -oA /tmp/syn_top

# Full port range on one key host
nmap -sS -T4 -p- --min-rate 1000 10.0.5.23 -oA /tmp/syn_full

# Polite scan for fragile networks (slow but gentle)
nmap -sS -T2 -p- --max-rate 100 10.0.5.23 -oA /tmp/syn_polite

# Read the states: open (service), closed (host alive, nothing there),
# filtered (firewall dropped the probe, unknown)
grep -E 'open|filtered' /tmp/syn_full.nmap | head -30
```

SYN scan needs raw socket privileges (root). It is the default because it
is fast and never completes the handshake, which keeps logs slightly
quieter.

## 2. Connect and UDP scans

```bash
# Connect scan: no root needed, completes the handshake (noisier in logs)
nmap -sT -T4 --top-ports 1000 10.0.5.23 -oN /tmp/conn.txt

# UDP scan: slow, test only the ports that matter
nmap -sU -T4 --top-ports 50 10.0.5.23 -oN /tmp/udp.txt

# Confirm a UDP hit with an application probe, since UDP states are guesses
echo | timeout 3 nc -u 10.0.5.23 53 | xxd | head -3
```

Use `-sT` on jump hosts where you lack root, and in environments where raw
sockets are blocked. UDP scanning a full range takes hours; scope it to the
top ports plus any UDP service the engagement cares about.

## 3. Timing and output discipline

```bash
# Aggressive timing for a short window (risks dropped packets)
nmap -sS -T5 --min-parallelism 100 -p- 10.0.5.23 -oA /tmp/fast

# IDS-evasion timing: slow and randomized (see nmap-evasion for the full set)
nmap -sS -T2 --scan-delay 5s 10.0.5.23 -oA /tmp/slow

# Always save all three formats; the XML feeds every later tool
nmap -sS -p- -oA /tmp/final 10.0.5.23
ls -la /tmp/final.*
```

`-oA` gives you normal, XML, and grepable output in one run. The XML file
is what parsers, spreadsheets, and the report all consume; never rely on
terminal scrollback.

## Edge cases

- Everything is filtered. The firewall drops probes; try ACK scans to map
  the filter ruleset, and report the filtering as a finding about the
  network posture.
- Results flap between runs. Rate limiting or load balancing is in play;
  lower the rate, raise retries, and keep the union with notes.
- The scan crashes a fragile host. Stop immediately, note the exact
  command and target, inform the test lead, and switch to polite timing
  for the rest of the scope.
- IPv6 targets behave differently. Scan them separately; firewall rules
  and service bindings often differ from IPv4.

## Escalation

- You need to map firewall rules, not just ports: use ACK, window, and
  FIN scans to infer stateful versus stateless filtering.
- The window is too short for full sweeps: masscan the range at speed,
  then nmap only the open ports it found.
- A host must not be scanned at all: exclude it with `--exclude`, get its
  data from the client, and note the gap honestly.

## Detection and defender view

Defenders see port scanning as the noisiest phase: SYN bursts across ports,
completed handshakes from connect scans, and long UDP probe series. IDS
scan detectors and firewall logs catch all of it. Defenses are scan
detection with alerting, rate limiting, and reducing open ports so scans
find little. Stealth scanning trades speed for quiet; it does not become
invisible.

## Key references

- MITRE ATT&CK T1046 (Network Service Discovery).
- MITRE ATT&CK T1595.002 (Active Scanning: Vulnerability Scanning).
- nmap 7.98 documentation: port scanning techniques.
