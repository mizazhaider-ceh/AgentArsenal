---
name: ecc-crypto-attacks
description: Use when assessing elliptic curve cryptography on an
  authorized engagement. Covers weak curve parameters, invalid curve
  attacks, nonce reuse in ECDSA, and implementation review. Also use
  when a product rolls its own ECC or uses unusual curves.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [crypto-fundamentals, rsa-attacks, tls-analysis]
tools:
  - name: Python
    version: 3.12
  - name: OpenSSL
    version: 3.4
---

Elliptic curve crypto is strong when the parameters and
implementation are right, and fragile when they are not: bad curves,
reused nonces, and missing point validation all break it. This skill
covers authorized assessment: checking the curve choice, testing
nonce handling, and reviewing implementations. It is analysis and
review, not breaking standard curves.

## Quick Workflow

1. Identify every use of ECC: key exchange, signatures, and the
   curves named.
2. Check the curve: standard (P-256, Curve25519) vs custom
   parameters.
3. Validate the parameters of any custom curve: order, cofactor,
   and twist security.
4. Test ECDSA nonce handling: reuse or bias leaks the private key.
5. Check point validation: does the code reject invalid points.
6. Review the implementation: constant time, blinding, and RNG.
7. Check the protocol use: signatures verified, keys validated.
8. Report with the specific parameter or code flaw.

## 1. Curve parameter review

```bash
# List the curves and code paths in use
grep -rn "secp256\|P-256\|curve25519\|ed25519\|secp256k1\|prime256v1" \
  --include="*.py" --include="*.c" --include="*.js" src/ | head -20
# Custom curve definitions need full parameter validation
openssl ecparam -list_curves | head -20
```

```python
#!/usr/bin/env python3
"""ECDSA nonce reuse demo: two signatures, same nonce -> key recovery."""
# s1 = k^-1 (h1 + d*r), s2 = k^-1 (h2 + d*r)  =>  solve for k, then d
# This is why RFC 6979 deterministic nonces exist: randomness failures
# must not leak the key.
print("check: does signing use RFC 6979 or a CSPRNG per signature?")
print("test (lab): sign the same message twice; identical r twice with")
print("different messages under one key = nonce reuse, key recoverable")
```

## 2. Invalid curve attack concept

```bash
# If the implementation does not validate that received points are on
# the correct curve, an attacker sends points on a weak twist curve
# and learns the private key bit by bit from the results.
# Review: does the code call the point validation routine before ECDH?
grep -rn "validate\|on_curve\|is_on_curve" ecc_src/ -i | head -10
# Missing validation on attacker supplied points = the finding
```

## Edge cases

- The library is well known (OpenSSL, libsodium). Focus on how the
  product uses it, not the library internals.
- Custom curves for "performance". Demand the parameter
  generation story; unexplained custom curves are suspect.
- Hybrid post quantum plus ECC. Review both halves; the migration
  is where mistakes happen.

## Escalation

- Nonce reuse confirmed in a lab build: this recovers keys;
  demonstrate on test keys, then report as critical.
- Invalid curve possible: prove with a test harness on lab keys
  before reporting.

## Detection and defender view

ECC misuse is found by review, not monitoring: parameter audits,
nonce uniqueness tests, and validation checks. Defenders standardize
on vetted curves (P-256, Ed25519, X25519), use audited libraries,
and test signatures against known answer vectors. The durable rule
is never roll your own curve or your own ECDSA nonce logic.

## Key references

- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CWE-330 (Use of Insufficiently Random Values): nonce issues.
- RFC 6979 (deterministic ECDSA), RFC 7748 (X25519/Ed25519).
