---
name: dark-web-monitoring
description: Use when setting up monitoring for your organization's
  data on criminal forums and marketplaces. Covers collection
  strategy, credential leak monitoring, brand and executive exposure,
  and operational security for the monitoring itself. Also use when a
  breach may have exposed data that is now traded.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [threat-intel, threat-actor-profiling, incident-response]
tools:
  - name: Python
    version: 3.12
---

Dark web monitoring watches where stolen data is traded: credential
dumps, initial access listings, and ransomware leak sites naming your
organization. This skill covers the defensive program: what to
monitor, how to do it safely, and how to act on findings. It is
intelligence collection for defense, with strict operational security
and legal boundaries.

## Quick Workflow

1. Define the watch list: domains, brand names, executive names, and
   key asset identifiers.
2. Choose collection: commercial feeds, vetted sharing communities,
   and limited direct collection with proper authorization.
3. Monitor credential leaks: corporate emails in dumps, with password
   reuse checks.
4. Watch for access listings: VPN, RDP, or email access sold for
   your organization.
5. Check ransomware leak sites for your organization's name.
6. Verify every hit before acting: false positives are common.
7. Act: force password resets, hunt for the access, notify per plan.
8. Protect the program: OPSEC for collectors, legal review of
   methods.

## 1. Monitoring setup

```bash
# Credential exposure check (commercial feed or authorized API)
# For each corporate domain: search dumps for @company addresses
python3 - << 'PY'
domains = ["company.example", "subsidiary.example"]
print("query each feed: domain, date range, source dump")
print("for hits: which dump, when, password present?")
print("action: force reset for affected users, check for reuse in SSO logs")
PY
```

```bash
# Ransomware leak site watch (defensive monitoring)
# Maintain the list of leak site onion addresses via your intel feed;
# check for your organization name on a schedule, with screenshots
# and timestamps as evidence
echo "alert on: org name, key domains, executive names"
```

## 2. Verification and response

```bash
# Verify before you act: is the data real, current, and yours
# - sample records checked against HR (with privacy care)
# - dump date vs your breach timeline
# - is it a combo list (old, aggregated) or fresh
echo "false positive cost: unnecessary resets erode trust; verify first"
```

```bash
# If access is listed for sale (e.g. "VPN access to company.example"):
# 1. preserve the listing (screenshot, timestamp, URL)
# 2. hunt internally: the access method named in the listing
# 3. rotate the exposed credentials and close the path
# 4. brief incident response; this may be an active intrusion
```

## Edge cases

- The monitoring itself needs Tor and forum accounts. Get legal
  approval first; some jurisdictions restrict this.
- Data found is about employees personally. Handle with HR and
  privacy care, not just security.
- A feed reports stale data as new. Track first seen dates to
  avoid repeated responses to the same dump.

## Escalation

- Active sale of your access: treat as a potential live intrusion
  and engage incident response.
- Ransomware listing confirmed: follow the ransomware playbook;
  do not contact the actors without counsel.

## Detection and defender view

Dark web monitoring is early warning, not prevention: it tells you
what already leaked. Its value is speed: faster resets, faster
hunting for the listed access, faster breach confirmation. The
durable program pairs monitoring with the fundamentals that make
leaks less useful: MFA everywhere, unique passwords, and quick
revocation.

## Key references

- Related skills: threat-intel, incident-response.
- TLP handling for shared findings.
- Legal guidance on OSINT collection in your jurisdiction.
