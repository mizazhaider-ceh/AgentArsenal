---
name: crypto-fundamentals
description: Use when you face hashes, tokens, or ciphertext on an authorized test, CTF, or code review and need an operator-grade crypto workflow. Covers hash identification and cracking with hashcat and John the Ripper (wordlists, rules, masks, and when to stop), why encoding such as base64 and hex is not encryption, JWT attacks (alg none, algorithm confusion, weak HMAC secrets), RSA pitfalls (small public exponents, shared prime factors, textbook RSA without padding), AES mode failures (ECB cut-and-paste, CBC padding oracles, predictable IVs), randomness failures in tokens and nonces, and practical tooling with CyberChef and OpenSSL. Emphasizes recognizing primitives before attacking them and never rolling custom crypto.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [web-sqli]
tools:
  - name: hashcat
    version: 7.x
  - name: john
    version: 1.9.0-jumbo-1
  - name: cyberchef
    version: 10.x
  - name: openssl
    version: 3.3.x
---

Cryptography for operators is about recognition and disciplined attack, not mathematics. On authorized tests you will meet hashes to crack, tokens to forge, and ciphertext to peel, and the winning move is almost always identifying the exact primitive and its misconfiguration rather than breaking the math. This skill gives you that workflow: tell encoding from encryption, identify the hash, crack it efficiently, abuse JWT and RSA misconfigurations, understand padding oracles conceptually, and use CyberChef and OpenSSL as your workbench. Never design your own crypto, and never attack crypto outside authorized scope.

## Quick Workflow

1. Identify the primitive: hash, encoding, symmetric ciphertext, asymmetric ciphertext, or structured token.
2. Rule out encoding first: base64, hex, and URL encoding are not encryption and decode instantly.
3. For hashes: identify the algorithm and mode, then crack in order, wordlist, rules, mask, and know when to stop.
4. For JWTs: decode the header, then test alg none, algorithm confusion, and weak HMAC secrets.
5. For RSA: check key size, public exponent, and whether the modulus shares factors with other keys.
6. For AES: determine the mode. ECB means cut-and-paste; CBC with error messages means test for padding oracles.
7. Document the primitive, the parameters, and the exact commands so the finding is reproducible.

## Phase 1: Encoding is not encryption

Half of all "crypto" challenges on tests are encoding. Base64, hex, URL encoding, and ROT13 provide zero confidentiality; they only change representation. Decode before assuming encryption.

```bash
echo 'aGVsbG8gd29ybGQ=' | base64 -d; echo
echo '68656c6c6f' | xxd -r -p; echo
python3 -c "import urllib.parse; print(urllib.parse.unquote('hello%20world'))"
```

In CyberChef, the "Magic" operation auto-detects many encodings, which makes it the fastest triage tool for unknown blobs. Also common: base64 of hex, hex of base64, and gzip or zlib compressed then encoded. If decoding produces another encoded-looking blob, decode again before concluding anything.

Hashes are not encryption either: they are one-way. You do not decrypt a hash; you guess inputs until one matches (cracking), or you find the plaintext elsewhere.

## Phase 2: Hash identification and cracking

Identify the algorithm from length and alphabet before choosing a hashcat mode:

- 32 hex chars: MD5 (mode 0) or NTLM (mode 1000). Distinguish by context: Windows SAM output is NTLM.
- 40 hex chars: SHA-1 (mode 100).
- 64 hex chars: SHA-256 (mode 1400).
- bcrypt `$2b$` / `$2y$` prefix (mode 3200): slow, wordlist-only, be patient.
- `$6$` prefix: SHA-512 crypt (mode 1800).

Crack in order of increasing cost. Wordlist first:

```bash
hashcat -m 0 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt
```

Then rules, which mutate each wordlist entry (case, suffixes, leetspeak):

```bash
hashcat -m 0 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

Then mask attack for known patterns (for example 8 lowercase letters followed by 2 digits):

```bash
hashcat -m 0 -a 3 hashes.txt '?l?l?l?l?l?l?l?l?d?d'
```

John the Ripper covers formats hashcat handles awkwardly and has excellent auto-detection:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5 hashes.txt
john --show --format=Raw-MD5 hashes.txt
```

Salted hashes need the salt in the input format hashcat expects; check the hashcat example hashes page for the exact layout. Know when to stop: bcrypt at high cost against a strong password is not worth days of GPU time on a test. Report it as a finding about password policy instead (CWE-521, CWE-916).

## Phase 3: JWT attacks

Decode the token first. A JWT is three base64url segments: header, payload, signature.

```bash
echo '<jwt>' | cut -d. -f1 | base64 -d 2>/dev/null; echo
echo '<jwt>' | cut -d. -f2 | base64 -d 2>/dev/null; echo
```

Attack in this order:

1. `alg: none`: strip the signature segment and set the header algorithm to `none`. Some libraries accept it.

```bash
python3 - <<'EOF'
import base64, json
def b64d(s): return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))
header = json.loads(b64d('<h>')); payload = json.loads(b64d('<p>'))
header['alg'] = 'none'
def b64e(o): return base64.urlsafe_b64encode(json.dumps(o).separators=(',',':')).encode()).decode().rstrip('=')
print(b64e(header) + '.' + b64e(payload) + '.')
EOF
```

2. Algorithm confusion: if the server publishes an RSA public key (or you can fetch it from a JWKS endpoint) and accepts `HS256`, sign with HMAC using the RSA public key as the HMAC secret.
3. Weak HMAC secret: crack the secret offline with hashcat mode 16500 and a wordlist, then forge arbitrary tokens.
4. Missing validation: `kid` header pointing to a file you control, or `jku` pointing at your server. Test each header parameter the library honors.

Always verify impact by actually using the forged token against the application; a parser quirk that the application rejects is not a finding.

## Phase 4: RSA pitfalls

You will rarely break RSA math, but implementations hand you the keys constantly:

- Small public exponent (e=3) with textbook RSA (no padding): cube-root attack on small messages. Check padding first; OAEP or PKCS#1 v1.5 padding defeats the naive version.
- Shared prime factors: if two moduli share a prime (broken RNG on embedded devices), `gcd(n1, n2)` recovers it instantly.

```bash
python3 - <<'EOF'
import math
n1 = int('...', 16); n2 = int('...', 16)
p = math.gcd(n1, n2)
print('shared factor found' if p != 1 else 'no shared factor')
EOF
```

- Small private exponent or small key size (512-bit): factorable with modern tools; treat anything under 2048 bits as a finding.
- Textbook RSA is malleable: multiplying ciphertexts multiplies plaintexts. This matters for blind signatures and voting-style schemes, not for padded encryption.
- Private key files lying around: check for `BEGIN RSA PRIVATE KEY` in repos, backups, and config directories. The most common RSA break is no break at all, just a leaked key.

## Phase 5: AES mode failures

Identify the mode before attacking. ECB is visually recognizable: identical plaintext blocks produce identical ciphertext blocks (the classic ECB penguin). If you can submit chosen plaintext and see repeated 16-byte ciphertext blocks, it is ECB, and cut-and-paste attacks let you rearrange blocks to forge messages.

CBC needs an unpredictable IV (CWE-329 covers predictable IVs). Reused or predictable IVs leak whether two messages share a prefix. CBC is also malleable: flipping a ciphertext bit garbles one plaintext block and flips the same bit in the next, which enables padding oracle attacks.

Padding oracle concept: if the server tells you (even through timing or a generic error difference) whether decrypted padding was valid, you can decrypt the entire message byte by byte without the key, and then forge valid ciphertexts. Requirements: a CBC-mode decryption oracle, distinguishable padding responses, and patience (roughly 128 requests per byte). Tools like PadBuster automate it; your job is recognizing the oracle condition in the application behavior.

GCM is the modern default: it provides authentication, which kills padding oracles and malleability. Never accept unauthenticated AES-CBC for new designs; flag it in reviews.

OpenSSL is your workbench for manual verification:

```bash
openssl enc -d -aes-256-cbc -in ct.bin -out pt.bin -K <hexkey> -iv <hexiv>
openssl enc -aes-256-cbc -in pt.bin -out ct.bin -K <hexkey> -iv <hexiv> -p
```

## Phase 6: Randomness and token failures

Predictable randomness breaks tokens, password resets, and nonces:

- Tokens derived from timestamps, PIDs, or `rand()` without a cryptographic seed: brute force the seed space.
- `mt_rand` or Mersenne Twister output: given enough consecutive outputs, the state is recoverable and all future outputs predictable.
- Password reset tokens sent in URLs that never expire or are guessable: test entropy by requesting several and looking for patterns.
- Nonce reuse in stream ciphers or GCM: catastrophic. Two ciphertexts under the same keystream XOR to the XOR of the plaintexts.

Test empirically: request the same token or nonce twice, request many in sequence, and check for structure. Document the generation code path from source review when you have it; black-box pattern analysis plus source confirmation is the strongest finding.

## Edge cases

- Hashcat reports "no hashes loaded": the input format is wrong for the mode. Check the example hashes for the exact expected layout, especially for salted formats.
- The hash is salted with an unknown salt: check the application source or database schema; salts are usually stored alongside the hash. Without the salt, switch to targeting the authentication flow instead.
- JWT attacks fail: the library may validate strictly. Confirm which validations actually happen (expiry, issuer, audience) before claiming bypasses; a forged token the app rejects is not a finding.
- Padding oracle gives no signal: generic error pages and constant-time responses close the oracle. Timing oracles need statistical measurement over many samples; do not eyeball single requests.
- RSA key looks fine: move on. Do not burn test time factoring 2048-bit keys; the finding is elsewhere.
- CyberChef "Magic" misidentifies the blob: it is a heuristic. Fall back to manual inspection of length, alphabet, and structure.

## Escalation

- Cracking stalls: escalate from wordlist to rules to masks to targeted wordlists built from the target (cewl-style scraping of their site, or context words from the engagement). Combinator attacks bridge the gap between wordlists and masks.
- One crypto primitive resists: pivot to where the key lives instead of the math. Keys in config files, environment variables, backups, and version control beat cryptanalysis every time.
- Custom crypto in source code: review it as code, not as math. Look for hardcoded keys (CWE-321), home-rolled padding, ECB mode, and weak RNG. Custom constructions fail at the construction level long before the primitive level.
- Protocol-level questions (TLS downgrade, weak cipher negotiation): test with testssl or openssl s_client against authorized targets and report the negotiable weak suites, not just the certificate.

## Detection and defender view

- Cracking activity is noisy: massive GPU usage and wordlist transfers on a server are anomalous. Monitor for hashcat and John binaries outside approved jump hosts.
- JWT abuse is visible in authentication logs: algorithm changes, missing signatures, and `kid` values pointing at unexpected files. Log the full token header on auth failures.
- Padding oracle probing looks like hundreds of similar requests with single-byte differences. Rate limiting and alerting on error-rate spikes catch it.
- Defenders prevent this class with: Argon2 or bcrypt with proper cost for passwords, authenticated encryption (AES-GCM) everywhere, cryptographically secure RNGs for all tokens, short-lived JWTs with strict validation, and key management in a KMS or HSM instead of config files.

## Key references

- MITRE ATT&CK: T1110.002 (Password Cracking), T1552.004 (Private Keys), T1606.001 (Web Cookies, for session token abuse), T1557 (Adversary-in-the-Middle, for crypto downgrade contexts).
- CWE: CWE-327 (Use of a Broken or Risky Cryptographic Algorithm), CWE-328 (Use of Weak Hash), CWE-329 (Generation of Predictable IV with CBC Mode), CWE-330 (Use of Insufficiently Random Values), CWE-338 (Use of Cryptographically Weak PRNG), CWE-347 (Improper Verification of Cryptographic Signature), CWE-354 (Improper Validation of Integrity Check Value), CWE-321 (Use of Hard-coded Cryptographic Key), CWE-326 (Inadequate Encryption Strength), CWE-780 (Use of RSA Algorithm without OAEP), CWE-760 (Use of a One-Way Hash with a Predictable Salt), CWE-916 (Use of Password Hash With Insufficient Computational Effort), CWE-208 (Observable Timing Discrepancy).
- Standards and docs: hashcat example hashes (hashcat.net wiki), John the Ripper documentation (openwall.com), CyberChef (gchq.github.io/CyberChef), NIST SP 800-63B (password guidance), OWASP JWT Cheat Sheet.
