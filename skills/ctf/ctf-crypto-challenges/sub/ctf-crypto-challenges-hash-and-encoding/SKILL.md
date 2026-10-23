---
name: ctf-crypto-challenges-hash-and-encoding
description: Use when a CTF crypto challenge involves password hashes,
  hash constructions, or layered encodings. Covers identifying hash types
  by length and format, cracking with hashcat and John the Ripper
  (wordlist, mask, and rule attacks), length extension attacks on MD5 and
  SHA1, encoding layer peeling (base64, hex, base32, reversed, ROT),
  CyberChef Magic triage, and recognizing when the preimage is short
  enough to brute force. Use when handed hex digests, $2y$ or $6$ strings,
  mysteriously encoded blobs, or MAC constructions built on plain hashes.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-crypto-challenges
requires: [ctf-crypto-challenges]
extends: []
relates: [ctf-crypto-challenges, ctf-forensics-challenges]
tools:
  - name: hashcat
    version: 6.2.6
  - name: John the Ripper
    version: 1.9.0-jumbo
  - name: Python
    version: 3.12
  - name: CyberChef
    version: latest
---

Hashes and encodings are the plumbing of CTF crypto: flags hashed with
weak algorithms, secrets hidden behind five encoding layers, and MACs
built on raw MD5. This sub-skill covers the authorized methodology for
both halves: identifying and cracking hashes efficiently, and peeling
encoding layers mechanically. Scope is CTF competitions and lab
exercises only.

## Quick Workflow

1. Identify the hash or encoding: length, charset, prefix markers
   (`$2y$`, `$6$`, `{SHA}`), CyberChef Magic for unknowns.
2. If it is an encoding, peel layers mechanically (section 4) before
   assuming crypto.
3. If it is a hash, run a wordlist attack first (rockyou covers most
   CTF preimages).
4. Escalate to masks and rules matching the challenge theme when
   wordlists fail.
5. For MAC-style constructions (`md5(secret + message)`), test length
   extension instead of cracking.
6. For slow hashes (bcrypt), keep the candidate space tiny or find
   the flaw elsewhere.
7. Verify cracked output against the flag format; partial matches
   usually mean a wrong hash mode.
8. Note the algorithm and mode for the writeup; hash challenges are
   easy points when the mode is right.

## 1. Hash identification

```bash
# Length and charset cheat sheet
# 32 hex chars  -> MD5(0), NTLM(1000), md5crypt(500)
# 40 hex chars  -> SHA1(100)
# 56 hex chars  -> SHA224(1300)
# 64 hex chars  -> SHA256(1400), SHA3-256(17400)
# 96 hex chars  -> SHA384(10800)
# 128 hex chars -> SHA512(1700)
# $2y$/$2a$...  -> bcrypt(3200)
# $6$...        -> sha512crypt(1800)
# $1$...        -> md5crypt(500)

# hashid-style identification (or CyberChef "Detect File Type" style heuristics)
python3 - <<'EOF'
import re
h = open("hash.txt").read().strip()
print("len:", len(h))
print("hex:", bool(re.fullmatch(r"[0-9a-fA-F]+", h)))
print("b64:", bool(re.fullmatch(r"[A-Za-z0-9+/=]+", h)))
print("prefix:", h[:4])
EOF
```

When in doubt, try the top 3 candidates for the length in hashcat
rather than identifying perfectly; a wrong mode just fails fast.

## 2. Cracking: wordlist, mask, rules

```bash
# Wordlist first: rockyou solves most CTF hashes
hashcat -m 0 hashes.txt /usr/share/wordlists/rockyou.txt --force

# Show cracked results
hashcat -m 0 hashes.txt --show

# Mask attack when the preimage pattern is known (e.g. flag{...} or 4 digits)
hashcat -m 0 -a 3 'flag{?l?l?l?l}' --force
hashcat -m 1400 -a 3 '?d?d?d?d?d?d' --force

# Rule-based mangling on a small custom wordlist (challenge theme words)
hashcat -m 0 hashes.txt theme_words.txt -r /usr/share/hashcat/rules/best64.rule --force

# John the Ripper auto-detects formats; good for crypt-style hashes
john --wordlist=/usr/share/wordlists/rockyou.txt hashes.txt
john --show hashes.txt
```

Speed notes: NTLM and raw MD5 crack at billions per second on GPU;
bcrypt at tens per second, so bcrypt challenges always have tiny
preimages or a flaw elsewhere. Match the effort to the algorithm.

## 3. Length extension attacks

When the construction is `hash(secret || message)` with MD5, SHA1, or
SHA256, append data without knowing the secret.

```python
#!/usr/bin/env python3
# Concept: H(secret || msg || padding || extension) is computable from H(secret || msg)
# Use a length-extension tool (hashpump / hash_extender) rather than hand-rolling:
#
# hashpump usage:
#   Input: original hex digest, original message, secret length guess, data to append
#   Output: forged digest + forged message
```

```bash
# hashpump (install per your environment)
hashpump -s 5d41402abc4b2a76b9719d911017c592 -d 'data' -k 16 -a 'evil'
# try secret lengths 8..32; the server accepting one of them confirms the guess

# hash_extender (Python alternative)
python3 hash_extender.py --data-format=hex --secret-min=8 --secret-max=32 \
  --data='data' --append='evil' --signature=5d41402abc4b2a76b9719d911017c592 --out-data-format=html
```

This breaks naive `md5(key + message)` MACs in CTF web/crypto hybrids.
HMAC is immune; the attack only works on raw Merkle-Damgard hashes.

## 4. Encoding layer peeling

```python
#!/usr/bin/env python3
"""Peel stacked encodings until the plaintext or flag appears."""
import base64, binascii, codecs

def try_peel(s):
    candidates = []
    def ok(x): return isinstance(x, str) and x and all(32 <= ord(c) < 127 or c in "\n\r\t" for c in x[:80])
    for name, fn in [
        ("base64", lambda x: base64.b64decode(x).decode()),
        ("base32", lambda x: base64.b32decode(x).decode()),
        ("hex", lambda x: bytes.fromhex(x).decode()),
        ("reverse", lambda x: x[::-1]),
        ("rot13", lambda x: codecs.decode(x, "rot_13")),
        ("url", lambda x: __import__("urllib.parse").unquote(x)),
    ]:
        try:
            out = fn(s)
            if out != s and ok(out): candidates.append((name, out))
        except Exception: pass
    return candidates

s = open("blob.txt").read().strip()
for depth in range(12):
    peels = try_peel(s)
    if not peels:
        print("stuck at:", s[:120]); break
    name, s = peels[0]
    print(f"[{depth}] {name}: {s[:80]}")
    if "flag{" in s or "CTF{" in s:
        print("FLAG FOUND:", s); break
```

CyberChef's Magic operation does this interactively and also tries XOR,
URL, and HTML entity layers. When the blob is binary (not text), check
`file` output after each peel; a peel that yields gzip/zlib data means
decompress next.

## 5. Recognizing short-preimage brute force

Some challenges hash a short secret (4-8 chars) with a strong hash;
the intended solve is brute force, not wordlists.

```bash
# hashcat mask for 6-char lowercase+digits SHA256
hashcat -m 1400 abc123hash.txt -a 3 '?l?l?l?l?l?l' -1 '?l?d' --force

# Python for tiny spaces with a custom alphabet (challenge-themed charset)
python3 - <<'EOF'
import hashlib, itertools, string
target = bytes.fromhex(open("hash.txt").read().strip())
alpha = string.ascii_lowercase + string.digits
for n in (4, 5, 6):
    for tup in itertools.product(alpha, repeat=n):
        cand = "".join(tup).encode()
        if hashlib.sha256(cand).digest() == target:
            print("found:", cand); raise SystemExit
    print("length", n, "exhausted")
EOF
```

Estimate the space first: 36^6 is 2 billion, too slow in Python but fine
in hashcat on GPU; 36^8 is out of reach, so the intended path is
different (wordlist, flaw, or oracle).

## Edge cases

- The "hash" is actually HMAC with an unknown key: cracking is
  impossible; look for key leakage or length extension on a related
  raw-hash construction instead.
- Salted hashes (`salt$hash`): hashcat handles common salt formats;
  for custom salting, read the source and replicate the construction
  in Python with a wordlist loop.
- The encoding blob decodes to more encoding: keep peeling; CTF
  authors stack 5-10 layers and the flag format check tells you when
  to stop.
- Case-sensitive base64 with missing padding: add `=` padding before
  decoding; some challenges strip it deliberately.
- The digest length matches nothing standard: it may be truncated (half
  MD5 is common in CTFs); try truncated variants of the top candidates.

## Escalation

- Wordlist plus masks fail on a fast hash: the preimage may be
  random-looking (then it is not meant to be cracked; find the flaw),
  or the mode is wrong (NTLM vs MD5 give different results for the
  same password; try both).
- Length extension guesses all fail: the secret length range may be
  wider, or the construction is HMAC (immune); re-read the source.
- bcrypt will not crack in competition time: the password is in the
  challenge materials (config, comment, another artifact); search
  there instead of burning GPU hours.
- The hash cracks but the preimage is not the flag: the preimage may be
  a key for the next stage (XOR key, archive password); try it as input
  to the surrounding challenge before moving on.

## Detection and defender view

Defenders use hash identification and cracking legitimately: auditing
password databases for weak passwords, verifying that dumps cannot be
cracked quickly (a red-team service, not an attack on others). The
defensive lessons are direct: store passwords with argon2id/bcrypt/
scrypt with proper work factors, never raw MD5/SHA; use HMAC, not raw
hash, for MACs; and treat any crackable hash exposure as a breach
requiring password resets. Detection focuses on credential stuffing
with cracked passwords and on code that still uses broken hashes.

## Key references

- MITRE ATT&CK T1110 (Brute Force) and T1552.001 (Credentials In
  Files).
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CWE-916 (Use of Password Hash With Insufficient Computational
  Effort).
- CWE-759 (Use of a One-Way Hash without a Salt).
- hashcat example hashes: https://hashcat.net/wiki/doku.php?id=example_hashes
- CyberChef: https://gchq.github.io/CyberChef/
