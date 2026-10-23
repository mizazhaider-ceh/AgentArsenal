---
name: output-encoding
description: Use when rendering untrusted data into HTML, JavaScript,
  URLs, or other contexts and you need it neutralized correctly. Covers
  context-sensitive encoding, framework auto-escaping, and the sinks that
  bypass it. Use when fixing XSS, when reviewing templates, when building
  HTML or JS output, or when auditing where encoding is missing.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
parent: secure-coding
requires: [secure-coding]
extends: []
relates: [code-reviewer, input-validation-patterns]
tools:
  - name: Python
    version: 3.12
  - name: Bandit
    version: 1.7
---

Output encoding neutralizes untrusted data for the context it renders
in: HTML body, attribute, JavaScript, URL, or CSS each need their own
encoder. This skill covers encoding done right: matching the encoder to
the sink, using framework auto-escaping correctly, and knowing the sinks
that encoding cannot save. Encoding is the XSS fix; validation is not.

## Quick Workflow

1. Find every place untrusted data renders: templates, JS, URLs.
2. Identify the exact context of each render point.
3. Apply the context's encoder; never one encoder for all contexts.
4. Use framework auto-escaping; mark safe only with justification.
5. Audit the bypass sinks: innerHTML, eval, URL javascript:.
6. Test each render point with a hostile string.
7. Add the hostile strings as regression tests.

## 1. Contexts and encoders

```python
#!/usr/bin/env python3
"""Context-sensitive encoding: the encoder must match the sink."""
import html
import json
import urllib.parse

def encode_html_body(value: str) -> str:
    return html.escape(value, quote=True)

def encode_html_attr(value: str) -> str:
    # Attribute context: quote the attribute AND encode the value
    return html.escape(value, quote=True)

def encode_js_string(value: str) -> str:
    # JavaScript string context: JSON encoding is the safe carrier
    return json.dumps(value)

def encode_url_param(value: str) -> str:
    return urllib.parse.quote(value, safe="")

# Test string that must render harmlessly in EVERY context:
TEST = """'"<>&`=test"""
```

```html
<!-- Template examples (Jinja2 auto-escapes by default: keep it that way) -->
<p>{{ user_input }}</p>              <!-- safe: HTML-escaped -->
<a href="/u/{{ user_id }}">x</a>     <!-- safe IF user_id is validated numeric -->

<!-- DANGEROUS: do not do these -->
<div>{{ user_input | safe }}</div>  <!-- bypasses escaping: needs justification -->
<script>var x = '{{ user_input }}';</script>  <!-- wrong encoder: use tojson -->
```

The `| safe` filter and its equivalents are where XSS is born in modern
frameworks. Every use needs a comment explaining why the data is trusted,
and "it comes from our database" is not trust.

## 2. Sinks encoding cannot save

```javascript
// These sinks execute or navigate; encoding the input does not fix them:
element.innerHTML = userInput;        // use textContent instead
eval(userInput);                      // never eval untrusted data
location.href = userInput;            // validate against allow-list first
document.write(userInput);            // do not use document.write

// Safe patterns:
element.textContent = userInput;      // text, never parsed as HTML
const url = new URL(userInput, base); // then check url.origin against allow-list
```

When the sink itself is dangerous, the fix is changing the sink, not
encoding harder. `innerHTML` with encoded input is still one mistake
away from XSS; `textContent` is safe by construction.

## 3. Testing render points

```python
#!/usr/bin/env python3
"""Regression strings: every render point must neutralize these."""
PAYLOADS = [
    "<script>alert(1)</script>",
    "\"><img src=x onerror=alert(1)>",
    "';alert(1);//",
    "javascript:alert(1)",
    "<svg onload=alert(1)>",
]

def check_rendered(rendered_html: str, payload: str) -> bool:
    # The payload must not appear unencoded in executable form
    return payload not in rendered_html

for p in PAYLOADS:
    out = encode_html_body(p)
    assert check_rendered(out, p), f"LEAK: {p}"
print("All render checks passed")
```

Automate the hostile strings as tests. Manual review catches today's
misses; the regression test catches next month's refactor that
reintroduces them.

## Edge cases

- Double encoding: data encoded twice renders as entities visibly.
  Encode once, at the render point, on the raw value.
- Encoding at storage instead of render: stored-encoded data breaks
  when rendered in a second context; always encode at output.
- JSON in script blocks: use the framework's tojson filter, not manual
  quoting; `</script>` inside the string breaks naive approaches.
- CSS contexts: avoid untrusted data in style entirely; if unavoidable,
  strict allow-listing beats encoding.

## Escalation

- A render point cannot be encoded (rich text requirement): use a
  strict sanitizer (DOMPurify server-side or equivalent) with an
  allow-list, and test it against the bypass corpus.
- Legacy templates without auto-escaping: enable auto-escaping globally
  and fix the breakages explicitly rather than leaving it off.
- Third-party widgets render your data: verify their encoding behavior;
  their sink is your vulnerability.

## Detection and defender view

Missing output encoding is found by code review and by scanners, but
the durable detection is the regression test suite: hostile strings in
tests catch regressions that reviews miss. In production, CSP reports
show where encoding failed (blocked inline scripts). The engineering
view: encoding is a property of the render point, so review render
points, not data flows.

## Key references

- CWE-79 (Cross-site Scripting).
- OWASP XSS Prevention Cheat Sheet.
- OWASP DOM XSS Prevention Cheat Sheet.
