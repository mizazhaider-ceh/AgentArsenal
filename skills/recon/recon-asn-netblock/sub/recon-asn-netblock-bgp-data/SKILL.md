---
name: recon-asn-netblock-bgp-data
parent: recon-asn-netblock
description: Use when you have the target's ASN and need the full list of prefixes it announces on the internet. Covers pulling announced prefixes from RIPEstat and bgp.he.net, reading announcement history from RouteViews, distinguishing the target's own prefixes from customer or downstream allocations, handling anycast and stale announcements, and producing the filtered prefix list for netblock enumeration. Authorized targets only.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-asn-netblock]
extends: []
relates: [recon-asn-netblock-asn-lookup, recon-asn-netblock-netblock-enumeration, recon-passive]
tools:
  - name: curl
    version: 8.5
  - name: jq
    version: 1.7
  - name: Python
    version: 3.12
---

BGP data shows which IP prefixes an ASN actually announces to the internet right now, and which it announced historically. That turns an ASN number into a concrete list of netblocks to enumerate. This sub-skill covers reading BGP data for recon-asn-netblock: sources, filtering, and the traps (customer prefixes, anycast, stale data). Only map prefixes for ASNs you are authorized to enumerate.

## Quick Workflow

1. Take the verified ASN inventory from the ASN lookup step.
2. Pull current announced prefixes from RIPEstat for each ASN.
3. Cross-check with bgp.he.net for prefix descriptions and neighbor context.
4. Check announcement history via RouteViews for prefixes that appeared or vanished.
5. Filter: drop customer allocations, downstream re-announcements, and anycast where noted.
6. Verify each kept prefix is currently announced via a looking glass.
7. Write the filtered prefix list with a keep/drop reason per prefix.

## 1. RIPEstat announced prefixes

```bash
curl -s "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS64496" \
  | jq -r '.data.prefixes[] | "\(.prefix) \(.timelines[0].starttime // "?")"' \
  | sort -u > bgp-prefixes.txt
wc -l bgp-prefixes.txt
cat bgp-prefixes.txt
```

Example output shape:

```
192.0.2.0/23 2021-03-14T00:00:00
198.51.100.0/24 2015-06-11T00:00:00
203.0.113.0/24 2008-01-01T00:00:00
```

The start time shows how long each prefix has been announced: long-stable prefixes are the core network; recently appeared ones may be new acquisitions or new deployments worth prioritizing. Save the raw JSON; re-parsing beats re-querying.

## 2. bgp.he.net context

bgp.he.net renders the ASN's prefixes with descriptions, plus the upstream and downstream neighbors:

- Read each prefix's description: "EXAMPLE-CORP-CUSTOMERS" versus "EXAMPLE-CORP-INFRA" tells you which to keep.
- Check the neighbor list: heavy downstream customer cones mean most prefixes are not the target's own.
- Note anycast flags: anycast prefixes enumerate unreliably and usually belong to shared services.

Use it as the human-readable cross-check against the RIPEstat machine list. When they disagree on whether a prefix is currently announced, trust the fresher source and verify with a looking glass.

## 3. Announcement history with RouteViews

```bash
# RIPEstat also exposes historical announcement data per prefix
curl -s "https://stat.ripe.net/data/bgplay/data.json?resource=203.0.113.0/24" -o bgplay.json
# Look for origin ASN changes over time: a prefix that moved between
# ASNs changed hands, which matters for ownership confidence
```

History answers: did this prefix always belong to this ASN, did it appear recently (new acquisition), did it disappear and come back (reallocated). A prefix announced by the target's ASN for ten years is high-confidence; one that appeared last month needs an ownership double-check before enumeration.

## 4. Filtering to the target's own prefixes

The keep/drop decision per prefix:

- Keep: description names the target, long stable announcement, size consistent with an org network (/24 to /20 typical for enterprise; larger needs justification).
- Drop: description names customers or "pool," downstream ASN re-announcing it, known CDN or cloud prefixes inside a shared ASN.
- Investigate: no description, recent appearance, odd size. Check whois on the prefix and the announcement history before deciding.

```bash
# prefix-decisions.txt format: prefix | KEEP/DROP | reason
# 203.0.113.0/24 | KEEP | EXAMPLE-CORP-INFRA, stable since 2008
# 198.51.100.0/24 | DROP | EXAMPLE-CORP-CUSTOMERS pool
# 192.0.2.0/23 | KEEP | no descr, stable 5y, whois shows org; asked, confirmed in scope
grep "KEEP" prefix-decisions.txt | cut -d'|' -f1 | tr -d ' ' > prefixes-final.txt
wc -l prefixes-final.txt
```

When the ASN is a provider's, expect to drop most prefixes. That is correct; enumerating customer space is out of scope by definition.

## Edge cases

- The ASN announces a huge aggregate (a /16 or larger): do not sweep it blindly. Break it into announced more-specifics first; if none exist, ask the program which parts are theirs.
- Prefixes visible in RIPEstat but not in your region's view: BGP views differ. Check two sources (RIPEstat plus a looking glass in another region) before declaring a prefix withdrawn.
- IPv6 prefixes: include them in the inventory; enumerate via DNS and certificate pivots rather than sweeping, since the space is too large.
- Private-use or reserved prefixes in the list: data artifacts; drop them.

## Escalation

- BGP data is thin for the ASN (few prefixes, sparse history): the org may be mostly cloud-hosted. Pivot to cloud IP range data (published JSON by AWS, Azure, GCP) correlated with the target's domains instead.
- Filtering drops everything: the ASN path may be wrong for this target, or the target may genuinely own no announced space. Re-verify the ASN lookup step before concluding.

## Detection and defender view

- BGP queries are fully passive: registries and stat APIs, never the target.
- Defenders: audit your announced prefixes regularly. Forgotten announcements are a classic shadow-infrastructure source, and stale registry descriptions mislead everyone including your own team.
- Monitor for unauthorized announcements of your prefixes (hijacks): BGP monitoring is a defensive control, and the same data hunters use for recon serves it.
- Keep prefix descriptions accurate: they are the first thing anyone, friendly or not, reads about your network.

## Key references

- RIPEstat API docs: https://stat.ripe.net/docs/data_api
- bgp.he.net: https://bgp.he.net
- RouteViews: http://www.routeviews.org
- Team Cymru BGP tools: https://www.team-cymru.com
- MITRE ATT&CK T1590.003 Network Trust Dependencies: https://attack.mitre.org/techniques/T1590/003/
