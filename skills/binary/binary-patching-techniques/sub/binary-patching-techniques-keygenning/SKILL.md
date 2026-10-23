---
name: binary-patching-techniques-keygenning
description: Use when you are authorized to analyze a software license
  validation routine, covering locating the check, understanding the algorithm,
  and assessing its strength. Covers finding validation code via strings
  and API references, reading checksum versus cryptographic versus
  server-side schemes, reimplementing the check for analysis, and
  writing the hardening assessment. Use only during authorized security
  assessments of your own or a client's software with explicit written
  permission. Never for bypassing licensing on software you are not
  authorized to assess.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: [binary-patching-techniques]
extends: []
parent: binary-patching-techniques
relates: [binary-patching, binary-anti-analysis-bypass]
tools:
  - name: Ghidra
    version: 11.3
  - name: x64dbg
    version: 2025.06
  - name: Python
    version: 3.12
---

License validation analysis asks one defensive question: how hard is
this scheme to defeat, and what should the vendor change. The work is
reading the validation routine, classifying its strength, and reporting
hardening recommendations. It is not producing working keys or
circumvention tools. This sub-skill covers the analysis methodology for
the parent skill under explicit authorization. Scope: analyze license
validation only for software you own or are engaged to assess, with
written permission, in an isolated lab. If scope is ambiguous, stop and
clarify before proceeding.

## Quick Workflow

1. Confirm written authorization covers license validation analysis.
2. Locate the validation routine via strings ("invalid key",
   "activation failed") and API references (registry reads, network).
3. Read the algorithm in the decompiler: inputs, transforms, verdict.
4. Classify the scheme: checksum, local crypto, server-side, or hybrid.
5. Reimplement the check in Python to verify your understanding.
6. Assess strength and write hardening recommendations.
7. Report findings; do not produce key generators or bypass tools.

## 1. Finding the validation routine

```text
String-led:
  search for "license", "activation", "serial", "invalid key",
  "trial expired", "register" in the string table
  follow cross-references to the using function

API-led:
  RegQueryValueEx on a license key path -> local check
  InternetConnect / HttpSendRequest near validation -> server check
  CryptVerifySignature -> signature-based check
```

In Ghidra, the decompiler view of the validation function is the
primary reading surface. Rename variables as you understand them
(key_buffer, checksum, expected); the function usually reads clearly
once the string references anchor you.

## 2. Scheme classification

```text
Checksum (weak):
  sum of digits % N == 0, or a CRC compared to embedded value
  -> anyone who reads the routine replicates it

Local crypto (medium):
  RSA/ECDSA signature verified with an embedded public key
  -> secure IF the key handling is sound and the check cannot be
     trivially patched (but patching is always possible locally)

Server-side (strong):
  key sent to a server, server returns signed token
  -> the check cannot be replicated offline; attack surface moves
     to token validation and replay

Hybrid:
  local check for UX, server check for authority
  -> assess each layer separately
```

Classify before assessing: a checksum scheme gets "broken by design",
a signature scheme gets "sound crypto, evaluate tamper resistance".

## 3. Reimplementing for understanding

```python
# Example: verify you understand a checksum scheme (analysis only)
def validate(key: str) -> bool:
    digits = [int(c) for c in key if c.isdigit()]
    if len(digits) != 16:
        return False
    return sum(digits) % 7 == 0

# Test against observed behavior, not to generate keys:
# feed keys the application accepted/rejected during dynamic testing
# and confirm your function agrees on all of them
for k, expected in [("1111111111111114", True), ("0000000000000000", False)]:
    assert validate(k) == expected, k
print("model matches observed behavior")
```

The reimplementation is a model for the report, validated against
observed accept/reject behavior. It demonstrates understanding; it is
not a deliverable for circumventing the scheme.

## 4. Assessing tamper resistance

Even strong crypto fails if the check is easy to remove:

- Is the validation result checked in one place or many? (One place:
  single patch point.)
- Does the program verify its own integrity? (No: patching is
  trivial.)
- Is the public key pinned or replaceable? (Replaceable: attacker
  substitutes their own key.)
- Are validation failures fatal or warnings? (Warnings: the program
  runs anyway.)

```text
Assessment shape:
  Scheme:      RSA-2048 signature, server-issued tokens (strong crypto)
  Weakness:    single check in main(), no integrity verification
  Finding:     a one-byte patch bypasses validation despite sound crypto
  Recommendation: move enforcement server-side for protected features;
    add integrity checks as defense in depth (not as sole protection)
```

## 5. Reporting

The deliverable is a findings report:

1. Scope and authorization reference.
2. Scheme description with the algorithm explained.
3. Strength classification with rationale.
4. Specific weaknesses with evidence (addresses, pseudocode).
5. Hardening recommendations ordered by impact.
6. Explicit statement of what was NOT done (no key generators, no
   redistribution of bypasses).

## Edge cases

- Obfuscated validation (VMProtect on the check): analysis cost
  rises sharply; scope the effort and report the obfuscation as a
  finding in itself.
- Time-based licenses: the check includes date logic; analyze the
  clock handling (local clock vs server time).
- Hardware-locked licenses: the check binds to machine identifiers;
  assess identifier spoofability.
- Trial logic: separate from key validation; analyze both, since
  trials are often the weaker path.

- White-box crypto in the validation routine: the key is embedded but obfuscated; analysis cost rises sharply, so scope it explicitly.

## Escalation

- If the assessment uncovers that the vendor's licensing also
  exposes customer data or has a server-side vulnerability, escalate
  immediately under responsible disclosure terms.
- If scope does not explicitly permit this analysis, stop and get
  written clarification; do not proceed on assumptions.
- If asked to produce working keys or a keygen tool, decline: that
  is outside defensive analysis regardless of framing.

- If the vendor's licensing server shows an API flaw discovered during assessment, follow responsible disclosure; do not test beyond scope.

## Detection and defender view

For vendors, this analysis is product security: the output is
hardening guidance (server-side enforcement, signature schemes,
tamper detection as defense in depth). For defenders assessing
third-party software, weak licensing often correlates with weak
overall security posture; note it in vendor risk reviews. The
methodology (locate, classify, model, assess) transfers to any
client-side security control: DRM checks, trial enforcement, and
feature flags all get the same treatment.

## Key references

- Ghidra documentation:
  https://ghidra-sre.org/
- x64dbg documentation:
  https://x64dbg.com/
- NIST guidance on software licensing is out of scope here; assess
  against standard cryptographic practice instead.
- MITRE ATT&CK: T1553 (Subvert Trust Controls), for context on how
  attackers view client-side checks
- Practical Binary Analysis (Dennis Andriesse), Chapters 6-8
  (analysis methodology)
