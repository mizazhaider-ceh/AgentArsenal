---
name: reviewer-auth-flaws
description: Use when reviewing authentication and authorization code for
  logic flaws. Covers password handling review, session management
  review, MFA implementation review, and access control logic review. Use
  when reviewing login flows, when auditing session code, when the
  password reset flow changed, or when checking that authz matches the
  intended policy.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
parent: code-reviewer
requires: [code-reviewer]
extends: []
relates: [secure-coding, auth-attacks]
tools:
  - name: Python
    version: 3.12
  - name: Bandit
    version: 1.7
---

Authentication code is where logic flaws hide: the password check that
compares wrong, the session that never expires, the reset token that
never expires either. This skill covers reviewing auth code: password
handling, session management, MFA, and the authorization logic around
them. Read auth code slowly; the flaws are in the branches, not the
happy path.

## Quick Workflow

1. Map the auth flows: login, logout, reset, MFA, session refresh.
2. Review password handling: hashing, comparison, policies.
3. Review session management: creation, rotation, expiry, invalidation.
4. Review MFA: enrollment, verification, recovery, bypass paths.
5. Review authorization around every authenticated endpoint.
6. Check the failure paths: what happens on every error branch.
7. Write findings with the flow, the flaw, and the fix.

## 1. Password handling review

```python
# Review checklist for password code:
# - Hashing: bcrypt/argon2/scrypt with proper cost, NEVER md5/sha1/sha256 alone
# - Comparison: constant-time compare for hashes and tokens
# - No plaintext: passwords never logged, never in error messages
# - Policy: length-focused, breached-password check, no composition theater

import hmac
# Constant-time token comparison (review for == on secrets: VULN)
if not hmac.compare_digest(provided_token, expected_token):
    raise Unauthorized()

# Password verification pattern to expect:
# verify(password, stored_hash) with the library's verify, not re-hashing
# and string-comparing
```

```bash
# Grep the review targets:
# md5( / sha1( near password -> VULN
# == token / == password -> REVIEW (timing)
# log.*password / print.*password -> VULN
```

Timing attacks on string comparison are real for tokens; `hmac.compare_digest`
is the fix and it costs nothing. Passwords get the slow hash; tokens get
the constant-time compare.

## 2. Session review

```python
# Review checklist for session code:
# - Rotation: new session id at login (fixation defense)
# - Expiry: idle timeout AND absolute timeout, enforced server-side
# - Invalidation: logout destroys the server-side session, not just the cookie
# - Cookie flags: Secure, HttpOnly, SameSite set on session cookies
# - No sensitive data in the session payload itself (JWT claims minimal)

# Patterns to flag:
# session["user_id"] = user.id   # then never rotated -> REVIEW
# def logout(): response.delete_cookie("session")  # client-only -> VULN
```

Read the logout function completely: the most common session flaw is
logout that clears the browser but leaves the server session valid.
Then read the "remember me" implementation with the same suspicion;
long-lived tokens need the same rotation and invalidation discipline.

## 3. MFA and reset review

```python
# MFA review checklist:
# - Server enforces the MFA step (no client-side "mfa_done" flag)
# - Codes: short lifetime, single use, strict attempt limits
# - Recovery codes: single use, shown once, hashed in storage
# - Enrollment: requires re-authentication, not just a session
# - No downgrade: SMS fallback does not bypass the primary silently

# Reset review checklist:
# - Tokens: random, single use, short expiry (15-60 min)
# - Delivered to the verified channel only
# - Using the token does not leak validity (uniform responses)
# - Password change invalidates existing sessions
```

Trace the MFA flow for the skip: after the password step, can the
attacker request an authenticated page directly? The code that says
"require MFA" must run on every protected handler, not just in the
login controller.

## Edge cases

- The auth library handles it. Verify the library is configured
  correctly (cost factors, timeouts); libraries with bad configs are
  the common case.
- Legacy auth code coexists with the new flow. Review both; attackers
  use the weaker one.
- The flaw needs chaining (auth bypass plus something else). Note the
  dependency; the finding stands but the severity reflects the chain.
- Tests cover the happy path only. Require failure-path tests as part
  of the fix.

## Escalation

- Systemic auth weakness (custom crypto, homegrown sessions):
  recommend replacing with the standard library/framework, with the
  instance list as the business case.
- A flaw is found in production auth: treat it as an incident input
  (check logs for exploitation) alongside the code fix.
- The team needs the patterns: turn the review findings into the
  team's auth checklist for future reviews.

## Detection and defender view

For defenders, auth code review is the highest-leverage review time:
auth flaws become account takeovers, the most damaging common finding.
Complement review with auth-focused DAST (the auth-attacks skill set)
against staging. Log auth decisions verbosely; the logs are both the
debugging tool and the incident evidence.

## Key references

- CWE-287 (Improper Authentication).
- CWE-384 (Session Fixation).
- CWE-307 (Improper Restriction of Excessive Authentication Attempts).
- OWASP Authentication Cheat Sheet.
