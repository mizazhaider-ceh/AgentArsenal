---
name: osint-breach-data
description: Use when you need to work with breach data during an
  authorized investigation or defensive security review. Covers
  scoping what you may query, searching breach corpora for your
  organization's own exposure with DeHashed-style services and
  hashcat 6.2.6, analyzing password patterns to audit corporate policy
  with Python 3.12, assessing credential-stuffing risk, and running
  breach notification and forced-reset workflows. Use when responding
  to a suspected credential leak, when auditing whether company
  credentials appear in public breaches, or when advising on password
  policy from real-world data. Authorized and defensive use only.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [osint-methodology, threat-intel, osint-username-enumeration]
tools:
  - name: Python
    version: 3.12
  - name: hashcat
    version: 6.2.6
  - name: jq
    version: 1.7
  - name: curl
    version: 8.5
---

Breach data work means querying collections of leaked credentials to
answer defensive questions: are our accounts exposed, how bad is the
exposure, and what do we do about it. This skill covers the
authorized, defensive workflow: scoping, querying breach search
services for your own domains and accounts, analyzing password
patterns to fix policy, and notifying and remediating. It does not
cover trafficking in stolen data, cracking other people's passwords,
or using breaches offensively. If your authorization does not cover
the query, do not run it.

## Quick Workflow

1. Establish authorization in writing: which domains, accounts, and
   breaches are in scope, and who approved the queries.
2. Inventory your exposure surface: corporate domains, executive
   accounts, service accounts, and third-party SaaS logins.
3. Query breach search services for your scoped domains and accounts.
4. Deduplicate and classify results: live credentials versus old,
   corporate versus personal reuse.
5. Analyze password patterns in your own leaked passwords to audit
   policy effectiveness.
6. Assess credential-stuffing risk: which exposed accounts have
   access to what.
7. Notify affected users and force resets with a clear timeline.
8. Document everything: queries run, results, notifications sent.

## 1. Scoping and rules of engagement

Write the scope before touching any breach data:

- Domains: `example.com`, plus acquired domains and common
  typosquat variants you own.
- Accounts: named executives, IT admins, service accounts, and any
  account the incident involves.
- Purpose: defensive notification and remediation, or a specific
  authorized investigation.
- Prohibitions: no querying individuals outside scope, no retaining
  plaintext passwords longer than the remediation window, no
  sharing results beyond the response team.

```bash
# Case file header template
cat > case-scope.md <<'EOF'
# Breach data case: <name>
Date: 2026-10-23
Authorized by: <name, role>
Scope domains: example.com
Scope accounts: <list or "all corporate accounts">
Purpose: defensive exposure check after <incident/audit>
Data handling: plaintext credentials purged after remediation
EOF
```

If legal or compliance needs to review the plan, that review happens
now, not after the queries.

## 2. Querying breach search services

Breach search services index public breach corpora behind a query
API. Query only your scoped domains and accounts.

```bash
# Pattern: authenticated API query for your domain (service-specific syntax)
curl -s -H "Authorization: Bearer $BREACH_API_KEY" \
  "https://api.breach-service.example/v1/query?domain=example.com" | jq .

# Example response shape
# {
#   "results": [
#     {"email": "alice@example.com", "breach": "Collection#1",
#      "date": "2019-01-07", "password_hash": "5baa61e4..."},
#     {"email": "ops@example.com", "breach": "VendorBreach2023",
#      "date": "2023-05-11", "password_plaintext": "Summer2023!"}
#   ],
#   "total": 2
# }
```

Save raw responses with timestamps, then immediately reduce: extract
the account list and breach names into the case file, and handle
plaintext passwords per your data-handling rule (use them for
notification, then purge).

The DeHashed-style workflow sub-skill covers query syntax, fielded
searches, and result parsing in depth.

## 3. Deduplication and classification

```python
# triage.py: dedupe and classify breach hits for your domain
import json
from collections import defaultdict

hits = json.load(open('breach-results.json'))['results']
by_account = defaultdict(list)
for h in hits:
    by_account[h['email'].lower()].append(h)

for account, items in sorted(by_account.items()):
    breaches = sorted({i['breach'] for i in items})
    plaintext = any('password_plaintext' in i for i in items)
    print(f"{account}: {len(items)} hits, breaches={breaches}, plaintext={'YES' if plaintext else 'no'}")
```

Example output shape:

```
alice@example.com: 3 hits, breaches=['Collection#1', 'VendorBreach2023'], plaintext=YES
ops@example.com: 1 hits, breaches=['VendorBreach2023'], plaintext=YES
```

Classify each account: does the person still work here, is the
account still active, does it have privileged access. An exposed
plaintext password on a current domain admin account is an immediate
reset and a review of what that account touched.

## 4. Password pattern analysis for policy audits

Use your own organization's leaked passwords (from the scoped query)
to test whether the password policy works. Aggregate, never
individualize.

```python
# policy-audit.py: aggregate patterns from your own breach hits
import re
from collections import Counter

passwords = [h['password_plaintext'] for h in hits if 'password_plaintext' in h]
patterns = Counter()
for p in passwords:
    if re.fullmatch(r'[A-Z][a-z]+\d{2,4}!', p):
        patterns['CapitalizedWord+digits+symbol'] += 1
    elif re.fullmatch(r'(?i)(summer|winter|spring|autumn|fall)\d{4}.*', p):
        patterns['Season+year'] += 1
    elif len(p) < 10:
        patterns['short (<10)'] += 1
    else:
        patterns['other'] += 1
print(patterns.most_common())
```

Example output shape:

```
[('Season+year', 34), ('CapitalizedWord+digits+symbol', 21), ('short (<10)', 8), ('other', 12)]
```

If 70 percent of leaked passwords match `Season+year`, the policy
that requires "a capital, a number, and a symbol" is producing
predictable passwords. That aggregate finding justifies moving to
passphrases or passwordless, without ever naming who chose what.
The password-pattern-analysis sub-skill goes deeper on masks and
hashcat-driven policy testing.

## 5. Credential-stuffing risk assessment

For each exposed account, answer: where could this password be
reused, and what does the account access.

```bash
# Checklist per exposed privileged account (manual, with the identity team)
# 1. Is the password still valid anywhere? (force reset regardless)
# 2. Does the user reuse it on personal accounts that share the email? (ask, do not test)
# 3. Are there login anomalies for the account? (check SIEM for the last 90 days)
# 4. Is MFA enforced on every service the account touches?
```

Prioritize: domain admins, cloud console users, VPN users, and
anyone with production database access. An exposed password plus
missing MFA on VPN is the classic initial access path; treat it as
an incident until proven otherwise.

## 6. Notification and forced resets

Template for the notification (adapt to your organization's voice):

```
Subject: Action required: password reset after breach exposure

We found your corporate email in a public data breach. As a
precaution, your password has been expired. Please set a new one
at <SSO portal> before <date>. Use a unique passphrase you do not
use anywhere else. Contact the service desk if you did not expect
this message.
```

```bash
# Track the remediation in the case file
cat > remediation.csv <<'EOF'
account,notified,reset_confirmed,mfa_verified,notes
alice@example.com,2026-10-23,2026-10-23,yes,was domain admin: reviewed sessions
ops@example.com,2026-10-23,pending,no,MFA enrollment required
EOF
```

Force the reset rather than requesting it, expire sessions, and
verify MFA enrollment. For service accounts, rotate the secret and
update the consumers in the same change window.

## Edge cases

- The breach data includes customers, not just employees. Customer
  notification has legal timelines in many jurisdictions; involve
  legal immediately and do not improvise the notice.
- Plaintext passwords appear for accounts outside your scope mixed
  into a combo list. Do not query or retain them; note the
  incidental exposure and purge.
- The service account password cannot be rotated without downtime.
  Schedule the rotation, add compensating monitoring meanwhile, and
  document the risk acceptance.
- An executive refuses the reset or delays. Escalate through the
  incident chain; exposed privileged credentials are not optional
  hygiene.
- The breach is fresh and the data may still be spreading. Assume
  the passwords are in attackers' hands now, not later, and
  prioritize resets over perfect triage.
- Your queries return nothing. That is a result, not a failure:
  record the negative with the same rigor, including the corpora
  covered and their dates.

## Escalation

- Exposed credentials show signs of active use (logins from
  unusual locations, new MFA devices). This is now an incident:
  invoke the incident-response skill and treat it as suspected
  account compromise.
- The breach involves a third-party vendor holding your data. Engage
  vendor management and legal; your notification duties may depend
  on the contract.
- You discover the breach data contains highly sensitive personal
  data beyond credentials (health, financial). Minimize handling,
  involve privacy counsel, and tighten the purge timeline.
- The volume suggests a systemic issue (hundreds of accounts, one
  breach). Escalate from individual resets to a program: forced
  org-wide rotation, MFA enforcement, and a post-incident review.

## Detection and defender view

This skill is the defender view: breach data as an early warning
system. Operationalize it with continuous monitoring (domain
alerting from breach notification services), MFA everywhere so
leaked passwords alone are insufficient, and password policy based
on blocklists and length rather than composition rules. The
strategic defense is reducing the value of stolen passwords: SSO,
phishing-resistant MFA, and short session lifetimes. Every breach
triage should end with a control improvement, not just resets.

## Key references

- Have I Been Pwned (domain and breach checking):
  https://haveibeenpwned.com/
- DeHashed-style breach search services (query syntax in the
  sub-skill; use per your authorization)
- NIST SP 800-63B (password guidance: length over complexity):
  https://pages.nist.gov/800-63-3/sp800-63b.html
- OWASP credential stuffing guidance:
  https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html
- hashcat documentation: https://hashcat.net/wiki/
- MITRE ATT&CK T1078 (Valid Accounts) and T1110 (Brute Force):
  https://attack.mitre.org/
- CISA guidance on MFA: https://www.cisa.gov/topics/cybersecurity-best-practices/multifactor-authentication
