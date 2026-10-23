---
name: bridge-attacks
description: Use when assessing cross chain bridge security on an
  authorized engagement. Covers bridge architectures, validator and
  relayer trust models, message verification flaws, and the classic
  bridge hack patterns. Also use when reviewing how a protocol moves
  assets between chains safely.
version: 1.0.0
domain: blockchain
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [smart-contract-audit, defi-threats, blockchain-forensics]
tools:
  - name: Python
    version: 3.12
  - name: Slither
    version: 0.11.0
---

Bridges hold enormous value and have lost billions: they lock assets
on one chain and mint representations on another, and the verification
in between is where the hacks happen. This skill covers authorized
assessment of bridge designs: architecture mapping, trust model
review, and testing the message verification that guards the mint.
Test on forks and testnets, never live bridges.

## Quick Workflow

1. Map the architecture: lock and mint, burn and release, or liquidity
   pools, on each chain.
2. Identify the trust model: validator set, multisig, optimistic
   fraud proofs, or light client verification.
3. Review message verification: what proof does the destination chain
   require before minting.
4. Check the validator or relayer set: size, key management, and what
   a compromise of N of M means.
5. Test the classic patterns on a fork: fake deposits, replayed
   messages, and uninitialized contracts.
6. Review upgradeability and pause: who can stop the bridge in an
   emergency.
7. Check liquidity and rate limits: caps that bound the damage.
8. Report each trust assumption with its compromise cost.

## 1. Message verification review

```bash
# Find the mint/release path and its authorization check
grep -rn "mint\|release" bridge-contracts/contracts --include="*.sol" | grep -i "function" | head -20
```

```solidity
// VULNERABLE pattern (simplified from real hacks):
// mint trusts a message without verifying it came from the source chain
function mint(address to, uint256 amt, bytes calldata proof) external {
    // missing: verify proof against source chain state
    _mint(to, amt);
}

// What to look for: the proof verification step, and who can bypass it
```

```bash
# Check initialization: many bridge hacks used uninitialized proxies
grep -rn "initialize\|initializer" bridge-contracts/contracts --include="*.sol" | head -20
# Then verify on chain (fork): was initialize actually called, and by whom
```

## 2. Validator set analysis

```bash
# Enumerate the validator/multisig set and threshold
# (adapt to the bridge's contracts: often a Gnosis Safe or custom multisig)
python3 - << 'PY'
print("record: number of validators, threshold, key holders")
print("compute: cost to compromise threshold (bribe, hack, coerce)")
print("flag: threshold <= 2, anonymous validators, shared infrastructure")
PY
```

```bash
# Check for pause and upgrade controls
grep -rn "pause\|unpause\|upgradeTo" bridge-contracts/contracts --include="*.sol" | head -10
# A bridge with no pause and no upgrade path cannot respond to an incident
```

## Edge cases

- The bridge uses zero knowledge proofs. Review the circuit trust
  setup and the verifier contract, not just the Solidity.
- Liquidity network bridges have different risks (liquidity theft,
  not minting). Adjust the checklist to the architecture.
- The bridge is deprecated but still holds value. Old bridges get
  attacked; recommend migration, not just monitoring.

## Escalation

- Verification flaw suspected: prove it on a local fork with a forged
  message before reporting.
- Validator compromise suspected on a live bridge: this is an
  emergency disclosure to the bridge team, not a routine finding.
- Design is fundamentally custodial: say so plainly so users price
  the trust correctly.

## Detection and defender view

Bridge defenders monitor for unusual mint volumes, validator key
usage anomalies, and pause worthy events with automated circuit
breakers. They defend with rate limits, per transaction caps,
multisig thresholds that require real distribution, and incident
runbooks that can pause both sides. The history of bridge hacks says
the verification step deserves the most review budget.

## Key references

- CWE-862 (Missing Authorization): unverified mint paths.
- CWE-306 (Missing Authentication for Critical Function).
- Major bridge incident post mortems: verification bypass patterns.
- SWC Registry: proxy and initialization weaknesses.
