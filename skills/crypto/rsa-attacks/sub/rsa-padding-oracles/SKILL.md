---
name: rsa-padding-oracles
description: Use when a service decrypts RSA ciphertexts and leaks
  padding validity through errors or timing on an authorized engagement
  or CTF. Covers PKCS#1 v1.5 oracle mechanics, Bleichenbacher-style
  attack concepts, identifying oracles, and safe testing discipline. Use
  when error messages differ on bad padding, when a decryption endpoint
  is exposed, or when assessing legacy RSA encryption.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
parent: rsa-attacks
requires: [rsa-attacks]
extends: []
relates: [crypto-fundamentals, api-security-testing]
tools:
  - name: Python
    version: 3.12
  - name: OpenSSL
    version: 3.0
---

A padding oracle is a service that tells you whether RSA decryption had
valid padding: different errors, different timing, different behavior.
That one bit of information, repeated thousands of times, decrypts
ciphertexts without the key. This skill covers understanding and testing
padding oracles on authorized engagements and in CTFs: recognizing the
oracle, understanding the attack shape, and testing safely.

## Quick Workflow

1. Find the RSA decryption endpoint and its error behaviors.
2. Test for the oracle: valid versus invalid padding, compare responses.
3. Characterize the oracle signal: error text, status code, timing.
4. Estimate the query cost (Bleichenbacher needs thousands).
5. Run the attack with established tooling if the scope allows.
6. Report the oracle with the signal evidence and the impact.

## 1. Identifying the oracle

```bash
# The oracle test: send a validly-padded ciphertext and a corrupted one,
# compare EVERYTHING about the responses
# Valid:   00 02 <random nonzero> 00 <message>
# Invalid: 00 03 ... or 00 02 with zero bytes in padding

# Compare: HTTP status, body text, response time, and any secondary effects
for variant in valid invalid; do
  echo "== $variant"
  curl -s -X POST 'https://target.example/decrypt' \
    -H 'Content-Type: application/json' \
    -d "{\"ct\":\"<${variant}_ciphertext_hex>\"}" \
    -o /tmp/oracle_$variant.txt -w '%{http_code} %{time_total}\n'
done
diff /tmp/oracle_valid.txt /tmp/oracle_invalid.txt | head -10
```

Any consistent difference is the oracle: distinct error messages are
the classic, but status codes, timing, and even log-visible differences
count. No difference means no oracle (or a subtler one needing more
probes).

## 2. Attack shape and cost

```python
#!/usr/bin/env python3
"""Bleichenbacher concept: why the oracle decrypts."""

# The attack exploits PKCS#1 v1.5 structure: decrypted value must start
# with 0x00 0x02. The oracle answers "does it start with 0x00 0x02?"
# for any ciphertext you submit.
#
# 1. Blind the target ciphertext: c' = c * s^e mod n for chosen s
# 2. Ask the oracle about c'; keep s values that give valid padding
# 3. Each valid s narrows the possible plaintext interval
# 4. Iterate until the interval holds one value: the plaintext
#
# Cost: thousands to millions of oracle queries depending on the
# oracle strength and key size. A fast, stable oracle is required.
```

The query count is the feasibility test: a million queries at 10ms
each is hours (feasible); at 1s each with rate limiting, it is not.
Measure the oracle's speed and stability before committing, and get
scope approval for the query volume: this attack is loud.

## 3. Safe testing discipline

```bash
# Rules for oracle testing on authorized targets:
# - Never run the full attack against production without explicit approval
# - Prove the oracle exists (the signal difference); the attack's
#   feasibility follows from published query counts
# - Test the full attack in a lab replica or staging first
# - Rate-limit yourself: the attack's traffic looks like an attack
#   because it is one; coordinate with the SOC

# The report needs: the oracle signal (evidence), the attack it enables,
# and the fix. A proven oracle plus the published attack is a complete
# finding without burning a million production queries.
```

Modern TLS removed RSA key exchange largely because of these oracles;
finding one in a custom protocol or legacy system is a significant
result. The fix is OAEP (or better, hybrid encryption with AEAD), plus
uniform error handling that never distinguishes padding failures.

## Edge cases

- The oracle is timing-based and noisy. Statistical testing over many
  samples can still extract the signal; measure the noise first.
- The service rate-limits decryption. The attack may be infeasible in
  practice; report the oracle with the measured rate limit as the
  mitigating factor.
- Only one error message exists but timing differs. That IS an oracle;
  test it statistically before dismissing.
- The padding is OAEP. Bleichenbacher does not apply; OAEP has its own
  (much harder) attack surface, usually via implementation flaws.

## Escalation

- The oracle is confirmed and the scope allows the full attack: use
  established implementations, run against the lab replica first, then
  the target with monitoring.
- The full attack is out of scope: the proven oracle plus the attack
  description is the complete finding; do not run what you cannot run.
- The protocol needs redesign: recommend RSA-KEM or hybrid encryption,
  never textbook or PKCS#1 v1.5 for new designs.

## Detection and defender view

For defenders, padding oracles show as high-volume decryption requests
with manipulated ciphertexts from one source: the query pattern is
distinctive. Defenses are OAEP for all RSA encryption, uniform error
responses (one error for all decryption failures), rate limiting
decryption endpoints, and monitoring for oracle-style query bursts. The
strategic fix is moving away from RSA encryption toward elliptic-curve
hybrid schemes.

## Key references

- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- Bleichenbacher (1998): chosen ciphertext attacks on PKCS#1.
- NIST SP 800-56B (RSA key establishment, padding guidance).
