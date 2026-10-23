---
name: secure-boot-bypass
description: Use when assessing secure boot implementations on devices
  you own or have authorization to test. Covers boot chain mapping,
  signature verification review, rollback protection checks, and common
  bypass classes at the design level. Also use when reviewing whether a
  device's chain of trust actually holds from ROM to application.
version: 1.0.0
domain: hardware
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [firmware-analysis, glitching-attacks, uart-jtag]
tools:
  - name: Ghidra
    version: 11.3
  - name: Python
    version: 3.12
  - name: OpenSSL
    version: 3.4
---

Secure boot is a chain of signatures from immutable ROM to the
application: each stage verifies the next before running it. Bypasses
break a link: a skipped check, a confused parser, a rollback to a
signed but vulnerable version. This skill covers authorized assessment
of secure boot on your own devices: mapping the chain, reviewing each
verification step, and testing the classic bypass classes without
damaging the device.

## Quick Workflow

1. Map the boot chain: ROM, first stage loader, second stage, kernel,
   application, and what verifies what.
2. Find the root of trust: where the first key lives (OTP, fuses) and
   whether it can be changed.
3. Review each verification step for the classic flaws: unchecked
   return values, TOCTOU between check and use, and parser bugs.
4. Check rollback protection: can a signed old version with known bugs
   still boot.
5. Check key management: test keys in production, debug unlock paths.
6. Attempt only in scope bypass tests on your own device, starting with
   software level tricks.
7. Document every link in the chain and its strength.
8. Recommend fixes per link, not just "enable secure boot".

## 1. Chain mapping and verification review

```bash
# Extract each boot stage from the flash dump (offsets from binwalk)
binwalk -e -C /tmp/boot_chain /tmp/flash_a.bin
ls -l /tmp/boot_chain/_flash_a.bin.extracted/ | head

# Check what each stage verifies: look for crypto and compare routines
strings -n 6 /tmp/boot_stage2.bin | grep -i -E "rsa|ecdsa|sha256|signature|verify" | head -20
```

```bash
# Verify a signature yourself to understand the format (lab)
# Extract the public key embedded in the stage (often a raw modulus)
python3 - << 'PY'
# Typical flow to replicate:
# 1. hash = SHA256(image_body)
# 2. rsa_verify(pubkey, signature, hash)
# Reimplement with OpenSSL to confirm you parsed the format right:
print("openssl dgst -sha256 -verify pubkey.pem -signature sig.bin image_body.bin")
PY
openssl dgst -sha256 -verify /tmp/pubkey.pem \
  -signature /tmp/sig.bin /tmp/image_body.bin && echo "signature valid"
```

## 2. Classic bypass classes to test

```bash
# 1. Rollback: is there a version counter, and is it enforced?
#    Look for anti-rollback fuses or version fields in the image header
xxd /tmp/image_header.bin | head -10
# Try booting the oldest signed image you can find (your own device)

# 2. TOCTOU: is the verified buffer the same one that gets executed?
#    Review: does verification read from flash while boot copies from RAM?

# 3. Parser confusion: does the image parser accept overlapping or
#    duplicate sections that change what is verified vs what runs?

# 4. Debug unlock: does a debug command disable verification?
grep -ai "secureboot.*disable\|sb_disable\|debug.*unlock" /tmp/flash_a.bin | head -5
```

```bash
# Check for test keys: production images signed with "test" or "debug" keys
strings -n 10 /tmp/flash_a.bin | grep -i -E "test.*key|debug.*key|do not ship" | head -10
# A test key in production means anyone with the test private key
# (often leaked in SDKs) can sign arbitrary firmware
```

## Edge cases

- The ROM stage is undocumented. Infer its behavior from the first
  mutable stage and from vendor security whitepapers.
- Verification uses a custom crypto implementation. Review it for the
  classic bugs (padding oracle in RSA, short exponents) before
  assuming the chain is sound.
- Rollback fuses are one time programmable and already burned. You
  cannot test rollback on that unit; test on a fresh unit or review
  only.
- The device boots encrypted images. You need the key management
  review, not image modification tests.

## Escalation

- Software review finds nothing: consider fault injection against the
  verification step (see glitching-attacks) on your own device.
- Fault injection out of scope: report the chain as reviewed with no
  software bypass found, and note the residual physical risk.
- Chain is sound but update delivery is not: pivot to the update
  mechanism (transport, parsing) as the weaker link.

## Detection and defender view

Defenders monitor secure boot through attestation: the device reports
measurements of each boot stage to a verifier. They detect bypasses
with boot failure counters, anti rollback fuse state, and remote
attestation mismatches. The durable design is a minimal ROM verifier,
hardware protected keys, enforced rollback counters, and measured boot
so a bypassed device cannot attest as healthy.

## Key references

- CWE-1191 (On-Chip Debug and Test Interface With Improper Access
  Control).
- CWE-347 (Improper Verification of Cryptographic Signature).
- CWE-494 (Download of Code Without Integrity Check).
- NIST SP 800-193: platform firmware resiliency guidelines.
