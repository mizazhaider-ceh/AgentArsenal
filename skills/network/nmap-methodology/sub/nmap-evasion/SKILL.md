---
name: nmap-evasion
description: Use when IDS, IPS, or firewalls block or detect standard nmap
  scans and you need quieter techniques on an authorized engagement. Covers
  timing controls, fragmentation, decoys, idle scanning concepts, source
  port tricks, and when evasion is appropriate versus when to scan openly.
  Use when testing detection capabilities, when the scope requires low
  visibility, when firewalls filter normal probes, or when assessing the
  blue team's alerting.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
parent: nmap-methodology
requires: [nmap-methodology]
extends: []
relates: [firewall-evasion, recon-active]
tools:
  - name: nmap
    version: 7.98
  - name: Wireshark
    version: 4.2
---

Evasion techniques make nmap traffic quieter or harder to attribute, for
engagements where testing the defenders' detection is part of the job.
This skill covers nmap's evasion toolkit on authorized tests: timing,
fragmentation, decoys, and probe tricks, plus the judgment of when to use
them. Evasion is slower and less reliable than open scanning; use it when
the objectives demand stealth, not by default, and always inside the agreed
rules.

## Quick Workflow

1. Confirm the engagement wants stealth or detection testing; default to
   open scanning otherwise.
2. Establish a baseline: what does the IDS see from a normal scan.
3. Apply one evasion technique at a time and measure the difference.
4. Verify results did not degrade (evasion loses accuracy).
5. Document which techniques the defenses caught and which they missed.
6. Report detection gaps as findings about monitoring, not as cleverness.

## 1. Timing and fragmentation

```bash
# Slow timing: the simplest and most effective quiet technique
nmap -sS -T2 --scan-delay 10s -p- 10.0.5.23 -oN /tmp/quiet.txt

# Randomize host order so the sweep has no obvious pattern
nmap -sS -T3 --randomize-hosts 10.0.5.0/24 -oN /tmp/rand.txt

# Fragment packets to dodge simple pattern matchers
nmap -sS -f --mtu 16 -p22,80,443 10.0.5.23 -oN /tmp/frag.txt

# Tiny MTU must be a multiple of 8; 16 and 24 are the practical choices
```

Timing beats trickery. A slow scan from an expected source during business
hours is quieter than any fragmentation from a strange host at 3 AM.

## 2. Decoys and source tricks

```bash
# Decoys: hide among fake sources (use only with permission; decoys
# can alarm innocent third parties, so prefer lab or scoped ranges)
nmap -sS -D RND:5 -p22,80,443 10.0.5.23 -oN /tmp/decoy.txt

# Spoofed source with manual decoy list
nmap -sS -D 10.0.5.50,10.0.5.51,ME -p22,80,443 10.0.5.23 -oN /tmp/decoy2.txt

# Source port 53 or 20: some firewalls trust DNS and FTP-data ports
nmap -sS --source-port 53 -p22,80,443 10.0.5.23 -oN /tmp/srcport.txt

# Idle scan concept: bounce the scan off a zombie host with a
# predictable IP ID (advanced, fragile, rarely worth it today)
# nmap -sI zombie.example 10.0.5.23
```

Decoys have a real-world cost: every decoy IP gets blamed in someone's
logs. Get explicit permission before using decoys outside lab networks,
and prefer timing-based quiet over attribution games.

## 3. Firewall probe tricks

```bash
# ACK scan: maps firewall rulesets rather than ports
nmap -sA -T4 -p1-1000 10.0.5.23 -oN /tmp/ack.txt
# unfiltered = no stateful firewall; filtered = stateful filtering

# FIN, NULL, Xmas scans: closed ports answer RST, open ports stay silent
# (works against stateless filters and some Unix stacks, not Windows)
nmap -sF -T4 -p22,80,443 10.0.5.23 -oN /tmp/fin.txt
nmap -sN -T4 -p22,80,443 10.0.5.23 -oN /tmp/null.txt

# Version detection through the firewall on allowed ports only
nmap -sV -p80,443 --source-port 53 10.0.5.23 -oN /tmp/ver_fw.txt
```

Read ACK scan output as firewall intelligence: it tells you where the
stateful boundary sits, which shapes every later phase more than any port
list.

## Edge cases

- Evasion techniques corrupt results. Fragmentation and idle scans lose
  packets; always re-verify critical ports with a clean scan.
- The IDS catches everything anyway. Modern NDR correlates behavior, not
  just signatures; note the detection as a positive defensive finding.
- Decoys trigger abuse complaints. Stop decoy use immediately, inform the
  test lead, and switch to timing-based quiet.
- Source-port tricks fail against stateful firewalls. They only help
  against naive packet filters; test, do not assume.

## Escalation

- The objective is detection testing: coordinate with the blue team on
  what to run when, so alerts map to techniques cleanly in the report.
- You need true stealth: consider whether scanning is needed at all;
  passive data, logs from a foothold, or client-provided inventories are
  quieter than any scan.
- Evasion is eating the time budget: time-box it, report what the open
  scan found, and list evasion as a follow-up test.

## Detection and defender view

This sub-skill is the defender's reading list: slow scans show as
low-and-slow connection attempts that NDR baselines flag; fragmentation
shows as odd packet sizes; decoys show as multiple sources with identical
patterns (the real source is the one that completes handshakes); source
port 53 scans show as SYN packets that are not DNS. Defenses are NDR
behavioral detection, egress filtering, and alerting on scan patterns
regardless of speed. Evasion raises attacker cost; good monitoring raises
it further.

## Key references

- MITRE ATT&CK T1595 (Active Scanning).
- MITRE ATT&CK T1018 (Remote System Discovery).
- nmap 7.98 documentation: timing and performance, firewall evasion.
