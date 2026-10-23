---
name: recon-cert-transparency-subdomain-extraction
parent: recon-cert-transparency
description: Use when you have raw certificate data from CT logs and need clean subdomain lists out of it. Covers parsing subject alternative names from crt.sh JSON and raw certificates, stripping wildcards and normalizing case, filtering to the target domain, deduplicating across runs, extracting naming patterns from dead subdomains for permutation seeding, and merging CT names with other passive sources. Authorized targets only.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-cert-transparency]
extends: []
relates: [recon-cert-transparency-crtsh-workflows, recon-cert-transparency-certstream-monitoring, recon-subdomain-enumeration-permutation-techniques]
tools:
  - name: jq
    version: 1.7
  - name: Python
    version: 3.12
  - name: openssl
    version: 3.2
---

Raw certificate data is messy: multi-name SAN fields, wildcards, mixed case, duplicates across thousands of certificates, and names for domains you do not care about. Extraction turns that mess into a clean subdomain list plus naming-pattern intelligence. This sub-skill covers the extraction pipeline for recon-cert-transparency. Extract names only for domains you are authorized to test.

## Quick Workflow

1. Take the raw source: crt.sh JSON, certstream hits, or a certificate file.
2. Parse the subject alternative names (and the subject CN as a fallback).
3. Normalize: lowercase, strip wildcard prefixes, split multi-name entries.
4. Filter strictly to the target domain; drop CDN-shared and unrelated names.
5. Deduplicate within the run and against previous runs.
6. Separate live candidates from dead names; feed dead names to permutation seeding.
7. Merge the clean list with other passive sources into the master candidate file.

## 1. Parsing SANs from crt.sh JSON

```bash
# name_value holds the SAN list, sometimes newline-separated per entry
jq -r '.[].name_value' crtsh-raw.json > san-raw.txt
wc -l san-raw.txt
# Inspect the mess before cleaning: wildcards, mixed case, multi-name lines
head -20 san-raw.txt
```

Example raw shape:

```
*.example.com
Example.COM
mail.example.com
cdn.partner.net
*.example.com
```

Also parse the subject commonName as a fallback for old certificates that predate SAN ubiquity:

```bash
jq -r '.[] | "\(.common_name // empty)"' crtsh-raw.json | sort -u | head
```

## 2. Normalization pipeline

```bash
tr '[:upper:]' '[:lower:]' < san-raw.txt \
  | sed 's/^\*\.//' \
  | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
  | grep -v '^$' \
  | sort -u > san-normalized.txt
wc -l san-raw.txt san-normalized.txt
```

Each step: lowercase (DNS is case-insensitive), strip the `*.` wildcard prefix, trim whitespace, drop empties, deduplicate. A typical raw file shrinks 30 to 60 percent here, mostly wildcard and case duplicates.

## 3. Strict domain filtering

```bash
# Keep only names under the target domain
grep -E '(^|\.)example\.com$' san-normalized.txt | sort -u > san-target.txt
# Review what was dropped, in case the filter is too aggressive
grep -vE '(^|\.)example\.com$' san-normalized.txt | sort -u > san-dropped.txt
wc -l san-target.txt san-dropped.txt
head -10 san-dropped.txt
```

Review `san-dropped.txt` briefly: it contains CDN-shared names (expected drops) but also occasionally reveals the organization's other domains. Those are scope questions, not targets; note them, do not enumerate them.

## 4. Dead names as permutation seeds

Names that no longer resolve are not waste; they are the organization's retired vocabulary:

```bash
# Split into resolving and non-resolving
while read -r n; do
  if dig +short "$n" A @1.1.1.1 | grep -q .; then echo "$n" >> san-live.txt
  else echo "$n" >> san-dead.txt; fi
done < san-target.txt
wc -l san-live.txt san-dead.txt
# Mine dead names for patterns: prefixes, environments, project words
cut -d. -f1 san-dead.txt | grep -oE '^[a-z]+' | sort | uniq -c | sort -rn | head -20
```

Dead names like `old-crm`, `project-falcon-dev`, `vpn-legacy` reveal naming conventions and project codenames. Feed these words into the permutation stage: the organization names new things the way it named old things.

## 5. Parsing raw certificates directly

When you have the certificate file itself (from a TLS handshake during authorized testing):

```bash
# SANs from a live certificate
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName 2>/dev/null \
  | tr ',' '\n' | sed 's/.*DNS://' | tr -d ' ' | sort -u
```

Example output shape:

```
example.com
www.example.com
api.example.com
```

Certificates on odd ports often carry different SAN lists than port 443: check 8443, 9443, and any non-standard TLS ports your port scan found. Each unique SAN list is more candidate names.

## Edge cases

- Punycode names (`xn--...`): decode with `idn2` or Python's idna codec before comparing; otherwise they pollute the list as unreadable entries.
- Certificates with hundreds of SANs (shared hosting): the domain filter handles it, but verify the filter against a known name first.
- name_value containing literal `\n` escapes: jq `-r` handles most; if you see backslash-n in output, add a `sed 's/\\n/\n/g'` pass.
- Duplicate names across crt.sh runs months apart: dedupe against the archived list with `comm`, and treat re-appearing names as renewals, not discoveries.

## Escalation

- Extraction yields names in an unexpected script or encoding: normalize to ASCII via punycode explicitly and keep both forms; resolution needs the punycode form.
- The SAN list names infrastructure patterns (like `db-01.internal`): internal names on public certificates are a defensive finding about certificate hygiene. Note it; do not treat internal names as test targets unless scoped.

## Detection and defender view

- Every SAN on a public certificate is public forever. Audit your certificates for internal hostnames, project codenames, and staging names before issuance; you cannot un-publish them.
- Prefer wildcard certificates for internal or staging names where possible, so individual names never enter the logs.
- Monitor your own SAN lists over time: unexpected new names in issued certificates are the shadow-IT signal.

## Key references

- crt.sh: https://crt.sh
- RFC 6962 Certificate Transparency: https://www.rfc-editor.org/rfc/rfc6962.html
- OpenSSL x509 documentation: https://www.openssl.org/docs/man3.2/man1/openssl-x509.html
- jq manual: https://jqlang.github.io/jq/manual/
- MITRE ATT&CK T1593.003 Digital Certificates: https://attack.mitre.org/techniques/T1593/003/
