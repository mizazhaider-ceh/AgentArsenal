---
name: recon-subdomain-enumeration-active-bruteforcing
parent: recon-subdomain-enumeration
description: Use when passive sources are exhausted and you are authorized for active DNS enumeration on the target domain. Covers wildcard detection before trusting results, brute forcing with dnsx and shuffledns, wordlist selection and custom wordlist building from discovered names, resolver choice and polite rate limiting, filtering wildcard noise, and validating hits. Authorized targets only, only brute force domains you are permitted to test actively.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-subdomain-enumeration]
extends: []
relates: [recon-active, recon-subdomain-enumeration-passive-sources, recon-subdomain-enumeration-permutation-techniques, dns-enumeration]
tools:
  - name: dnsx
    version: 1.2
  - name: shuffledns
    version: 1.1
  - name: massdns
    version: 1.0
  - name: dig
    version: 9.18
---

Active brute forcing resolves dictionary guesses against the target domain to find names no database lists. It generates DNS query volume, so it requires authorization for active testing and polite rates. This sub-skill covers the active brute forcing layer of recon-subdomain-enumeration: wildcard handling, tooling, wordlists, resolvers, and validation. Only brute force domains your authorization covers.

## Quick Workflow

1. Confirm the authorization covers active DNS enumeration, and record it in SCOPE.txt.
2. Probe for wildcard DNS with a random name; record the wildcard IP if present.
3. Pick the wordlist: start with subdomains-top1million, then build a custom list from discovered naming patterns.
4. Choose resolvers: a trusted public resolver list, never the target's authoritative servers at volume.
5. Run dnsx (moderate) or shuffledns with massdns (large), with rate limits set.
6. Filter results against the wildcard IP and response fingerprints.
7. Merge validated hits into the consolidated list and probe with httpx.

## 1. Wildcard detection

Run this before every brute force campaign; a missed wildcard poisons the whole result set:

```bash
dig +short qwer-no-such-name-98765.example.com A @1.1.1.1
dig +short another-random-zz112233.example.com A @1.1.1.1
```

If both return the same IP, the domain has wildcard DNS: every guess will resolve. Record the IP. dnsx and shuffledns filter wildcard responses automatically, but the manual probe tells you the ground truth first. Also check per-label wildcards (`*.dev.example.com`) when brute forcing specific sub-labels; wildcards can exist at any level.

## 2. dnsx for moderate runs

dnsx is the workhorse for wordlists up to a few hundred thousand names:

```bash
dnsx -d example.com \
  -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt \
  -silent -resp -o dnsx-hits.txt -t 100 -rl 200 -retry 2
wc -l dnsx-hits.txt
head -5 dnsx-hits.txt
```

Example output shape:

```
vpn.example.com ["203.0.113.20"]
jenkins.example.com ["203.0.113.21"]
grafana.example.com ["203.0.113.21"]
```

Flags that matter: `-t` threads, `-rl` rate limit per second, `-retry` for flaky networks. `-resp` records the resolving IP, which you need for wildcard filtering and for spotting interesting infrastructure (multiple names on one IP, names on unexpected ASNs).

## 3. shuffledns and massdns for large runs

For million-plus wordlists, shuffledns driving massdns is far faster:

```bash
# resolvers.txt: trusted public resolvers, one per line
shuffledns -d example.com -list /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-2000000.txt \
  -r resolvers.txt -o shuffled-hits.txt -t 5000
```

Validate `resolvers.txt` first: dead resolvers silently shrink results. Keep a known-good list (e.g. from the trickest public resolver lists) and re-validate periodically. shuffledns handles wildcard filtering natively; still do the manual probe from section 1 so you can sanity-check its filtering.

## 4. Wordlist strategy

Wordlist choice decides the yield more than tooling:

- Start broad: `subdomains-top1million-110000.txt` from SecLists catches the common names fast.
- Go deep on promising targets: the 2-million variant, then combined lists.
- Build custom from discoveries: extract the naming patterns from confirmed names and generate variants. If the target uses `svc-<name>-prod`, your wordlist should contain their service names with that pattern, not generic words.

```bash
# Extract second labels from confirmed names to learn the vocabulary
cut -d. -f1 confirmed.txt | sort | uniq -c | sort -rn | head -30
# Build targeted guesses: append discovered prefixes to service words
for prefix in dev staging prod test qa uat; do
  while read -r svc; do echo "$prefix-$svc"; echo "$svc-$prefix"; done < services.txt
done > custom-wordlist.txt
wc -l custom-wordlist.txt
```

Also mine job postings, tech blogs, and the target's own documentation for service names (jenkins, gitlab, vault, consul, kibana): internal tooling subdomains follow the stack the company advertises.

## 5. Validation and merging

Filter, deduplicate, and confirm each hit is real:

```bash
# Drop wildcard-IP hits and dedupe
grep -v "WILDCARD_IP" dnsx-hits.txt shuffled-hits.txt | sort -u > brute-validated.txt
# Re-resolve once through a public resolver to confirm
cut -d' ' -f1 brute-validated.txt | sed 's/ \[.*//' | sort -u > brute-names.txt
dnsx -l brute-names.txt -silent -resp -o brute-confirmed.txt
wc -l brute-confirmed.txt
```

Names that resolve consistently across two runs and two resolver sets are confirmed. Merge into the master candidate list for httpx probing.

## Edge cases

- Wildcard at a sub-label (`*.dev.example.com`): brute forcing `dev.example.com` names needs per-label wildcard detection; filter against the sub-label wildcard IP.
- Resolver rate limiting: symptoms are shrinking hit counts on re-runs. Lower `-rl`, rotate resolvers, or split the wordlist across runs.
- The target's DNS drops high-volume queries: that is the authorization boundary talking. Slow down rather than pushing through; dropped queries mean missed names, not just slow runs.
- Empty results on a domain you know has subdomains: check the wordlist encoding, the resolver health, and whether you are appending the domain correctly (a `-d` flag mistake resolves garbage).
- DNS over HTTPS resolvers in dnsx: supported via `-r` with https:// URLs; useful when port 53 is filtered on your network.

## Escalation

- Brute forcing plateaus: switch to permutations of confirmed names (see the permutation sub-skill), which exploit the target's naming convention instead of generic dictionaries.
- Still plateaued: enumerate the ASN's netblocks and reverse-DNS sweep the ranges; PTR records often name hosts that forward DNS never lists.
- Yield is zero on a large org: verify the domain spelling and authorization first; then consider that the org may live mostly on a different root domain (acquisitions, rebrands) and re-scope.

## Detection and defender view

- Active brute forcing is visible: high-volume, dictionary-ordered DNS queries at the resolver, and at the target's authoritative servers if you query them directly. This is why authorization and pacing matter.
- Defenders can detect enumeration patterns: query entropy analysis, NXDOMAIN rate spikes, and known wordlist ordering. Alert on these, but expect authorized hunters too.
- Wildcard DNS pollutes attacker results but does not hide names from certificate transparency; it is not a substitute for CT monitoring.
- Rate limiting DNS at the authoritative server slows enumeration but also degrades legitimate use; prefer monitoring and alerting over aggressive blocking.

## Key references

- dnsx documentation: https://github.com/projectdiscovery/dnsx
- shuffledns documentation: https://github.com/projectdiscovery/shuffledns
- massdns documentation: https://github.com/blechschmidt/massdns
- SecLists DNS wordlists: https://github.com/danielmiessler/SecLists
- MITRE ATT&CK T1590.002 DNS: https://attack.mitre.org/techniques/T1590/002/
- BIND 9 dig documentation: https://www.isc.org/bind/
