---
name: osint-breach-data-breach-notification
description: Use when breach exposure is confirmed and affected users
  must be notified and remediated during an authorized response. Covers
  building the notification list from triaged breach data with Python
  3.12, drafting clear notification messages, coordinating forced
  password resets and session revocation, verifying MFA enrollment,
  tracking remediation to completion, and handling customer
  notification duties with legal. Use when the parent osint-breach-data
  workflow confirms exposure, after any incident involving credential
  theft, or when running a proactive breach-notification program,
  driving forced resets through IdP APIs with curl.
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
---

Breach notification is the operational end of breach data work:
telling the right people, forcing the resets, and proving it is done.
Slow or vague notification turns a manageable exposure into an
incident. This sub-skill covers the notification list, the message,
the reset mechanics, and the tracking that closes the loop. It
assumes the exposure is confirmed and the case scope authorizes
contacting the affected users.

## Quick Workflow

1. Build the notification list from the triaged breach data,
   deduplicated by person.
2. Prioritize: privileged accounts and plaintext exposures first.
3. Draft the notification: what happened, what to do, by when, who
   to contact.
4. Get legal and comms review for customer-facing notices.
5. Send notifications and force password resets in the same motion.
6. Revoke sessions and verify MFA enrollment per account.
7. Track every account to confirmed remediation.
8. Close the case with metrics: notified, reset, MFA-verified.

## 1. Building the notification list

```python
# notify-list.py: from triage to per-person notification list
import json, csv
from collections import defaultdict

data = json.load(open('merged.json'))['results']
people = defaultdict(lambda: {'breaches': set(), 'plaintext': False, 'privileged': False})
for r in data:
    email = r['email'].lower()
    people[email]['breaches'].add(r['breach'])
    if r.get('password_plaintext'):
        people[email]['plaintext'] = True
    if any(k in email for k in ['admin', 'ops', 'svc', 'root']):
        people[email]['privileged'] = True

with open('notify-list.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['email', 'breaches', 'plaintext', 'privileged', 'priority'])
    for email, info in sorted(people.items()):
        prio = 'P1' if (info['privileged'] and info['plaintext']) else \
               'P2' if info['plaintext'] else 'P3'
        w.writerow([email, ';'.join(sorted(info['breaches'])),
                    info['plaintext'], info['privileged'], prio])

print(f"{len(people)} people to notify")
```

Example output shape:

```
38 people to notify
# notify-list.csv head:
# ops@example.com,VendorBreach2023,True,True,P1
# alice@example.com,Collection#1,True,False,P2
```

One row per person, even if they appear in five breaches; nobody
needs five emails about the same password hygiene.

## 2. The notification message

Internal template (adapt the voice to your organization):

```
Subject: Action required: reset your password by <date>

Hi <name>,

Your work email appeared in a public data breach (<breach name>,
<breach date>). We have expired your password as a precaution.

What to do now:
1. Set a new password at <SSO portal link> before <date>.
2. Make it unique: do not reuse it anywhere else.
3. Confirm MFA is enabled when prompted.

If you used this password on other sites, change it there too.
Questions: contact the service desk at <contact>.

This is a legitimate security notice. We will never ask for your
password by email.
```

Rules: say what happened plainly, give one clear action with a
deadline, link only to known-good internal portals, and include the
anti-phishing line. Never include the leaked password in the notice.

## 3. Forced resets and session revocation

Notification without enforcement is a suggestion. Pair them:

```bash
# Pattern: expire passwords via your identity provider API (IdP-specific)
# Example shape with a generic IdP API:
curl -s -X POST -H "Authorization: Bearer $IDP_TOKEN" \
  "https://idp.example.local/api/v1/users/ops@example.com/expire-password"

# Revoke sessions so the old credential stops working everywhere
curl -s -X POST -H "Authorization: Bearer $IDP_TOKEN" \
  "https://idp.example.local/api/v1/users/ops@example.com/revoke-sessions"
```

Order per account: notify, expire, revoke sessions, then verify the
new password and MFA at next login. For service accounts, rotate the
secret and update consumers in the same change window; an expired
service credential with no updated consumer is an outage.

## 4. Tracking to completion

```bash
# remediation.csv is the source of truth; update it from IdP reports
cat > remediation.csv <<'EOF'
email,notified_at,reset_at,mfa_verified,status,notes
ops@example.com,2026-10-23T10:00Z,2026-10-23T10:40Z,yes,closed,"was domain admin; sessions reviewed, no anomalies"
alice@example.com,2026-10-23T10:00Z,,,open,"reminder sent 2026-10-24"
EOF

# Daily check: who is still open past the deadline
python3 - <<'EOF'
import csv
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
for row in csv.DictReader(open('remediation.csv')):
    if row['status'] == 'open':
        print(f"OVERDUE-CHECK: {row['email']} notified {row['notified_at']} - {row['notes']}")
EOF
```

Chase opens on a schedule: reminder at 48 hours, manager escalation
at 5 days, access suspension per policy after that. An untracked
notification program quietly fails; the CSV is what keeps it honest.

## 5. Customer notification duties

When the breach touches customer data, the rules change: legal
timelines, regulator notices, and public communication. Involve legal
before drafting anything external, and prepare:

- What data was exposed, for whom, and when (facts only).
- What you are doing (resets, monitoring, MFA offers).
- What customers should do (reset, watch for phishing).
- A dedicated contact channel, not the general support queue.

Never minimize in writing ("no evidence of misuse" is a hostage to
fortune). State what you know, what you are doing, and when you
will update.

## 6. Closing metrics

```
Notified: 38/38 (100%)
Reset confirmed: 36/38 (95%), 2 escalated to managers
MFA verified: 34/38 (89%), 4 enrolled during this cycle
Mean time to reset: 31 hours
Plaintext exposures closed: 12/12
Purge of working plaintext data: completed 2026-11-23
```

The metrics go to leadership and into the case file. They also set
the baseline for the next cycle: notification programs improve when
measured.

## Edge cases

- The user left the organization. Disable the account instead of
  notifying; confirm disabled status and check for recent logins.
- The email belongs to a shared mailbox or role account. Notify the
  owning team, rotate the credential, and record the team as the
  responsible party.
- The user claims they never had that password. Believe the reset,
  not the debate: expire it anyway, since the breach row ties the
  email to a password whether or not the user remembers it.
- Notification emails bounce. Fall back to the manager chain and
  the service desk; document the alternate channel.
- The breach notice triggers a phishing wave imitating your
  notification. Warn users in the original notice ("we will never
  ask for your password"), and have the service desk ready.
- Legal holds the customer notice for review past the regulatory
  deadline. Document the tension in writing; missing a statutory
  deadline needs a conscious, recorded decision.

## Escalation

- Resets reveal active compromise (the account was being used by
  someone else). Stop the notification routine for that account and
  invoke incident response; it is now a live intrusion.
- A P1 account owner is unresponsive past the deadline. Escalate to
  their leadership and consider suspending access; an exposed
  privileged credential cannot wait on convenience.
- Customer data exposure triggers regulatory clocks. Escalate to
  legal and executive leadership immediately with the facts as
  known; do not wait for the full triage to finish.
- The notification itself becomes a media event. Hand external
  communication to the designated spokespeople; the response team
  sticks to facts and remediation.

## Detection and defender view

Notification programs are a detective control: they assume breaches
happen and minimize the window between exposure and reset. The
mature version is continuous: domain monitoring on breach feeds,
automatic flagging of exposed accounts, and self-service reset
flows that make the whole cycle fast. Measure it, because "we notify
people about breaches" without metrics is a policy, not a program.
And every cycle should feed back into prevention: the accounts that
keep appearing are the ones that need MFA, passwordless, or
privilege reduction.

## Key references

- Parent workflow: osint-breach-data (this repo)
- Have I Been Pwned notification services:
  https://haveibeenpwned.com/
- NIST SP 800-63B: https://pages.nist.gov/800-63-3/sp800-63b.html
- CISA MFA guidance:
  https://www.cisa.gov/topics/cybersecurity-best-practices/multifactor-authentication
- OWASP Credential Stuffing Prevention:
  https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html
