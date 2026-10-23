---
name: ctf-crypto-challenges
description: Use when competing in a CTF cryptography challenge,
  practicing in a lab, or analyzing cryptographic constructions you are
  authorized to examine. Covers the crypto workflow, identifying the
  cipher or construction, attacking classical ciphers (Caesar, Vigenere,
  substitution, transposition), exploiting RSA mistakes (small e, common
  modulus, Wiener, Hastad broadcast, CRT faults), cracking hashes and
  encodings, and scripting solvers in Python. Use when handed ciphertext
  with a suspicious key setup, when source shows custom crypto, or when
  the flag is locked behind a breakable construction.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ctf-web-challenges, ctf-forensics-challenges]
tools:
  - name: Python
    version: 3.12
  - name: CyberChef
    version: latest
  - name: John the Ripper
    version: 1.9.0-jumbo
  - name: hashcat
    version: 6.2.6
---

CTF crypto challenges are built around mistakes: weak ciphers, misused
RSA, custom constructions with a flaw, and hashes protecting short
secrets. The winning pattern is identification first (what construction
is this, what are the parameters), then the known attack for that
mistake, then a Python solver. This skill covers the authorized
methodology across classical, RSA, and hash/encoding challenges, with
concrete attack code. Scope is CTF competitions, lab exercises, and
constructions you are authorized to analyze; it does not cover attacking
real-world systems.

## Quick Workflow

1. Identify the construction: ciphertext shape, provided parameters
   (n, e, c for RSA), source code when given.
2. Check for the classic mistakes first: ECB mode, small e with small
   message, reused nonce, hardcoded key in source.
3. For classical ciphers, try CyberChef's magic and frequency analysis
   before writing code.
4. For RSA, run the parameter checklist (small e, shared n, close
   primes, small d via Wiener, broadcast) in order.
5. For hashes, identify the algorithm (length, charset, source) and
   crack with a wordlist or mask attack.
6. Write the solver in Python, keeping the attack steps separate from
   parsing so it is reusable.
7. Verify the output matches the flag format; partial decryptions
   usually mean one wrong parameter.
8. Document the flaw class; CTF crypto is pattern matching, and notes
   compound across events.

## 1. Identification: reading the challenge

```bash
# Ciphertext shape hints
echo "aGVsbG8=" | base64 -d        # base64 wrapper? decode first
# hex string of even length        # maybe raw bytes as hex
# long integer n, e, c             # RSA parameters

# CyberChef "Magic" operation tries dozens of decodings at once;
# paste the ciphertext there before anything else.

# Python quick checks
python3 - <<'EOF'
ct = open("cipher.txt").read().strip()
print("length:", len(ct))
from collections import Counter
freq = Counter(ct)
print("top chars:", freq.most_common(8))
# single-case letters, no digits -> classical cipher likely
# hex charset -> bytes; base64 charset -> encoded layer
EOF
```

When source is provided, read it fully: the flaw is usually one line
(`e = 3`, `key = b"password"`, `random` instead of `secrets`, ECB mode).

## 2. RSA parameter checklist

```python
#!/usr/bin/env python3
"""RSA triage: checks the classic CTF mistakes in order."""
import math

n = 0x...  # from challenge
e = 0x...  # from challenge
c = 0x...  # from challenge (possibly a list for broadcast)

# 1. Small e with small message: c = m^e < n -> integer e-th root
def iroot(k, c):
    lo, hi = 0, int(pow(c, 1.0 / k)) + 2
    while lo < hi:
        mid = (lo + hi) // 2
        if mid**k < c: lo = mid + 1
        else: hi = mid
    return lo
m = iroot(e, c)
if pow(m, e) == c:
    print("small-e root attack worked:", m.to_bytes((m.bit_length()+7)//8, "big"))

# 2. n factors trivially (small n, or p/q given elsewhere)
#    try: factor(n) with Pollard Rho, or check gcd with other challenge moduli

# 3. Common modulus: same n, two ciphertexts with coprime e1, e2
#    extended Eucldiean: a*e1 + b*e2 = 1 -> m = c1^a * c2^b mod n

# 4. Wiener: d < n^0.25 -> continued fraction attack on e/n
#    (implement or use owiener / RsaCtfTool --private)

# 5. Hastad broadcast: same m, e=3, three different n -> CRT then cube root
```

RsaCtfTool automates most of this:

```bash
# Feed n, e, c and let it try every known attack
python3 RsaCtfTool.py -n 0xC0FFEE... --uncipher 0xDEAD... -e 3 --private
```

Order matters: try small-e root and factoring first (seconds), then
Wiener and broadcast (minutes), then CTF-specific variants (CRT fault,
partial key exposure via Coppersmith).

## 3. Classical cipher attacks

```python
#!/usr/bin/env python3
from collections import Counter
import string

ct = "WKH TXLFN EURZQ IRA MXPSV..."  # example Caesar

# Caesar: try all 26 shifts, score by English frequency
def caesar(s, k):
    return "".join(chr((ord(c) - 65 + k) % 26 + 65) if c.isupper()
                   else chr((ord(c) - 97 + k) % 26 + 97) if c.islower() else c
                   for c in s)
for k in range(26):
    print(k, caesar(ct, k)[:40])

# Vigenere: Kasiski / Friedman to find key length, then per-column Caesar
# (CyberChef's Vigenere break with known crib is faster interactively)

# Substitution: frequency analysis seed, then manual solving
freq = Counter(c for c in ct.upper() if c.isalpha())
print(freq.most_common())
# map most common ciphertext letter -> E, then refine with digraphs

# Transposition (columnar/rail fence): try rail fence depths 2..12
def rail_decrypt(ct, rails):
    n = len(ct); cycle = 2 * rails - 2
    idx = sorted(range(n), key=lambda i: min(i % cycle, cycle - i % cycle))
    pt = [""] * n
    for plain_pos, cipher_pos in enumerate(idx):
        pt[cipher_pos] = ct[plain_pos]
    return "".join(pt)
for r in range(2, 13):
    print(r, rail_decrypt(ct.replace(" ", ""), r)[:40])
```

XOR with repeating key: guess key length via Hamming distance between
blocks, then solve each column as single-byte XOR (frequency attack on
each byte position).

## 4. Hash cracking and identification

```bash
# Identify the hash by length and charset
# 32 hex  -> MD5 / NTLM / md5crypt variant
# 40 hex  -> SHA1
# 64 hex  -> SHA256
# $2y$... -> bcrypt ; $6$... -> sha512crypt

# hashcat modes: 0=MD5, 100=SHA1, 1400=SHA2-256, 1800=sha512crypt, 3200=bcrypt
hashcat -m 0 hashes.txt /usr/share/wordlists/rockyou.txt --force
hashcat -m 1400 hashes.txt -a 3 '?l?l?l?l?d?d' --force   # mask: 4 lower + 2 digits

# John the Ripper auto-detects many formats
john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt
```

In CTFs the preimage is usually a short secret, a flag-format string,
or a dictionary word; run rockyou first, then masks matching the
challenge theme, then targeted wordlists.

## 5. Encoding layers

CTF crypto often wraps the real cipher in encodings. Peel mechanically:

```python
#!/usr/bin/env python3
import base64, binascii

s = open("cipher.txt").read().strip()
for _ in range(10):  # peel up to 10 layers
    changed = False
    for name, fn in [
        ("b64", lambda x: base64.b64decode(x).decode()),
        ("hex", lambda x: bytes.fromhex(x).decode()),
        ("b32", lambda x: base64.b32decode(x).decode()),
        ("rev", lambda x: x[::-1]),
        ("rot13", lambda x: __import__("codecs").decode(x, "rot_13")),
    ]:
        try:
            s2 = fn(s)
            if s2 != s and all(32 <= ord(c) < 127 or c in "\n" for c in s2[:50]):
                print(f"peeled {name}: {s2[:60]}")
                s, changed = s2, True
                break
        except Exception:
            pass
    if not changed:
        break
print("final:", s[:200])
```

CyberChef's "Magic" operation does the same interactively and catches
XOR and rail fence layers too.

## Edge cases

- The ciphertext is not English after full decryption: the plaintext
  may be the flag directly (no English to score); check the flag
  format instead of readability.
- RSA with e = 65537 and proper padding: the flaw is elsewhere
  (shared primes across challenges, small private exponent, faulty
  CRT in source); do not waste time on textbook attacks.
- Custom S-box or Feistel in source: reimplement it exactly in
  Python and invert round by round; one transcription error breaks
  everything, so test encryption round-trips first.
- The challenge is interactive (oracle): count your queries; padding
  oracles and CBC bit-flipping need many requests, so script them
  and stay within rate limits.
- The challenge mixes crypto with another category (crypto-pwn,
  web-crypto): solve the outer layer first with its own skill, then
  attack the crypto core; do not blend the toolchains.

## Escalation

- No classic mistake found in RSA: check for related-message attacks
  (Franklin-Reiter), partial private key (Coppersmith with known
  bits), and faulty signatures leaking CRT components.
- Classical cipher resists frequency analysis: the plaintext may be
  compressed or the flag only (too short for statistics); try crib
  dragging with `flag{` as the known plaintext.
- Hash will not crack: the preimage may be a key, not a password;
  look for length-extension (MD5/SHA1 with secret prefix in source)
  instead of cracking.
- Everything looks correct but the flag is wrong: check byte order
  (little vs big endian in int-to-bytes), padding bytes included in
  the message, and off-by-one in key length.

## Detection and defender view

Defenders care about the inverse: ensuring none of these mistakes ship.
That means using vetted libraries (never custom ciphers), RSA with
OAEP padding and e = 65537, unique random nonces, password hashing with
argon2/bcrypt/scrypt (never raw MD5/SHA), and key management that keeps
secrets out of source. Detection of weak crypto in the wild uses
fingerprinting (small RSA keys in certificates, ECB patterns in
ciphertext) and code scanning for hardcoded keys and weak algorithms.
CTF crypto trains exactly the recognition skills defenders need in code
review.

## Key references

- MITRE ATT&CK T1552 (Unsecured Credentials) for hardcoded keys.
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CWE-798 (Use of Hard-coded Credentials).
- CWE-330 (Use of Insufficiently Random Values).
- CWE-916 (Use of Password Hash With Insufficient Computational
  Effort).
- RsaCtfTool: https://github.com/RsaCtfTool/RsaCtfTool
- CyberChef: https://gchq.github.io/CyberChef/
