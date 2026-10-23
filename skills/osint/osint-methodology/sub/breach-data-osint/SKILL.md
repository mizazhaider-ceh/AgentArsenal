---
name: breach-data-osint
description: Use when checking whether credentials or data from public
  breaches affect the engagement's scope on authorized security work.
  Covers breach lookup discipline, handling breached credentials safely,
  and assessing organizational exposure. Use when the scope includes
  credential risk, when building password lists with permission, when
  assessing user exposure, or when the client asks "are we in the
  breaches."
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-methodology
requires: [osint-methodology]
extends: []
relates: [password-attacks, auth-attacks]
tools:
  - name: Python
    version: 3.12
  - name: Hashcat
    version: 6.2.6
---

Breach data turns public leaks into credential risk: the passwords your
users reused elsewhere are now attacker wordlists. This skill covers
using breach data responsibly on authorized engagements: looking up
exposure, handling any credentials found with extreme care, and
assessing the organizational impact. Breach data is sensitive personal
data; the handling discipline here is the point.

## Quick Workflow

1. Confirm the scope covers breach-data checks and the specific
   identifiers.
2. Look up exposure through reputable breach notification services.
3. For in-scope findings, assess: which accounts, what data, how fresh.
4. Handle any retrieved credentials under the strictest rules.
5. Report exposure factually: who is affected, what to do.
6. Delete working copies of breach data at engagement end.

## 1. Lookup discipline

```bash
# Reputable lookup approach (per identifier, with authorization):
# - Use established breach notification services for email checks
# - For organizational assessment: the domain's exposure summary
# - Record: breach name, date, data types exposed, nothing more

# What to record per hit:
# breach: <name>, date: <date>, data: <types>, accounts affected: <count>
# What NOT to record: the actual passwords, in notes or tickets

# Organizational exposure pattern:
python3 - <<'EOF'
print("Assess per department/role where the scope allows:")
print("- Executives and IT admins in breaches: priority resets")
print("- Service account emails in breaches: investigate reuse")
print("- Fresh breaches (< 1 year): higher credential-stuffing risk")
EOF
```

Look up, do not download: the question "is this email in a breach" has
established services; bulk breach datasets are a handling liability
that most engagements do not need.

## 2. Credential handling

```bash
# If the engagement authorizes credential testing from breach data:
# 1. The credential list lives encrypted, access-logged, minimal copies
# 2. Testing follows credential-stuffing rules (rate limits, approval)
# 3. Every confirmed hit is reported through the sensitive channel
# 4. The client forces resets; you verify the resets

# After the engagement:
# shred -u /tmp/breach_working_list.txt  (and any copies)
# Confirm deletion in the closeout notes
```

Breached passwords in your hands are a liability from the first second:
encrypt at rest, minimize copies, and destroy on schedule. The handling
rules are stricter than for any other engagement data because the data
belongs to real people who did not consent to your holding it.

## 3. Organizational assessment

```bash
# The deliverable for "are we in the breaches":
# - Exposure summary: N accounts in M breaches, by data type
# - Priority actions: who resets what, in what order
# - Policy fixes: breached-password blocking at registration and login
# - Monitoring: ongoing breach alerts for the domain

# The systemic fix (recommend once, reference everywhere):
# check new and changed passwords against breach corpora;
# NIST SP 800-63B requires it, and it kills the reuse problem at the root
```

The assessment's value is the action list, not the breach list: who
resets, what policy changes, what monitoring starts. Breach exposure
without the remediation plan is just bad news.

## Edge cases

- The scope does not cover breach checks. Do not improvise them;
  credential-adjacent work without authorization is the fastest way to
  end an engagement badly.
- The data is clearly fake or poisoned. Breach datasets contain junk;
  validate hits before acting on them.
- An executive is heavily exposed. Report factually through the agreed
  channel; do not editorialize about their personal security.
- Legal restricts breach data use. Some jurisdictions limit it; legal
  clears the approach before the work starts.

## Escalation

- Active credential abuse is suspected from the exposure: treat as an
  incident input (forced resets, session revocation) alongside the
  assessment.
- The organization needs ongoing monitoring: recommend the breach
  alerting service that fits, with the current exposure as the
  baseline.
- You need the full dataset analyzed: that is a data-handling decision
  for leadership and legal, not a technical one.

## Detection and defender view

For defenders, breach data is both threat intel and hygiene input: monitor
the organization's domains in breach feeds, force resets on exposure,
and block breached passwords proactively. The defender's automation is
the registration-time breach check; every password set that matches a
breach corpus is a future credential-stuffing success prevented.

## Key references

- NIST SP 800-63B (breached password checks).
- CWE-521 (Weak Password Requirements).
- Have I Been Pwned and similar notification services (lookup method).
