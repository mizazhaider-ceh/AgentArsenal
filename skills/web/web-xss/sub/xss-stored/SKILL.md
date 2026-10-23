---
name: xss-stored
description: Use when testing for stored cross-site scripting on an
  authorized engagement, where attacker input is saved and later rendered to
  other users. Covers storage point discovery, payload persistence through
  validation, finding every render location including admin panels and
  exports, and impact assessment. Use when comments, profiles, tickets,
  usernames, or file metadata persist input, when you need to trace where
  stored data renders, or when assessing worm or account-takeover potential.
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

Stored cross-site scripting is the most dangerous XSS class because the
payload lives in the application and fires for every user who views the
infected data, with no crafted link needed. This skill covers the stored
XSS methodology on authorized tests: finding storage points, getting
payloads past input validation, hunting every render location, and judging
impact honestly. Because stored payloads affect other users, this sub-skill
carries extra care rules: benign payloads only, cleanup after the test, and
no real session theft without explicit permission.

## Quick Workflow

1. Inventory every place the application stores user input: comments,
   profiles, tickets, usernames, file names, rich text fields.
2. Store a unique canary at each point and note exactly what was accepted.
3. Visit every page that might render the stored data, including admin
   panels, exports, emails, and PDFs.
4. Classify the render context at each location and craft the breakout.
5. Prove execution with a harmless marker payload.
6. Assess blast radius: which roles view the data, and how often.
7. Delete every test payload and confirm cleanup.

## 1. Storage point discovery

```bash
# Store canaries with distinct markers per field
curl -s -X POST 'https://target.example/comment' \
  -b session.txt -d 'post=1&text=storedAAA111'
curl -s -X POST 'https://target.example/profile' \
  -b session.txt -d 'displayname=storedBBB222&bio=hello'

# File name storage: upload with a canary file name
curl -s -X POST 'https://target.example/upload' \
  -b session.txt -F 'file=@/tmp/x.txt;filename="storedCCC333.txt"'

# Check what the application kept: fetch your own profile and content
curl -s 'https://target.example/profile/me' -b session.txt \
  | grep -o '.\{30\}\(storedAAA111\|storedBBB222\).\{30\}'
```

Note transformations: truncation, case changes, stripped tags, encoded
characters. The stored form, not your submitted form, is what you must break
out of.

## 2. Getting payloads to persist

Validation often differs between storage and rendering. Probe both.

```bash
# If <script> is stripped at storage, try event handlers
# Stored bio: "><svg onload=console.log('stored')>

# If quotes are stripped, try quote-free vectors
# <svg/onload=console.log(1)>

# Length limits: check the stored length, then fit the vector
# <img src=x onerror=console.log(1)> is 32 chars

# Multi-field: the vulnerable field may not be the obvious one
# (author name reflected in the comment list, not the comment body)
```

Rich text editors are prime targets: they must allow some HTML, and their
allow-lists are often wrong. Test `style` attributes, `data:` URIs, SVG, and
MathML elements one at a time.

## 3. Hunting render locations

The payload may render far from where it was stored. Crawl as the roles that
would see it.

```bash
# As a second test user, visit content lists, profiles, search results
curl -s 'https://target.example/users' -b victim.txt | grep -o '.\{30\}storedBBB222.\{30\}'

# Admin panel render (use a test admin account provided for the engagement)
curl -s 'https://target.example/admin/users' -b admin.txt | grep -c 'storedBBB222'

# Exports: CSV, PDF, and email digests render stored data too
curl -s 'https://target.example/admin/export.csv' -b admin.txt | grep 'storedBBB222'
```

Stored XSS in an admin panel is typically the highest-impact finding in a
web test: it can lead to full administrative takeover. Document which roles
render the payload and whether any approval workflow stands in between.

## Edge cases

- The payload fires for you but not for others. Caching, role-specific
  rendering, or approval queues may hide it; test with a clean second
  account in each role.
- The application sanitizes on render, not on store. Your stored canary
  looks raw in the database but safe on the page; test the render path,
  because sanitizer differences between pages are common.
- The payload persists in exports or emails you cannot easily view. Ask
  the test lead for a safe way to trigger and inspect them, or note the
  suspected sink as unconfirmed.
- Rate limits or moderation queues delay storage. Wait for the queue, or
  use a test account with moderation rights if the engagement provides
  one.

## Escalation

- No render location executes the payload: re-examine the exact stored
  bytes (view source, check for double encoding) before declaring it
  safe; sanitizers that encode once but render twice are a classic miss.
- You need to prove admin-panel impact: with permission, use a harmless
  title-change marker in the admin session and screenshot it; never take
  over the real admin session or plant persistence.
- Cleanup is uncertain: list every payload location in your notes and
  verify deletion by re-fetching each page; report any payload you could
  not remove to the test lead immediately.
- The finding enables a worm (payload spreads itself): describe the worm
  scenario in the report, do not build or release a self-spreading
  payload, even on a test environment, without explicit written approval.

## Detection and defender view

Defenders see stored XSS as persistent malicious content in their database,
often found by users reporting strange behavior or by content scans. The
attacker's setup requests look like normal content creation with odd
strings. Durable defense is output encoding at every render point (not just
input filtering at storage), a strict sanitizer such as DOMPurify for rich
text, Content Security Policy to blunt successful injections, and admin
panels treated as high-trust render surfaces with extra review.

## Key references

- MITRE ATT&CK T1189 (Drive-by Compromise).
- CWE-79 (Improper Neutralization of Input During Web Page Generation,
  Cross-site Scripting).
- OWASP Testing Guide: Testing for Stored Cross Site Scripting
  (OTG-INPVAL-002).
- OWASP XSS Prevention Cheat Sheet.
- PortSwigger Web Security Academy: Stored XSS labs.
