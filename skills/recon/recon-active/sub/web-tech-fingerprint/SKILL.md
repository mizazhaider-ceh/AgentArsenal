---
name: web-tech-fingerprint
description: Use when you need to identify the technologies behind web
  targets during authorized active reconnaissance. Covers header and cookie
  analysis, framework and CMS detection, JavaScript library inventory with
  version checks against known CVEs, and WAF identification. Use when
  scoping web testing, when prioritizing targets by technology risk, when
  choosing version-specific exploits, or when mapping the application stack
  before web-sqli and web-xss phases.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
parent: recon-active
requires: [recon-active]
extends: []
relates: [web-sqli, web-xss, api-security-testing]
tools:
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
  - name: nmap
    version: 7.98
---

Web technology fingerprinting identifies the stack behind an HTTP service:
server, framework, CMS, JavaScript libraries, and protective layers. This
skill covers authorized fingerprinting through headers, cookies, page
content, and behavior, plus mapping library versions to known
vulnerabilities. It is read-only recon: no exploitation, just inventory
that tells the web testing phases where to aim.

## Quick Workflow

1. Fetch headers, cookies, and the landing page for each web target.
2. Identify the server, framework, and CMS from headers and page markers.
3. Inventory JavaScript libraries and record exact versions.
4. Check versions against known CVEs to prioritize targets.
5. Detect WAFs, CDNs, and bot protection that will shape later testing.
6. Write the per-target technology profile with confidence notes.

## 1. Headers, cookies, and page markers

```bash
# Full header and cookie capture
curl -s -D /tmp/headers.txt -o /tmp/index.html https://target.example/
cat /tmp/headers.txt

# Framework cookies are loud: PHPSESSID, JSESSIONID, ASP.NET_SessionId
grep -i '^set-cookie' /tmp/headers.txt

# Page markers: generator tags, framework paths, comments
grep -i -o '.\{0,60\}generator.\{0,60\}' /tmp/index.html | head -5
grep -o 'wp-content[^"]*' /tmp/index.html | head -5
grep -o '/static/[^"]*\.js' /tmp/index.html | head -10

# Error pages leak stack details; request a bad URL
curl -s https://target.example/this-page-cannot-exist-123 | head -30
```

Server headers lie sometimes (admins spoof them), so treat headers as one
vote and corroborate with cookies and page content before finalizing the
profile.

## 2. JavaScript library inventory

```bash
# Extract script URLs and look for version strings
grep -o 'src="[^"]*\.js[^"]*"' /tmp/index.html | head -20
for js in jquery bootstrap vue react angular; do
  echo "== $js =="
  grep -i -o "$js[^\"']*" /tmp/index.html | head -3
done

# Fetch a library file and read its header comment for the version
curl -s https://target.example/static/js/jquery.min.js | head -5

# Quick CVE relevance check pattern (manual; verify before reporting)
# jquery 1.x/2.x -> check for known CVEs; bootstrap < 4 -> check;
# outdated moment.js, lodash -> check prototype pollution history
```

An outdated jQuery on a login page is a prioritization signal, not a
finding by itself. Record the version, check it against a CVE source, and
let the web phases decide whether it is exploitable in context.

## 3. WAF and CDN detection

```bash
# WAF-indicating headers and cookies
grep -i -E 'x-sucuri|__cf_bm|_abck|bm_sz|incap_ses|_dd_s' /tmp/headers.txt

# Behavior test: send a benign attack-like string and watch the response
curl -s -o /dev/null -w '%{http_code}\n' \
  "https://target.example/search?q=<script>alert(1)</script>"
# 403 with a WAF-branded body names the product; compare with baseline

# CDN detection via headers and IP ownership
grep -i -E 'x-cache|cf-ray|via:|x-amz-cf' /tmp/headers.txt
```

Knowing the WAF product before testing saves hours: each product has known
bypass families, and the test plan should account for them from the start
rather than discovering the block mid-engagement.

## Edge cases

- The site is a single-page app with an empty initial HTML. Render it
  (browser or headless fetch) before fingerprinting; the real technology
  lives in the JavaScript bundle.
- Headers are stripped by the CDN. Fall back to content markers, TLS
  certificate details, and behavior probes.
- Multiple technologies stack (WordPress behind Cloudflare with a React
  frontend). Profile each layer separately instead of picking one label.
- Version strings are removed or faked. Use behavior and file hashes
  against known releases when strings cannot be trusted.

## Escalation

- You need certainty for exploit selection: download the exact library
  file, hash it, and compare against the vendor's release hashes.
- The engagement is WAF-heavy: document the WAF on every target up front
  so the web phases plan bypass work into their time budget.
- Fingerprinting must stay quiet: stick to the landing page and headers,
  skip aggressive probing, and accept lower confidence.

## Detection and defender view

Defenders see tech fingerprinting as normal-looking web requests with
security-tool User-Agents or odd header combinations, plus 404 probes for
CMS paths (`/wp-admin`, `/phpinfo.php`). It blends with regular traffic,
which is why it is hard to alert on reliably. Defenses are header
minimization, removing version strings and generator tags, and keeping
everything patched so fingerprinting finds nothing actionable.

## Key references

- MITRE ATT&CK T1592 (Gather Victim Host Information).
- OWASP Testing Guide: Fingerprint Web Server (OTG-INFO-002).
- OWASP Testing Guide: Fingerprint Web Application Framework.
- Wappalyzer technology database (technique reference).
