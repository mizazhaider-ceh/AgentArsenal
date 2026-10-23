---
name: mfa-bypass-testing
description: Use when testing whether multi-factor authentication can be
  bypassed on an authorized engagement. Covers response manipulation, MFA
  step skipping, brute-forcing short codes, backup code and recovery flow
  abuse, and push fatigue scenarios. Use when an application offers MFA,
  when assessing the real strength of the second factor, when reviewing
  enrollment and recovery flows, or when the scope asks how far an
  attacker gets with only the password.
version: 1.0.0
domain: auth
lifecycle: stable
last_verified: 2026-10-23
parent: auth-attacks
requires: [auth-attacks]
extends: []
relates: [password-attacks, web-xss]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
  - name: curl
    version: 8.5
---

Multi-factor authentication is the single best defense against password
attacks, which makes its bypasses high-impact findings. This skill covers
testing MFA implementations on authorized engagements: the classic logic
flaws (skipping the step, tampering with the verification response),
code-space attacks, and recovery flow abuse. Test only with accounts the
engagement provides, and never lock real users out of their MFA.

## Quick Workflow

1. Enroll MFA on a test account and map the full flow: enrollment,
   challenge, verification, recovery.
2. Test step skipping: request authenticated pages directly after the
   password step.
3. Test response tampering: modify the verification request and response.
4. Test the code space: rate limits, attempt limits, and code lifetime.
5. Test recovery flows: backup codes, email fallback, help-desk reset.
6. Review push-based MFA for fatigue and number-matching gaps.
7. Document each bypass or the controls that stopped you.

## 1. Step skipping and response tampering

```bash
# After the password step, try the destination directly
curl -s -c /tmp/mfa1.txt -X POST 'https://target.example/login' \
  -d 'username=test&password=Test123!' -o /dev/null -w '%{http_code}\n'
curl -s -b /tmp/mfa1.txt 'https://target.example/dashboard' \
  -o /tmp/dash.html -w '%{http_code}\n'
grep -i -c 'welcome' /tmp/dash.html  # nonzero means the MFA step was skipped

# Tamper the verification response in Burp: change {"success":false}
# to {"success":true}, or status 401 to 200, and see if the client
# or server trusts it

# Try omitting the MFA parameter entirely
curl -s -b /tmp/mfa1.txt -X POST 'https://target.example/mfa/verify' \
  -d '' -o /dev/null -w '%{http_code}\n'
```

The most common MFA flaw is trusting the client: the server sets an
"mfa_done" cookie or the frontend decides. Every one of these tests checks
whether the server enforces the step.

## 2. Code-space attacks

```bash
# Six-digit TOTP/SMS codes: check attempt limits first with wrong codes
for i in 1 2 3 4 5 6; do
  code=$(curl -s -b /tmp/mfa1.txt -X POST 'https://target.example/mfa/verify' \
    -d 'code=000000' -w '%{http_code}\n' -o /dev/null)
  echo "attempt $i -> $code"
done
# If attempt 6 still returns 200/302 without a lockout, the code space
# is brute-forceable: 1M codes at even 10/sec is ~28 hours, often less
# with no rate limit

# Check code lifetime and reuse: submit a valid code twice
# A code that works twice has no single-use enforcement
```

Short codes without strict attempt limits are the classic bypass. Also
test whether the code is bound to the session: a code issued for user A
that verifies user B's challenge is a logic flaw.

## 3. Recovery and enrollment flows

```bash
# Backup codes: are they single use? guessable? shown once?
# Request new backup codes twice and compare: identical sets mean
# they are not rotated

# Email fallback: does "send code by email" downgrade MFA to
# "access to email", and is that downgrade logged and notified?

# Enrollment: can an attacker with the password enroll their own
# second factor? (Test on a fresh test account.)
curl -s -b /tmp/fresh.txt 'https://target.example/mfa/enroll' \
  | grep -i -o 'qr[^<]*\|secret[^<]*' | head -3
```

Recovery flows are where MFA dies in practice: a help-desk reset with weak
identity proofing, or an email fallback with no notification, undoes the
whole second factor. Test the recovery with the same rigor as the primary
flow.

## Edge cases

- Push MFA with number matching resists fatigue. Verify the matching is
  actually enforced; some implementations show the number but accept any
  approval.
- The app allows "remember this device" for 30 days. Review how the
  device token is stored and whether stealing it skips MFA (it usually
  does, which makes its security equal to the session's).
- Rate limiting is per-IP. The finding stands (the control is weak), but
  note that distributed attacks bypass it; do not run a distributed test
  without explicit approval.
- Hardware keys (WebAuthn) are in use. Test for downgrade options: does
  the app let the user fall back to SMS or email, and is that fallback
  as strong as the key.

## Escalation

- A bypass works: prove it end to end with the test account, screenshot
  the authenticated session, and report the exact steps; MFA bypasses
  are typically critical findings.
- No bypass found: document the controls that held (attempt limits,
  single-use codes, enforced server-side state) as positive assurance.
- The scope includes social engineering of help-desk reset: only with
  explicit written approval, and follow the engagement's pretext rules.

## Detection and defender view

Defenders see MFA attacks as password-step successes followed by MFA-step
anomalies: many code attempts, rapid enrollment changes, recovery flow
use at odd hours. Defenses are strict attempt limits with lockout, short
code lifetimes, single-use codes, server-side MFA state that cannot be
skipped, notifications on enrollment and recovery changes, and phishing
resistant factors (WebAuthn) for high-value accounts.

## Key references

- MITRE ATT&CK T1110 (Brute Force).
- MITRE ATT&CK T1556 (Modify Authentication Process).
- CWE-307 (Improper Restriction of Excessive Authentication Attempts).
- CWE-287 (Improper Authentication).
- OWASP Testing Guide: Testing for Weak Authentication.
- OWASP MFA Cheat Sheet.
