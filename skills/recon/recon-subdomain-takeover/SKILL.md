---
name: recon-subdomain-takeover
description: Use when authorized reconnaissance finds DNS records pointing at third-party services and you need to check for subdomain takeover. Covers how takeovers happen (dangling CNAMEs, expired cloud resources, unclaimed service endpoints), DNS record analysis to find candidates, fingerprinting cloud and SaaS services for claimable states, safe verification methods that prove the issue without harm, and documenting findings for in-scope bug bounty programs. Authorized targets only, only test domains you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [recon-subdomain-enumeration, recon-active, dns-enumeration, bugbounty-methodology, bug-bounty-workflow]
tools:
  - name: dig
    version: 9.18
  - name: subjack
    version: 0.0
  - name: Python
    version: 3.12
  - name: httpx
    version: 1.6
---

Subdomain takeover happens when a DNS record points at a third-party service that no longer serves the organization: a deleted cloud bucket, an expired app deployment, an unclaimed SaaS endpoint. Whoever claims the dangling endpoint controls content on the organization's subdomain. This skill covers finding and safely verifying takeovers during authorized recon: DNS analysis, service fingerprinting, and proof methods that stay inside the rules. Only test domains you are authorized to test, and never claim a resource outside a program that explicitly permits takeover verification.

## Quick Workflow

1. Confirm the authorization covers takeover verification; some programs restrict claiming even on in-scope names.
2. Enumerate DNS records for every in-scope subdomain: CNAME, A, NS, and their targets.
3. Flag dangling records: CNAMEs to unresolvable or unclaimed services, A records to expired cloud IPs, NS to dead nameservers.
4. Fingerprint each candidate: fetch it and match the response against known service fingerprints.
5. Verify safely: prove claimability with the least invasive method the program allows (often a benign proof file, never defacement).
6. Document: the DNS record, the fingerprint match, the verification evidence, timestamps.
7. Report per the program's process; do not hold a claimed resource longer than needed.

## 1. How takeovers happen

The pattern is always the same: the organization stops using a service but leaves the DNS pointing at it.

- Dangling CNAME: `blog.example.com` CNAMEs to `example-blog.herokuapp.com`, but the Heroku app was deleted. Anyone can create an app with that name and serve content on `blog.example.com`.
- Expired cloud resource: an A record points at an Elastic IP or cloud VM that was released; the IP is now assigned to someone else, or available to claim.
- Unclaimed SaaS: CNAMEs to services like Shopify, Tumblr, or status-page providers where the account was never created or was deleted.
- Dead nameservers: NS records pointing at nameservers that no longer exist or are claimable at a registrar.

The impact ranges from phishing on a trusted domain to cookie theft on sibling subdomains. Programs pay well for takeovers because the proof is unambiguous.

## 2. DNS record analysis for candidates

```bash
# CNAME targets for every confirmed subdomain
while read -r sub; do
  target=$(dig +short "$sub" CNAME @1.1.1.1 | head -1)
  [ -n "$target" ] && echo "$sub -> $target"
done < confirmed.txt > cnames.txt
wc -l cnames.txt
head -10 cnames.txt
```

Example output shape:

```
blog.example.com -> example-blog.herokuapp.com.
shop.example.com -> shops.myshopify.com.
docs.example.com -> example-docs.s3-website-us-east-1.amazonaws.com.
```

Flag candidates: CNAME targets containing known-takeoverable service domains (herokuapp, s3-website, azurewebsites, github.io, tumblr, shopify where unclaimed), targets that do not resolve at all (NXDOMAIN on the CNAME target means the service endpoint is gone), and A records pointing at cloud IP ranges worth checking for reassignment. Also check NS records for delegated subdomains whose nameservers are dead.

## 3. Fingerprinting the candidate

Fetch the candidate subdomain and match the response against known service fingerprints:

```bash
curl -sk -m 15 https://blog.example.com/ -o body.html -w "%{http_code}\n"
head -c 600 body.html
# Known fingerprints (examples):
# Heroku: "No such app" / "There's nothing here, yet."
# GitHub Pages: "There isn't a GitHub Pages site here."
# S3 website: "NoSuchBucket" with BucketName in XML
# Tumblr: "There's nothing here." with tumblr branding
grep -oiE "no such app|there isn't a github pages site|NoSuchBucket|there's nothing here" body.html
```

A fingerprint match means the service endpoint is unclaimed and almost certainly claimable. No match does not clear the candidate: services change their error pages, so also check for NXDOMAIN on the CNAME target and try the service's own lookup (e.g. the S3 bucket name in the CNAME either exists or it does not).

## 4. Safe verification

Verification proves you could claim it. Rules:

- Only verify when the program permits takeover proof. Some programs accept fingerprint plus NXDOMAIN evidence without claiming; prefer that when offered.
- If claiming is allowed: claim it, place one benign proof file (a text file with your handle and the date, or the program's requested canary), screenshot, then release or hand over per the program's instructions. Never deface, never serve phishing content, never keep it.
- Never claim a resource you cannot release, and never claim outside the exact in-scope name.
- For expired cloud IPs: do not spin up infrastructure on a stranger's former IP to "prove" anything beyond what the program asks. DNS plus fingerprint evidence usually suffices.

Document everything with timestamps: the dig output, the fingerprint match, the proof file, the release. Takeover reports live or die on this evidence chain.

## Edge cases

- The CNAME target resolves but serves a generic parking page: the service may be claimed by someone else already, or the organization may have repointed sloppily. Check the page carefully; a squatter's page is a different finding (report it as suspicious, do not fight them for it).
- Fingerprint matches but the service says the name is taken: someone claimed it first. Document the dangling record anyway; the organization still needs to fix the DNS.
- The program forbids claiming entirely: submit with DNS evidence plus fingerprint match. Many programs accept this as a complete report.
- Wildcard DNS plus a dangling CNAME: verify the specific name, not the wildcard; the wildcard may mask the record.

## Escalation

- Fingerprint is inconclusive: check the CNAME target's resolution (NXDOMAIN is strong evidence), query the service's API for the endpoint name where one exists, and look for historical screenshots in web archives showing the service previously served there.
- Multiple dangling records on one program: report each separately with its own evidence; takeovers are per-endpoint findings.

## Detection and defender view

- Audit your DNS regularly for dangling records: every CNAME to a service you no longer use is a takeover waiting to happen. Automate the check.
- Monitor certificate transparency for your subdomains: a new certificate issued for a dangling name by someone else means the takeover already happened.
- When decommissioning a service, remove the DNS record first, then delete the service. The order matters: DNS pointing at a live-then-deleted service is the vulnerability window.
- For cloud resources with DNS pointing at them, use elastic IPs or reserved addresses you control, or accept the risk explicitly with monitoring.

## Key references

- subjack: https://github.com/haccer/subjack
- HackerOne takeover guidance: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- MITRE ATT&CK T1590.002 DNS: https://attack.mitre.org/techniques/T1590/002/
- Can I take over XYZ (service fingerprint list): https://github.com/EdOverflow/can-i-take-over-xyz
