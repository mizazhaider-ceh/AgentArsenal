---
name: recon-subdomain-enumeration-passive-sources
parent: recon-subdomain-enumeration
description: Use when you need subdomains without sending any packets to the target's infrastructure. Covers the full passive source stack, subfinder with API keys, amass in passive mode, crt.sh certificate transparency queries, DNS dataset services (VirusTotal, SecurityTrails, AlienVault OTX), search engine scraping, and merging everything into a deduplicated candidate list. Authorized targets only, only enumerate domains you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-subdomain-enumeration]
extends: []
relates: [recon-passive, recon-cert-transparency, recon-subdomain-enumeration-active-bruteforcing, domain-osint]
tools:
  - name: subfinder
    version: 2.6
  - name: amass
    version: 4.2
  - name: Python
    version: 3.12
---

Passive sources are databases other people built: certificate logs, DNS datasets, search indexes, and threat intel feeds. Querying them never touches the target, which makes this the safest and often the richest enumeration layer. This sub-skill covers the full passive source stack for recon-subdomain-enumeration: which sources, how to query them well, and how to merge the results. Only enumerate domains you are authorized to test.

## Quick Workflow

1. Confirm authorization and create the working directory with SCOPE.txt.
2. Configure API keys for subfinder and amass (VirusTotal, AlienVault OTX, Shodan, SecurityTrails, Censys).
3. Run subfinder for fast multi-source collection.
4. Run amass in passive mode for the deep source sweep; never omit `-passive` at this stage.
5. Query crt.sh directly for certificate transparency names.
6. Pull DNS datasets: VirusTotal, SecurityTrails, AlienVault OTX passive DNS.
7. Merge all outputs, strip wildcards, deduplicate into candidates.txt.
8. Hand the candidate list to resolution and validation.

## 1. subfinder with API keys

subfinder queries dozens of sources; keys unlock the best ones:

```bash
# Configure once: ~/.config/subfinder/provider-config.yaml
# virustotal, shodan, securitytrails, censys, alienvault keys go here
subfinder -d example.com -silent -all -o subfinder.txt
wc -l subfinder.txt && head -10 subfinder.txt
```

The `-all` flag uses every configured source. Without keys, subfinder still works but returns a fraction; with keys it is often the single highest-yield passive tool. Re-run when you add new keys; sources you could not query before may add hundreds of names.

## 2. amass in passive mode

Amass passive queries the widest source set but takes the longest:

```bash
amass enum -passive -d example.com -o amass-passive.txt
```

The default amass mode does active DNS resolution and brute forcing, which touches the target: at the passive stage, `-passive` is mandatory, not optional. Expect 10 to 30 minutes. Add keys for AlienVault OTX, VirusTotal, Shodan, and Twitter-adjacent sources in the amass config to widen coverage. When it finishes, compare counts against subfinder; the two tools' source sets overlap partially, so each finds names the other misses.

## 3. crt.sh direct queries

Certificate transparency is the richest single passive source. Query it directly for control over the output:

```bash
curl -s "https://crt.sh/?q=%25.example.com&output=json" \
  | jq -r '.[].name_value' \
  | sed 's/^\*\.//' \
  | sort -u > crtsh.txt
wc -l crtsh.txt
```

The `%25` is a URL-encoded `%` wildcard, catching `mail.example.com` and deeper names. Also query without the wildcard for the bare domain's own certificates, and check historical entries: crt.sh keeps every certificate ever issued, including for subdomains that no longer resolve. Dead names reveal naming patterns for the permutation stage. Also read issuer and validity dates: a certificate issued yesterday for a new subdomain can reveal infrastructure being staged right now.

## 4. DNS datasets and threat intel

Passive DNS databases record which names resolved to which IPs historically:

```bash
# AlienVault OTX passive DNS via API
curl -s "https://otx.alienvault.com/api/v1/indicators/domain/example.com/passive_dns" \
  -H "X-OTX-API-KEY: $OTX_KEY" | jq -r '.passive_dns[].hostname' | sort -u > otx.txt

# VirusTotal domain relations (needs API key)
curl -s "https://www.virustotal.com/api/v3/domains/example.com/subdomains?limit=40" \
  -H "x-apikey: $VT_KEY" | jq -r '.data[].id' | sort -u > vt.txt
```

SecurityTrails, RiskIQ (now Microsoft), and Censys offer similar data via web UI or API. These sources shine for older or renamed infrastructure that current tools miss: a subdomain that existed in 2022 and was deleted still sits in passive DNS, and its naming pattern feeds permutations.

## 5. Merging into candidates

```bash
cat subfinder.txt amass-passive.txt crtsh.txt otx.txt vt.txt \
  | sed 's/^\*\.//' \
  | tr '[:upper:]' '[:lower:]' \
  | sort -u > candidates.txt
wc -l candidates.txt
```

Lowercase everything (DNS is case-insensitive; mixed case creates false duplicates), strip wildcard prefixes, deduplicate. This file is the passive deliverable. Typical yield: hundreds to thousands of candidates for a mid-size organization, before any active work.

## Edge cases

- A source needs a paid key you do not have: note it and move on; the free tier plus the other sources usually suffice for the first pass.
- crt.sh returns names for a shared CDN certificate covering thousands of unrelated domains: filter strictly to names ending in the target domain.
- Amass passive finds nothing new over subfinder: normal for small domains; its value grows with target size and key coverage.
- Passive DNS shows IPs that no longer match: record the disagreement; it hints at infrastructure moves worth investigating in the active phase.
- Rate limits on free API tiers: stagger the runs (subfinder first, amass overnight) rather than hammering all sources at once.

## Escalation

- Passive yield is thin: check whether the domain is new (few certificates, little history). New domains need heavier active and permutation work; old domains usually reward more dataset digging (archives, historical certificates).
- One source dominates the yield: double-check its coverage for false negatives by spot-checking known names against it. A source that misses known names will miss unknown ones too.

## Detection and defender view

- Truly passive: the target sees nothing. Your queries hit crt.sh, OTX, VirusTotal, and search providers, not the target's servers.
- What the defender can see: certificate transparency is public, so defenders monitoring crt.sh see the same names you do. Good defenders alert on new certificates for lookalike domains too.
- API keys are the OPSEC surface: Shodan, Censys, and VirusTotal log your queries. Use an engagement-specific account, not a personal one.
- Defenders should assume every subdomain with a public certificate is already enumerated by someone; there is no obscurity in CT logs.

## Key references

- subfinder documentation: https://github.com/projectdiscovery/subfinder
- OWASP Amass documentation: https://github.com/owasp-amass/amass
- crt.sh: https://crt.sh
- AlienVault OTX API docs: https://otx.alienvault.com/api
- VirusTotal API v3 docs: https://developers.virustotal.com/reference/overview
- MITRE ATT&CK T1593.003 Digital Certificates: https://attack.mitre.org/techniques/T1593/003/
