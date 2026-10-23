---
name: dao-governance-risks
description: Use when assessing DAO governance security on an authorized
  engagement. Covers vote buying, flash loan governance attacks,
  proposal thresholds, timelock review, and multisig versus token vote
  tradeoffs. Also use when a protocol's decentralization claims need
  verification against the actual contracts.
version: 1.0.0
domain: blockchain
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [smart-contract-audit, defi-threats, bridge-attacks]
tools:
  - name: Python
    version: 3.12
---

DAOs promise decentralized control, but the contracts often allow one
whale, one flash loan, or one multisig to rule. This skill covers
authorized assessment of governance: who can really change the
protocol, what an attack costs, and whether the timelocks and
thresholds hold. Review the contracts and the live state, not the
marketing.

## Quick Workflow

1. Map the governance contracts: token, governor, timelock, and any
   multisig with powers.
2. Read the parameters: quorum, proposal threshold, voting delay,
   voting period, and timelock delay.
3. Measure token distribution: who holds enough to propose or pass
   alone.
4. Test flash loan governance attacks on a fork: borrow, delegate,
   propose, vote.
5. Review the timelock: delay length, who can cancel, and what
   bypasses it.
6. Check emergency powers: pause, upgrade, and treasury access that
   skip governance.
7. Assess voter apathy: typical turnout versus quorum.
8. Report the real control structure with the attack costs.

## 1. Parameter and distribution review

```bash
# Read governance parameters from the contracts (fill addresses)
cast call $GOVERNOR "quorum(uint256)" 1000000 --rpc-url $RPC_URL
cast call $GOVERNOR "proposalThreshold()" --rpc-url $RPC_URL
cast call $GOVERNOR "votingDelay()" --rpc-url $RPC_URL
cast call $GOVERNOR "votingPeriod()" --rpc-url $RPC_URL
cast call $TIMELOCK "getMinDelay()" --rpc-url $RPC_URL
```

```python
#!/usr/bin/env python3
"""Governance attack cost sketch (public holder data)."""
total_supply = 100_000_000
quorum = 4_000_000
top_holders = [30_000_000, 12_000_000, 8_000_000]  # from explorer
print("top holder share:", top_holders[0] / total_supply)
print("can top holder pass alone?", top_holders[0] > quorum)
print("flash loan needed for quorum:", quorum, "tokens")
print("check: does voting power snapshot before the loan block?")
```

## 2. Flash loan governance test (fork)

```bash
# On your local fork:
# 1. flash borrow governance tokens from a lending pool
# 2. delegate to yourself in the same transaction if delegation is instant
# 3. check: does the proposal threshold use a snapshot from before?
# Vulnerable: voting weight counted at vote time with no delegation delay
# Safe: snapshot at proposal creation plus voting delay longer than loan
```

```bash
# Timelock review: what can skip it
grep -rn "onlyOwner\|onlyAdmin\|executor\|canceller\|proposer" dao-contracts/contracts --include="*.sol" | head -20
# Findings: proposer can also cancel (griefing), short delay, EOA admin
```

## Edge cases

- Off chain voting (Snapshot) with on chain execution. The off chain
  part needs its own review: who controls the space admins.
- Delegation is concentrated in a few delegates. The DAO is really an
  oligarchy; report the effective control.
- The team holds a veto multisig "temporarily". Temporary vetoes
  become permanent; price the trust accordingly.

## Escalation

- Active governance attack in progress: alert the protocol team and
  major delegates immediately; time is the voting period.
- Centralization is structural: recommend staged decentralization
  with milestones, not just criticism.

## Detection and defender view

DAO defenders monitor for large delegations before votes, new
proposals from unknown addresses, and timelock queue anomalies. They
defend with voting delays, delegation requirements, timelocks the
community can review, and emergency pause controlled by a
distributed multisig. The durable principle is that governance
security equals the cost of attack versus the value controlled.

## Key references

- CWE-862 (Missing Authorization): governance bypasses.
- Flash loan governance attack case studies.
- DAO governance security research literature.
