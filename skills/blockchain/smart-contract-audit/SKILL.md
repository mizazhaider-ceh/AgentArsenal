---
name: smart-contract-audit
description: Use when auditing Solidity smart contracts on an authorized
  engagement or for your own project. Covers static analysis with
  Slither, manual review of access control and arithmetic, reentrancy
  testing, and upgradeability review. Also use when a DeFi protocol
  needs a security review before mainnet deployment.
version: 1.0.0
domain: blockchain
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding, code-reviewer, defi-threats]
tools:
  - name: Python
    version: 3.12
  - name: Slither
    version: 0.11.0
---

Smart contract bugs are final: once deployed, the code holds real
money and often cannot be patched. This skill covers the audit method
for Solidity contracts you are authorized to review: automated
scanning with Slither, focused manual review of the dangerous
patterns, and upgradeability checks. Work on testnets and local forks,
never against mainnet contracts you do not own.

## Quick Workflow

1. Get the full scope: contracts, deployment scripts, docs, and the
   threat model (who is trusted, what is the worst loss).
2. Compile cleanly and run Slither; triage every high and medium
   finding.
3. Review access control on every state changing function: who can
   call it and what it can do.
4. Check arithmetic, reentrancy, and oracle usage manually; scanners
   miss logic bugs.
5. Review upgradeability: proxy patterns, admin keys, and timelocks.
6. Test economic attacks on a local fork: flash loans, price
   manipulation, and sandwiching.
7. Write findings with severity, proof of concept, and fix.
8. Recommend a retest after fixes and monitoring for the admin keys.

## 1. Static analysis with Slither

```bash
# Compile and scan (assumes a hardhat or foundry project you own)
cd /tmp/audit/target-project
slither . --exclude-dependencies
```

```bash
# Triage: focus on high impact detectors first
slither . --exclude-dependencies 2>&1 | grep -A3 -i "reentrancy\|access\|arbitrary" | head -40
# False positives are common; confirm each one by reading the code
```

```bash
# Printer for quick overviews: inheritance, variables, function summary
slither . --print inheritance --print variable-order 2>/dev/null | head -60
```

## 2. Manual review checklist

```bash
# Access control: every external/public state changing function needs
# an explicit check; list functions and their modifiers
grep -rn "function.*public\|function.*external" contracts/ | head -30
```

```solidity
// VULNERABLE: no access control on a sensitive function
function setOwner(address n) public { owner = n; }

// FIXED: restrict to the current owner
function setOwner(address n) public onlyOwner { owner = n; }
```

```solidity
// VULNERABLE: reentrancy, state updated after external call
function withdraw() public {
    (bool ok,) = msg.sender.call{value: balances[msg.sender]}("");
    require(ok);
    balances[msg.sender] = 0;  // too late
}

// FIXED: checks-effects-interactions
function withdraw() public {
    uint256 amt = balances[msg.sender];
    balances[msg.sender] = 0;
    (bool ok,) = msg.sender.call{value: amt}("");
    require(ok);
}
```

```bash
# Oracle review: where do prices come from, and can they be manipulated?
grep -rn "getReserves\|latestRoundData\|price" contracts/ | head -20
# Single source spot prices are manipulable; check for TWAP or Chainlink
```

## 3. Upgradeability review

```bash
# Proxy pattern check: who is the admin, is there a timelock
grep -rn "TransparentUpgradeableProxy\|UUPS\|upgradeTo\|_authorizeUpgrade" contracts/ | head -20
# Findings: EOA admin with no timelock, missing upgrade authorization,
# storage collisions between proxy and implementation
```

## Edge cases

- The code uses inline assembly. Review it line by line; scanners
  struggle with assembly and it often handles memory unsafely.
- Upgradeable contracts use initializers, not constructors. Check
  that initialize cannot be called twice or front run.
- The protocol relies on off chain keepers or oracles. Those are
  trusted third parties; document the trust assumption.
- Findings depend on economic conditions (low liquidity). State the
  assumptions so the severity is honest.

## Escalation

- Slither will not run (old Solidity version): pin a compatible
  solc with `solc-select` and retry, or review manually.
- Logic bug suspected but not proven: write a Foundry test that
  demonstrates the exploit on a local fork.
- Admin key risk dominates: recommend multisig plus timelock and
  monitoring, since code cannot fix key management.

## Detection and defender view

Defenders of live protocols monitor for exploit patterns: flash loans
followed by large swaps, admin key usage, upgrade events, and oracle
deviations. They use pausable contracts, bug bounties, and real time
monitoring (Forta style bots). The durable defense is layered: audit,
formal verification for critical invariants, timelocked upgrades, and
incident response runbooks for pausing.

## Key references

- CWE-841 (Improper Enforcement of Behavioral Workflow): reentrancy.
- CWE-862 (Missing Authorization): access control gaps.
- CWE-682 (Incorrect Calculation): arithmetic and oracle issues.
- SWC Registry: smart contract weakness classification.
- Slither 0.11.0 documentation: detectors and printers.
