---
name: bugbounty-scope-recon-asset-discovery
parent: bugbounty-scope-recon
description: Use when a program's scope statement is written and you need to turn it into a concrete asset inventory without crossing the lines. Covers expanding wildcard domains into verified subdomain lists, expanding CIDR ranges into live IPs, extracting API hosts and endpoints from web JavaScript and mobile apps, verifying each asset actually belongs to the scope, and building the final in-scope inventory file. Authorized targets only, only test assets the program explicitly lists in scope.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-scope-recon]
extends: []
relates: [recon-subdomain-enumeration, recon-asn-netblock, recon-cert-transparency, bugbounty-scope-recon-scope-boundary-mapping]
tools:
  - name: subfinder
    version: 2.6
  - name: amass
    version: 4.2
  - name: dnsx
    version: 1.2
  - name: httpx
    version: 1.6
  - name: nmap
    version: 7.98
---

Asset discovery converts scope lines like "*.example.com" and "203.0.113.0/24" into a concrete inventory of testable assets: verified subdomains, live IPs, API hosts, and mobile app endpoints. Every discovered asset gets checked against the scope before it enters the inventory. This sub-skill covers only the discovery step of bugbounty-scope-recon. Only discover and test assets the program lists in scope.

## Quick Workflow

1. Read SCOPE.txt and list each scope line as a discovery task (wildcard, CIDR, app, API).
2. For each wildcard domain: enumerate subdomains passively, then resolve and keep only names under the scoped domain.
3. For each CIDR range: expand to IPs, verify current ownership with whois, then check liveness politely.
4. For mobile apps: extract API hosts and endpoints from the app package and its traffic.
5. For APIs: collect base URLs from web JavaScript and documentation, and verify they are in scope.
6. Deduplicate everything into one inventory file with a source note per asset.
7. Hand the inventory to scope boundary mapping for the in, out, and gray verdicts.

## 1. Wildcard domains to verified subdomains

```bash
subfinder -d example.com -silent -o subfinder.txt
amass enum -passive -d example.com -o amass.txt
curl -s "https://crt.sh/?q=%25.example.com&output=json" \
  | jq -r '.[].name_value' | sed 's/^\*\.//' | sort -u > crtsh.txt
cat subfinder.txt amass.txt crtsh.txt | sort -u > candidates.txt
# Keep only names actually under the scoped domain, then resolve
grep -E '(^|\.)example\.com$' candidates.txt | sort -u > scoped-names.txt
dnsx -l scoped-names.txt -silent -resp -o resolved.txt
wc -l candidates.txt scoped-names.txt resolved.txt
```

Example output shape:

```
812 candidates.txt
764 scoped-names.txt
301 resolved.txt
```

The 48 names dropped between candidates and scoped-names were lookalikes or parent-domain artifacts; dropping them is the point. Record per-asset source notes: which tool found each name, so you can re-verify later.

## 2. CIDR ranges to live IPs

Expand the range, verify ownership has not changed, then check liveness gently:

```bash
python3 -c "import ipaddress; print('\n'.join(str(h) for h in ipaddress.ip_network('203.0.113.0/24').hosts()))" > range-ips.txt
# Spot-check ownership of the range before scanning it
whois 203.0.113.0 | grep -iE "orgname|netname|descr" | head -5
# Liveness check at a polite rate (ping sweep only where the program allows scanning)
nmap -sn -T3 --max-retries 1 -iL range-ips.txt -oG ping-sweep.gnmap
grep "Up" ping-sweep.gnmap | cut -d' ' -f2 > live-ips.txt
wc -l live-ips.txt
```

If whois shows the range now belongs to someone else, stop: the scope is stale and those IPs are not yours to test. Report the mismatch to the program as a scope question.

## 3. Mobile apps and API hosts

Mobile apps are in scope as applications, but the hosts they talk to need verification:

```bash
# Unpack the APK and extract candidate hosts (on your own machine, from the store copy)
apktool d app.apk -o app-unpacked
grep -rhoE 'https?://[a-zA-Z0-9.\-]+\.[a-z]+' app-unpacked/ | sort -u > app-hosts.txt
# Also capture the app's traffic through your proxy during normal use
# and merge the observed hosts into app-hosts.txt
cat app-hosts.txt
```

For web APIs, harvest base URLs from JavaScript and docs:

```bash
grep -rhoE 'https://[a-zA-Z0-9.\-]+\.example\.com(/[a-zA-Z0-9/_\-\.]*)?' js/ \
  | sort -u > api-hosts.txt
# Check for swagger/openapi specs that enumerate the whole API
httpx -l resolved.txt -silent -path /swagger.json -mc 200 -o swagger-found.txt
```

Every extracted host goes through the same scope check: is the name or IP inside the stated scope. App-discovered hosts outside the listed scope are gray until the program confirms.

## 4. Building the inventory

Merge all verified assets into one file with source notes:

```bash
{
  echo "# In-scope asset inventory for example.com, built 2026-10-23"
  echo "# Format: asset | type | source"
  awk '{print $1" | subdomain | subfinder/amass/crtsh"}' resolved.txt
  awk '{print $1" | ip | range-203.0.113.0/24"}' live-ips.txt
} | sort -u > inventory.txt
wc -l inventory.txt
head -10 inventory.txt
```

This inventory is the input to scope boundary mapping. Anything not in this file does not get tested.

## Edge cases

- A wildcard subdomain resolves to a third-party SaaS IP: the name is in scope, the provider's infrastructure is not. Test the app behavior, not the provider.
- crt.sh floods the list with CDN certificate names: filter to names that resolve and match the scoped domain.
- The CIDR range is huge (a /16): do not sweep it blindly. Ask the program which parts are actually theirs, and start with the hosts your other sources already named.
- The mobile app pins certificates: proxying its traffic needs a rooted test device or repackaging, and repackaging may violate the program's app testing rules. Read the mobile testing section of the policy first.
- An API host from the app is a generic cloud endpoint (e.g. a firebaseio or S3 URL): the program's data there may be in scope but the platform is not. Confirm with the program before touching shared infrastructure.

## Escalation

- Discovery inside the scope stalls: pivot on what you have (certificate hashes, ASN neighbors, web archives) but keep every pivot target inside the scope lines.
- The scope looks smaller than the company's real footprint: document the gap precisely (acquired domains, rebrands) and ask the program to expand scope. Precise asks get yeses.
- A discovered asset is clearly the program's but unlisted: gray list, ask in writing, do not test meanwhile.

## Detection and defender view

- Passive discovery (subfinder, crt.sh, amass passive) is invisible to the target; the defender sees nothing.
- Ping sweeps and liveness checks do touch the target: keep them inside the authorized range and at polite rates, exactly as the policy allows.
- Defenders should expect hunters to enumerate everything the scope implies; a scope that implies a /16 will get a /16's worth of attention. Scope narrowly if you want narrow testing.
- Keep the inventory file: it is your proof of what you considered in scope if anyone asks later.

## Key references

- subfinder documentation: https://github.com/projectdiscovery/subfinder
- OWASP Amass documentation: https://github.com/owasp-amass/amass
- dnsx documentation: https://github.com/projectdiscovery/dnsx
- httpx documentation: https://github.com/projectdiscovery/httpx
- apktool documentation: https://ibotpeaches.github.io/Apktool/
- HackerOne scope documentation: https://docs.hackerone.com
