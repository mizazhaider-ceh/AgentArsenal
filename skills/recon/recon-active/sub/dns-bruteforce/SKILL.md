---
name: dns-bruteforce
description: Use when you need to discover subdomains and DNS records of a
  target domain during authorized active reconnaissance. Covers wordlist
  brute-forcing with dnsenum and custom scripts, zone transfer attempts,
  wildcard detection, and validating results against passive data. Use when
  expanding the attack surface beyond known hosts, when passive recon missed
  subdomains, or when you need DNS records (MX, TXT, SRV) mapped before
  port scanning.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
parent: recon-active
requires: [recon-active]
extends: []
relates: [recon-passive, nmap-methodology]
tools:
  - name: Python
    version: 3.12
  - name: nmap
    version: 7.98
  - name: Amass
    version: 4.2
---

DNS brute-forcing finds subdomains that passive sources missed by guessing
names from wordlists and checking which ones resolve. This skill covers
authorized DNS enumeration: wordlist selection, wildcard handling (the most
common source of false positives), zone transfer tests, and record
enumeration. It stays on DNS only; what you do with the hosts you find
belongs to port-service-enum and web-tech-fingerprint. Keep query rates
sane: DNS brute-forcing is noisy by nature, so stay inside the agreed scope
and window.

## Quick Workflow

1. Confirm the target domain and scope in writing before sending any query.
2. Test for zone transfers (AXFR) against every authoritative nameserver.
3. Check for DNS wildcards before brute-forcing, so you can filter them.
4. Brute-force with a curated wordlist, then a larger one only if needed.
5. Enumerate record types (A, AAAA, MX, TXT, SRV, CNAME) for each live host.
6. Deduplicate against passive recon results and resolve every name to IPs.
7. Hand the clean host list to the next recon phase.

## 1. Zone transfers and wildcard checks

```bash
# Find authoritative nameservers first
dig +short NS target.example

# Try AXFR against each nameserver (usually refused, but one success
# hands you the whole zone)
dig AXFR target.example @ns1.target.example

# Wildcard test: resolve a name that cannot exist
dig +short nonexistent-xyz123.target.example
# If it resolves, the zone has a wildcard: every guess will "hit",
# so you must filter by comparing against this baseline IP
```

If AXFR succeeds, you are done with brute-forcing for that zone: the
transfer is the complete answer. Record it and move on.

## 2. Wordlist brute-forcing

```bash
# Fast stdlib Python bruter with wildcard filtering
python3 - <<'EOF'
import socket, sys

DOMAIN = "target.example"
# baseline: resolve the impossible name once
try:
    WILDCARD = socket.gethostbyname("nonexistent-xyz123." + DOMAIN)
except socket.gaierror:
    WILDCARD = None

found = set()
with open("/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-5000.txt") as f:
    for line in f:
        name = line.strip() + "." + DOMAIN
        try:
            ip = socket.gethostbyname(name)
        except socket.gaierror:
            continue
        if ip != WILDCARD and name not in found:
            found.add(name)
            print(f"{name} -> {ip}", flush=True)

print(f"[*] {len(found)} unique hosts", file=sys.stderr)
EOF

# nmap's dns-brute script as an alternative
nmap --script dns-brute --script-args dns-brute.domain=target.example \
  -oN /tmp/dnsbrute.txt target.example
```

Start with the top 5000 subdomains list. Only move to the million-entry
lists when the small list is exhausted and the scope allows the noise and
time.

## 3. Record enumeration

```bash
# Full record sweep for the domain and each discovered host
for rtype in A AAAA MX TXT SRV NS CAA; do
  echo "== $rtype =="
  dig +short $rtype target.example
done

# SRV records reveal services (sip, ldap, kerberos)
dig +short SRV _sip._tcp.target.example
dig +short SRV _ldap._tcp.target.example
dig +short SRV _kerberos._tcp.target.example

# TXT records often leak SPF, verification tokens, and service hints
dig +short TXT target.example

# Resolve every found host and note IP sharing (one IP, many names
# usually means virtual hosting, which changes web testing)
sort -u /tmp/hosts.txt | while read h; do
  echo "$h -> $(dig +short A $h | tr '\n' ' ')"
done
```

TXT and SRV records are recon gold: they name third-party services, mail
providers, and internal service layouts without a single port scan.

## Edge cases

- The wildcard resolves to a parking page IP. Filter every result against
  the baseline IP, and re-check the baseline hourly in case it changes.
- DNS rate limiting drops your queries. Slow the loop, randomize name
  order, and resume from the last wordlist offset instead of restarting.
- Split-horizon DNS answers differently inside and outside. Note which view
  you tested; internal names may only resolve from the engagement network.
- The wordlist finds nothing new. Combine discovered names into mutations
  (dev2, staging2, old) and try permutations of known hosts before giving
  up on the zone.

## Escalation

- AXFR refused everywhere and brute-forcing stalls: pivot to certificate
  transparency logs and passive sources (see recon-passive), then feed new
  names back into the bruter as seeds.
- You need vhost discovery on a shared IP: brute-force the Host header
  against the IP with ffuf instead of DNS, since the names may not have
  DNS records at all.
- DNSSEC is in use: walk NSEC records to enumerate the zone directly
  (`dig +dnssec target.example`), which is quieter and complete.

## Detection and defender view

Defenders see DNS brute-forcing as a burst of NXDOMAIN responses from one
source in their DNS logs, which is one of the most recognizable recon
patterns there is. Zone transfer attempts are almost always logged and
alerted. Defenses are rate limiting on resolvers, refusing AXFR to
untrusted sources, monitoring for NXDOMAIN spikes, and keeping the public
DNS footprint minimal so brute-forcing finds little.

## Key references

- MITRE ATT&CK T1590.002 (Gather Victim Network Information: DNS).
- MITRE ATT&CK T1595 (Active Scanning).
- NIST SP 800-115 (Technical Guide to Information Security Testing).
- SecLists DNS wordlists: subdomains-top1million series.
