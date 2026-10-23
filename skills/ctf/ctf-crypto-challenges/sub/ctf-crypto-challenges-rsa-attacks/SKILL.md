---
name: ctf-crypto-challenges-rsa-attacks
description: Use when a CTF crypto challenge provides RSA parameters (n,
  e, c) or source implementing RSA with a flaw. Covers the ordered attack
  checklist, small-e cube root, factoring weak moduli, common modulus with
  coprime exponents, Wiener's small-d attack, Hastad broadcast with CRT,
  shared prime factors via gcd across challenges, partial key exposure
  concepts, and RsaCtfTool automation. Use when handed n/e/c tuples, when
  multiple challenges share primes, when e is tiny, or when source shows
  textbook RSA without padding.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-crypto-challenges
requires: [ctf-crypto-challenges]
extends: []
relates: [ctf-crypto-challenges, ctf-web-challenges]
tools:
  - name: Python
    version: 3.12
  - name: CyberChef
    version: latest
---

RSA in CTFs is never attacked mathematically in the hard sense; it is
attacked through implementation mistakes the challenge author planted:
tiny exponents, shared moduli, factorable n, small private exponents,
and broadcast encryption. This sub-skill covers the authorized attack
checklist in the order that solves the most challenges per minute, with
working Python for each and RsaCtfTool as the automation backstop. Scope
is CTF competitions and lab exercises only.

## Quick Workflow

1. Parse the parameters: n, e, c (and any extra: multiple ciphertexts,
   multiple moduli, leaked bits, signatures).
2. Try the instant wins: small-e root when m^e < n, trivial factoring
   when n is small.
3. Check cross-challenge gcd: shared primes across challenges or
   services are the most common multi-part CTF RSA flaw.
4. Try common modulus (same n, coprime e values) with the extended
   Euclidean attack.
5. Try Wiener's attack when d may be small (e large relative to n).
6. Try Hastad broadcast when the same message went to 3+ recipients
   with e = 3.
7. Run RsaCtfTool with --private and let it try the long tail.
8. Decrypt, convert int to bytes, and check the flag format.

## 1. Small exponent root attack

When e is small (3, 5, 7) and the message is short, c = m^e may be
smaller than n, so no modular reduction happened and m is the integer
e-th root of c.

```python
#!/usr/bin/env python3
def iroot(k, c):
    """Integer k-th root via binary search."""
    lo, hi = 0, 1 << ((c.bit_length() // k) + 1)
    while lo < hi:
        mid = (lo + hi) // 2
        if mid**k < c: lo = mid + 1
        else: hi = mid
    return lo

n = 0x...; e = 3; c = 0x...
m = iroot(e, c)
if pow(m, e) == c:
    flag = m.to_bytes((m.bit_length() + 7) // 8, "big")
    print("recovered:", flag)
else:
    print("no small-e root: reduction happened, try other attacks")
```

Also try when e = 3 and c is only slightly above n: small multiples
(c + k*n for small k) may be perfect cubes; loop k up to a few million.

## 2. Factoring weak moduli

```python
#!/usr/bin/env python3
import math, random

def pollard_rho(n):
    if n % 2 == 0: return 2
    while True:
        c = random.randrange(1, n)
        f = lambda x: (x*x + c) % n
        x = y = 2; d = 1
        while d == 1:
            x = f(x); y = f(f(y))
            d = math.gcd(abs(x-y), n)
        if d != n: return d

n = 0x...
p = pollard_rho(n); q = n // p
print("p =", hex(p)); print("q =", hex(q))
phi = (p-1)*(q-1)
d = pow(e, -1, phi)
m = pow(c, d, n)
print(m.to_bytes((m.bit_length()+7)//8, "big"))
```

Pollard Rho factors CTF-sized weak moduli (under ~120 digits, or primes
with special form) in seconds. For close primes (q near p), Fermat's
method is faster: `a = isqrt(n)`, then check `a*a - n` for perfect
squares. For n under ~512 bits with no structure, try factordb or
online factor databases before local ECM.

## 3. Cross-challenge gcd: shared primes

```python
#!/usr/bin/env python3
import math
# collect every n from the challenge set (and past challenges by the same author)
moduli = [0x..., 0x..., 0x...]
for i in range(len(moduli)):
    for j in range(i+1, len(moduli)):
        g = math.gcd(moduli[i], moduli[j])
        if g != 1:
            print(f"shared prime between n[{i}] and n[{j}]: {hex(g)}")
            p = g; q = moduli[i] // p
            # now decrypt challenge i with phi = (p-1)*(q-1)
```

This is the highest-value check in multi-RSA CTF sets: one gcd loop
breaks every challenge sharing a prime. Always run it before deeper
attacks.

## 4. Common modulus attack

Same n, same message, two coprime exponents e1, e2: recover m without
factoring.

```python
#!/usr/bin/env python3
def egcd(a, b):
    if b == 0: return (a, 1, 0)
    g, x, y = egcd(b, a % b)
    return (g, y, x - (a // b) * y)

n = 0x...; e1 = 0x10001; e2 = 0x...; c1 = 0x...; c2 = 0x...
_, a, b = egcd(e1, e2)   # a*e1 + b*e2 = 1
# handle negative exponents with modular inverse
m1 = pow(c1, a, n) if a > 0 else pow(pow(c1, -1, n), -a, n)
m2 = pow(c2, b, n) if b > 0 else pow(pow(c2, -1, n), -b, n)
m = (m1 * m2) % n
print(m.to_bytes((m.bit_length()+7)//8, "big"))
```

## 5. Wiener's small-d attack

When d < n^0.25 (and e is large), the continued fraction convergents of
e/n reveal d.

```bash
# RsaCtfTool has Wiener built in; fastest path:
python3 RsaCtfTool.py --publickey pub.pem --uncipherfile cipher.bin --private
```

```python
#!/usr/bin/env python3
# Sketch: convergents of e/n, test each denominator as candidate d
from fractions import Fraction
def convergents(num, den):
    convs = []
    while den:
        q = num // den
        convs.append(q)
        num, den = den, num - q*den
    # build convergents k/d from partial quotients, test each d:
    # check (e*d - 1) % k == 0 and phi candidate factors n
    return convs
# (full Wiener test per candidate: standard 30-line implementation)
```

In practice use RsaCtfTool or owiener; hand-rolling Wiener is error
prone under time pressure.

## 6. Hastad broadcast attack

Same message encrypted with e = 3 under three (or e) different moduli:
combine with CRT, then take the integer cube root.

```python
#!/usr/bin/env python3
def crt(remainders, moduli):
    M = 1
    for m in moduli: M *= m
    x = 0
    for r, m in zip(remainders, moduli):
        Mi = M // m
        x += r * Mi * pow(Mi, -1, m)
    return x % M

ns = [0x..., 0x..., 0x...]   # distinct moduli
cs = [0x..., 0x..., 0x...]   # same plaintext, e=3
c_crt = crt(cs, ns)          # equals m^3 exactly (m^3 < n1*n2*n3)
m = iroot(3, c_crt)          # iroot from section 1
print(m.to_bytes((m.bit_length()+7)//8, "big"))
```

Generalizes to e ciphertexts for exponent e. Padding (even PKCS#1 v1.5)
usually defeats this; CTF broadcast challenges use textbook RSA.

## 7. RsaCtfTool automation

```bash
# Private key recovery attempts (tries Wiener, small-e, Fermat, etc.)
python3 RsaCtfTool.py -n 0xC0FFEE --uncipher 0xDEADBEEF -e 65537 --private

# With a public key file and encrypted file
python3 RsaCtfTool.py --publickey pubkey.pem --uncipherfile flag.enc --private

# Pastctf-style: dump all parameters it can find
python3 RsaCtfTool.py --publickey pubkey.pem --dumpkey
```

Run it in the background while you hand-check the fast attacks; it
covers the long tail (Boneh-Durfee, partial key exposure, CRT faults)
that is slow to hand-roll.

## Edge cases

- e = 65537 and n strong: textbook attacks fail; the flaw is in the
  protocol (chosen ciphertext, padding oracle, faulty signing) or
  the key handling (private exponent leaked in source).
- The challenge gives a signature, not a ciphertext: verify-then-
  forge attacks (Bleichenbacher e=3 forgery, small-e signature
  malleability) apply instead of decryption attacks.
- Multiple test cases share one n with related messages
  (m2 = m1 + delta): Franklin-Reiter / Coppersmith related-message
  attack; RsaCtfTool covers it.
- n is prime (not a product): then "RSA" is just modular
  exponentiation; solve the discrete log if the group is small, or
  the challenge is about something else entirely.
- The challenge hands you d or phi directly in a "broken" keygen:
  verify the values satisfy e*d = 1 mod phi before trusting them;
  authors plant red herrings.

## Escalation

- Nothing factors and no parameter flaw found: re-read the source
  for the real flaw (bad PRNG like `random` module, nonce reuse in a
  custom scheme, private key in an error message).
- RsaCtfTool runs long with no result: cap it and pivot; CTF RSA is
  designed to fall to one clean idea, not to a 2-hour lattice attack.
- Partial private key bits leaked: Coppersmith needs enough known
  bits (about a quarter); fewer bits means the intended path is
  different.
- The modulus is huge (4096-bit) and e is 65537: look for
  implementation flaws (CRT fault injection via a signing oracle,
  timing) rather than math.

## Detection and defender view

Defenders prevent all of this with boring correctness: 2048-bit+
moduli from a vetted CSPRNG, e = 65537, OAEP padding (never textbook
RSA), unique keys per system, and no private key material in logs or
errors. Detection of weak RSA in the wild uses certificate and key
scanning (small keys, shared primes across devices, CVE-2008-0166
Debian weak keys). Code review flags `random` for key generation,
hardcoded primes, and textbook `pow(m, e, n)` encryption. CTF RSA
trains the exact recognition skills needed to spot these in audits.

## Key references

- MITRE ATT&CK T1552 (Unsecured Credentials) for key handling flaws.
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CWE-330 (Use of Insufficiently Random Values).
- CWE-798 (Use of Hard-coded Credentials).
- RsaCtfTool: https://github.com/RsaCtfTool/RsaCtfTool
- "Twenty Years of Attacks on the RSA Cryptosystem" (Boneh): the
  survey behind the checklist.
