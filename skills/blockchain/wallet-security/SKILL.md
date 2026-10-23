---
name: wallet-security
description: Use when reviewing cryptocurrency wallet security for users
  or on an authorized product assessment. Covers seed phrase handling,
  hardware versus software wallets, transaction signing risks, and
  common theft techniques to defend against. Also use when advising on
  safe custody setups for teams.
version: 1.0.0
domain: blockchain
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding, phishing-defense, blockchain-forensics]
tools:
  - name: Python
    version: 3.12
---

Wallets are where users meet the blockchain, and almost all crypto
theft is wallet compromise, not chain compromise: phishing, malicious
signing requests, and clipboard malware. This skill covers defensive
review: how wallets should handle keys, what attacks to expect, and
how to set up custody that survives mistakes. It is defensive and
educational; it does not cover stealing anyone's funds.

## Quick Workflow

1. Classify the wallet: hot or cold, custodial or self custody,
   single sig or multisig.
2. Review seed phrase handling: generation, display, storage, and
   recovery flows.
3. Check transaction signing: what the user sees before signing, and
   whether blind signing is possible.
4. Test the dApp connection flow for phishing resistance.
5. Review the common theft techniques against this wallet type.
6. Recommend a custody setup matched to the value at risk.
7. Document backup and inheritance procedures.
8. Verify the setup with a small test transaction before funding.

## 1. Seed and key handling review

```bash
# Review checklist for a wallet product (code and UX)
# - seed generated with a CSPRNG (check the randomness source)
# - seed shown once, never logged, never sent to a server
# - optional passphrase (25th word) supported
# - no cloud backup of the raw seed without user opt in and encryption
grep -rn "mnemonic\|seed\|entropy" wallet-src/ -i | head -20
```

```python
#!/usr/bin/env python3
"""Entropy sanity check for a test wallet implementation (lab only)."""
import secrets
# A proper wallet uses OS level randomness; verify the source, not the output
print("secrets module source:", secrets.__file__)
seed = secrets.token_bytes(32)
print("generated 256 bits:", seed.hex()[:32], "...")
# Never generate real seeds in a script you might log or share
```

## 2. Signing risk review

```bash
# What does the user see before signing? Check:
# - full recipient address (not truncated to first/last chars only)
# - exact amount and token
# - contract method name in plain language
# - domain and chain ID for EIP-712 (anti replay across chains)
echo "blind signing (approving unreadable data) is the top risk;"
echo "hardware wallets with clear signing are the mitigation"
```

```bash
# Common theft techniques to brief users on:
# - clipboard hijackers swapping pasted addresses (verify on device screen)
# - fake wallet apps and phishing sites (bookmark, verify signatures)
# - malicious token approvals (revoke unused approvals regularly)
# - address poisoning (similar looking addresses in history; verify fully)
echo "defense: verify addresses on the hardware screen, keep approvals minimal"
```

## 3. Custody setup guidance

```bash
# Tiered recommendation by value at risk:
# small: reputable mobile wallet + seed on paper in one safe place
# medium: hardware wallet + seed split in two locations
# large/team: multisig (2 of 3) across devices and locations + inheritance plan
python3 - << 'PY'
tiers = {
    "small": "hardware wallet, paper backup, test recovery yearly",
    "team": "2-of-3 multisig, geographically split, documented runbook",
}
for k, v in tiers.items():
    print(f"{k}: {v}")
PY
```

## Edge cases

- The user lost the seed. There is no recovery; be honest about that
  and focus on securing what remains.
- Multisig coordinator goes offline. Keep redundant coordinators and
  documented recovery with the seed holders.
- Firmware updates on hardware wallets. Verify the update through the
  vendor's official channel; never from a link in an email.
- Inheritance: without a plan, the funds die with the holder. A
  sealed, lawyer held procedure beats a sticky note.

## Escalation

- Suspected compromise: move funds to a fresh wallet generated on a
  clean device immediately; investigate after.
- Team custody dispute: follow the pre agreed multisig policy; the
  skill cannot resolve human conflicts.
- Product vulnerability found: disclose to the vendor through their
  security channel with a proof of concept on testnet.

## Detection and defender view

Defenders (users and teams) detect wallet attacks through unexpected
approval requests, addresses that do not match the device screen, and
transactions they did not initiate. Monitoring services alert on
drain patterns. The durable defense is process: verify on the
hardware screen, minimize approvals, use multisig for serious money,
and practice recovery before it is needed.

## Key references

- CWE-798 (Use of Hard-coded Credentials): embedded keys in apps.
- CWE-330 (Use of Insufficiently Random Values): weak seed generation.
- EIP-712: typed structured data signing.
- Vendor security advisories for the specific wallet.
