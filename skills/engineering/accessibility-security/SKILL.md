---
name: accessibility-security
description: Use when reviewing the intersection of accessibility and
  security in web applications. Covers how assistive tech interacts
  with security controls, CAPTCHA alternatives, and avoiding
  accessibility versus security tradeoffs. Also use when a CAPTCHA or
  MFA flow blocks users with disabilities.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding, auth-attacks, webapp-pentest-methodology]
tools:
  - name: Python
    version: 3.12
---

Security controls often break accessibility: visual CAPTCHAs block
blind users, timeouts punish slow input, and MFA apps assume a
smartphone. This skill covers designing controls that are both secure
and usable: accessible alternatives, honest tradeoff analysis, and
testing with assistive technology. Security that excludes people is
broken security.

## Quick Workflow

1. Inventory the security controls in the user journey: login,
   CAPTCHA, MFA, timeouts, and verification steps.
2. Test each with a screen reader and keyboard only: what breaks.
3. Replace exclusionary controls: invisible risk scoring instead of
   visual CAPTCHAs, multiple MFA options.
4. Check timeouts: extend or warn, especially on security sensitive
   forms.
5. Verify error messages: specific enough to act on, not so
   specific they leak (balance with auth-attacks guidance).
6. Test the alternatives adversarially: the accessible path must be
   as strong as the main path.
7. Document the choices: which standard each control meets.
8. Include assistive tech in the security test plan permanently.

## 1. Control review

```bash
# Journey audit checklist:
# - login: screen reader announces fields and errors correctly?
# - CAPTCHA: is there a non visual alternative? is it equally strong?
# - MFA: options beyond app push (SMS, hardware key, codes)?
# - session timeout: warning before expiry? easy re auth?
# - password rules: announced clearly? paste allowed in the field?
echo "test with: keyboard only, screen reader, 200% zoom, voice control"
```

```bash
# CAPTCHA alternative assessment (authorized test):
# - risk based (invisible) scoring: test the fallback when score is low
# - honeypot fields: accessible (screen readers must skip them properly)
# - proof of work challenges: do they work with assistive tech?
# Rule: the fallback path gets the same adversarial testing as the main path
echo "attackers use the accessible fallback; test it like an attacker would"
```

## 2. Balanced error messages

```bash
# The classic tension: "invalid password" (secure, vague) vs
# "no account with this email" (usable, enumerates).
# Resolution: keep login vague, but make recovery and signup flows
# clear; document the decision and its reasoning.
echo "decide per flow, document it, and apply consistently"
```

## Edge cases

- Regulations require both (WCAG plus security standards). Map
  each control to both and resolve conflicts explicitly.
- The accessible alternative is weaker. Then strengthen it or add
  compensating controls; do not ship the weak path silently.
- Third party widgets (CAPTCHA providers) are the blocker. Choose
  vendors with real accessibility commitments.

## Escalation

- Fundamental conflict found: bring product, security, and
  accessibility together; the tradeoff is a product decision with
  legal input.

## Detection and defender view

Attackers exploit accessibility features too: they abuse the
"accessible" fallback as the weaker path. Defenders monitor the
fallback usage rate; a spike means abuse, not inclusion. The
durable design makes the accessible path a first class citizen:
same strength, tested the same way, monitored the same way.

## Key references

- WCAG 2.2: accessibility standard.
- W3C guidance on accessible authentication.
- Related skills: auth-attacks, secure-coding.
