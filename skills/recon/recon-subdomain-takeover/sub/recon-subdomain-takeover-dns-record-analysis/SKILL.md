---
name: recon-subdomain-takeover-dns-record-analysis
parent: recon-subdomain-takeover
description: Use when you have an in-scope subdomain list and need to find takeover candidates in the DNS records. Covers enumerating CNAME, A, and NS records at scale with dig, spotting dangling CNAMEs (targets that no longer resolve), expired cloud IP assignments, dead delegated nameservers, and building the candidate list with evidence per record. Authorized targets only, only analyze domains you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-subdomain-takeover]
extends: []
relates: [recon-subdomain-takeover-cloud-service-fingerprints, dns-enumeration, recon-subdomain-enumeration]
tools:
  - name: dig
    version: 9.18
  - name: dnsx
    version: 1.2
  - name: Python
    version: 3.12
---

Takeover candidates hide in DNS records: CNAMEs pointing at gone services, A records on released cloud IPs, NS delegations to dead nameservers. Systematic record analysis across the whole subdomain list finds them all instead of the lucky few. This sub-skill covers the DNS analysis step of recon-subdomain-takeover. Only analyze domains you are authorized to test.

## Quick Workflow

1. Take the confirmed in-scope subdomain list as input.
2. Pull CNAME, A, and NS records for every name with dig through a public resolver.
3. Build the CNAME map: subdomain to target, and flag targets that do not resolve.
4. Check A records against known cloud IP ranges for reassignment risk.
5. Check NS delegations for dead or claimable nameservers.
6. Write the candidate list: record, target, why it is suspicious, timestamp.
7. Hand candidates to fingerprinting for verification.

## 1. Bulk record collection

```bash
# CNAME map for the whole confirmed list
while read -r sub; do
  target=$(dig +short "$sub" CNAME @1.1.1.1 | head -1)
  [ -n "$target" ] && echo "$sub $target"
done < confirmed.txt > cname-map.txt

# A records alongside, for cloud IP checks
dnsx -l confirmed.txt -silent -a -resp -o a-records.txt -t 50

# NS records for delegated subdomains
while read -r sub; do
  ns=$(dig +short "$sub" NS @1.1.1.1 | tr '\n' ' ')
  [ -n "$ns" ] && echo "$sub NS: $ns"
done < confirmed.txt > ns-map.txt

wc -l cname-map.txt a-records.txt ns-map.txt
```

Run these through a public resolver, not the target's authoritative servers. Save all three maps; the fingerprinting step needs the CNAME targets, and the report needs the raw record evidence.

## 2. Dangling CNAME detection

A CNAME target that does not resolve is the classic takeover signal:

```bash
# For each unique CNAME target, check if it resolves
cut -d' ' -f2 cname-map.txt | sort -u > cname-targets.txt
while read -r t; do
  ip=$(dig +short "$t" A @1.1.1.1 | head -1)
  if [ -z "$ip" ]; then echo "DANGLING: $t"; else echo "alive: $t -> $ip"; fi
done < cname-targets.txt > cname-status.txt
grep DANGLING cname-status.txt
```

Example output shape:

```
DANGLING: example-blog.herokuapp.com.
DANGLING: old-docs.s3-website-us-east-1.amazonaws.com.
alive: shops.myshopify.com. -> 23.227.38.65
```

Also flag CNAME targets on known-takeoverable service domains even when they resolve: a resolving `*.herokuapp.com` may still be an unclaimed app slot serving the "no such app" page. Resolution is necessary but not sufficient; fingerprinting decides.

## 3. A records and cloud IP reassignment

A records pointing at cloud provider ranges deserve a second look when the hostname suggests the resource may be gone:

```bash
# Example: list A records and eyeball cloud ranges
cat a-records.txt | head -20
# Spot-check ownership signals: reverse DNS of the IP
dig +short -x 203.0.113.87 @1.1.1.1
```

Signals of a released resource: the PTR shows a generic cloud hostname rather than the organization's name, the IP serves nothing or someone else's content, and historical data shows the IP previously served the organization. Confirm carefully: an A record on a cloud IP that still serves the organization's content is just cloud hosting, not a finding. The finding needs the resource-gone evidence, usually from the fingerprint step.

## 4. Dead delegated nameservers

Subdomain NS delegations are the overlooked takeover vector:

```bash
cat ns-map.txt
# For each delegated nameserver, check it resolves and serves the zone
ns="ns1.old-provider.example"
dig +short "$ns" A @1.1.1.1 || echo "DEAD NS: $ns"
dig @"$ns" delegated.example.com SOA +short 2>/dev/null || echo "NS not serving: $ns"
```

A dead nameserver that is claimable at a registrar (expired domain) means whoever registers it controls the delegated zone. Verify the domain's registration status with whois before calling it claimable; a dead-but-registered nameserver is a reliability issue, not a takeover.

## 5. The candidate list

```bash
# candidates-takeover.txt format: subdomain | record | target | signal | date
# blog.example.com | CNAME | example-blog.herokuapp.com. | target NXDOMAIN | 2026-10-23
# docs.example.com | CNAME | old-docs.s3-website-us-east-1.amazonaws.com. | target NXDOMAIN | 2026-10-23
# shop.example.com | CNAME | shops.myshopify.com. | service domain, needs fingerprint | 2026-10-23
wc -l candidates-takeover.txt
```

Each line carries its evidence pointer (the dig output file and timestamp). Candidates with only a weak signal go in a separate watch list, not the verification queue.

## Edge cases

- CNAME chains (CNAME to CNAME to service): follow the full chain; the dangling link may be two hops down. `dig +trace` or repeated dig calls resolve the chain.
- The CNAME target resolves via wildcard at the provider: some providers wildcard their whole service domain, so resolution proves nothing. Fingerprinting is the decider there.
- GeoDNS or split-horizon answers: the record you see depends on where you query from. Note the resolver used; a target that looks dangling from one region may be alive in another.
- Large subdomain lists: the per-name dig loop is slow. Batch with dnsx where possible and parallelize the loop with xargs -P for the rest.

## Escalation

- DNS analysis finds nothing: check historical DNS (SecurityTrails, passive DNS) for CNAMEs that existed last year and were removed. A removed CNAME to a still-unclaimed service name can be re-pointed by the organization or is already fixed; either way the history teaches the pattern.
- A candidate's service domain is unfamiliar: research whether that service allows endpoint claiming before spending verification effort. Not every SaaS with a CNAME is takeoverable.

## Detection and defender view

- The candidate list is also the defender's audit list: every dangling record is a fix ticket. Automate this exact analysis on a schedule.
- Monitor DNS changes: a new CNAME to an external service should trigger a review, and a deleted service should trigger DNS cleanup in the same change ticket.
- Log which of your names delegate to external nameservers; those delegations are trust decisions, review them like firewall rules.

## Key references

- BIND 9 dig documentation: https://www.isc.org/bind/
- dnsx documentation: https://github.com/projectdiscovery/dnsx
- Can I take over XYZ: https://github.com/EdOverflow/can-i-take-over-xyz
- MITRE ATT&CK T1590.002 DNS: https://attack.mitre.org/techniques/T1590/002/
- HackerOne takeover guidance: https://docs.hackerone.com
