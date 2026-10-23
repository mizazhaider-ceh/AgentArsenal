---
name: post-quantum-basics
description: Use when you need working knowledge of post quantum
  cryptography for planning and assessment. Covers the threat model,
  NIST standardized algorithms, hybrid deployments, and migration
  planning. Also use when a client asks what quantum computing means
  for their crypto inventory.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [crypto-fundamentals, tls-analysis, ecc-crypto-attacks]
tools:
  - name: Python
    version: 3.12
  - name: OpenSSL
    version: 3.4
---

Quantum computers threaten RSA and ECC through Shor's algorithm:
"harvest now, decrypt later" means recorded traffic is already at
risk. This skill gives the working knowledge for migration planning:
which algorithms are threatened, what NIST standardized, how hybrids
work, and how to inventory crypto for the transition. It is planning
and assessment, not quantum physics.

## Quick Workflow

1. Learn the threat: Shor breaks RSA/ECC, Grover weakens symmetric
   (double key lengths).
2. Inventory crypto: where RSA/ECC is used, key sizes, and data
   lifetimes.
3. Prioritize by harvest risk: long lived secrets in recorded
   traffic first.
4. Learn the NIST standards: ML-KEM (key exchange), ML-DSA and
   SLH-DSA (signatures).
5. Plan hybrids: classical plus PQC during the transition.
6. Check library support: what your stack already offers.
7. Review agility: can the system swap algorithms without a rewrite.
8. Write the migration roadmap with phases and owners.

## 1. Inventory and prioritization

```bash
# Crypto inventory: find RSA/ECC usage and key sizes
grep -rn "RSA\|ECDSA\|secp256\|BEGIN RSA PRIVATE KEY" \
  --include="*.py" --include="*.conf" --include="*.pem" /etc/app/ 2>/dev/null | head -20
# TLS: check negotiated key exchange on important endpoints
openssl s_client -connect app.example:443 -tls1_3 2>/dev/null | grep -i "key exchange\|server temp key" | head -5
```

```python
#!/usr/bin/env python3
"""Harvest risk prioritization."""
assets = [
    ("customer PII archive (10y retention)", "RSA-2040 TLS", 10),
    ("session tokens (1h lifetime)", "ECDHE P-256", 0.1),
    ("code signing keys", "RSA-3072", 5),
    ("database backups (7y)", "RSA-2048", 7),
]
for name, crypto, years in sorted(assets, key=lambda a: a[2], reverse=True):
    print(f"{years:4.1f}y  {crypto:15s} {name}")
print("migrate long lived secrets first; short lived sessions last")
```

## 2. Standards and hybrid check

```bash
# NIST standards to know:
# - ML-KEM (FIPS 203): key encapsulation, replaces ECDH/RSA KEM
# - ML-DSA (FIPS 204): signatures, replaces ECDSA/RSA
# - SLH-DSA (FIPS 205): hash based signatures, conservative backup
# Check your OpenSSL/provider for PQC support:
openssl list -providers 2>/dev/null | head
# Hybrid TLS: X25519+ML-KEM already shipping in browsers; verify your
# servers negotiate it where clients offer it
```

## Edge cases

- The vendor has no PQC roadmap. Document the dependency and set a
  review date; you cannot migrate alone.
- Performance concerns (larger keys, slower signs). Benchmark on
  your workload; ML-KEM is fast, signatures need sizing.
- Long lived embedded devices. They may never migrate; plan
  compensating controls and replacement cycles.

## Escalation

- Regulatory deadline applies (government timelines): build the
  inventory now, since migration takes years.
- Immediate risk (state level harvest): prioritize the long lived
  data paths first.

## Detection and defender view

PQC migration is defensive preparation: inventory, prioritize, and
migrate before the threat materializes. "Detection" here means
tracking the migration: which systems still use quantum vulnerable
algorithms, and the timeline to fix them. The durable practice is
crypto agility: algorithm identifiers in protocols, no hardcoded
suites, and a standing inventory.

## Key references

- NIST FIPS 203, 204, 205: the PQC standards.
- NIST IR 8547 (migration guidance).
- Related skills: crypto-fundamentals, tls-analysis.
