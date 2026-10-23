---
name: input-validation-patterns
description: Use when writing or reviewing code that accepts user input
  and you need validation done right. Covers allow-list versus block-list
  validation, type and range checks, canonicalization, and validation
  placement. Use when building forms or APIs, when fixing injection flaws,
  when the code trusts client input, or when setting the team's validation
  standard.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
parent: secure-coding
requires: [secure-coding]
extends: []
relates: [code-reviewer, output-encoding]
tools:
  - name: Python
    version: 3.12
  - name: Bandit
    version: 1.7
---

Input validation is the first defensive layer: decide what is allowed,
reject everything else, and do it on the server. This skill covers the
validation patterns that actually work: allow-lists, strict typing,
canonicalization before checks, and validating at the trust boundary.
Validation is necessary but not sufficient; it reduces attack surface,
while output encoding and parameterized queries do the real neutralizing.

## Quick Workflow

1. Identify every trust boundary: where untrusted data enters.
2. Define the allow-list for each input: type, range, format, length.
3. Validate on the server; treat client validation as UX only.
4. Canonicalize before validating (decode, normalize, then check).
5. Reject invalid input loudly; do not silently fix it.
6. Log validation failures for attack detection.
7. Test the validation with hostile inputs, not just happy paths.

## 1. Allow-list patterns

```python
#!/usr/bin/env python3
"""Allow-list validation patterns: the correct default."""
import re
from urllib.parse import urlparse

def valid_username(value: str) -> bool:
    # Allow-list: what IS a username, nothing else
    return bool(re.fullmatch(r"[a-z0-9_]{3,20}", value))

def valid_age(value) -> bool:
    # Type and range, not just presence
    return isinstance(value, int) and 0 <= value <= 150

def safe_redirect(target: str) -> bool:
    # Open redirect defense: allow-list the destinations
    allowed = {"app.example.com", "www.example.com"}
    parts = urlparse(target)
    return not parts.netloc or parts.netloc in allowed

# Block-list (fragile, avoid):
#   if "<script>" not in value:  # bypassed by <ScRiPt>, encoding, ...
```

Allow-list validation fails closed: new attack techniques are rejected
by default because they were never allowed. Block-lists fail open: every
technique the author did not think of passes through.

## 2. Canonicalization

```python
#!/usr/bin/env python3
"""Validate AFTER decoding and normalizing, never before."""
import html
import unicodedata
from urllib.parse import unquote

def canonical(value: str) -> str:
    # Decode repeatedly: %253C is %3C after one decode, < after two
    prev = None
    cur = value
    while prev != cur:
        prev = cur
        cur = unquote(cur)
    # Normalize unicode: fullwidth and lookalikes collapse here
    cur = unicodedata.normalize("NFKC", cur)
    return cur

def valid_path_segment(value: str) -> bool:
    c = canonical(value)
    # Now the check sees what the filesystem will see
    return bool(re.fullmatch(r"[a-z0-9_.-]{1,64}", c)) and ".." not in c
```

Validating before canonicalization is the classic bypass: the check sees
`%2e%2e%2f` and the filesystem sees `../`. Decode fully, normalize, then
validate the result.

## 3. Placement and failure handling

```python
#!/usr/bin/env python3
"""Validate at the trust boundary, fail loudly."""

def create_user(request_data: dict):
    username = request_data.get("username", "")
    if not valid_username(username):
        # Loud rejection: log it, return 400, do not guess intent
        log_validation_failure("username", username)
        raise ValueError("Invalid username")
    # ... proceed with the KNOWN-GOOD value, not the raw input
    return store_user(username)

# Rules:
# - Validate at the server trust boundary (API handler, not the client)
# - Re-validate at security-critical sinks (the query, the shell call)
# - Never "sanitize and continue": stripped input is still attacker input
```

Defense in depth means the sink validates too: the database layer uses
parameterized queries regardless of what the API validated, because
validation is one layer and layers fail independently.

## Edge cases

- Validation is duplicated across client and server and they disagree.
  The server is the authority; the client is convenience. Test the
  server alone.
- Legitimate input needs rich content (names with apostrophes,
  international text). Widen the allow-list deliberately with tests,
  never by disabling validation.
- File uploads need validation. Check extension, magic bytes, size,
  and content type independently; any one alone is bypassable.
- Validation performance matters at scale. Compile regexes once,
  keep checks O(n), and never let validation become a ReDoS vector
  (avoid nested quantifiers in the patterns).

## Escalation

- The input cannot be allow-listed (free text fields): validate length
  and encoding, then rely on output encoding and parameterized sinks;
  document that validation is partial here by design.
- A validation bypass is found: fix the canonicalization order first,
  then the pattern; add the bypass as a regression test.
- Team standard needed: publish the allow-list patterns as shared
  validators, not copy-pasted regexes.

## Detection and defender view

Validation failures are detection signal: log them with the input
(truncated), the rule violated, and the source. A burst of failures
from one source is an attack in progress; a steady trickle is normal
user error. Alert on the bursts. The engineering view: validation
moves attacks from "exploited" to "logged and rejected," which is the
whole point.

## Key references

- CWE-20 (Improper Input Validation).
- OWASP Input Validation Cheat Sheet.
- OWASP Testing Guide: input validation sections.
