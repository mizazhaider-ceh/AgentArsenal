---
name: api-rate-limit-bypass
description: Use when testing API rate limits on an authorized
  assessment. Covers limit discovery, header and IP spoofing bypasses,
  endpoint and method variations, and distinguishing real enforcement
  from cosmetic headers. Also use when a client believes their API is
  protected against abuse or credential stuffing.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [api-security-testing, auth-attacks, password-attacks]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
---

Rate limits are supposed to stop brute force and abuse, but many are
keyed on spoofable values or applied inconsistently. This skill covers
authorized testing: finding the real limit, trying the standard
bypass families, and proving whether the limit actually protects the
endpoint. Stay inside the agreed request budget; bypassing a limit
does not authorize ignoring the scope's request caps.

## Quick Workflow

1. Find the limit: send requests until you see 429 or a slowdown, and
   read the limit headers.
2. Identify the key: IP, API key, user account, or endpoint.
3. Try header spoofing: X-Forwarded-For and friends, if the key is IP
   based.
4. Try endpoint variations: case, trailing slash, and versioned paths
   that may miss the limiter.
5. Try method and auth variations: unauthenticated vs authenticated
   paths to the same resource.
6. Measure the real throughput after each bypass attempt.
7. Confirm the security impact: what does unlimited access enable
   (brute force, scraping, enumeration).
8. Report the bypass with the exact requests and the achieved rate.

## 1. Limit discovery

```bash
# Find the limit and the key it uses
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    'https://target.example/api/login-attempt')
  echo -n "$code "
  [ $((i % 20)) -eq 0 ] && echo
done
echo
# Note where 429s start; also capture the limit headers once
curl -s -i 'https://target.example/api/login-attempt' \
  -H "Authorization: Bearer $TOKEN" | grep -i -E "ratelimit|retry-after|x-rate" | head
```

## 2. Bypass families

```python
#!/usr/bin/env python3
"""Rate limit bypass prober (stays within the agreed test budget)."""
import urllib.request

URL = "https://target.example/api/login-attempt"
BASE_HEADERS = {"Authorization": "Bearer TEST_TOKEN"}

def count(headers, n=25):
    ok = limited = 0
    for _ in range(n):
        req = urllib.request.Request(URL, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                ok += 1 if r.status == 200 else 0
        except Exception as e:  # noqa: BLE001
            if "429" in str(e):
                limited += 1
    return ok, limited

# Baseline
print("baseline:", count(BASE_HEADERS))
# X-Forwarded-For rotation (only valid if the app trusts the header)
for i in range(3):
    h = dict(BASE_HEADERS)
    h["X-Forwarded-For"] = f"10.9.0.{10 + i}"
    print(f"xff 10.9.0.{10 + i}:", count(h))
```

```bash
# Endpoint variations that often escape the limiter
for path in "/api/login-attempt" "/api/login-attempt/" "/API/login-attempt" \
            "/api//login-attempt" "/api/v2/login-attempt"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" "https://target.example$path")
  echo "$path -> $code"
done
```

## Edge cases

- The limit is global, not per key. Header tricks fail; test whether
  the global bucket is shared across tenants (worse finding).
- 429s come from a CDN, not the app. The app itself may have no
  limit; test the origin directly if in scope.
- The limit uses a sliding window. Short bursts pass; sustained
  abuse is what you are really testing, so measure over minutes.
- Your test IP gets blocked entirely. Rotate to the backup test IP
  in the scope, or ask for allowlisting.

## Escalation

- Header spoofing works: the limit is decorative; demonstrate the
  brute force or enumeration it was meant to stop, within budget.
- Endpoint variation works: the fix is normalizing paths before the
  limiter, plus tests for each variation.
- Nothing bypasses: verify the limit actually triggers under
  realistic abuse (distributed sources if the scope allows).

## Detection and defender view

Defenders see bypass attempts as X-Forwarded-For rotation, many 404s
or path variations probing for unprotected routes, and traffic that
ignores 429 backoff. Detect with alerts on header spoofing patterns
and on clients that never back off. The durable fix keys limits on
unspoofable values (authenticated user, API key), normalizes paths
before limiting, and treats the CDN limit as one layer, not the
whole defense.

## Key references

- CWE-770 (Allocation of Resources Without Limits).
- CWE-307 (Improper Restriction of Excessive Authentication Attempts).
- OWASP API Security Top 10: API4 Unrestricted Resource Consumption.
