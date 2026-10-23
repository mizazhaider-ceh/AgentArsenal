---
name: infra-osint
description: Use when mapping an organization's internet infrastructure
  from public sources on an authorized engagement. Covers ASN and netblock
  discovery, certificate transparency, cloud asset discovery, and
  technology fingerprinting from public data. Use when building the
  external attack surface, when the scope is the organization (not just
  named hosts), or when finding forgotten internet-facing assets.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-methodology
requires: [osint-methodology]
extends: []
relates: [recon-passive, recon-active]
tools:
  - name: Amass
    version: 4.2
  - name: theHarvester
    version: 4.6
  - name: Python
    version: 3.12
---

Infrastructure OSINT maps what an organization exposes to the internet
without touching it: netblocks, domains, certificates, and cloud assets,
all from public sources. This skill covers building the external
footprint for authorized engagements: the sources, the correlation, and
the forgotten assets it finds. It feeds the active recon phases with a
target list grounded in public fact.

## Quick Workflow

1. Identify the organization's ASNs, netblocks, and domains.
2. Harvest subdomains from certificate transparency and passive DNS.
3. Discover cloud assets in the organization's name.
4. Fingerprint technologies from public banners and records.
5. Correlate: which assets belong together, which are forgotten.
6. Hand the verified list to active recon with the source notes.

## 1. ASN and netblock discovery

```bash
# Find the organization's ASNs (via whois and BGP public data)
whois -h whois.radb.net -- '-i origin AS15169' 2>/dev/null | head -10
# Then the announced prefixes per ASN:
whois -h whois.radb.net -- '-i origin AS15169' 2>/dev/null | grep -E '^route' | head -20

# Organization name search in whois (the starting point)
whois "Example Corp" 2>/dev/null | head -20
```

Netblocks define the authorized scanning scope as much as the target
list: confirm each block belongs to the organization before it goes
anywhere near active tools. Acquisitions and divestitures make this
stale fast; verify, do not assume.

## 2. Certificate transparency and passive DNS

```bash
# Certificate transparency: every public cert is logged with its names
# Query crt.sh for the organization's domains
curl -s 'https://crt.sh/?q=%25.example.com&output=json' 2>/dev/null \
  | python3 -c "
import json,sys
data = json.load(sys.stdin)
names = set()
for e in data:
    for n in e['name_value'].split('\n'):
        names.add(n.strip())
print('\n'.join(sorted(names)[:30]))
print('total:', len(names))
"

# Passive DNS and Amass round out the subdomain list
amass enum -passive -d example.com -o /tmp/infra_subs.txt 2>/dev/null | head -20
```

Certificate transparency is the highest-yield public source for
subdomains: it is complete, current, and free. New certificates appear
here first, which makes it the monitoring feed for new assets too.

## 3. Cloud and technology footprint

```bash
# Cloud assets: search public bucket and naming patterns for the org
# (passive techniques: certificate names, DNS, public indexes)
# Record: buckets, CDN distributions, SaaS instances in the org's name

# Technology fingerprinting from public records:
# - MX records: the mail provider and its security posture
dig +short MX example.com
# - TXT records: SPF, verification tokens naming SaaS products
dig +short TXT example.com
# - NS records: the DNS provider (takeover risk if dangling)
dig +short NS example.com
```

Dangling DNS (CNAME to a deleted cloud resource) is the classic infra
OSINT finding: it is visible publicly, verifiable passively, and
directly exploitable. Check every CNAME's target resolvability as part
of the footprint review.

## Edge cases

- The organization uses many brands and subsidiaries. Map each
  separately; shared infrastructure still gets tested once with the
  right scope.
- Public sources conflict. Prefer the freshest (CT logs over old
  whois); note conflicts rather than picking silently.
- The footprint is enormous. Prioritize by exposure (internet-facing,
  data-bearing) and hand the prioritized list forward.
- Attribution is uncertain (shared hosting, CDNs). Verify ownership
  through multiple sources before scoping decisions.

## Escalation

- You find a clearly forgotten, vulnerable asset: report it as the
  priority finding of the recon phase; forgotten assets are where
  breaches start.
- The footprint suggests a recent acquisition: confirm whether it is
  in scope before active testing; acquisitions are scope gray areas.
- Continuous monitoring needed: the CT and passive DNS checks become
  the scheduled job.

## Detection and defender view

For defenders, infrastructure OSINT is the external attack surface
management program: the same public sources, monitored continuously,
showing what the organization exposes. The defender's work is keeping
the public footprint minimal and monitored: retire dangling DNS,
inventory cloud assets, and watch CT logs for unauthorized
certificates. Attackers do this recon for free; defenders should do it
first.

## Key references

- OSINT framework references (infrastructure sources).
- Certificate Transparency (RFC 6962) documentation.
- MITRE ATT&CK T1590 (Gather Victim Network Information).
