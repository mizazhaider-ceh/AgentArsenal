---
name: encoding-vs-encryption
description: Use when you encounter encoded or obfuscated data and need
  to tell encoding apart from real encryption on an authorized
  engagement. Covers base64, hex, URL encoding recognition, layered
  encodings, and the "is this actually encrypted" decision. Use when
  triaging unknown blobs, when decoding CTF or malware strings, when
  reviewing "encrypted" data handling, or when teaching the distinction.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
parent: crypto-fundamentals
requires: [crypto-fundamentals]
extends: []
relates: [reviewer-crypto-misuse]
tools:
  - name: Python
    version: 3.12
---

Encoding is not encryption: base64 hides nothing from anyone who looks,
while real encryption needs a key. This skill covers telling them apart
fast: recognizing the common encodings, peeling layered encodings, and
deciding whether the blob is actually encrypted (and what that implies).
Most "mysterious blobs" in engagements are encoding, not crypto; this
skill resolves them in seconds.

## Quick Workflow

1. Look at the blob: alphabet, length, padding, structure.
2. Try the common decodings in order: base64, hex, URL, base32.
3. Check if the result is readable or structured; if yes, done.
4. If layered, repeat: decode the result again.
5. If nothing decodes to sense, assess: encrypted, compressed, or
   random.
6. Document the decoding chain for the finding.

## 1. Recognition and decoding

```bash
# base64: A-Za-z0-9+/ with = padding, length multiple of 4
# hex: 0-9a-f, even length
# URL encoding: %XX sequences
# base32: A-Z2-7 with = padding

python3 - <<'EOF'
import base64, binascii, urllib.parse

def try_decode(blob: str):
    results = {}
    s = blob.strip()
    # base64
    try:
        results["base64"] = base64.b64decode(s).decode("utf-8", errors="replace")
    except Exception:
        pass
    # hex
    try:
        if all(c in "0123456789abcdefABCDEF" for c in s) and len(s) % 2 == 0:
            results["hex"] = bytes.fromhex(s).decode("utf-8", errors="replace")
    except Exception:
        pass
    # url
    if "%" in s:
        results["url"] = urllib.parse.unquote(s)
    return results

for b in ["aGVsbG8gd29ybGQ=", "68656c6c6f", "hello%20world"]:
    print(b, "->", try_decode(b))
EOF
```

Length is a clue: base64 expands by 4/3, hex doubles. A 44-character
base64 blob decodes to 32 bytes: probably a 256-bit key or hash. Match
the decoded length against known sizes (16/20/32/64 bytes) for hints.

## 2. Layered encodings

```bash
# Attackers and developers layer encodings: base64 of hex, URL of base64
python3 - <<'EOF'
import base64, urllib.parse

def peel(blob: str, max_layers=5):
    cur = blob
    for i in range(max_layers):
        # try base64
        try:
            nxt = base64.b64decode(cur).decode()
            if nxt != cur and nxt.isprintable():
                print(f"layer {i+1} base64 -> {nxt[:60]}")
                cur = nxt
                continue
        except Exception:
            pass
        # try url decode
        nxt = urllib.parse.unquote(cur)
        if nxt != cur:
            print(f"layer {i+1} url -> {nxt[:60]}")
            cur = nxt
            continue
        break
    return cur

peel("aGVsbG8lMjB3b3JsZA==")  # base64 -> url-encoded -> text
EOF
```

Peel until the output stops changing or becomes readable. Each layer
found is worth noting: single base64 is usually just transport;
five layers is deliberate obfuscation, which is itself a signal about
intent.

## 3. Encrypted versus random versus compressed

```bash
python3 - <<'EOF'
import math
from collections import Counter

def entropy(data: bytes) -> float:
    counts = Counter(data)
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in counts.values())

# Rough guide (per byte):
# < 4.5: text or structured data (decode it)
# 4.5-7.5: compressed or encoded structured data
# > 7.5: encrypted or random (needs a key or is a key)
for name, sample in [("text", b"hello world" * 10),
                     ("random", bytes(range(256)) * 2)]:
    print(name, round(entropy(sample), 2))
EOF
```

High entropy plus no decodable structure means encrypted (needs a key
you probably do not have) or random (it IS the key/token). Either way,
the next step is finding the key or the code that uses the blob, not
more decoding. Check for magic bytes too: compressed data (gzip,
zlib) has recognizable headers and decompresses.

## Edge cases

- The blob decodes to binary, not text. It may be a serialized object,
  an encrypted payload, or a key; identify by length and context.
- Custom encodings (XOR with a key, ROT variants). Look for the decode
  routine in the nearby code; custom encoding without the routine is
  usually breakable but needs the context.
- The "encryption" is just base64. Report it as obfuscation, not
  encryption; the severity differs enormously.
- JWTs and structured tokens. They are base64url with dots: decode
  the segments separately and read the claims.

## Escalation

- It is real encryption and you need the plaintext: find the key
  (config, code, memory) rather than attacking the cipher.
- The encoding hides malicious content (phishing, malware): decode
  fully for the IOC extraction, then handle as malicious.
- The team keeps confusing the two: make this distinction part of the
  secure-coding review checklist.

## Detection and defender view

For defenders, the encoding-versus-encryption distinction matters in
reviews: "encrypted with base64" in a design doc is a red flag that
the design needs rework. Detection-wise, encoded blobs in logs and
traffic are normal; the review catches the misuse before deployment.
Teach the distinction once and the whole team stops making the error.

## Key references

- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CWE-312 (Cleartext Storage of Sensitive Information).
- RFC 4648 (base encodings reference).
