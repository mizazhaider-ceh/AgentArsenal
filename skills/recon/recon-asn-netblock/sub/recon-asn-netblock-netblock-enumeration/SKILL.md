---
name: recon-asn-netblock-netblock-enumeration
parent: recon-asn-netblock
description: Use when you have the filtered in-scope prefix list and need to find the live hosts inside each netblock. Covers reverse DNS sweeps with dnsx, polite ping and port checks with nmap, banner and certificate pivots back to hostnames, handling large prefixes without blind sweeping, and merging discovered hosts into the master target list. Authorized targets only, only enumerate prefixes you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-asn-netblock]
extends: []
relates: [recon-asn-netblock-bgp-data, recon-asn-netblock-asn-lookup, recon-active, nmap-methodology]
tools:
  - name: dnsx
    version: 1.2
  - name: nmap
    version: 7.98
  - name: httpx
    version: 1.6
  - name: Python
    version: 3.12
---

Netblock enumeration finds the live hosts inside an authorized prefix: reverse DNS for names, liveness checks for hosts without names, and service pivots to identify what each host is. This is the noisiest recon step, so it runs last, inside authorized prefixes only, at polite rates. This sub-skill covers the enumeration for recon-asn-netblock. Only enumerate prefixes your authorization covers.

## Quick Workflow

1. Take prefixes-final.txt from the BGP filtering step; confirm each is still in scope.
2. Expand each prefix to its IP list.
3. Reverse-DNS sweep the IPs with dnsx through a public resolver; record every PTR name.
4. For IPs without PTR, run polite ping sweeps where the authorization allows active checks.
5. For live hosts, identify services: top-ports scan at a gentle rate, then certificate and banner pivots.
6. Pivot every IP back to names: PTR, TLS SANs, Shodan host data.
7. Merge hosts and new names into the master target list with source notes.

## 1. Expanding prefixes

```bash
# Expand all final prefixes to IP lists (example: two /24s)
while read -r p; do
  python3 -c "import ipaddress; print('\n'.join(str(h) for h in ipaddress.ip_network('$p').hosts()))"
done < prefixes-final.txt | sort -u > netblock-ips.txt
wc -l netblock-ips.txt
```

For prefixes larger than a /22, do not expand blindly: 65,000 IPs is a sweep, not recon. For large prefixes, enumerate via targeted means first (known hostnames resolved into the range, certificate pivots, Shodan net searches) and sweep only the sub-ranges where those cluster.

## 2. Reverse DNS sweep

PTR records are the quietest host discovery: one DNS query per IP, through a public resolver:

```bash
dnsx -l netblock-ips.txt -silent -ptr -resp -o ptr-sweep.txt -t 100 -rl 300
# Keep only IPs that returned a name
awk '$2 != "" && $2 != "[NXDOMAIN]"' ptr-sweep.txt > ptr-hits.txt
wc -l ptr-hits.txt
head -15 ptr-hits.txt
```

Example output shape:

```
203.0.113.10 vpn.example.com
203.0.113.21 jenkins.example.com
203.0.113.25 mail2.example.com
```

PTR names often include hosts that forward DNS never lists: management interfaces, backup hosts, numbered infrastructure. Every new name goes back into the subdomain candidate list for httpx probing.

## 3. Liveness for unnamed hosts

Where the authorization permits active checks, find which IPs are up:

```bash
nmap -sn -T3 --max-retries 1 --max-rtt-timeout 500ms \
  -iL netblock-ips.txt -oG ping-sweep.gnmap
grep "Up" ping-sweep.gnmap | cut -d' ' -f2 > netblock-live.txt
wc -l netblock-live.txt
```

Keep it gentle: `-T3`, single retry, and no port scanning in this pass. The goal is a live-host list, not a service map yet. If the authorization forbids even ping sweeps, skip this step; the PTR sweep and passive pivots still produce value.

## 4. Service identification on live hosts

For live hosts, a restrained top-ports pass plus pivots:

```bash
nmap -sV --top-ports 100 -T3 --max-retries 1 \
  -iL netblock-live.txt -oA netblock-services
grep -E "open" netblock-services.gnmap | head -30
```

Then pivot per host without more scanning:

```bash
# TLS certificates on open 443/8443 name the hosted domains
# Shodan host data gives banners passively
shodan host 203.0.113.44 --fields ip_str,port,hostnames,org 2>/dev/null
```

Prioritize hosts by strangeness: odd open ports, old software banners, hostnames suggesting admin or staging. Those go to the top of the later testing queue.

## 5. Merging into the master list

```bash
# New names from PTR go back to subdomain candidates
cut -d' ' -f2 ptr-hits.txt | sort -u > ptr-names.txt
cat ptr-names.txt >> all-candidates.txt && sort -u all-candidates.txt -o all-candidates.txt
# Live IPs with no names: direct-IP list (only if IP testing is authorized)
comm -23 <(sort netblock-live.txt) <(cut -d' ' -f1 ptr-hits.txt | sort -u) > unnamed-live.txt
wc -l ptr-names.txt unnamed-live.txt
```

Every asset carries its source note (ptr-sweep, ping-sweep, shodan-pivot) so later phases know how it was found and how fresh it is.

## Edge cases

- The prefix is mostly empty (cloud-allocated but unused): a handful of live hosts in a /24 is normal for cloud space. Do not re-sweep hoping for more.
- PTR sweep returns generic cloud names (ec2-...amazonaws.com): those confirm occupancy but add no intelligence; rely on certificate and Shodan pivots instead.
- The sweep triggers an abuse complaint or block: stop immediately, note what rate caused it, and continue only with passive pivots. Report the incident to your engagement lead.
- IPv6 prefixes: never sweep; use DNS, CT logs, and certificate pivots exclusively. The space is too large for any sweep to be meaningful or polite.

## Escalation

- Netblock yields nothing new: the prefix may be genuinely sparse. Cross-check with Shodan's net search (`net:203.0.113.0/24`) which sometimes sees hosts your sweep missed due to ICMP filtering.
- Interesting hosts sit just outside the authorized prefix: stop at the boundary. Note them as a scope question with evidence, do not probe them.

## Detection and defender view

- Sequential PTR sweeps and ping sweeps are the classic netblock-enumeration signature: monitor for them and alert, distinguishing authorized hunters (expected during engagements) from unknown sources.
- PTR records leak hostnames: audit yours. `db-backup-prod` in a PTR record tells an attacker exactly what to prioritize.
- Unused IP space that suddenly gets swept is often a precursor to targeted work; correlate sweep alerts with other recon signals.
- Keep prefix authorizations tight: hunters enumerate what the scope allows, so scope precision directly controls sweep volume against your network.

## Key references

- dnsx documentation: https://github.com/projectdiscovery/dnsx
- nmap documentation: https://nmap.org/book/man.html
- Shodan CLI documentation: https://developer.shodan.io
- RIPEstat API docs: https://stat.ripe.net/docs/data_api
- MITRE ATT&CK T1590.002 DNS: https://attack.mitre.org/techniques/T1590/002/
