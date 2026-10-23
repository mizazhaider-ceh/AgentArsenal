---
name: firewall-evasion
description: Use when nmap scans are blocked, filtered, or rate limited by
  firewalls and IDS on authorized engagements. Covers packet fragmentation,
  MTU games, decoy scans, source port spoofing, idle (zombie) scans, timing
  and delay tuning, bad checksums, data length padding, and tunneling scans
  through proxies. Use when the standard scan returns all filtered, when
  the target drops your IP after a few probes, or when you need to map
  firewall rules themselves. Requires nmap-methodology for scan basics.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires: [nmap-methodology]
extends: []
relates: [recon-active]
tools:
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.4
---

A firewall between you and the target changes what a scan means: `filtered`
is the firewall talking, not the host. Firewall evasion is the craft of
getting accurate answers anyway, by shaping packets so the firewall passes
them while the target still responds. This skill covers the nmap 7.98
evasion toolkit on authorized engagements: fragmentation, decoys, idle
scans, source port tricks, timing control, and proxy tunneling, plus how to
map the firewall's own rule set from its responses. It assumes you know
scan types and timing from nmap-methodology. Evasion is still scanning, so
it stays inside the written scope and rate limits. All testing targets
systems you have written permission to test.

## Quick Workflow

1. Run a baseline scan and record exactly what is open, closed, filtered,
   and dropped.
2. Identify the firewall behavior: stateless filter, stateful, or IDS with
   rate limiting.
3. Pick the least exotic evasion that answers the question, and try it on
   one host first.
4. Tune timing so the scan stays under rate limits and the agreed window.
5. Map the firewall rules from differential responses.
6. Re-run service detection only on the ports you proved real.
7. Document which technique defeated which control.

## 1. Read the baseline correctly

Before evading anything, characterize the obstacle. Different responses
mean different firewalls.

```bash
# Baseline SYN scan with reason codes: why does nmap think so?
sudo nmap -sS -p 1-1000 --reason -T4 192.0.2.10 -oN /tmp/base.txt

# ACK scan: distinguishes stateless from stateful filtering
sudo nmap -sA -p 22,80,443 --reason 192.0.2.10
```

Interpretation guide: `filtered` on an ACK scan means a stateful firewall
is in the path. `unfiltered` on ACK but `filtered` on SYN means the
firewall allows the ACK through but the host is not answering SYNs (or a
stateless filter passes ACKs). No response at all to anything, including
ping, suggests a drop-all posture or an IPS shunning your IP.

```bash
# Check whether your IP got shunned: scan from a second source if allowed
# Or test with a single innocent probe after a pause
sleep 60; sudo nmap -sS -p 80 --reason 192.0.2.10
```

If probes that worked ten minutes ago now get nothing, you tripped a rate
limit or shun. Back off before trying anything clever.

## 2. Fragmentation and MTU tricks

Splitting the TCP header across fragments can slip past simple packet
filters that only inspect the first fragment. Modern stateful firewalls
reassemble, so this works best against old or misconfigured gear.

```bash
# Fragment probes into 8-byte IP fragments
sudo nmap -sS -f -p 22,80,443 192.0.2.10

# Smaller MTU forces more fragments (must be a multiple of 8)
sudo nmap -sS --mtu 16 -p 22,80,443 192.0.2.10

# Combine fragmentation with a slow timing template
sudo nmap -sS -f -T2 -p 1-1024 192.0.2.10 -oN /tmp/frag.txt
```

Verify with Wireshark that fragments actually leave your box as fragments;
some virtual interfaces reassemble before the wire. Compare the open port
count against the baseline: new `open` results are ports the filter was
hiding.

## 3. Decoys

Decoys hide your address among fake source addresses. The target sees
probes from you plus N decoys and cannot tell which is real.

```bash
# Three decoys plus your real IP (ME), random positions
sudo nmap -sS -D 198.51.100.7,203.0.113.44,192.0.2.99,ME -p 22,80,443 192.0.2.10

# Random decoys: RND:10 generates ten random addresses
sudo nmap -sS -D RND:10 -p 1-1024 192.0.2.10 -oN /tmp/decoy.txt
```

Rules: never use decoys that belong to real third parties without
permission; spoofed sources can trigger abuse complaints and backscatter
to innocent owners. `ME` keeps your real IP in the mix so you still get
results. Decoys defeat simple per-IP rate limits, not stateful
inspection.

## 4. Source port and firewall-trust tricks

Some firewalls trust traffic from well known source ports, assuming it is
reply traffic. nmap can set its source port explicitly.

```bash
# Source port 53 (DNS): old filters often allow it
sudo nmap -sS --source-port 53 -p 22,80,443 192.0.2.10

# Source port 67 (DHCP) and 20 (FTP data) are other classic guesses
sudo nmap -sS --source-port 67 -p 1-1024 192.0.2.10

# Data length padding: append random bytes to dodge fixed-offset signatures
sudo nmap -sS --data-length 32 -p 22,80,443 192.0.2.10
```

Test each trick against the baseline and keep only what changes results.
These are low cost probes, so they belong early in the escalation order.

## 5. Idle (zombie) scan

The idle scan bounces the scan off a third host (the zombie) with a
predictable IP ID sequence, so the target never sees your address. It is
the stealthiest scan nmap offers and the fiddliest.

```bash
# Find a zombie: idle host with incremental IP IDs
sudo nmap -sS -O -p 80 --reason 192.0.2.0/24 -oG /tmp/zcandidates.gnmap
# Then check IP ID behavior:
sudo nmap -O -p 80 192.0.2.25 | grep -i "ip id sequence"
# Want: "Incremental"

# Run the idle scan through the zombie
sudo nmap -sI 192.0.2.25 -p 22,80,443 192.0.2.10
```

Requirements: the zombie must be truly idle (its IP ID must not move for
other reasons) and must trust or reach the target. Verify the zombie is
still idle right before the scan; a busy zombie produces garbage results.
In practice, printers and old cameras make good zombies.

## 6. Timing, delays, and staying under the radar

Rate limiting is the most common control you will meet. Beat it with
patience, not cleverness.

```bash
# Polite scan: T2 with explicit delays between probes
sudo nmap -sS -T2 --scan-delay 5s --max-retries 1 -p 1-1024 192.0.2.10

# Paranoid timing for tight IDS: one probe every 15 seconds
sudo nmap -sS -T0 --scan-delay 15s -p 22,80,443,3306,5432 192.0.2.10

# Cap parallelism so you never burst
sudo nmap -sS --max-parallelism 1 --max-rate 10 -p 1-65535 192.0.2.10
```

`--max-rate 10` (ten packets per second) stays under most default rate
limits. A full 65k port scan at that rate takes about two hours, so narrow
the port list first using the baseline and service guesses. Always check
the agreed test window before starting a slow scan.

## 7. Tunnel through a proxy

When your source network is the problem (egress filtering, shunning),
route the scan through an in-scope proxy or jump host.

```bash
# SOCKS proxy tunnel (proxychains must be configured first)
# /etc/proxychains.conf: socks5 127.0.0.1 1080
sudo proxychains nmap -sT -Pn -p 22,80,443 192.0.2.10

# nmap's own proxy support for HTTP/CONNECT
sudo nmap -sT --proxies http://proxy.in-scope.example:8080 -p 80,443 192.0.2.10
```

Proxy scans must use `-sT` (connect scan); raw packet scans cannot go
through a proxy. You lose OS detection and stealth, but you gain a fresh
source address and sometimes a whole different network view.

## 8. Map the firewall rules themselves

Differential responses reveal the rule set. Probe systematically and read
the firewall's mind.

```bash
# Which ports does the firewall treat differently? Compare SYN vs ACK vs NULL
for st in sS sA sN; do
  echo "=== -$st ==="
  sudo nmap -$st -p 21,22,23,25,53,80,110,143,443,993,3306,3389,5432,8080 \
    --reason 192.0.2.10 | grep -E '^[0-9]+/tcp'
done | tee /tmp/fw-map.txt

# Test source port trust across candidate ports
for sp in 53 67 20 123 161; do
  echo "=== source port $sp ==="
  sudo nmap -sS --source-port $sp -p 80,443 --reason 192.0.2.10 \
    | grep -E '^[0-9]+/tcp'
done
```

Build a small table: port, SYN result, ACK result, trusted source ports.
That table is the firewall rule map, and it goes straight into the report
as evidence of the filtering posture.

## Edge cases

- Everything is `filtered` no matter the technique. The firewall is
  stateful and correct; say so, and move testing to allowed paths (web,
  VPN) instead of burning the window.
- Your IP gets shunned mid-scan. Stop, wait out the shun (ask the client
  for the timeout), then resume slower or from the approved alternate
  source.
- Decoys trigger abuse complaints. Use only approved decoy addresses,
  and prefer `RND` with small counts over real addresses.
- The idle scan returns nonsense. The zombie was not idle; re-verify IP
  ID behavior immediately before scanning.
- Fragmentation changes nothing. The firewall reassembles; drop the
  technique and try timing or source port tricks.
- Proxy scans miss everything. The proxy egresses somewhere unexpected;
  confirm the proxy's exit IP and its own filtering first.
- Scan results differ run to run. Load balancers and anycast make each
  probe hit a different back end; scan longer and note the variance.

## Escalation

- One evasion works on one host. Apply it subnet-wide, but re-baseline
  per host; firewall rules often differ by segment.
- Nothing works from outside. Request an internal scan position in
  writing; inside-outside comparison is itself a valuable finding.
- The firewall is application aware. Evasion at the packet layer will
  not beat a WAF or NGFW that understands the protocol; pivot to
  application layer testing (see webapp-pentest-methodology).
- You mapped the rules. Turn the map into recommendations: default deny,
  remove trusted source port exceptions, and alert on scan patterns.

## Detection and defender view

Defenders see evasion as fragmented packets with tiny MTUs, bursts of
decoy sources hitting the same ports, slow but relentless single-port
probes over hours, and idle scan artifacts (a zombie's IP ID climbing
without its own traffic). Good NDR reassembles fragments before
inspection, correlates decoys by timing, and rate limits regardless of
source port. The durable fixes: default deny with explicit allows,
stateful inspection with reassembly, no trust based on source port alone,
IDS tuned for slow scans (not just fast ones), and shun lists with
sensible timeouts. Log denied packets; the denied log is where scans
show up.

## Key references

- MITRE ATT&CK T1046 (Network Service Discovery): scanning itself.
- MITRE ATT&CK T1090 (Proxy): tunneling scans through proxies.
- MITRE ATT&CK T1205 (Traffic Signaling): port and protocol tricks map
  loosely here; treat as an analogy, not a claim.
- nmap 7.98 manual, firewall and IDS evasion section:
  https://nmap.org/book/man-bypass-firewalls-ids.html
- Wireshark display filters for fragments: `ip.flags.mf == 1`
