---
name: recon-subdomain-takeover-cloud-service-fingerprints
parent: recon-subdomain-takeover
description: Use when DNS analysis has produced takeover candidates and you need to fingerprint the cloud or SaaS service behind each one. Covers fetching candidate responses safely, matching against known service fingerprints (Heroku, GitHub Pages, S3, Azure, Shopify, Tumblr, and more), handling services that changed their error pages, checking bucket and app name availability via service APIs, and recording fingerprint evidence for the report. Authorized targets only.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-subdomain-takeover]
extends: []
relates: [recon-subdomain-takeover-dns-record-analysis, recon-subdomain-takeover-claiming-and-verification, bug-bounty-workflow]
tools:
  - name: curl
    version: 8.5
  - name: httpx
    version: 1.6
  - name: Python
    version: 3.12
---

Fingerprinting decides whether a dangling DNS record is actually claimable: the service's own error page tells you the endpoint is unclaimed. This sub-skill covers matching candidate subdomains against known cloud and SaaS fingerprints for recon-subdomain-takeover, safely and with evidence. Only fingerprint candidates on domains you are authorized to test.

## Quick Workflow

1. Take the candidate list from DNS record analysis.
2. Fetch each candidate over HTTPS (and HTTP as a fallback) with timeouts, saving status code and body.
3. Match bodies and status codes against the known fingerprint table.
4. For ambiguous responses, check the CNAME target's resolution and the service's own availability signals.
5. Record match or no-match with the exact evidence (status, body snippet, timestamp).
6. Sort candidates into claimable, uncertain, and cleared.
7. Hand claimable candidates to the claiming and verification step.

## 1. Fetching candidates safely

```bash
while read -r line; do
  sub=$(echo "$line" | cut -d'|' -f1 | tr -d ' ')
  code=$(curl -sk -m 15 -o "fp-$sub.html" -w "%{http_code}" "https://$sub/")
  echo "$sub $code $(wc -c < fp-$sub.html) bytes"
done < candidates-takeover.txt > fp-status.txt
cat fp-status.txt
```

One request per candidate, short timeout, no aggressive retries. You are reading an error page, not load testing. Save every body; the report needs the exact snippet, and fingerprints change over time so today's body is tomorrow's evidence.

## 2. The fingerprint table

Match response bodies against these known signatures (verify against the current can-i-take-over-xyz list, since providers change pages):

| Service | CNAME pattern | Unclaimed fingerprint |
|---|---|---|
| Heroku | *.herokussl.com, *.herokuapp.com | "No such app", "There's nothing here, yet." |
| GitHub Pages | *.github.io | "There isn't a GitHub Pages site here." |
| AWS S3 website | *.s3-website-*.amazonaws.com | "NoSuchBucket" XML with BucketName |
| Azure | *.azurewebsites.net, *.cloudapp.net | NXDOMAIN on target or Azure 404 page |
| Shopify | *.myshopify.com | "Sorry, this shop is currently unavailable" (only when never claimed) |
| Tumblr | *.tumblr.com | "There's nothing here." / "Not found" |
| Pantheon | *.pantheonsite.io | "404 error unknown site" |
| Fastly | various | "Fastly error: unknown domain" |
| Surge.sh | *.surge.sh | "project not found" |

```bash
# Batch match against the common fingerprints
grep -liE "no such app|there's nothing here|there isn't a github pages site|NoSuchBucket|unknown domain|project not found" fp-*.html
```

A match is strong evidence of claimability. Record which pattern matched and the exact body snippet.

## 3. Service-side availability checks

For some services, the service itself tells you whether the endpoint name is free:

- S3: request the bucket URL directly. `NoSuchBucket` means the bucket name is unclaimed; `AccessDenied` means it exists but is private (not takeoverable, move on).
- Heroku: the "No such app" page is the signal; no API check needed.
- GitHub Pages: the fingerprint page is definitive for unclaimed.
- Azure: NXDOMAIN on the `*.azurewebsites.net` target is the strongest signal, since Azure holds names briefly after deletion.

```bash
# S3 bucket check example: bucket name from the CNAME target
curl -s "https://old-docs.s3-website-us-east-1.amazonaws.com/" | head -c 300
# NoSuchBucket with <BucketName>old-docs</BucketName> => unclaimed
```

Never attempt to create the resource as a "check." Availability probing via normal reads is fine; claiming belongs to the verification step and only with program permission.

## 4. Sorting the candidates

```bash
# claimable.txt: fingerprint matched, ready for verification
# uncertain.txt: ambiguous response, needs deeper checks
# cleared.txt: clearly claimed or alive, with reason
```

Uncertain cases get: a second fetch with HTTP/1.1 versus HTTP/2 (some fingerprints differ), a check of the CNAME target's own resolution, and a look at web archives for what the name served historically. If it served the organization's content last year and now serves a generic page, the service was deleted and the fingerprint may just be a new error page variant; treat as likely claimable and verify carefully.

## Edge cases

- The provider changed its error page since the fingerprint list was written: fall back to first principles. NXDOMAIN on the CNAME target plus no content served is claimable regardless of page text.
- The response is a WAF or CDN generic error: the fingerprint is masked. Check the CNAME target resolution directly and the service-side signals from section 3.
- Multiple services could match (CNAME chain through two providers): fingerprint each hop; the claimable one is the terminal unclaimed endpoint.
- The candidate serves the organization's real content: cleared, not a finding. Note it as verified-alive so nobody re-checks it next quarter.

## Escalation

- Fingerprints are inconclusive across the board: escalate to the claiming step only for the strongest candidates (NXDOMAIN targets), and report the rest as informational dangling records with the evidence you have.
- A new service not in any fingerprint list: research its claiming model from its docs before concluding anything. Unknown services get reported as suspicious DNS, not as confirmed takeovers.

## Detection and defender view

- This fingerprint table is also a defensive checklist: if your DNS points at any listed service you no longer use, you are vulnerable right now.
- Monitor your subdomains' HTTP responses for fingerprint strings: an automated check that alerts when `blog.example.com` starts serving "No such app" catches takeovers within minutes.
- When decommissioning a service on any listed platform, delete the DNS record in the same change as the service deletion. The gap between the two is the vulnerability window.

## Key references

- Can I take over XYZ: https://github.com/EdOverflow/can-i-take-over-xyz
- subjack: https://github.com/haccer/subjack
- httpx documentation: https://github.com/projectdiscovery/httpx
- HackerOne takeover guidance: https://docs.hackerone.com
- MITRE ATT&CK T1590.002 DNS: https://attack.mitre.org/techniques/T1590/002/
