---
name: session-management-security
description: Use when assessing session management on an authorized
  web engagement. Covers cookie attributes, session fixation,
  timeout and rotation, concurrent session handling, and logout
  completeness. Also use when login security needs review beyond
  the password.
version: 1.0.0
domain: auth
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [auth-attacks, webauthn-security, webapp-pentest-methodology]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

Sessions are what login creates: get the cookie handling wrong and
authentication does not matter. This skill covers authorized testing
of session management: cookie flags, fixation, timeouts, rotation,
and logout. Test with your own accounts on systems you may assess.

## Quick Workflow

1. Map the session tokens: names, where they live, and their
   lifetime.
2. Check cookie attributes: Secure, HttpOnly, SameSite, and Path.
3. Test session fixation: can you plant a session ID the victim
   then uses.
4. Test rotation: does the ID change at login and privilege change.
5. Check timeouts: idle and absolute, enforced server side.
6. Test logout: is the session destroyed server side, everywhere.
7. Check concurrent sessions: limits and user visibility.
8. Report each gap with the exact request sequence.

## 1. Cookie and fixation tests

```bash
# Cookie attributes (your test login)
curl -s -i -X POST 'https://target.example/login' \
  -d "user=test@example.com&pass=Test1234!" | grep -i "^set-cookie:" | head -5
# Want: __Host- prefix or Secure; HttpOnly; SameSite=Lax or Strict
# Missing Secure/HttpOnly/SameSite = findings, graded by context
```

```bash
# Session fixation test:
# 1. get a session ID anonymously
curl -s -i 'https://target.example/' | grep -i "^set-cookie:" | head -3
# 2. log in WITH that cookie set; 3. check if the same ID is now authed
# If the pre login ID becomes the authed session: fixation works
echo "fix: rotate the session ID at login, always"
```

```bash
# Rotation at privilege change: log in, then elevate (or step up auth)
# and check whether the session ID changed again
echo "also test: password change should kill other sessions (or warn)"
```

## 2. Timeout and logout

```bash
# Idle timeout: wait past the stated idle limit, then use the session
# Absolute timeout: sessions must die even if active (8-24h typical)
# Test server side: the cookie expiring client side is not enforcement
echo "verify server side by using the old token after the window"
```

```bash
# Logout completeness:
# 1. log out, 2. replay the old session cookie -> must be rejected
# 3. check: API tokens revoked? remember me cleared? other devices?
curl -s 'https://target.example/api/me' -H "Cookie: session=$OLD" | head -c 200
# 200 with the old cookie after logout = broken logout
```

## Edge cases

- JWTs as sessions. Then "logout" needs a denylist or short
  expiry; verify which one exists.
- SSO sessions layered under app sessions. Log out of both, and
  test each layer.
- Remember me tokens are long lived. They need rotation on use
  and theft detection to be safe.

## Escalation

- Fixation works: demonstrate with two test accounts (attacker
  plants, victim logs in) as the proof.
- No server side invalidation: the finding is architectural;
  recommend server side session stores.

## Detection and defender view

Defenders see session attacks as fixation attempts (login with
planted IDs), session reuse after logout, and concurrent session
anomalies. They defend with the cookie attributes, rotation, and
server side invalidation this skill tests, plus anomaly detection
on session use. The durable design treats sessions as credentials:
generated securely, bound to context, and revocable instantly.

## Key references

- CWE-384 (Session Fixation).
- CWE-613 (Insufficient Session Expiration).
- CWE-614 (Sensitive Cookie Without Secure Attribute).
- OWASP Session Management Cheat Sheet.
