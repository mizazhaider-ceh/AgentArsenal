---
name: rsa-small-exponent
description: Use when RSA uses a small public or private exponent and
  you need to assess exploitability on an authorized engagement or CTF.
  Covers e=3 broadcast and related-message attacks, Wiener's attack
  concepts for small d, and the Hastad broadcast scenario. Use when the
  public exponent is tiny, when the same message went to multiple keys,
  or when the private exponent may be small.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
parent: rsa-attacks
requires: [rsa-attacks]
extends: []
relates: [crypto-fundamentals, rsa-common-mistakes]
tools:
  - name: Python
    version: 3.12
  - name: OpenSSL
    version: 3.0
---

Small exponents create specific, well-understood RSA breaks: e=3 with
unpadded messages falls to cube roots and broadcast attacks, and tiny
private exponents fall to Wiener's attack. This skill covers assessing
and exploiting small-exponent RSA on authorized engagements and in CTFs:
recognizing the conditions, running the standard attacks, and knowing
when the exponent is actually fine (proper padding saves e=3).

## Quick Workflow

1. Read e from the public key; note if it is 3 or otherwise small.
2. Check the padding: textbook (attackable) versus OAEP (safe).
3. For e=3 textbook: try the cube-root attack on each ciphertext.
4. For broadcast scenarios: collect ciphertexts of the same message
   under different moduli and apply Hastad.
5. For small d suspicion: check Wiener's conditions.
6. Verify every recovery by decrypting or by the padding structure.

## 1. Cube-root and broadcast attacks

```python
#!/usr/bin/env python3
"""e=3 textbook RSA attacks."""

def icbrt(c):
    # Integer cube root via binary search (exact, no float error)
    lo, hi = 0, c
    while lo < hi:
        mid = (lo + hi) // 2
        if mid ** 3 < c:
            lo = mid + 1
        else:
            hi = mid
    return lo

def try_cube_root(c):
    m = icbrt(c)
    return m if m ** 3 == c else None
    # Works when m^3 < n (message small relative to modulus)

# Hastad's broadcast: same m, e=3, three different moduli n1,n2,n3
# c1 = m^3 mod n1, c2 = m^3 mod n2, c3 = m^3 mod n3
# CRT combines to m^3 mod (n1*n2*n3); since m^3 < n1*n2*n3,
# the CRT result IS m^3 exactly, then cube-root it.
def crt(a_list, n_list):
    from math import prod
    N = prod(n_list)
    x = 0
    for a, n in zip(a_list, n_list):
        Ni = N // n
        inv = pow(Ni, -1, n)
        x = (x + a * Ni * inv) % N
    return x
```

The broadcast attack needs the SAME plaintext under THREE different
keys with e=3: common in CTFs, rare in production (proper padding kills
it everywhere). When the conditions hold, it is deterministic and fast.

## 2. Wiener's attack concept

```python
#!/usr/bin/env python3
"""Wiener's attack: small private exponent d via continued fractions."""

# Condition: d < n^0.25 / 3 (roughly). Then k/d approximates e/n,
# and continued fractions of e/n reveal k/d, hence d.
#
# Steps:
# 1. Compute continued fraction convergents of e/n
# 2. For each convergent k/d candidate, test if it yields factors:
#    phi = (e*d - 1) / k must be integer; then solve x^2 - (n-phi+1)x + n = 0
# 3. Integer roots are p and q: key recovered
#
# In practice: use an established Wiener implementation; the concept
# above is what to verify when it claims success (it must produce
# factors that multiply to n).
```

Wiener's attack matters when d was chosen small for performance (a
mistake) or leaked partially. Modern libraries do not generate small
d; finding one means custom key generation, which is itself the
finding.

## 3. When small exponents are fine

```bash
# e=3 or e=65537 with OAEP padding: NOT vulnerable to these attacks
# The padding randomizes the message, killing cube-root and broadcast.
# Review checklist:
# - Padding = OAEP or PKCS#1 v1.5 with careful implementation -> e=3 OK
# - Padding = none (textbook) -> e=3 BROKEN, any small message falls
# - d small by design -> BROKEN regardless of padding (Wiener)

# e=65537 (the standard) with any proper padding: fine, move on
openssl rsa -pubin -in /tmp/pubkey.pem -text -noout | grep -i exponent
```

Do not report e=3 as a finding without checking the padding: e=3 with
OAEP is standard practice in some deployments and completely fine. The
finding is "textbook RSA with e=3," not "e=3."

## Edge cases

- Related messages (not identical) under e=3: Franklin-Reiter style
  attacks apply when messages differ by a known polynomial; rarer,
  but check when broadcast data looks related.
- The exponent is small but the key is huge: the attacks depend on
  the exponent and padding, not the key size; 4096-bit textbook e=3
  falls to the same cube root.
- Partial key exposure: related attacks (Coppersmith) apply when most
  of d or p leaks; that is advanced territory needing specialized
  tooling.

## Escalation

- An attack succeeds: demonstrate the decryption, report the exact
  conditions (exponent, padding absence, message reuse), and recommend
  OAEP plus e=65537.
- The conditions are close but not met: document the near-miss with
  the missing condition; near-misses guide the hardening.
- Custom RSA implementation found: recommend replacing with the
  standard library rather than patching the exponent choice.

## Detection and defender view

For defenders, small-exponent issues are prevented by standards: use
the vetted library's defaults (e=65537, OAEP), never textbook RSA, and
never custom key generation. Audit existing deployments for e values
and padding modes; legacy integrations are where textbook e=3 hides.
The defender's check is a configuration audit, not monitoring: these
attacks leave no distinctive log pattern until the plaintext is used.

## Key references

- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- Hastad (1988): broadcast attack on RSA.
- Wiener (1990): cryptanalysis of short RSA secret exponents.
