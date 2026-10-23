---
name: session-hijacking
description: "Use when testing session management weaknesses on an authorized engagement: stealing, fixing, or predicting session tokens. Covers cookie attribute review, session fixation testing, token entropy analysis, and logout and expiry behavior. Use when assessing login and session handling, when cookies lack flags, when testing single sign-on flows, or when you need to prove that a stolen token grants access."
version: 1.0.0
domain: auth
lifecycle: stable
last_verified: 2026-10-23
parent: auth-attacks
requires: [auth-attacks]
extends: []
relates: [web-xss, password-attacks]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
---
Session hijacking takes over a user's authenticated state by stealing or
fixing their session token. This skill covers testing session management on
authorized engagements: reviewing cookie security, attempting fixation,
analyzing token randomness, and verifying logout actually kills the
session. It pairs naturally with XSS (the usual theft vector) but stands
alone as a session-layer assessment. Only test with accounts provided for
the engagement.

## Quick Workflow

1. Log in with a test account and capture every cookie and token.
2. Review cookie attributes: Secure, HttpOnly, SameSite, Path, expiry.
3. Test session fixation: plant a token before login, check it after.
4. Analyze token entropy across several logins.
5. Test logout, expiry, and concurrent session behavior.
6. Prove the impact by replaying a token in a clean session where allowed.
7. Record every behavior with request and response evidence.

## 1. Cookie review

```bash
# Capture the full Set-Cookie headers at login
curl -s -D /tmp/login_hdrs.txt -o /dev/null -X POST \
  'https://target.example/login' -d 'username=test&password=Test123!'
grep -i '^set-cookie' /tmp/login_hdrs.txt

# Checklist per cookie:
# Secure: present (HTTPS only) ............ required
# HttpOnly: present (no JS access) ........ required for session cookies
# SameSite: Lax or Strict ................. required against CSRF
# __Host- prefix: present ................. best practice
# Expiry: session or short-lived .......... no year-long sessions

# Replay the session cookie in a clean context to prove it works alone
curl -s 'https://target.example/account' \
  -H 'Cookie: session=abc123def456' | grep -i 'welcome\|dashboard' | head -2
```

A session cookie without HttpOnly is stealable by any XSS; without
Secure it leaks over HTTP; without SameSite it rides CSRF requests. Each
missing flag is a concrete, reportable weakness.

## 2. Fixation testing

```bash
# Step 1: get a session token WITHOUT logging in
curl -s -D /tmp/pre.txt -o /dev/null 'https://target.example/login'
grep -i '^set-cookie' /tmp/pre.txt

# Step 2: log in using that pre-login cookie jar
curl -s -b /tmp/pre_cookies.txt -c /tmp/post_cookies.txt -X POST \
  'https://target.example/login' -d 'username=test&password=Test123!' -o /dev/null

# Step 3: compare. If the session token is unchanged after login,
# fixation is possible: an attacker who plants the token owns the session
diff <(grep -i session /tmp/pre_cookies.txt) <(grep -i session /tmp/post_cookies.txt) \
  && echo "TOKEN UNCHANGED: fixation likely"
```

Also test the URL: if the application accepts `?session=...` in links,
tokens leak through referrers and logs, which is a finding on its own.

## 3. Token entropy and lifecycle

```bash
# Collect session tokens across fresh logins and eyeball the structure
for i in 1 2 3 4 5; do
  curl -s -D - -o /dev/null -X POST 'https://target.example/login' \
    -d 'username=test&password=Test123!' | grep -i '^set-cookie: session='
done

# Short, sequential, or timestamp-based tokens are predictable;
# 128+ bits of randomness in base64/hex is the bar

# Logout test: the token must die server-side, not just in the browser
curl -s -X POST 'https://target.example/logout' -b /tmp/post_cookies.txt -o /dev/null
curl -s 'https://target.example/account' -b /tmp/post_cookies.txt \
  | grep -c -i 'welcome'  # must be 0 after logout
```

Test idle timeout and absolute timeout with the test account: leave the
session idle past the stated limit and confirm the server rejects it, not
just the client.

## Edge cases

- The app uses JWTs instead of cookies. Decode the token, check the
  algorithm (`none` is the classic flaw), expiry, and whether the server
  validates the signature at all.
- Sessions are tied to IP or User-Agent. Note the binding; it mitigates
  theft but breaks legitimate roaming, so report the tradeoff.
- Logout kills the cookie client-side only. Replaying the old token after
  logout proves the server-side flaw; this is a common and serious miss.
- Remember-me tokens are long-lived. Review their entropy and theft
  impact separately; a year-long token is a year-long vulnerability.

## Escalation

- You need theft impact proof: with permission, demonstrate reading the
  cookie via the confirmed XSS and replaying it; stop at proof of
  access, and use only test accounts.
- Token prediction looks possible: collect a larger sample, analyze with
  a script, and only claim predictability with statistical evidence.
- SSO or OAuth is in play: test the session layer of the relying party
  and the token handling of the flow separately.

## Detection and defender view

Defenders see hijacking as sessions used from unusual IPs or devices,
impossible-travel logins, and concurrent sessions from distant locations.
Fixation shows as pre-login tokens that become authenticated. Defenses are
rotating session IDs at login, strong cookie flags, short timeouts with
server-side invalidation, binding sessions to device fingerprints where
appropriate, and alerting on anomalous session use.

## Key references

- MITRE ATT&CK T1539 (Steal Web Session Cookie).
- MITRE ATT&CK T1606.001 (Forge Web Credentials: Web Cookies).
- CWE-384 (Session Fixation).
- CWE-613 (Insufficient Session Expiration).
- CWE-614 (Sensitive Cookie in HTTPS Session Without Secure Attribute).
- OWASP Testing Guide: Session Management Testing.
