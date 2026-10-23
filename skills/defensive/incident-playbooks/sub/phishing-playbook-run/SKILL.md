---
name: phishing-playbook-run
description: Use when a phishing email is reported or a user clicked and
  the phishing playbook must be executed. Covers triaging the report,
  finding who else got it, containing clicked credentials and sessions,
  and removing the phish. Use when the phishing mailbox gets a report,
  when EDR flags a malicious attachment open, when credentials were
  entered on a phish site, or when running the tabletop version.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
parent: incident-playbooks
requires: [incident-playbooks]
extends: []
relates: [incident-response, phishing-defense]
tools:
  - name: Python
    version: 3.12
---

Phishing is the most common initial access: one click can be one
compromised account or the start of a breach. This skill is the
executable playbook: triage the report, find the blast radius, contain
the clicked accounts, and remove the phish everywhere. Speed matters,
but accuracy matters more: the wrong "all clear" is worse than a slow
containment.

## Quick Workflow

1. Triage the reported email: headers, URLs, attachments, verdict.
2. Find every recipient: who got it, who opened it, who clicked.
3. Contain clicked accounts: reset passwords, revoke sessions and
   tokens.
4. Remove the phish: mailbox purge, block the infrastructure.
5. Check for post-click activity: logons, mailbox rules, forwarding.
6. Decide: isolated click or active incident (escalate if the latter).
7. Close the loop with the reporter and the affected users.

## 1. Triage

```bash
# Pull the reported message with full headers
# Check in order:
# 1. Authentication: SPF, DKIM, DMARC results in the headers
# 2. URLs: expand shorteners, compare display text versus href
# 3. Attachments: hash and detonate in the sandbox, do not open locally
# 4. Verdict: malicious, suspicious, or benign (with the evidence)

# Header red flags checklist:
# - Return-Path domain differs from From domain
# - Received chain shows unexpected relays
# - Reply-To points elsewhere
```

Triage in the sandbox and the mail gateway, not on your workstation.
One analyst clicking the live phish during triage is the incident
repeating itself.

## 2. Blast radius

```bash
# Query the mail gateway/logs for the campaign identifiers:
# - Sender address or domain
# - Subject line (exact and fuzzy)
# - Attachment hash
# - Phish URL domain

# For each recipient, determine: delivered, opened, clicked, submitted
# (gateway + proxy + EDR data combined; no single source is complete)

# Priority order for containment:
# 1. Submitted credentials on the phish site
# 2. Clicked but unknown submission
# 3. Opened the attachment
# 4. Received but no interaction
```

The recipient list is the scope. Until you have it, you do not know
whether this is one user or fifty, and the response differs completely.

## 3. Containment and cleanup

```bash
# For every clicked/submitted account:
# 1. Force password reset (user does it, you verify)
# 2. Revoke all sessions and tokens (SSO, VPN, mail, cloud)
# 3. Check mailbox rules and forwarding the attacker may have set
#    (the classic persistence: silent forward to the attacker)
# 4. Review logons in the last 7 days for odd IPs and times

# Mailbox rule check (the most-missed persistence):
# List inbox rules for each affected mailbox; delete attacker rules

# Infrastructure blocks:
# - Block the phish domains/URLs at proxy and mail gateway
# - Block the sender at the gateway
# - Purge the message from all mailboxes (gateway purge feature)
```

Mailbox rules are the persistence mechanism phishing buys: the attacker
keeps reading mail after the password reset through a forward rule.
Check them on every affected mailbox, every time, without exception.

## Edge cases

- The user entered credentials but the site was down. Treat as
  compromised anyway; you cannot prove the attacker got nothing.
- The phish targeted an admin or finance user. Escalate the scrutiny:
  review their recent actions for BEC-style fraud, not just access.
- The attachment was opened on a personal device. The corporate playbook
  still applies to the accounts; the device needs its own handling.
- Hundreds of recipients. Automate the triage queries, prioritize by
  interaction level, and staff the containment in waves.

## Escalation

- Post-click activity found (logons, rules, data access): this is now
  an active incident; hand to ir-scoping with the phishing evidence.
- BEC fraud is suspected (wire instructions changed): involve finance
  and legal immediately; time is money literally.
- The campaign is ongoing: keep the blocks and monitoring in place
  past the initial cleanup.

## Detection and defender view

The defender's investment that makes this playbook fast: a monitored
phishing report mailbox, mail gateway logging that answers the blast
radius questions in minutes, EDR on endpoints for the click data, and
SSO session revocation that actually works. User reporting is the
detection control; make reporting one click and thank reporters
publicly (anonymized) so the reports keep coming.

## Key references

- NIST SP 800-61 (incident handling).
- CISA phishing guidance.
- MITRE ATT&CK T1566 (Phishing).
