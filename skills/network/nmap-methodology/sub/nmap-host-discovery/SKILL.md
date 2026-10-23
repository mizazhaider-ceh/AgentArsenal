---
name: nmap-host-discovery
description: Use when you need to find which hosts are alive in a network
  range before deeper scanning on an authorized engagement. Covers ping
  sweep techniques, ARP discovery on local networks, TCP and UDP ping
  probes through firewalls, and choosing the right probe per network
  position. Use when starting network enumeration, when ICMP is blocked, when
  scanning from different vantage points, or when you need a reliable live
  host list for port scanning.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
parent: nmap-methodology
requires: [nmap-methodology]
extends: []
relates: [recon-active, network-pivoting]
tools:
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
---

Host discovery answers the first network question: which addresses are
alive. nmap's discovery engine tries several probe types because any single
one can be blocked. This skill covers choosing and running the right host
discovery on authorized engagements: ARP on local segments, ICMP and TCP
probes across routers, and UDP probes for stubborn networks. It produces the
live-host list that every later nmap phase consumes.

## Quick Workflow

1. Determine your vantage point: same subnet (ARP works) or routed (ARP
   does not).
2. Pick probe types the network is likely to answer: ARP locally, ICMP
   plus TCP SYN remotely.
3. Run discovery only (`-sn`) and save the live host list.
4. Spot-check the list against expected hosts (gateways, known servers).
5. Tune probes if hosts are missing: add TCP ports, try UDP, adjust
   timing.
6. Export the clean list for the port scanning phase.

## 1. Local network discovery

```bash
# ARP discovery is the most reliable on a local segment: hosts must
# answer ARP to communicate at all
nmap -sn -PR 10.0.5.0/24 -oN /tmp/arp_disc.txt

# Extract just the live IPs for the next phase
grep -oE 'Nmap scan report for [0-9.]+' /tmp/arp_disc.txt \
  | awk '{print $NF}' > /tmp/live.txt
wc -l /tmp/live.txt

# Skip discovery entirely when you already know the targets
nmap -Pn -sS --top-ports 100 -iL /tmp/live.txt -oN /tmp/ports.txt
```

On a local segment, `-PR` rarely misses. If hosts are missing here, they
are down, firewalled at layer 2, or outside the segment you think you are
on.

## 2. Routed network discovery

```bash
# Default discovery: ICMP echo, ICMP timestamp, TCP SYN to 443, TCP ACK
# to 80, plus ARP where applicable
nmap -sn 10.1.0.0/24 -oN /tmp/disc1.txt

# ICMP blocked: lead with TCP SYN pings to common ports
nmap -sn -PS22,80,443,3389 10.1.0.0/24 -oN /tmp/disc2.txt

# Both blocked: TCP ACK ping and UDP ping as last resorts
nmap -sn -PA80,443 -PU53,161 10.1.0.0/24 -oN /tmp/disc3.txt

# Compare the lists; the union with notes is your answer
cat /tmp/disc*.txt | grep -oE 'Nmap scan report for [0-9.]+' \
  | awk '{print $NF}' | sort -u > /tmp/live_all.txt
```

Firewalls that block ICMP usually still pass TCP to open service ports, so
`-PS` with the ports you expect to be open is the workhorse probe across
routers.

## 3. Timing and reliability

```bash
# Slow, reliable discovery for fragile or heavily filtered networks
nmap -sn -T2 --max-retries 3 10.2.0.0/24 -oN /tmp/slow.txt

# Fast discovery when the window is short (less reliable)
nmap -sn -T4 --min-parallelism 100 10.3.0.0/16 -oN /tmp/fast.txt

# DNS resolution control: skip it for speed, keep it for readability
nmap -sn -n 10.4.0.0/24 -oN /tmp/nonames.txt
```

Discovery reliability trades against speed directly. For the authoritative
inventory, prefer the slower run; for a quick check during pivoting, the
fast run is fine.

## Edge cases

- Every host appears down. The probe type is blocked, not the hosts;
  switch probe families before concluding the range is empty.
- The VPN or tunnel drops ARP. Routed probes only; `-PR` silently does
  nothing useful off-segment.
- Duplicate IPs or virtual IPs inflate the list. Note gateways, VIPs, and
  load balancer addresses separately from real hosts.
- Host discovery finds hosts that port scanning cannot reach. Asymmetric
  routing or host firewalls cause this; note the discrepancy and scan
  from a closer vantage point if the engagement allows.

## Escalation

- You need stealth: use `-T2` with decoys (`-D`) during agreed windows,
  or discover from traffic you already cause (DNS logs, ARP tables on a
  compromised host) instead of scanning.
- A critical subnet must not be ping-swept: get the live list from the
  client (DHCP leases, asset inventory) and note the method in the
  report.
- Results must be reproducible: save the exact command, nmap version,
  and timestamp with every host list.

## Detection and defender view

Defenders see host discovery as probe bursts (ICMP sweeps, ARP storms,
TCP SYN to many hosts) that IDS and NDR flag as the classic start of an
attack. ARP discovery is visible to anyone on the segment. Defenses are
IDS sweep detection, firewall rules that drop unsolicited probes, and
network segmentation so discovery finds little of value. Quiet discovery
uses existing traffic, not new probes.

## Key references

- MITRE ATT&CK T1018 (Remote System Discovery).
- MITRE ATT&CK T1595 (Active Scanning).
- nmap 7.98 documentation: host discovery.
