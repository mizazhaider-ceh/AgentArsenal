---
name: nmap-methodology
description: Use when planning or running nmap scans during authorized engagements: host discovery options, TCP SYN, connect, UDP, NULL, FIN, Xmas, and ACK scan types, service and OS detection, timing templates T0 to T5, evasion techniques (fragmentation, decoys, idle scans, source port tricks, data length padding), NSE script selection by category, and output formats for evidence. Covers choosing the right scan for the objective, tuning speed against stealth, and reading results accurately on firewalled networks with nmap 7.98.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates:
  - recon-active
tools:
  - name: nmap
    version: 7.98
  - name: ncat
    version: 7.98
---

nmap is the standard network scanner, and most bad scans come from bad scan
choice, not from nmap itself. This skill is a methodology: which scan type
for which goal, how timing and evasion interact, how to use the Nmap Scripting
Engine without drowning in output, and how to read results honestly when
firewalls lie to you. It assumes you already have a verified host list (see
recon-active) and written authorization for every target. All examples use
nmap 7.98 syntax.

## Quick Workflow

1. Define the objective: host discovery, port inventory, service versions, OS, or vulnerability triage.
2. Pick the least invasive scan type that answers the objective.
3. Choose timing: fast for internal ranges, polite for fragile or third party networks.
4. Decide whether evasion is authorized and needed; default to no evasion.
5. Run service and OS detection only on confirmed open ports.
6. Add NSE scripts by category, never the whole database at once.
7. Save all three output formats for evidence, then interpret states correctly.

## 1. Choosing the scan type

Match the technique to the question. SYN scan is the default for a reason:
fast, and it never completes the TCP handshake.

```bash
sudo nmap -sS -p- 203.0.113.10 -oN syn-full.txt
```

Connect scan needs no privileges but completes handshakes, so it is louder
and gets logged by the target application:

```bash
nmap -sT --top-ports 1000 203.0.113.10 -oN connect-top1k.txt
```

UDP scanning is slow because closed ports may not answer at all, forcing
retransmits. Scan UDP only for specific services, not the full range, unless
you have hours:

```bash
sudo nmap -sU --top-ports 100 203.0.113.10 -oN udp-top100.txt
```

Stealth scan flavors (NULL, FIN, Xmas) exploit RFC behavior: closed ports
answer with RST, open ports stay silent. They only work against RFC-compliant
TCP stacks, so on modern Windows and filtered networks they are unreliable:

```bash
sudo nmap -sN 203.0.113.10 -oN null-scan.txt
sudo nmap -sF 203.0.113.10 -oN fin-scan.txt
sudo nmap -sX 203.0.113.10 -oN xmas-scan.txt
```

ACK scan does not find open ports; it maps firewall rulesets by distinguishing
filtered from unfiltered:

```bash
sudo nmap -sA -p 22,80,443,3389 203.0.113.0/24 -oN ack-filtermap.txt
```

IP protocol scan lists which IP protocols (TCP, UDP, ICMP, GRE) a host
supports, useful before tunneling work:

```bash
sudo nmap -sO 203.0.113.10 -oN ip-proto.txt
```

## 2. Host discovery done right

Never port scan a range without host discovery unless you have a reason
(`-Pn` treats every IP as alive and wastes time on dead space). Tune the
discovery probes to the network:

```bash
sudo nmap -sn -PE -PP -PM 203.0.113.0/24 -oN icmp-discovery.txt
sudo nmap -sn -PS80,443 -PA80,443 203.0.113.0/24 -oN tcp-discovery.txt
nmap -sn --disable-arp-ping 203.0.113.0/24 -oN no-arp.txt
```

On a local segment, ARP ping is king: fast and unblockable without breaking
the LAN. Across routers, combine ICMP echo, timestamp, and netmask with TCP
SYN and ACK to common ports. `--disable-arp-ping` matters when ARP responses
mislead you on networks with proxy ARP.

## 3. Service and OS detection

Version detection probes open ports with a battery of probes and matches
responses. OS detection uses TCP/IP stack fingerprinting. Both are noisier
than port scanning, so run them after you know which ports are open:

```bash
sudo nmap -sS -sV -O -p 22,80,443,3306,3389 203.0.113.10 -oN version-os.txt
```

Increase version intensity when the default probes miss (intrusion detection
may notice the extra traffic):

```bash
sudo nmap -sV --version-intensity 9 -p 8080,8443 203.0.113.10 -oN version-deep.txt
```

If OS detection is inconclusive, say so in your notes. Guessing the OS from
a TTL or a banner and writing it as fact is how wrong reports get written.
`--osscan-guess` gives a best effort match when you explicitly need one:

```bash
sudo nmap -O --osscan-guess 203.0.113.10 -oN os-guess.txt
```

## 4. Timing and performance

Timing templates T0 (paranoid) through T5 (insane) set probe parallelism and
timeouts. T4 is the practical default for internal networks; T3 is the safe
default nmap ships with. T5 risks missing ports and crashing fragile devices.

```bash
sudo nmap -sS -T4 --top-ports 1000 203.0.113.0/24 -oN t4-sweep.txt
sudo nmap -sS -T2 -p 80,443 203.0.113.0/24 -oN t2-polite.txt
```

Fine tune for big ranges: raise parallelism, set explicit timeouts, and skip
slow hosts instead of waiting on them:

```bash
sudo nmap -sS -T4 --min-rate 500 --max-retries 2 --host-timeout 10m \
  -p- 203.0.113.0/24 -oN fast-full.txt
```

`--min-rate` keeps packet flow steady, `--max-retries 2` stops nmap from
hammering unresponsive hosts, and `--host-timeout` abandons black holes.
For fragile targets (printers, PLCs, old switches), go the other way:

```bash
sudo nmap -sS -T1 --max-retries 1 --scan-delay 1s 203.0.113.50 -oN fragile.txt
```

Always estimate duration first with a small sample before launching a /16.

## 5. Evasion techniques

Use evasion only when the rules of engagement explicitly allow testing the
defenses. Default scans are honest; evasion tests the IDS, not the network.

Fragmentation splits probes into tiny IP fragments to dodge simple packet
filters:

```bash
sudo nmap -sS -f -p 80,443 203.0.113.10 -oN frag.txt
```

Decoys hide your real source among fake ones. The real scan still happens;
this only confuses log review, and some decoy IPs may get abuse complaints:

```bash
sudo nmap -sS -D RND:10 -p 80,443 203.0.113.10 -oN decoy.txt
```

Spoof the source port to look like replies from a trusted service (53 and
67 often pass lazy firewall rules):

```bash
sudo nmap -sS --source-port 53 -p 80,443 203.0.113.10 -oN srcport.txt
```

Pad packets with random data to defeat size-based signatures, and randomize
host order so the scan does not walk the subnet sequentially:

```bash
sudo nmap -sS --data-length 24 --randomize-hosts -p- 203.0.113.0/24 -oN padded.txt
```

Idle (zombie) scan bounces the scan off a third party host with predictable
IP IDs, hiding your address entirely. It needs a suitable zombie and is
slow; document authorization carefully because a third party host is involved:

```bash
sudo nmap -sI 203.0.113.99:80 203.0.113.10 -p 22,80,443 -oN idle.txt
```

## 6. NSE: scripting with discipline

The Nmap Scripting Engine has hundreds of scripts in categories: safe,
discovery, version, auth, brute, exploit, vuln, and more. Run categories, not
everything. Start safe and targeted:

```bash
sudo nmap -sS -sV --script "safe or default" -p 80,443 203.0.113.10 -oN nse-safe.txt
```

Vulnerability triage scripts check for known issues without exploiting:

```bash
sudo nmap -sV --script vuln -p 80,443,445 203.0.113.10 -oN nse-vuln.txt
```

Targeted enumeration per service keeps output readable:

```bash
sudo nmap -sV --script "http-title,http-headers,ssl-cert,ssl-enum-ciphers" \
  -p 443 203.0.113.10 -oN nse-tls.txt
sudo nmap --script "smb-os-discovery,smb-security-mode,smb2-security-mode" \
  -p 445 203.0.113.10 -oN nse-smb.txt
```

Brute and exploit categories are intrusive: they attempt logins and may run
proof-of-concept exploits. Use them only with explicit authorization, and
prefer the dedicated skills (auth-attacks, password-attacks) for that work.
Update the script database before an engagement:

```bash
sudo nmap --script-updatedb
```

## 7. Output and evidence

Always save machine-readable output alongside human-readable. You will thank
yourself at report time:

```bash
sudo nmap -sS -sV -O -p- 203.0.113.10 -oA evidence/webserver-01
ls evidence/
```

`-oA` writes `.nmap` (human), `.xml` (parseable), and `.gnmap` (greppable).
Parse the XML for your report instead of retyping:

```bash
grep -o 'portid="[0-9]*"' evidence/webserver-01.xml | sort -u
python3 -c "
import xml.etree.ElementTree as ET
t = ET.parse('evidence/webserver-01.xml')
for h in t.getroot().iter('host'):
    ip = h.find('address').get('addr')
    for p in h.iter('port'):
        st = p.find('state').get('state')
        if st == 'open':
            svc = p.find('service')
            print(ip, p.get('portid'), svc.get('name'), svc.get('product',''))
"
```

## 8. Reading results honestly

nmap reports six port states. Know what each one means before you write
findings: open (service accepting), closed (reachable, nothing listening),
filtered (no response, firewall or drop), unfiltered (ACK scan only, reachable
but state unknown), open|filtered (cannot distinguish, common for UDP),
closed|filtered (IP ID idle scan ambiguity). A filtered port is not a finding
of safety; it is a finding of a firewall. Re-scan filtered ports of interest
with different techniques before concluding. Version strings are banners, and
banners lie: backported patches keep old version numbers, so treat a banner
as a lead and confirm with behavior-based checks.

## Edge cases

- UDP scans against rate limiting firewalls take forever. Cap UDP to the top
  100 ports and move on; full-range UDP is rarely worth it.
- `--top-ports` uses nmap's frequency table, which skews toward common
  enterprise ports. Unusual services hide above port 10000, so do at least
  one full-range TCP pass on key hosts.
- OS detection fails through NAT and load balancers because you fingerprint
  the middlebox. Note the network path before trusting OS guesses.
- Some hosts crash under fast scans (old printers, embedded devices). If a
  device goes silent mid-scan, stop, note it, and continue at T1 or T0.
- nmap's default DNS resolution can leak your scanning through PTR queries.
  Use `-n` to skip reverse DNS when you want quiet, or keep it when you want
  the hostname intelligence.
- IPv6 scanning needs `-6` and link-local targets need a scope id
  (`fe80::1%eth0`). Global IPv6 ranges are too large to sweep; enumerate from
  DNS and neighbor discovery instead.

## Escalation

When nmap results contradict each other: cross-check with a second tool
(masscan for port confirmation, netcat for banner grabs). When every port
shows filtered, try the ACK scan to map the firewall, then scan from a
different network position if the rules allow (internal versus external view
differ enormously). When version detection draws a blank, grab banners
manually with ncat and compare against known service fingerprints. When the
IDS blocks your source IP mid-scan, stop and coordinate with the blue team
contact instead of rotating source addresses; evading the very team that
authorized you breaks the engagement.

## Detection and defender view

Defenders see nmap clearly: SYN packets to closed ports, OS detection probe
patterns, NSE script traffic (HTTP requests with distinctive user agents),
and timing patterns. IDS signatures exist for default nmap behavior, decoy
scans, and idle scans. Evasion techniques do not make you invisible; they
make you look like someone trying to hide, which is itself a high severity
alert. The professional move is the agreed scanning window and source IP,
documented in the rules of engagement. Your scan logs with timestamps are
the evidence that every packet was authorized.

## Key references

- MITRE ATT&CK T1046 Network Service Discovery
- MITRE ATT&CK T1595.001 Scanning IP Blocks
- MITRE ATT&CK T1595.002 Vulnerability Scanning
- CWE-200 Exposure of Sensitive Information to an Unauthorized Actor
- nmap man page and book: https://nmap.org/book/man.html
- NSE documentation: https://nmap.org/book/nse.html
- nmap 7.98 release notes: https://nmap.org/changelog.html
