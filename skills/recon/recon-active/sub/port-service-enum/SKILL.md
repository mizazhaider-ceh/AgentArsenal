---
name: port-service-enum
description: Use when you have a list of in-scope hosts and need to find
  open ports and identify the services behind them during authorized active
  reconnaissance. Covers scan strategy from fast discovery to full port
  sweeps, service probing without nmap scripts, interpreting ambiguous
  results, and building a clean service inventory. Use when starting network
  enumeration, when nmap-methodology needs a focused service pass, or when
  you must map what is reachable before choosing attack paths.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
parent: recon-active
requires: [recon-active]
extends: []
relates: [nmap-methodology, recon-passive]
tools:
  - name: nmap
    version: 7.98
  - name: masscan
    version: 1.3.2
  - name: Python
    version: 3.12
---

Port and service enumeration turns a list of hostnames into a map of what
is actually reachable: open ports, the services on them, and first-glance
fingerprints. This skill covers the enumeration layer on authorized tests:
scan strategy that balances speed against stealth, service identification
beyond banner grabs, and result triage. Full nmap methodology (host
discovery, scripting, evasion) lives in nmap-methodology; this sub-skill is
the focused service-inventory pass.

## Quick Workflow

1. Start from the confirmed in-scope host list, with IPs resolved.
2. Run a fast top-ports sweep to find live services quickly.
3. Follow with a full TCP port sweep on hosts that matter.
4. Probe open ports for service identity: banners, handshakes, TLS.
5. Sweep the most common UDP services (DNS, SNMP, NTP) lightly.
6. Deduplicate, resolve ambiguities, and write the service inventory.
7. Flag interesting services (databases, admin panels, legacy protocols)
   for deeper phases.

## 1. Fast discovery sweep

```bash
# Top 1000 ports, fast, service detection on hits only
nmap -T4 --top-ports 1000 -sV --open -oN /tmp/fast.txt 10.0.5.0/24

# Masscan for very large ranges, then nmap the hits precisely
masscan 10.0.0.0/16 -p1-65535 --rate 10000 -oX /tmp/mass.xml
python3 - <<'EOF'
import xml.etree.ElementTree as ET
hosts = {}
for h in ET.parse('/tmp/mass.xml').getroot().iter('host'):
    ip = h.find('address').get('addr')
    ports = [p.get('portid') for p in h.iter('port')]
    hosts[ip] = ports
with open('/tmp/targets.txt', 'w') as f:
    for ip, ports in hosts.items():
        f.write(f"{ip} {','.join(ports)}\n")
print(f"[*] {len(hosts)} hosts with open ports")
EOF
```

Masscan finds ports at speed; nmap identifies services with care. Use both
in that order on large scopes, and nmap alone on small ones.

## 2. Full port sweeps and service probing

```bash
# Full TCP sweep on one important host, all 65535 ports
nmap -T4 -p- --min-rate 1000 -oN /tmp/full.txt 10.0.5.23

# Service detection with version intensity on the found ports
nmap -sV --version-intensity 5 -p 22,80,443,3306,3389 \
  -oN /tmp/svc.txt 10.0.5.23

# Manual banner grabs when nmap is unsure (noisy services, custom ports)
(echo; sleep 1) | timeout 5 nc 10.0.5.23 22 | head -3
printf 'HEAD / HTTP/1.0\r\n\r\n' | timeout 5 nc 10.0.5.23 80 | head -10

# TLS fingerprint on HTTPS ports: certificate names leak hosts and org data
echo | timeout 5 openssl s_client -connect 10.0.5.23:443 -servername target.example 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

When nmap labels a service `tcpwrapped` or `unknown`, the manual probes
above usually resolve it in seconds.

## 3. Light UDP enumeration

```bash
# Top UDP services only; full UDP sweeps are slow and often out of scope
nmap -T4 -sU --top-ports 20 --open -oN /tmp/udp.txt 10.0.5.23

# Confirm SNMP with a community string probe (default strings only,
# never brute-force communities without permission)
snmpwalk -v2c -c public 10.0.5.23 1.3.6.1.2.1.1.1.0 2>&1 | head -3
```

UDP scanning is unreliable by nature (no handshake to confirm). Treat
`open|filtered` as a lead to confirm with an application probe, not as a
finding.

## Edge cases

- All ports show filtered. A firewall is dropping probes; try ACK scans or
  different timing, and note the filtering in the inventory instead of
  reporting zero services.
- The host responds but every banner is generic. Load balancers and
  honeypots do this; check TTL values, TCP window sizes, and response
  consistency for signs of fakery.
- Scan results differ between runs. Load-balanced backends or port
  knocking cause flapping; run the sweep twice and keep the union with
  notes.
- IPv6 is in scope but untested. Enumerate it separately; services often
  listen on IPv6 with different firewall rules than IPv4.

## Escalation

- You need stealth: drop to `-T2`, scan from the engagement jump host
  during business hours so the traffic blends in, or split the sweep
  across several days.
- A critical host must not be fully scanned: agree a top-ports-only
  exception with the test lead in writing and note the limitation.
- Service identity stays unknown after probes: capture the handshake with
  Wireshark and compare against known protocol fingerprints before
  labeling it unknown.

## Detection and defender view

Defenders see port scanning as connection bursts across many ports from one
source, which IDS and firewalls flag reliably. Full 65k sweeps and masscan
at high rates are unmistakable. Defenses are IDS scan detection, firewall
rate limiting, and minimizing exposed services so scans find little. Slow,
distributed scanning raises cost for both sides; the durable answer is a
small external footprint.

## Key references

- MITRE ATT&CK T1046 (Network Service Discovery).
- MITRE ATT&CK T1595 (Active Scanning).
- nmap 7.98 documentation: service detection.
- NIST SP 800-115 (Technical Guide to Information Security Testing).
