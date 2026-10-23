---
name: defi-threats
description: Use when assessing DeFi protocols for economic and technical
  attacks on an authorized engagement. Covers flash loan attacks, oracle
  manipulation, sandwich attacks, and governance takeovers at the design
  level. Also use when reviewing whether a protocol's economic
  assumptions hold under adversarial pressure.
version: 1.0.0
domain: blockchain
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [smart-contract-audit, bridge-attacks, dao-governance-risks]
tools:
  - name: Python
    version: 3.12
---

DeFi attackers do not break code, they break assumptions: that prices
are fair, that liquidity is deep, that voters are honest. This skill
covers authorized assessment of DeFi threat models: mapping the
economic assumptions, testing them on forks, and reviewing the
mitigations. Test on local mainnet forks, never against live
protocols.

## Quick Workflow

1. Map the money flows: deposits, borrows, swaps, liquidations, and
   fees, with the contracts involved.
2. List every external dependency: oracles, DEX pools, and other
   protocols it composes with.
3. Identify the economic assumptions: price sources, liquidity depth,
   and honest majority assumptions.
4. Test flash loan attacks on a fork: borrow, manipulate, profit,
   repay, all in one transaction.
5. Test oracle manipulation: move the price source and see what the
   protocol does.
6. Review MEV exposure: can transactions be sandwiched or frontrun for
   profit.
7. Check governance: can an attacker buy votes and change the rules.
8. Report each broken assumption with the fork test that broke it.

## 1. Fork based testing setup

```bash
# Fork mainnet locally for safe testing (needs an RPC URL you control)
anvil --fork-url "$RPC_URL" --fork-block-number 21000000 &
echo "local fork on 127.0.0.1:8545; fund a test account and attack the fork"
```

```bash
# Impersonate a whale account on the fork to get test capital
cast rpc anvil_impersonateAccount 0xWhaleAddress --rpc-url http://127.0.0.1:8545
# Never do this on mainnet; it only works on your local fork
```

## 2. Oracle manipulation test pattern

```python
#!/usr/bin/env python3
"""Oracle manipulation test outline (run against your local fork)."""
print("attack pattern:")
print("1. read the protocol's price source (which pool, which oracle)")
print("2. on the fork, swap a large amount to move the pool price")
print("3. call the protocol function that reads the manipulated price")
print("4. measure the profit: borrow too much, liquidate unfairly, etc.")
print("5. check mitigations: TWAP window, Chainlink fallback, sanity bounds")
```

```bash
# Inspect what the protocol actually reads for prices
grep -rn "getReserves\|latestRoundData\|consult\|quote" contracts/ | head -20
# Then on the fork: move the underlying pool and observe the effect
```

## 3. Flash loan attack surface checklist

```bash
# Functions callable in one transaction that depend on manipulable state
grep -rn "flashLoan\|borrow\|liquidate" contracts/ --include="*.sol" | head -20
# For each: what stops an attacker from borrowing big, distorting a
# price, and extracting value before repaying in the same transaction
```

## Edge cases

- The fork drifts from mainnet state. Pin the block number and note
  it; results are valid for that state.
- Mitigations exist but have parameters (TWAP window, deviation
  thresholds). Test the boundary values, not just the happy path.
- The protocol is upgradeable. Economic review must cover the admin's
  power too, not just the current logic.
- Composability: the protocol is safe alone but dangerous combined
  with another protocol's feature. Test the composition.

## Escalation

- Attack unprofitable on the fork due to gas or slippage: compute the
  capital threshold where it becomes profitable and report that.
- Logic too complex for manual review: use symbolic execution or
  fuzzing (Foundry invariant tests) on the critical invariants.
- Governance risk found: hand to dao-governance-risks for the deep
  review.

## Detection and defender view

DeFi defenders monitor mempools for attack transactions, oracles for
deviations, and admin actions for surprises. They defend with TWAP
oracles, borrow caps, pause mechanisms, and bug bounties sized to the
TVL. The durable lesson from every major DeFi hack is that economic
assumptions need the same rigor as code: document them, test them
adversarially, and monitor them live.

## Key references

- SWC Registry: oracle and access weaknesses.
- Major incident post mortems: oracle manipulation case studies.
- Flash loan attack literature and mitigations.
