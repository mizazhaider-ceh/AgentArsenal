---
name: recon-cert-transparency
description: Use when you want to mine certificate transparency logs for authorized reconnaissance on a target domain. Covers how CT logs work and why they leak subdomains, crt.sh query workflows (web UI, JSON API, wildcard searches), real-time certstream monitoring for new certificates, extracting and cleaning subdomain lists from certificates (SAN parsing, wildcard stripping, dedup), and using issuance timing to spot staged infrastructure. Authorized targets only, only query logs for domains you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [recon-passive, recon-subdomain-enumeration, recon-subdomain-enumeration-passive-sources, domain-osint]
tools:
  - name: Python
    version: 3.12
  - name: jq
    version: 1.7
  - name: curl
    version: 8.5
---

Every public TLS certificate is logged to certificate transparency, and every log entry names the domains the certificate covers. That makes CT logs one of the richest passive subdomain sources: no packets to the target, just queries to public log search services. This skill covers the full CT workflow for authorized recon: how the logs work, crt.sh queries, real-time monitoring with certstream, and turning raw certificates into clean subdomain lists. Only query CT logs for domains you are authorized to test.

## Quick Workflow

1. Confirm authorization and record the target domains in SCOPE.txt.
2. Query crt.sh for the domain with a wildcard search; save the JSON.
3. Parse the subject alternative names, strip wildcards, lowercase, deduplicate.
4. Check historical entries: crt.sh keeps every certificate ever issued, including dead subdomains.
5. Read issuance dates: certificates issued in the last days can reveal infrastructure being staged.
6. Set up certstream monitoring for real-time alerts on new certificates for the target.
7. Merge the CT-derived names into your subdomain candidate list.
8. Re-run periodically: CT logs grow constantly and new certificates appear daily.

## 1. How certificate transparency leaks subdomains

Certificate authorities must log every publicly trusted certificate to CT logs before browsers accept it. Each log entry contains the certificate, and each certificate lists its domains in the Subject Alternative Name field. Anyone can search these logs. Consequences for recon:

- Any subdomain that ever had a public certificate is listed, forever, even after the DNS record is deleted.
- Wildcard certificates (`*.example.com`) appear, but the log also captures the many non-wildcard certificates that name subdomains explicitly.
- Pre-certificates (submitted before issuance) appear too, sometimes for infrastructure that never went live.

You query crt.sh or a CT API, never the target. This is fully passive.

## 2. crt.sh query workflows

The web UI works for spot checks; the JSON API works for pipelines:

```bash
# Wildcard search: %25 is URL-encoded %, catching all subdomains
curl -s "https://crt.sh/?q=%25.example.com&output=json" -o crtsh-raw.json
# Deduplicated name list
jq -r '.[].name_value' crtsh-raw.json \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/^\*\.//' \
  | sort -u > crtsh-names.txt
wc -l crtsh-names.txt
head -15 crtsh-names.txt
```

Example output shape:

```
admin.example.com
api.example.com
beta.example.com
dev-portal.example.com
legacy-app.example.com
```

Also query the bare domain (`?q=example.com`) to catch certificates issued for the root, and query with `match==` style exact searches when you need precision. For large result sets, crt.sh paginates; loop with the appropriate parameters or use the PostgreSQL-style query interface crt.sh documents.

## 3. Reading certificates for more than names

Each crt.sh JSON entry carries metadata worth mining:

```bash
# Issuer, validity dates, and serial per certificate
jq -r '.[] | "\(.issuer_name) | \(.not_before) | \(.name_value)"' crtsh-raw.json \
  | sort -u | head -20
# Newest certificates first: spot staged infrastructure
jq -r '.[] | "\(.not_before) \(.name_value)"' crtsh-raw.json \
  | sort -r | head -20
```

What to look for: certificates issued in the last few days for unfamiliar subdomains (staging infrastructure being prepared), issuer changes (a subdomain moving from one CA to another hints at infrastructure moves), and short-lived certificates (automation like ACME, which suggests modern, actively managed hosts versus legacy manual ones).

## 4. Real-time monitoring with certstream

certstream streams newly issued certificates as they are logged, letting you catch subdomains the moment they appear:

```bash
pip install certstream
certstream --json | python3 -c "
import sys, json
for line in sys.stdin:
    msg = json.loads(line)
    domains = msg['data']['leaf_cert']['all_domains']
    hits = [d for d in domains if d.endswith('example.com')]
    if hits:
        print('NEW CERT:', ', '.join(hits), flush=True)
"
```

Run this as a long-lived process during an engagement. New certificates for `staging-newapp.example.com` appearing mid-engagement tell you where the target's attention is, often before the DNS is even advertised. Log every hit with a timestamp; the issuance timeline becomes part of your recon notes.

## 5. Cleaning and merging

CT-derived names need cleaning before they join the candidate list:

```bash
# Strip wildcards, lowercase, drop punycode noise optionally, dedupe
jq -r '.[].name_value' crtsh-raw.json \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/^\*\.//' \
  | grep -E '\.example\.com$' \
  | sort -u > crtsh-clean.txt
# Merge with other passive sources
cat crtsh-clean.txt subfinder.txt amass-passive.txt | sort -u > passive-merged.txt
wc -l crtsh-clean.txt passive-merged.txt
```

Filter strictly to the target domain: shared CDN certificates list thousands of unrelated names. Keep the raw JSON; when a name looks odd later, the full certificate (issuer, dates, serial) explains it.

## Edge cases

- crt.sh is slow or rate limits: it does under load. Retry with backoff, query at off-peak times, or use a mirror / alternative CT search API.
- Massive result sets for domains behind shared certificates: the domain filter in section 5 is mandatory, not optional.
- Certificates for lookalike domains (examp1e.com): out of scope unless your authorization covers them. Note them for the phishing or brand-protection angle, do not enumerate them as targets.
- Pre-certificates for names that never resolve: still valuable. They reveal naming patterns and planned infrastructure for the permutation stage.
- crt.sh shows no results for a domain you know uses TLS: check the exact query encoding and try the UI once to validate; API quirks (not missing data) are the usual cause.

## Escalation

- CT yield plateaus: pivot to certstream for new issuances, historical dataset digs (full CT log mirrors), and searching for the organization's name in certificate subject fields (O=Example Ltd) which catches certificates on unrelated domains.
- The target uses a private CA internally: public CT logs will not have those names. That is a finding about their PKI hygiene only if in scope to assess; do not go hunting their internal CA.

## Detection and defender view

- CT logs are public by design: assume every subdomain with a public certificate is already known to attackers. There is no obscurity here.
- Defenders must monitor CT for their own domains: alert on any new certificate you did not issue. Unexpected certificates mean misissuance, a compromised CA account, or shadow IT.
- Also monitor lookalike domains: attackers register them and get certificates too. CT monitoring is the cheapest phishing early-warning there is.
- Consider whether every subdomain needs a public certificate: internal names on public certs leak internal naming conventions to the world.

## Key references

- crt.sh: https://crt.sh
- Certificate Transparency (RFC 6962): https://www.rfc-editor.org/rfc/rfc6962.html
- certstream: https://github.com/CaliDog/certstream-python
- crt.sh usage documentation: https://crt.sh/?q=example.com (query interface)
- Google CT log list: https://www.gstatic.com/ct/log_list/v3/log_list.json
- MITRE ATT&CK T1593.003 Digital Certificates: https://attack.mitre.org/techniques/T1593/003/
