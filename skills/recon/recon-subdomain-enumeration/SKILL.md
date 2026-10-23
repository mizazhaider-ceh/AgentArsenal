---
name: recon-subdomain-enumeration
description: Use when starting authorized reconnaissance on a target domain and you need the complete subdomain enumeration playbook. Covers passive collection (subfinder, amass passive, certificate transparency, DNS datasets), active brute forcing (dnsx, shuffledns, wordlists), permutation and alteration techniques, resolving and validating results, wildcard detection, and consolidating everything into one clean target list. Authorized targets only, only enumerate domains you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [recon-passive, recon-active, recon-cert-transparency, dns-enumeration, bugbounty-methodology]
tools:
  - name: subfinder
    version: 2.6
  - name: amass
    version: 4.2
  - name: dnsx
    version: 1.2
  - name: httpx
    version: 1.6
  - name: shuffledns
    version: 1.1
---

Subdomain enumeration turns one domain into the full list of names worth testing. It runs in three layers: passive sources that never touch the target, active brute forcing that resolves guesses, and permutations that mutate known names into undiscovered ones. This skill covers the complete playbook plus validation: wildcard detection, resolution, and consolidation into one clean list. Only enumerate domains you are authorized to test.

## Quick Workflow

1. Confirm authorization and write the scope (domains, rules) into SCOPE.txt before collecting anything.
2. Collect passively: subfinder, amass in passive mode, crt.sh, and DNS datasets.
3. Check for wildcard DNS with a random-name probe before trusting any resolution results.
4. Brute force actively with dnsx or shuffledns and a good wordlist, through a public resolver.
5. Generate permutations from the names you found (alterations, additions, common patterns).
6. Resolve every candidate, filter against the wildcard IP, and deduplicate.
7. Probe the resolved names with httpx for live web services.
8. Write the consolidated list: subdomain, IP, status, title, technology. This feeds all later phases.

## 1. Passive collection

Passive sources query third-party databases, not the target:

```bash
mkdir -p recon/example.com && cd recon/example.com
subfinder -d example.com -silent -o subfinder.txt
amass enum -passive -d example.com -o amass-passive.txt
curl -s "https://crt.sh/?q=%25.example.com&output=json" \
  | jq -r '.[].name_value' | sed 's/^\*\.//' | sort -u > crtsh.txt
```

Add API keys to subfinder and amass configs (VirusTotal, AlienVault OTX, Shodan, SecurityTrails) to widen coverage; without keys you get a fraction of the sources. Let amass passive finish; it takes 10 to 30 minutes across dozens of sources.

## 2. Wildcard detection first

Before trusting any active result, probe for wildcard DNS:

```bash
dig +short this-name-definitely-not-real-xyz123.example.com A @1.1.1.1
```

If it returns an IP, the domain uses a wildcard: every guessed name will appear to resolve. Record the wildcard IP and filter all later results against it. Tools like dnsx and shuffledns can filter wildcard responses automatically, but verify with the manual probe first so you know what you are filtering.

## 3. Active brute forcing

Resolve wordlist guesses through a public resolver, never the target's authoritative server at high volume:

```bash
dnsx -d example.com -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt \
  -silent -resp -o bruteforce.txt -t 100 -rl 200
```

Example output shape:

```
api.example.com ["203.0.113.10"]
dev-api.example.com ["203.0.113.11"]
staging.example.com ["203.0.113.12"]
```

For larger runs, shuffledns with massdns is faster:

```bash
shuffledns -d example.com -list subdomains-top1million.txt -r resolvers.txt -o shuffled.txt
```

Use a trusted public resolver list for `-r` (not the target's). Keep the rate sane: `-rl 200` is polite; thousands of queries per second against a small target's infrastructure is not passive-adjacent, it is a scan, and belongs under the authorization for active testing.

## 4. Permutation techniques

Permutations mutate known names into names nobody listed:

```bash
# dnsgen-style alterations from your confirmed list
dnsgen -l confirmed.txt -w /dev/null > permutations.txt
# Common manual patterns worth adding:
# dev-api, api-dev, api2, api-v2, old-api, api-old, api-staging,
# internal-api, api-internal, corp-api, api-test, test-api
dnsx -l permutations.txt -silent -resp -o permuted-resolved.txt -t 100
```

Also try: environment prefixes (dev, staging, qa, prod, test, uat), numbered variants (api1, api2, v1, v2), hyphen versus no-hyphen forms, and service names from job postings or the target's tech stack (jenkins, grafana, kibana, gitlab as subdomains). Naming conventions repeat; once you learn a target's pattern, permutations write themselves.

## 5. Consolidation

Merge all layers, resolve once, probe for live web:

```bash
cat subfinder.txt amass-passive.txt crtsh.txt bruteforce.txt permuted-resolved.txt \
  | sed 's/ \[.*//' | sort -u > all-candidates.txt
dnsx -l all-candidates.txt -silent -resp -o resolved-final.txt
cut -d' ' -f1 resolved-final.txt | httpx -silent -o live.txt \
  -title -tech-detect -status-code -follow-redirects
wc -l all-candidates.txt resolved-final.txt live.txt
```

`live.txt` is the deliverable: every live web host with title and technology. Save the intermediate files; when a new technique appears next month, you re-run from candidates, not from zero.

## Edge cases

- Wildcard DNS everywhere: filter resolved results against the wildcard IP, and treat names that only exist because of the wildcard as unconfirmed until httpx shows distinct content.
- crt.sh floods with CDN certificate names: keep only names matching the target domain that actually resolve.
- Brute forcing returns nothing new: your wordlist does not match the target's naming convention. Mine the confirmed names for patterns and build a custom wordlist from them.
- Rate limiting from the resolver: drop `-t` and `-rl`, or rotate resolvers. Getting blocked by 1.1.1.1 mid-run corrupts results silently.
- Internationalized or odd names: punycode shows up in CT logs; decode before resolving.

## Escalation

- All three layers stall: pivot to certificate hash searches in Shodan, ASN neighbor enumeration, web archives for dead names that reveal patterns, and code search for the domain in public repos.
- The target has thousands of subdomains: prioritize by technology and title from httpx (login pages, admin panels, old software versions) instead of treating the list as flat.
- Enumeration is done when new runs add nothing: freeze the list, timestamp it, and move to service and content enumeration.

## Detection and defender view

- Passive collection is invisible to the target; active brute forcing is visible as DNS query volume at the resolver and, if you query authoritatively, at the target's nameservers.
- Wildcard DNS is a defender choice with a cost: it hides nothing (CT logs still list names) and it pollutes attacker results, but it also breaks naive monitoring of "new subdomain" alerts. Prefer explicit records plus CT monitoring.
- Monitor certificate transparency for your own domains: every new cert is a new subdomain the world knows about. Alert on names you did not issue.
- DNS query logging at the resolver or authoritative server shows enumeration patterns: high-entropy, high-volume, dictionary-ordered queries. That is what your brute forcing looks like; keep it authorized and paced.

## Key references

- subfinder documentation: https://github.com/projectdiscovery/subfinder
- OWASP Amass documentation: https://github.com/owasp-amass/amass
- dnsx documentation: https://github.com/projectdiscovery/dnsx
- httpx documentation: https://github.com/projectdiscovery/httpx
- shuffledns documentation: https://github.com/projectdiscovery/shuffledns
- crt.sh: https://crt.sh
- SecLists DNS wordlists: https://github.com/danielmiessler/SecLists
- MITRE ATT&CK T1590.002 DNS: https://attack.mitre.org/techniques/T1590/002/
