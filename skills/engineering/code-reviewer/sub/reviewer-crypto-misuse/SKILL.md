---
name: reviewer-crypto-misuse
description: Use when reviewing cryptographic code for misuse: weak
  algorithms, bad randomness, broken TLS validation, and key management
  flaws. Covers the review checklist per crypto use, safe patterns to
  require, and when to demand a standard library. Use when reviewing
  encryption code, when auditing TLS handling, when tokens or hashes are
  custom-built, or when the code touches keys.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
parent: code-reviewer
requires: [code-reviewer]
extends: []
relates: [secure-coding, crypto-fundamentals]
tools:
  - name: Python
    version: 3.12
  - name: Bandit
    version: 1.7
---

Cryptography fails in practice through misuse, not through broken math:
ECB mode, hardcoded IVs, `random` instead of secrets, disabled cert
validation. This skill covers reviewing crypto code: the misuse checklist,
the safe patterns to require, and the rule that custom crypto gets
replaced, not fixed. When reviewing crypto, assume misuse until the code
proves otherwise.

## Quick Workflow

1. Find every crypto use: encryption, hashing, randomness, TLS, tokens.
2. For each, check the algorithm, mode, randomness source, and key
   handling against the checklist.
3. Verify TLS validation is enabled and complete.
4. Check key storage and lifecycle: generation, storage, rotation.
5. Flag custom constructions for replacement with standard libraries.
6. Write findings with the misuse, the risk, and the standard pattern.

## 1. The misuse checklist

```python
# Reviewer checklist (flag on sight):
# - ECB mode anywhere                          -> VULN (CWE-327)
# - Hardcoded key or IV                        -> VULN (CWE-321, CWE-329)
# - random module for secrets/tokens           -> VULN (use secrets)
# - MD5/SHA1 for security purposes            -> VULN (CWE-327)
# - Custom encryption construction             -> REVIEW HARD (replace)
# - verify=False / CERT_NONE in TLS            -> VULN (CWE-295)
# - Home-rolled password hashing               -> VULN (use bcrypt/argon2)

import secrets
token = secrets.token_urlsafe(32)   # SAFE randomness
# NOT: import random; random.randint(...)  # predictable

import hashlib
# Password hashing: use bcrypt/argon2, never bare SHA-256
# File integrity: SHA-256 is fine. Know which use you are reviewing.
```

```bash
# Grep the review targets:
# ECB / MODE_ECB -> flag
# verify=False / CERT_NONE / check_hostname=False -> flag
# random\.randint / random\.choice near token|key|secret -> flag
# md5( / sha1( near password|token|auth -> flag
# hardcoded hex keys: "[0-9a-f]{32,}" near key|secret|iv -> review
```

Algorithm choice is the first filter, but mode and randomness are where
most findings live. AES with ECB or a static IV is broken AES; the
algorithm name in the code means nothing without the parameters.

## 2. TLS review

```python
# What correct TLS looks like in review:
import ssl
ctx = ssl.create_default_context()  # validation ON by default
# NOT: ssl._create_unverified_context()  -> VULN
# NOT: requests.get(url, verify=False)   -> VULN

# Review checklist:
# - Certificate validation enabled (the default; flag any disable)
# - Hostname verification enabled (flag check_hostname=False)
# - Minimum TLS 1.2 (flag explicit 1.0/1.1 allowance)
# - No pinning bypass left from debugging
```

Disabled validation in production almost always started as a debugging
shortcut. Grep for it on every review; it is a five-second check that
catches a critical finding.

## 3. Key management review

```python
# Review checklist:
# - Keys generated with a CSPRNG (secrets module, not random)
# - Keys stored in the secret manager, never in code or config files
# - Keys rotatable (the rotation procedure exists and was tested)
# - Key scope minimal (one key per purpose, not one key everywhere)
# - Old keys revoked after rotation (verify the old key fails)

# Data encryption pattern to expect:
# - Unique random IV/nonce per encryption (never reused, never hardcoded)
# - Authenticated encryption (AES-GCM or ChaCha20-Poly1305, not CBC alone)
# - The nonce stored alongside the ciphertext, the key never alongside
```

Key reuse across purposes and nonce reuse with the same key are the
subtle killers: the code looks correct (AES-GCM, good library) but the
key discipline breaks the security. Review the key lifecycle, not just
the cipher.

## Edge cases

- The crypto is in a third-party library. Review the version for known
  CVEs and the configuration; the library is safe, its use may not be.
- Legacy compatibility forces weak algorithms. Document the exception,
  scope it narrowly, and plan the migration; "legacy" without a plan
  is permanent.
- The code encrypts but never decrypts (or vice versa). Dead crypto
  is a review smell: find what it was for before approving it.
- Performance drove a weak choice. Measure first; modern AEAD is fast,
  and "AES-ECB for speed" is never the answer.

## Escalation

- Custom crypto is load-bearing: do not try to fix it in review;
  require replacement with the standard construction, with a migration
  plan and tests.
- A key leaked: trigger the secret-handling leak response immediately;
  the review finding becomes an incident input.
- The team needs crypto standards: publish the approved algorithms,
  modes, and libraries as the checklist this skill implements.

## Detection and defender view

For defenders, crypto misuse is found in review and in config audits
(TLS scans, cipher suite checks), not in logs. The runtime signals are
indirect: weak TLS shows in scans, hardcoded keys show in leaks. The
defender's investment is the approved-crypto standard plus automated
checks (TLS scanning, secret scanning in CI) that enforce it without
relying on every reviewer being a cryptographer.

## Key references

- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CWE-330 (Use of Insufficiently Random Values).
- CWE-295 (Improper Certificate Validation).
- CWE-321 (Use of Hard-coded Cryptographic Key).
