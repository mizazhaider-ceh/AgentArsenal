---
name: recon-asn-netblock-asn-lookup
parent: recon-asn-netblock
description: Use when you know some of the target's IPs or domains and need to identify their autonomous system numbers. Covers IP-to-ASN lookup via Team Cymru and regional whois, domain-to-ASN via resolution plus lookup, handling multi-ASN organizations and acquisitions, verifying the ASN actually announces the prefix today, and recording the ASN inventory that feeds prefix mapping. Authorized targets only.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-asn-netblock]
extends: []
relates: [recon-asn-netblock-bgp-data, recon-passive, domain-osint]
tools:
  - name: whois
    version: 5.5
  - name: dig
    version: 9.18
  - name: Python
    version: 3.12
---

The ASN lookup step answers: which autonomous systems does this organization operate. Get it wrong and you enumerate someone else's network; get it right and the prefix mapping that follows is precise. This sub-skill covers identifying the target's ASNs for recon-asn-netblock: lookup methods, verification, and the multi-ASN reality of modern organizations. Only look up ASNs for organizations you are authorized to test.

## Quick Workflow

1. Collect known-good IPs: resolved subdomains, mail server IPs, IPs from Shodan host data.
2. Look up each IP's origin ASN via Team Cymru; record ASN, prefix, and AS name.
3. Cross-check with regional whois for the organization name on the ASN and prefix.
4. Deduplicate to the ASN set; investigate when known IPs map to different ASNs.
5. Verify each ASN announces its prefixes today via a looking glass or BGP data.
6. Record the ASN inventory with evidence per ASN; hand it to prefix mapping.

## 1. IP to ASN with Team Cymru

```bash
# Single IP
whois -h whois.cymru.com " -v 203.0.113.45"
# Bulk: feed IPs, get ASN mapping back
cat known-ips.txt | whois -h whois.cymru.com " -v -f" 2>/dev/null | sort -u
```

Example output shape:

```
AS      | IP            | BGP Prefix     | CC | Registry | Allocated  | AS Name
64496   | 203.0.113.45  | 203.0.113.0/24 | US | arin     | 2008-01-01 | EXAMPLE-CORP
64496   | 198.51.100.23 | 198.51.100.0/24| US | arin     | 2015-06-11 | EXAMPLE-CORP
```

Bulk mode is efficient: pipe your whole resolved-IP list through once and sort the ASN column. One dominant ASN means a simple footprint; several ASNs mean acquisitions, multi-cloud, or CDN fronting that needs untangling.

## 2. ASN details and organization check

```bash
# ASN record: name, allocated date, registry
whois -h whois.cymru.com " -v AS64496"
# Regional registry for the organization behind it
whois -h whois.arin.net AS64496 | grep -iE "asname|orgname|descr" | head -5
```

What to verify: the AS name resembles the target organization, the allocation date is plausible (a 2024 ASN for a 1998 company suggests a recent acquisition or a new network), and the registry matches the expected region. Mismatches do not disqualify an ASN, they just demand an explanation before you enumerate its prefixes.

## 3. Domain to ASN path

For domain-first recon, resolve then look up:

```bash
# Resolve key hostnames, then map their IPs to ASNs
for h in example.com mail.example.com vpn.example.com; do
  dig +short "$h" A @1.1.1.1 | head -3
done | sort -u > key-ips.txt
cat key-ips.txt | whois -h whois.cymru.com " -v -f" 2>/dev/null | sort -u
```

CDN-fronted names will map to the CDN's ASN (Cloudflare, Akamai), not the target's. That is correct and useful: it tells you which names are fronted, and the origin ASN hunt continues via historical DNS, certificate SANs on odd ports, and the other pivot techniques.

## 4. Multi-ASN situations

Large or acquisitive organizations legitimately hold several ASNs. Untangle them:

- List every ASN your IPs map to, with counts. The ASN holding most IPs is usually the primary.
- Research each: acquisition announcements, subsidiary names in the AS name, regional registries (a RIPE ASN for the EU subsidiary, an ARIN ASN for HQ).
- Record per-ASN scope status separately: your authorization may cover the primary ASN but not an acquired subsidiary's network. When unsure, ask.
- Watch for cloud ASNs (AWS, Azure, GCP): the target's cloud workloads live there, but the ASN is shared with millions of others. Cloud IPs need domain or certificate pivots, not ASN enumeration.

## 5. Verification before enumeration

Before enumerating any ASN's prefixes, verify it is real and current:

```bash
# RIPEstat: is the ASN currently announcing
curl -s "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS64496" \
  | jq '.data.prefixes | length'
# A looking glass or bgp.he.net confirms the announcements visually
```

An ASN with zero current announcements is either withdrawn (skip it) or your data is stale (re-check). Record the verification date; BGP changes and your notes should show when the picture was taken.

## Edge cases

- The IP maps to a DDoS-mitigation ASN (always-on scrubbing): the real origin ASN hides behind it. Look at historical BGP data from before the mitigation contract, or at non-HTTP services that bypass it.
- Private ASN numbers in whois output: data error or internal leak; ignore for internet enumeration.
- The ASN lookup returns different results per query time: BGP anycast and traffic engineering shift announcements. Take two snapshots hours apart and use the stable set.

## Escalation

- No ASN maps cleanly to the organization (everything is CDN or cloud): the ASN path is a dead end for this target. Fall back to domain and certificate pivots, which work regardless of where the IPs live.
- You find an ASN that looks like the target but the name is ambiguous: research the acquisition history before enumerating. Enumerating the wrong company's network is the failure mode this step exists to prevent.

## Detection and defender view

- ASN lookups are fully passive: queries hit Team Cymru and registries, never the target.
- Defenders should know their ASN inventory, including subsidiaries and acquisitions. Unknown ASNs in your name are either shadow IT or someone else's problem; find out which.
- Keep ASN and prefix registrations accurate: stale registry data sends authorized hunters toward the wrong networks and slows incident response.

## Key references

- Team Cymru IP to ASN: https://www.team-cymru.com/ip-asn-mapping
- RIPEstat API docs: https://stat.ripe.net/docs/data_api
- bgp.he.net: https://bgp.he.net
- ARIN whois: https://www.arin.net
- MITRE ATT&CK T1590 Gather Victim Network Information: https://attack.mitre.org/techniques/T1590/
