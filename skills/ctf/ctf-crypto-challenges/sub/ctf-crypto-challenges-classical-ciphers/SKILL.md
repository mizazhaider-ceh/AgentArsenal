---
name: ctf-crypto-challenges-classical-ciphers
description: Use when a CTF crypto challenge uses a classical cipher
  (Caesar, Vigenere, substitution, transposition, Playfair, Enigma-style
  rotor hints) or an unknown cipher producing letter-only ciphertext. Covers
  frequency analysis, Caesar brute force with English scoring, Vigenere key
  length recovery and per-column solving, substitution cracking with
  cribs, rail fence and columnar transposition attacks, repeating-key XOR
  via Hamming distance, and crib dragging with flag{ known plaintext. Use
  when ciphertext is alphabetic, when CyberChef Magic suggests a classical
  cipher, or when the challenge theme hints at historical cryptography.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-crypto-challenges
requires: [ctf-crypto-challenges]
extends: []
relates: [ctf-crypto-challenges, ctf-forensics-challenges]
tools:
  - name: Python
    version: 3.12
  - name: CyberChef
    version: latest
---

Classical ciphers substitute or reorder letters with small key spaces,
which makes them solvable with statistics and brute force rather than
math. CTFs use them as warmups and as layers inside bigger challenges.
This sub-skill covers the authorized solver toolkit: identifying the
cipher family from ciphertext shape, breaking each family with Python,
and using cribs (known plaintext like `flag{`) to collapse the search.
Scope is CTF competitions and lab exercises only.

## Quick Workflow

1. Profile the ciphertext: alphabet size, case, spaces preserved,
   length; each family has a signature.
2. Run CyberChef Magic first; it names many classical ciphers outright.
3. Caesar/shift: brute force all shifts and score for English.
4. Polyalphabetic (Vigenere): find key length (Kasiski/Friedman), then
   solve each column as Caesar.
5. Monoalphabetic substitution: frequency seed plus crib dragging.
6. Transposition: try rail fence depths and columnar with crib
   anchoring.
7. Repeating-key XOR: Hamming distance for key length, then per-byte
   frequency attack.
8. Verify the output reads as English or matches the flag format.

## 1. Ciphertext profiling

```python
#!/usr/bin/env python3
from collections import Counter
import math

ct = open("cipher.txt").read().strip()
letters = [c for c in ct.upper() if c.isalpha()]
print("total:", len(ct), "letters:", len(letters))
print("distinct letters:", len(set(letters)))

# Index of coincidence: ~0.065 English, ~0.038 random, ~0.065 monoalphabetic too
n = len(letters)
freq = Counter(letters)
ic = sum(f * (f - 1) for f in freq.values()) / (n * (n - 1))
print(f"IC: {ic:.4f}")
# IC near 0.065 with flat-ish top frequencies -> Vigenere/transposition
# IC near 0.065 with English-like curve -> Caesar/substitution
# IC near 0.038 -> polyalphabetic with long key, or random
```

Signatures: spaces preserved plus English word lengths visible ->
transposition or Vigenere. No spaces, even length hex -> bytes layer,
not classical. Repeated digraphs at regular intervals -> Vigenere (note
the distances; their GCD hints the key length).

## 2. Caesar and affine ciphers

```python
#!/usr/bin/env python3
# Caesar brute force with chi-squared English scoring
ENGLISH = [0.0817,0.0149,0.0278,0.0425,0.1270,0.0223,0.0202,0.0609,0.0697,
           0.0015,0.0077,0.0403,0.0241,0.0675,0.0751,0.0193,0.0009,0.0599,
           0.0633,0.0906,0.0276,0.0098,0.0236,0.0015,0.0197,0.0007]

def chi2(text):
    text = [c for c in text.upper() if c.isalpha()]
    n = len(text)
    if not n: return float("inf")
    obs = [text.count(chr(65+i)) for i in range(26)]
    return sum((o - n*e)**2/(n*e) for o, e in zip(obs, ENGLISH))

def caesar(s, k):
    return "".join(chr((ord(c)-65+k)%26+65) if c.isupper()
                   else chr((ord(c)-97+k)%26+97) if c.islower() else c for c in s)

ct = open("cipher.txt").read().strip()
for k in range(26):
    pt = caesar(ct, k)
    print(f"{k:2d} chi2={chi2(pt):8.1f}  {pt[:50]}")
# lowest chi2 is the answer

# Affine (ax+b mod 26): 312 key combos, brute force all with the same scorer
def affine(s, a, b):
    inv = pow(a, -1, 26)
    return "".join(chr((inv*(ord(c)-65-b))%26+65) if c.isupper()
                   else chr((inv*(ord(c)-97-b))%26+97) if c.islower() else c for c in s)
best = min(((affine(ct,a,b),a,b) for a in [1,3,5,7,9,11,15,17,19,21,23,25]
            for b in range(26)), key=lambda t: chi2(t[0]))
print("affine best:", best[1], best[2], best[0][:60])
```

## 3. Vigenere: key length then columns

```python
#!/usr/bin/env python3
from collections import Counter

ct = "".join(c for c in open("cipher.txt").read().upper() if c.isalpha())

# Kasiski: distances between repeated trigrams
def kasiski(ct):
    dists = []
    for i in range(len(ct)-3):
        tri = ct[i:i+3]
        j = ct.find(tri, i+1)
        while j != -1:
            dists.append(j-i)
            j = ct.find(tri, j+1)
    from math import gcd
    from functools import reduce
    return reduce(gcd, dists) if dists else 0
print("likely key length divides:", kasiski(ct))

# Friedman test as cross-check, then solve each column as Caesar
def solve_vigenere(ct, klen):
    key = ""
    for col in range(klen):
        column = ct[col::klen]
        best = min(range(26), key=lambda k: chi2(caesar(column, k)))
        key += chr(65+best)
    return key, caesar(ct, sum(ord(c)-65 for c in key) % 26)  # placeholder
```

Cleaner: decrypt with the recovered key directly:

```python
def vigenere_decrypt(ct, key):
    return "".join(chr((ord(c)-65-(ord(key[i % len(key)])-65))%26+65) for i, c in enumerate(ct))

for klen in range(2, 21):
    key = "".join(chr(65+min(range(26), key=lambda k: chi2(caesar(ct[col::klen], k))))
                  for col in range(klen))
    pt = vigenere_decrypt(ct, key)
    print(f"len={klen} key={key} chi2={chi2(pt):.1f} {pt[:40]}")
```

The correct key length shows a sharp chi2 drop. Autokey variants need a
crib; use the crib-dragging technique from section 6.

## 4. Monoalphabetic substitution with cribs

Pure frequency mapping gets you 70 percent; cribs finish it.

```python
#!/usr/bin/env python3
# Crib dragging: slide "FLAG{" (or "THE") across the ciphertext,
# keep placements with consistent mapping
def crib_drag(ct, crib):
    ct = "".join(c for c in ct.upper() if c.isalpha())
    hits = []
    for i in range(len(ct)-len(crib)+1):
        mapping, ok = {}, True
        for a, b in zip(crib, ct[i:i+len(crib)]):
            if a in mapping and mapping[a] != b: ok = False; break
            if b in {v for k, v in mapping.items() if k != a}: ok = False; break
            mapping[a] = b
        if ok: hits.append((i, mapping))
    return hits

for pos, m in crib_drag(open("cipher.txt").read(), "FLAG"):
    print(pos, m)
```

Extend the mapping from the hit: apply it to the whole text, guess the
remaining letters from partial English words, and iterate. Common CTF
cribs: `flag{`, `ctf{`, `picoctf{`, `the`, `and`.

## 5. Transposition ciphers

```python
#!/usr/bin/env python3
# Rail fence: try depths 2..len//2
def rail_decrypt(ct, rails):
    n = len(ct); cycle = 2*rails-2
    order = sorted(range(n), key=lambda i: min(i % cycle, cycle - i % cycle) if cycle else 0)
    pt = [""]*n
    for plain_pos, cipher_pos in enumerate(order):
        pt[cipher_pos] = ct[plain_pos]
    return "".join(pt)

ct = "".join(open("cipher.txt").read().split())
for r in range(2, min(15, len(ct)//2)):
    pt = rail_decrypt(ct, r)
    if chi2(pt) < 150:   # English-like
        print(r, pt[:60])

# Columnar: with a crib, deduce the column order
# (CyberChef's "Rail Fence Cipher Decode" with brute force covers this interactively)
```

Columnar by hand: write the ciphertext into rows under the guessed key
length, then permute columns until the crib appears; the crib anchors
the column order and the rest follows.

## 6. Repeating-key XOR

```python
#!/usr/bin/env python3
# Key length via normalized Hamming distance, then per-column single-byte XOR
def hamming(a, b): return bin(int.from_bytes(a,"big") ^ int.from_bytes(b,"big")).count("1")

data = open("cipher.bin","rb").read()
def keylen_score(k):
    blocks = [data[i*k:(i+1)*k] for i in range(4)]
    return sum(hamming(blocks[i], blocks[j])/k for i in range(4) for j in range(i+1,4))/6
klen = min(range(2, 41), key=keylen_score)
print("likely key length:", klen)

key = bytes(max(range(256),
    key=lambda b: sum(1 for c in data[i::klen] if chr(c ^ b) in
        "etaoin shrdluETAOINSHRDLU")) for i in range(klen))
print("key:", key)
print(bytes(c ^ key[i % klen] for i, c in enumerate(data))[:200])
```

Single-byte XOR scoring by English letter frequency is the inner loop;
run it per column once the key length is fixed.

## Edge cases

- Ciphertext too short for statistics (under ~100 letters): lean on
  cribs and brute force instead of frequency analysis.
- Homophonic or polyphonic hints in the description: the challenge
  says which family; do not fight the hint.
- Playfair: digraph statistics and the 5x5 grid; CyberChef has a
  Playfair operation, use it before hand-rolling.
- The "classical cipher" is a red herring over modern crypto: if IC
  is flat and nothing classical fits, look for the real construction
  underneath (XOR with a stream, not a repeating key).
- Multiple classical layers stacked (Vigenere over transposition): peel
  outside-in; solve the layer whose statistics are cleanest first, then
  re-profile.

## Escalation

- Vigenere key length will not resolve: try autokey and running-key
  variants, or the key may be as long as the message (one-time pad
  with a reused pad: crib-drag the pad instead).
- Substitution mapping stalls at 80 percent: look for nulls
  (decoy letters) or a final transposition applied after
  substitution; solve in reverse order of application.
- Repeating-key XOR key length ambiguous: the data may be compressed
  first (deflates frequency signals); try decompressing candidate
  plaintexts with zlib before scoring.
- CyberChef Magic names the cipher but your solver disagrees: trust the
  tool's identification and port its exact algorithm; hand-rolled
  variants drift on details like alphabet ordering.

## Detection and defender view

Defenders treat classical ciphers as broken by definition: their
presence in real systems (XOR "encryption", Caesar-style obfuscation,
hardcoded substitution tables) is a finding, not a control. Detection
is by code review and secret scanning, since ciphertext patterns (high
IC with letter-only alphabets, repeating-key XOR artifacts) are
recognizable. The durable fix is modern authenticated encryption from
a vetted library. For analysts, these techniques double as
deobfuscation tools for malware that hides strings with XOR or
single-byte ciphers.

## Key references

- MITRE ATT&CK T1027 (Obfuscated Files or Information).
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CyberChef: https://gchq.github.io/CyberChef/
- "The Code Book" (Singh): classical cipher background.
- dCode classical cipher solvers: https://www.dcode.fr/en (crib and
  brute-force tools for competitions).
