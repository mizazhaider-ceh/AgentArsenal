---
name: rsa-common-mistakes
description: Use when assessing RSA implementations for the classic
  deployment mistakes on an authorized engagement or in a CTF. Covers
  small modulus factoring, common prime reuse, e=3 issues, and textbook
  RSA pitfalls. Use when you capture RSA public keys, when reviewing
  key generation, when the modulus looks factorable, or when triaging
  which RSA attack applies.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
parent: rsa-attacks
requires: [rsa-attacks]
extends: []
relates: [crypto-fundamentals, reviewer-crypto-misuse]
tools:
  - name: Python
    version: 3.12
  - name: OpenSSL
    version: 3.0
---

RSA breaks in practice through implementation mistakes, not through
attacks on the math: small keys, reused primes, tiny exponents, and
textbook (unpadded) encryption. This skill covers recognizing and
exploiting the common mistakes on authorized engagements and in CTFs:
which mistake the key material suggests, and the standard recovery for
each. It is triage plus the easy wins; padding oracles and exponent
attacks are their own sub-skills.

## Quick Workflow

1. Extract the public key material: n, e, and any ciphertext.
2. Check key size: under 512 bits is factorable on a laptop.
3. Check for prime reuse across keys (gcd of moduli).
4. Check the exponent: e=3 with textbook RSA is fragile.
5. Apply the matching recovery; verify by decrypting a known value.
6. Document the mistake and the recovered plaintext.

## 1. Small modulus factoring

```bash
# Extract n and e from a PEM public key
openssl rsa -pubin -in /tmp/pubkey.pem -text -noout 2>/dev/null | head -10

# Key size check: 512-bit and below factor on commodity hardware
python3 - <<'EOF'
# Rough guidance:
# 256-bit: seconds | 512-bit: minutes-hours | 768-bit: serious effort
# 1024-bit: nation-state in practice; 2048-bit: safe
print("If n < 2**512: try factoring first, ask questions later")
EOF

# Factor with your tool of choice (yafu/msieve/ecm for 512-bit),
# then recover d and decrypt
```

```python
#!/usr/bin/env python3
"""Recover the private exponent from factors, then decrypt."""
from math import gcd

def egcd(a, b):
    if b == 0:
        return (a, 1, 0)
    g, x1, y1 = egcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)

def modinv(a, m):
    g, x, _ = egcd(a, m)
    assert g == 1
    return x % m

# p, q from the factoring step; e from the public key
# n = p * q; phi = (p-1)*(q-1); d = modinv(e, phi)
# plaintext = pow(ciphertext, d, n)
```

Always verify the recovered key by decrypting something: a known
plaintext, or the PKCS#1 padding structure. Factors that do not
decrypt are wrong factors.

## 2. Common prime and exponent issues

```python
#!/usr/bin/env python3
"""Batch GCD: find shared primes across many moduli."""
from math import gcd

moduli = []  # load n values from captured keys
# Pairwise gcd finds any shared prime: gcd(ni, nj) = p means
# both keys share p, and both factor immediately
for i in range(len(moduli)):
    for j in range(i + 1, len(moduli)):
        g = gcd(moduli[i], moduli[j])
        if g != 1:
            print(f"shared prime between key {i} and {j}: {g}")

# e=3 with textbook RSA (no padding): cube-root attack on small messages
# if m^3 < n, then c = m^3 and m = round(c ** (1/3))
def cube_root(c):
    x = round(c ** (1/3))
    for cand in (x - 2, x - 1, x, x + 1, x + 2):
        if cand ** 3 == c:
            return cand
    return None
```

Shared primes come from bad RNGs (embedded devices, VMs at boot);
batch gcd across all captured keys is cheap and decisive. e=3 is only
exploitable when padding is absent or broken; with proper OAEP, e=3 is
fine, so check the padding before celebrating.

## Edge cases

- The key is 1024-bit. Factoring is out of reach; look for protocol
  mistakes (padding, exponent) instead of math attacks.
- The ciphertext uses proper OAEP. Textbook attacks do not apply;
  move to implementation review (side channels, oracles).
- Multiple keys, no shared primes. The RNG is fine; the mistake is
  elsewhere.
- The "mistake" is in a CTF with intentional weakness. The triage
  order is the same: size, gcd, exponent, padding.

## Escalation

- Factoring succeeds: recover the full private key, demonstrate
  decryption, and report the key size as the root cause.
- The mistake is systemic (device fleet with shared primes): report
  the fleet impact, not just the one key; every key sharing the prime
  falls.
- No common mistake found: hand the key to rsa-padding-oracles or
  rsa-small-exponent for the advanced attacks.

## Detection and defender view

For defenders, RSA mistakes are prevented at generation: use a vetted
library, 2048-bit minimum (3072 for long-lived), proper padding (OAEP
for encryption, PSS for signatures), and a real RNG. Audit existing
keys for size and generation source; embedded and legacy systems are
where the small keys and shared primes hide. The defender's check is
simple: list every RSA key, check size and provenance, replace the
weak ones.

## Key references

- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CWE-330 (Use of Insufficiently Random Values).
- NIST SP 800-56B (RSA key establishment guidance).
