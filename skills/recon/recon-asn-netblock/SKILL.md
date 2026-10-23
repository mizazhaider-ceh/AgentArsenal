---
name: recon-asn-netblock
description: Use when authorized reconnaissance needs to move from domain names to the organization's network infrastructure. Covers finding the target's autonomous system numbers (whois, Team Cymru, BGP data), mapping the netblocks an ASN announces, enumerating live hosts inside those netblocks, and pivoting from netblocks back to hostnames via reverse DNS and certificate data. Authorized targets only, only enumerate networks you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [recon-passive, recon-active, recon-subdomain-enumeration, bugbounty-scope-recon, nmap-methodology]
tools:
  - name: whois
    version: 5.5
  - name: dig
    version: 9.18
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
---

An autonomous system number identifies the networks an organization operates on the internet. Enumerating the ASN's netblocks finds infrastructure that domain-based recon never names: unlabeled hosts, management interfaces, VPN concentrators, and forgotten servers. This skill covers the full ASN-to-hosts pipeline for authorized recon: ASN lookup, BGP announced-prefix mapping, netblock enumeration, and pivoting back to names. Only enumerate networks your authorization covers.

## Quick Workflow

1. Confirm authorization covers network enumeration, and record the scope in SCOPE.txt.
2. Find the target's ASN: whois on known IPs, Team Cymru IP-to-ASN, BGP looking glasses.
3. Map the ASN's announced prefixes from BGP data (RouteViews, RIPEstat, bgp.he.net).
4. Filter prefixes to the ones plausibly operated by the target (size, description, history).
5. Enumerate live hosts inside in-scope prefixes: reverse DNS sweeps, polite ping and port checks.
6. Pivot back to names: PTR records, certificate SANs on discovered IPs, Shodan host data.
7. Merge new hosts and names into the master target list with source notes.

## 1. Finding the ASN

Start from IPs you already know belong to the target:

```bash
# whois on a known IP reveals the origin ASN
whois -h whois.cymru.com " -v 203.0.113.45"
# Example output shape:
# AS | IP | BGP Prefix | CC | Registry | Allocated | AS Name
# 64496 | 203.0.113.45 | 203.0.113.0/24 | US | arin | 2008-01-01 | EXAMPLE-CORP

# Or query by ASN directly
whois -h whois.cymru.com " -v AS64496"
```

Team Cymru's whois service is the fastest IP-to-ASN lookup. Cross-check with `whois 203.0.113.45` against the regional registry (ARIN, RIPE, APNIC) for the organization name, and with a BGP looking glass to confirm the prefix is actually announced by that ASN right now, not just registered to it.

## 2. Mapping announced prefixes

An ASN may announce dozens of prefixes; you need the list:

```bash
# RIPEstat API: announced prefixes for an ASN
curl -s "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS64496" \
  | jq -r '.data.prefixes[].prefix' | sort -u > asn-prefixes.txt
wc -l asn-prefixes.txt
head -10 asn-prefixes.txt
```

Example output shape:

```
203.0.113.0/24
198.51.100.0/24
192.0.2.0/23
```

Also check bgp.he.net for the ASN's prefix list with descriptions, and RouteViews data for announcement history. Filter the list: drop prefixes clearly belonging to customers or downstream allocations (check the whois description and the size; a /8 is not one company's office network). Keep only prefixes your authorization covers; an ASN shared with customers means most prefixes are out of scope.

## 3. Netblock enumeration

For each in-scope prefix, find the live hosts. Reverse DNS first, it is the quietest:

```bash
# Generate IPs and reverse-resolve (example for a /24)
python3 -c "import ipaddress; print('\n'.join(str(h) for h in ipaddress.ip_network('203.0.113.0/24').hosts()))" > block-ips.txt
# Bulk reverse DNS through a public resolver
dnsx -l block-ips.txt -silent -ptr -resp -o ptr.txt
grep -v "NXDOMAIN" ptr.txt | head -20
```

Example output shape:

```
203.0.113.10 -> vpn.example.com
203.0.113.21 -> jenkins.example.com
203.0.113.44 -> (no PTR)
```

PTR records often name hosts that forward DNS never lists. For hosts without PTR, polite liveness checks where authorized:

```bash
nmap -sn -T3 --max-retries 1 -iL block-ips.txt -oG ping.gnmap
grep "Up" ping.gnmap | cut -d' ' -f2 > block-live.txt
```

Then check what the live hosts serve: certificates on open TLS ports give SANs, and Shodan host data gives banners without you scanning.

## 4. Pivoting back to names

Every discovered IP gets pivoted back to the domain world:

```bash
# Certificates on the IP often name subdomains (SNI-less handshake)
echo | openssl s_client -connect 203.0.113.44:443 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName 2>/dev/null | tr ',' '\n' | grep DNS
# Shodan host lookup by IP (passive, uses their index)
shodan host 203.0.113.44 --fields ip_str,port,hostnames,org
```

Hostnames from PTR, SANs, and Shodan merge back into the subdomain candidate list, often revealing names the DNS-based enumeration missed entirely. IPs with no names at all go on the direct-IP testing list, but only if the authorization covers IP-based testing.

## Edge cases

- The ASN is a hosting provider or CDN: 99 percent of prefixes belong to customers. Only enumerate prefixes the target actually operates; when unsure, treat the prefix as out of scope.
- Anycast prefixes: the same prefix announced from many places. Host enumeration on anycast space is unreliable; focus on the unicast prefixes.
- Prefixes announced but not routed to you: some prefixes are announced for DDoS mitigation or backup. If you cannot reach them, note it and move on.
- Stale BGP data: verify announcements are current with a looking glass before spending enumeration time on a withdrawn prefix.
- IPv6 prefixes: enumerate them too; organizations often leave IPv6 space far less hardened, but the address space is too large to sweep, so rely on DNS and certificate pivots instead of brute force.

## Escalation

- Netblock enumeration stalls: pivot on the discovered IPs in Shodan and Censys for banners and certificate history, which often names neighboring hosts.
- A prefix yields interesting hosts just outside your authorization: stop at the boundary and ask. Network-adjacent is not in-scope.
- The target operates multiple ASNs (common after acquisitions): repeat the pipeline per ASN, keeping separate prefix lists and scope notes.

## Detection and defender view

- ASN enumeration is passive until the host enumeration step; whois and BGP queries touch registries, not the target.
- Ping sweeps and reverse-DNS sweeps of whole netblocks are visible and noisy. Keep them inside authorized prefixes and at polite rates.
- Defenders: know your ASN footprint. Audit announced prefixes for ones you forgot, and ensure PTR records do not leak sensitive hostnames (db-backup-prod is a label, not a secret, but it helps attackers prioritize).
- Monitor for enumeration patterns against your netblocks: sequential PTR queries and ping sweeps are the signature.

## Key references

- Team Cymru IP to ASN: https://www.team-cymru.com/ip-asn-mapping
- RIPEstat API docs: https://stat.ripe.net/docs/data_api
- bgp.he.net: https://bgp.he.net
- RouteViews: http://www.routeviews.org
- ARIN whois: https://www.arin.net
- MITRE ATT&CK T1590.003 Network Trust Dependencies: https://attack.mitre.org/techniques/T1590/003/
- nmap documentation: https://nmap.org/book/man.html
