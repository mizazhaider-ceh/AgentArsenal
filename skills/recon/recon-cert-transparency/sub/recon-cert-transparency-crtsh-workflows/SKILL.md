---
name: recon-cert-transparency-crtsh-workflows
parent: recon-cert-transparency
description: Use when crt.sh is your main certificate transparency interface for authorized recon on a target domain. Covers the web UI for spot checks, the JSON API for pipelines (wildcard, exact, and identity searches), handling pagination on large result sets, extracting issuer and validity metadata, and troubleshooting the slow or rate-limited responses crt.sh is known for. Authorized targets only, only query domains you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-cert-transparency]
extends: []
relates: [recon-cert-transparency-subdomain-extraction, recon-cert-transparency-certstream-monitoring, recon-passive]
tools:
  - name: curl
    version: 8.5
  - name: jq
    version: 1.7
  - name: Python
    version: 3.12
---

crt.sh is the standard free interface to certificate transparency logs, run as a public service. It offers a web UI and a JSON API over the same database. This sub-skill covers using both well for recon-cert-transparency: query types, pagination, metadata extraction, and surviving its performance quirks. Only query domains you are authorized to test.

## Quick Workflow

1. Start with the web UI for one spot check to validate your query shape.
2. Move to the JSON API for repeatable pipeline queries; save raw JSON every run.
3. Run three query shapes: wildcard (`%25.`), bare domain, and exact-match where needed.
4. Handle pagination on large result sets; do not silently accept a truncated page.
5. Extract names plus metadata (issuer, not_before, serial) in one pass.
6. Diff against your previous run to find newly issued certificates.
7. Log query dates; CT data grows and your notes should show when each snapshot was taken.

## 1. Web UI spot checks

Open `https://crt.sh/?q=%25.example.com` in a browser for a quick look. The UI shows the certificate list with identity, issuer, and validity dates, and it is the fastest way to validate that a query shape returns what you expect before scripting it. Use the UI to answer one-off questions ("did they issue anything this week") and the API for everything repeatable.

## 2. JSON API query shapes

```bash
# Wildcard: all names under the domain (the workhorse query)
curl -s "https://crt.sh/?q=%25.example.com&output=json" -o wild.json

# Bare domain: certificates issued for the root itself
curl -s "https://crt.sh/?q=example.com&output=json" -o bare.json

# Identity search: certificates where the organization field matches
curl -s "https://crt.sh/?Identity=Example%20Ltd&output=json" -o org.json
```

The Identity search catches certificates on unrelated domains issued to the same organization, which sometimes reveals acquisitions or shadow infrastructure. Remember the authorization boundary: names outside your scoped domains are leads for scope questions, not targets.

Each JSON entry includes `issuer_ca_id`, `issuer_name`, `name_value`, `not_before`, `not_after`, `serial`, and more. Save the raw files; re-parsing beats re-querying.

## 3. Pagination on large results

crt.sh caps rows per response. For large domains, a single query silently truncates:

```bash
# Check result counts between runs to detect truncation
jq length wild.json
# If the count looks capped, page explicitly. crt.sh supports
# PostgreSQL-style paging on some endpoints; otherwise split the
# query by time window using not_before ranges, or fall back to
# an alternative CT API (e.g. censys certificates search) for the remainder.
```

Practical approach: query once, note the count and the date range covered, and if the newest entries stop suspiciously early, split by year using date-bounded queries and merge. Document the coverage ("2020-2026, ~48k rows across 3 queries") so future you trusts the snapshot.

## 4. Metadata extraction in one pass

```bash
# Names plus issuer plus validity, deduplicated, newest first
jq -r '.[] | "\(.not_before) | \(.issuer_name | split("=")[-1]) | \(.name_value)"' wild.json \
  | tr '[:upper:]' '[:lower:]' \
  | sort -u | sort -r > crtsh-meta.txt
head -20 crtsh-meta.txt
```

Example output shape:

```
2026-10-20 | lets encrypt | new-staging.example.com
2026-10-18 | digicert | api.example.com
2026-09-02 | lets encrypt | legacy-app.example.com
```

Read this for: new issuances (top of the sorted list), issuer diversity (many CAs suggests decentralized issuance, possibly shadow IT), and short validity periods (ACME automation versus manual processes).

## 5. Diffing runs for new certificates

```bash
# Previous run: crtsh-names-old.txt. Current: crtsh-names.txt
comm -13 <(sort crtsh-names-old.txt) <(sort crtsh-names.txt) > crtsh-new.txt
cat crtsh-new.txt
```

New names between runs are the highest-signal output of CT monitoring: they represent infrastructure created since your last check. During an engagement, run the wildcard query daily and diff. Each new name goes straight into resolution and httpx probing.

## Edge cases

- crt.sh times out or returns 500s: it does under load. Retry with exponential backoff, run at off-peak hours, and keep the last good snapshot so a failed run never leaves you empty-handed.
- Rate limiting after many queries: space queries minutes apart; crt.sh is a free service and aggressive polling gets throttled.
- JSON with embedded newlines in name_value: use jq's raw output carefully and split multi-name entries on newlines before deduping.
- Identity search returns unrelated orgs with similar names: verify with the domain filter before treating anything as a lead.

## Escalation

- crt.sh cannot cover a huge domain's full history: supplement with alternative CT search APIs (Censys certificates, commercial CT monitors) for the remainder, and note the coverage gap.
- You need programmatic access at scale: run your own CT log mirror client against the public log list instead of hammering crt.sh.

## Detection and defender view

- crt.sh is public: defenders see the same data. Set up alerts on your own domains for certificates you did not issue.
- Querying crt.sh leaves no trace on the target; it is fully passive. The only logs are crt.sh's own.
- If your CT monitoring spots a certificate you did not authorize, treat it as a potential CA compromise or account takeover and investigate immediately.

## Key references

- crt.sh: https://crt.sh
- crt.sh query interface docs: https://crt.sh/?q=example.com
- RFC 6962 Certificate Transparency: https://www.rfc-editor.org/rfc/rfc6962.html
- Google CT log list: https://www.gstatic.com/ct/log_list/v3/log_list.json
- Censys certificates search: https://search.censys.io
