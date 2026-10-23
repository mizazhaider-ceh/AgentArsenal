---
name: osint-breach-data-dehashed-workflows
description: Use when you need to query breach search engines
  effectively within an authorized defensive investigation. Covers
  DeHashed-style query syntax and fielded searches, API usage with
  curl 8.5 and Python 3.12, paginating large result sets, parsing
  JSON with jq 1.7, correlating emails, usernames, IPs, and hashes
  across breaches, and maintaining chain of custody for results. Use
  when the parent osint-breach-data workflow reaches the querying
  phase, when you need precise fielded searches instead of broad
  domain dumps, or when results must be defensible in a report.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-breach-data
requires: [osint-breach-data]
extends: []
relates: [osint-breach-data]
tools:
  - name: Python
    version: 3.12
  - name: curl
    version: 8.5
  - name: jq
    version: 1.7
---

Breach search engines index combo lists and breach dumps behind a
query interface: email, username, IP, hash, password, phone. Knowing
the query syntax turns a thousand-row dump into the twelve rows that
matter. This sub-skill covers fielded search patterns, API
automation, pagination, and result handling for defensive cases.
Query only what your authorization covers, and treat every result as
sensitive data with a purge plan.

## Quick Workflow

1. Confirm the exact query targets from the case scope (domains,
   accounts, indicators).
2. Start with fielded searches: email and domain first, then
   username and IP pivots.
3. Page through large result sets completely; do not sample.
4. Parse JSON into a normalized table with jq or Python.
5. Correlate across breaches: same email in multiple dumps, password
   reuse patterns.
6. Reduce to the case-relevant set and purge the rest per policy.
7. Record every query string, timestamp, and result count.
8. Hand the reduced set to the parent workflow for notification.

## 1. Query syntax and fielded searches

Breach search engines support fielded queries. Learn the fields:

```bash
# Email and domain searches (the defensive bread and butter)
# Web UI or API query patterns (service-specific, pattern shown):
#   email:alice@example.com
#   domain:example.com
#   username:alice_ops
#   ip:203.0.113.45
#   hash:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8

# API pattern with curl
curl -s -H "Authorization: Bearer $BREACH_API_KEY" \
  --get "https://api.breach-service.example/v1/search" \
  --data-urlencode "query=email:alice@example.com" \
  --data-urlencode "size=100" | jq .
```

Example response shape:

```json
{
  "total": 3,
  "results": [
    {
      "email": "alice@example.com",
      "username": "alice_ops",
      "breach": "Collection#1",
      "breach_date": "2019-01-07",
      "password_plaintext": "Summer2019!",
      "ip": "203.0.113.45"
    }
  ]
}
```

Fielded searches to run per account: email, username, and any known
IP. Per domain: the domain query, then the top usernames from it as
follow-ups. Document each query string verbatim; "I searched the
domain" is not reproducible, the exact query is.

## 2. Pagination and complete collection

```bash
# Paginate until total is reached; partial collection misses breaches
PAGE=1
while true; do
  RESP=$(curl -s -H "Authorization: Bearer $BREACH_API_KEY" \
    --get "https://api.breach-service.example/v1/search" \
    --data-urlencode "query=domain:example.com" \
    --data-urlencode "page=$PAGE" --data-urlencode "size=100")
  echo "$RESP" > page-${PAGE}.json
  TOTAL=$(echo "$RESP" | jq .total)
  COUNT=$(echo "$RESP" | jq '.results | length')
  echo "page $PAGE: $COUNT results (total $TOTAL)"
  [ "$COUNT" -eq 0 ] && break
  PAGE=$((PAGE + 1))
done
```

Merge pages into one normalized file:

```bash
jq -s '{results: map(.results) | add}' page-*.json > merged.json
jq '.results | length' merged.json
```

Never sample a large result set for a defensive case. The one row
you skip is the domain admin's plaintext password; completeness is
the point.

## 3. Parsing and normalization with jq

```bash
# Table of email, breach, date, and whether plaintext is present
jq -r '.results[] | [.email, .breach, .breach_date,
  (if .password_plaintext then "PLAINTEXT" else "hash-only" end)] | @tsv' \
  merged.json | sort | uniq -c | sort -rn | head -30

# Pivot: all breaches touching privileged accounts
jq -r '.results[] | select(.email | test("admin|ops|svc|root"; "i")) |
  [.email, .breach] | @tsv' merged.json | sort -u

# Extract unique IPs for infrastructure pivots (authorized scope only)
jq -r '.results[] | .ip // empty' merged.json | sort -u > ips.txt
```

Example output shape:

```
3 alice@example.com Collection#1 2019-01-07 PLAINTEXT
2 ops@example.com VendorBreach2023 2023-05-11 PLAINTEXT
1 svc-backup@example.com OldForum2016 2016-11-02 hash-only
```

The `sort | uniq -c` pattern collapses combo-list duplication, where
the same credential appears in many repackaged lists. Deduplicate
before counting exposure, or the numbers mislead.

## 4. Cross-breach correlation

```python
# correlate.py: link accounts across breaches, spot password reuse
import json
from collections import defaultdict

data = json.load(open('merged.json'))['results']
by_email = defaultdict(list)
for r in data:
    by_email[r['email'].lower()].append(r)

for email, rows in sorted(by_email.items()):
    breaches = sorted({r['breach'] for r in rows})
    pwds = {r.get('password_plaintext') for r in rows if r.get('password_plaintext')}
    if len(breaches) > 1:
        print(f"{email}: {len(breaches)} breaches {breaches}")
        if len(pwds) == 1:
            print(f"  SAME password across all breaches -> reuse confirmed")
```

Example output shape:

```
ops@example.com: 3 breaches ['OldForum2016', 'Collection#1', 'VendorBreach2023']
  SAME password across all breaches -> reuse confirmed
```

Password reuse across breaches is the finding that justifies forced
resets beyond the single breach: the password is not just leaked, it
is a skeleton key the user carries between services.

## 5. Chain of custody for results

```bash
# Hash raw result files at collection time
sha256sum page-*.json merged.json > results.sha256
cat results.sha256

# Case log entry per query batch
cat >> query-log.md <<'EOF'
## 2026-10-23 10:15 UTC
Query: domain:example.com (pages 1-4, 342 results)
Authorization: case-scope.md v1
Raw files: page-1.json .. page-4.json, sha256 in results.sha256
Reduced: triage.csv (38 in-scope accounts)
Purge due: 2026-11-23 (plaintext fields)
EOF
```

If results may support disciplinary or legal action, this log is what
makes them admissible as an investigative record rather than a
screenshot someone could have edited.

## Edge cases

- The API returns truncated or redacted passwords on your plan.
  Note the limitation; hash-only results still prove exposure and
  still justify resets.
- Rate limits throttle a large domain query. Back off, resume with
  pagination state saved, and note the elapsed collection window.
- Combo lists duplicate the same credential dozens of times. The
  dedupe step is mandatory before any counting or reporting.
- A result references a breach you cannot verify exists. Treat the
  row as uncorroborated; do not name the breach in external
  communications until confirmed.
- The query returns accounts of people who left years ago. Still
  notify IT to disable or confirm disabled status; stale accounts
  with known passwords are a real attack path.
- Plaintext fields appear for accounts outside your scope in a
  shared dump. Exclude them from the case file and purge the raw
  pages on schedule.

## Escalation

- Results show active credential use (recent breach, privileged
  account, no MFA). Escalate to incident response immediately;
  notification can run in parallel but containment comes first.
- The breach is not public knowledge and affects customers. Engage
  legal before any external statement; your query log now matters.
- You discover the search service itself is dubious (no clear data
  sourcing, offers full dumps for sale). Do not use it; find a
  reputable source and note why you rejected the first one.
- Query volume suggests a compromise of your own infrastructure
  (thousands of corporate accounts in one fresh breach). Escalate
  from case handling to a coordinated response with leadership.

## Detection and defender view

Breach search engines are dual-use: defenders query their own
exposure, attackers query everyone else's. The defense is making the
query worthless: unique passwords per service (so one breach does
not cascade), MFA everywhere (so passwords alone do not grant
access), and monitoring for your domain in new breaches so you learn
from the alert feed instead of the attacker. Run this workflow on a
schedule, not just after incidents; the alert that arrives before
the attacker acts is the whole value proposition.

## Key references

- Parent workflow: osint-breach-data (this repo)
- Have I Been Pwned API: https://haveibeenpwned.com/API/v3
- NIST SP 800-63B: https://pages.nist.gov/800-63-3/sp800-63b.html
- OWASP Credential Stuffing Prevention:
  https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html
- MITRE ATT&CK T1078 (Valid Accounts): https://attack.mitre.org/
- jq manual: https://jqlang.github.io/jq/manual/
