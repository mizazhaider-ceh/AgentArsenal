---
name: bugbounty-methodology-recon-phase
parent: bugbounty-methodology
description: Use when you are in the reconnaissance phase of an in-scope bug bounty hunt and need the exact ordered pipeline. Covers passive subdomain collection (subfinder, amass passive, certificate transparency), DNS resolution and live-host probing (dnsx, httpx), paced port scanning, content discovery (ffuf), JavaScript endpoint harvesting, and building the consolidated target list that feeds application mapping. Authorized targets only, only test assets the program lists in scope.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-methodology]
extends: []
relates: [recon-subdomain-enumeration, recon-cert-transparency, recon-active, recon-passive, nmap-methodology]
tools:
  - name: subfinder
    version: 2.6
  - name: amass
    version: 4.2
  - name: dnsx
    version: 1.2
  - name: httpx
    version: 1.6
  - name: ffuf
    version: 2.1
---

The recon phase turns a program's scope statement into a concrete target list: every subdomain, every live host, every open port, every hidden path, every JavaScript endpoint. Do it in order of increasing intensity, passive first, and record everything; recon output becomes the appendix of your reports and the map for the exploitation phase. This sub-skill covers only the recon phase of bugbounty-methodology. Only enumerate assets the program lists in scope.

## Quick Workflow

1. Create the program workspace and write SCOPE.txt with the exact authorized assets.
2. Collect subdomains passively: subfinder, amass in passive mode, crt.sh.
3. Merge, deduplicate, and resolve every name with dnsx through a public resolver.
4. Probe resolved hosts with httpx for live web services, titles, technologies, and status codes.
5. Run paced port scanning on the most interesting hosts with nmap.
6. Run content discovery with ffuf on live web hosts, one host at a time, polite rate.
7. Harvest JavaScript files and extract API endpoints, keys, and hidden parameters.
8. Consolidate everything into one target list (hosts, ports, paths, endpoints) and hand it to the mapping phase.

## 1. Passive subdomain collection

Start with sources that never touch the target's infrastructure:

```bash
mkdir -p ~/bb/target.com && cd ~/bb/target.com
subfinder -d target.com -silent -o subfinder.txt
amass enum -passive -d target.com -o amass-passive.txt
curl -s "https://crt.sh/?q=%25.target.com&output=json" \
  | jq -r '.[].name_value' | sed 's/^\*\.//' | sort -u > crtsh.txt
wc -l subfinder.txt amass-passive.txt crtsh.txt
```

Example output shape:

```
245 subfinder.txt
389 amass-passive.txt
512 crtsh.txt
```

Amass passive can take 10 to 30 minutes as it queries dozens of sources; let it finish. Add API keys (AlienVault OTX, VirusTotal, Shodan) to the Amass config to widen coverage.

## 2. Resolution and live-host probing

Merge, deduplicate, then resolve once through a public resolver:

```bash
cat subfinder.txt amass-passive.txt crtsh.txt | sort -u > all-subs.txt
dnsx -l all-subs.txt -silent -resp -o resolved.txt
wc -l all-subs.txt resolved.txt
```

Then probe for live web services and fingerprint them:

```bash
cut -d' ' -f1 resolved.txt | httpx -silent -o live.txt \
  -title -tech-detect -status-code -follow-redirects
cat live.txt
```

Example output shape:

```
https://portal.target.com [200] [Customer Portal] [nginx,Vue.js]
https://api.target.com [401] [Unauthorized] [cloudflare,Node.js]
https://legacy.target.com [200] [Welcome to Legacy] [Apache/2.4.41,PHP/7.4.3]
```

The legacy host on old PHP is already a lead. Old software versions in banners are recon gold; record every version string.

## 3. Paced port scanning

Only scan hosts you confirmed in scope, at a polite rate, and never with aggressive timing against a bounty target:

```bash
nmap -sV --top-ports 1000 -T3 --max-retries 2 \
  -iL <(cut -d' ' -f1 resolved.txt) -oA nmap-top1000
grep -E "open| Discovered" nmap-top1000.gnmap | head -40
```

For web-heavy programs, a focused service scan on the live web hosts is usually more valuable than a full port sweep of everything. Respect any program rule about scanning intensity; when the policy says "no automated scanners," port scanning is what they mean.

## 4. Content discovery

One host at a time, medium wordlist, polite rate, and match on the interesting status codes:

```bash
ffuf -u https://portal.target.com/FUZZ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -mc 200,201,204,301,302,307,401,403 -t 20 -p 0.2 \
  -o ffuf-portal.json
```

A 403 on `/admin` is more interesting than a 200 on `/about`. Record every non-404 path; 401 and 403 responses confirm the path exists and may be reachable with different auth or headers. Also fuzz for virtual hosts when the server hosts many sites:

```bash
ffuf -u https://portal.target.com -H "Host: FUZZ.target.com" \
  -w subdomains-top1million.txt -mc 200,301,302 -fs 1234 -o ffuf-vhost.json
```

## 5. JavaScript endpoint harvesting

Collect every JS file the application loads, then mine it:

```bash
# Gather JS URLs from live hosts (example with one host)
httpx -l live.txt -silent -json | jq -r '.url' > urls.txt
# fetch each page, extract script src values, download them, then:
grep -rhoE '"(/[a-zA-Z0-9/_\-\.?=&%]+)"' js/ | sort -u > js-endpoints.txt
grep -rhoE '(api[_-]?key|secret|token)["'\'']?\s*[:=]\s*["'\''][^"'\'']+' js/ | sort -u > js-secrets.txt
head -30 js-endpoints.txt
```

Endpoints found in JavaScript are authorized testing surface when the host is in scope. Look for `/api/v1/internal`, `/debug`, versioned endpoints, and GraphQL paths. Keys found here are leads for broken authentication testing, not findings by themselves.

## Edge cases

- Wildcard DNS makes every guessed name resolve: test with a random string like `no-such-xyz123.target.com` first, and filter resolved lists against the wildcard IP.
- crt.sh returns thousands of junk entries for CDN-shared certificates: keep only names that resolve and belong to the target, drop CDN provider names.
- httpx shows hundreds of hosts with identical titles (parking pages, default configs): fingerprint the default page size and filter it out.
- ffuf drowns you in false positives on wildcard-responding apps: calibrate with `-fs` on the response size of a random path first.
- Amass passive stalls: run it with fewer sources or rely on subfinder plus crt.sh; a smaller clean list beats a huge dirty one.
- The program forbids active scanning entirely: stay passive (this section's steps 1 to 2 plus JS analysis of publicly loaded files) and say so in your methodology notes.

## Escalation

- Passive lists stop growing: pivot on certificate hashes in Shodan, the org's ASN netblocks, web archives for dead subdomains that reveal naming patterns, and code search for the domain string in public repos.
- Live hosts are all behind a WAF with identical fingerprints: hunt the origin via historical DNS, certificate SANs on odd ports, and favicon hashes in Shodan.
- Content discovery plateaus: switch to parameter discovery on known endpoints and API schema files (swagger.json, openapi.yaml, .graphql) instead of more path fuzzing.
- Recon is done when new runs add nothing: freeze the target list, timestamp it, and move to application mapping. Recon that never ends is procrastination.

## Detection and defender view

- Passive collection (subfinder, crt.sh, amass passive) is invisible to the target; queries hit third-party databases.
- dnsx resolution through public resolvers and httpx probing do touch the target: they look like normal browsing at low rates, but aggressive concurrency looks like a scan. Keep rates polite.
- Port scanning is the noisiest step: the target's IDS will log it. Stay within program rules on scan intensity; that is what the rules are for.
- Defenders monitor certificate transparency too: assume they see the same subdomain data you do, and expect newly issued certs on odd subdomains to be watched.

## Key references

- subfinder documentation: https://github.com/projectdiscovery/subfinder
- OWASP Amass documentation: https://github.com/owasp-amass/amass
- httpx documentation: https://github.com/projectdiscovery/httpx
- dnsx documentation: https://github.com/projectdiscovery/dnsx
- ffuf documentation: https://github.com/ffuf/ffuf
- crt.sh: https://crt.sh
- HackerOne documentation on recon: https://docs.hackerone.com
