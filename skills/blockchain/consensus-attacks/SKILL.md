---
name: consensus-attacks
description: Use when you need working knowledge of consensus layer
  attacks for blockchain security assessments. Covers 51 percent
  attacks, selfish mining, long range attacks on PoS, eclipse attacks,
  and finality concepts. Also use when evaluating the security budget
  of a smaller chain or a new PoS design.
version: 1.0.0
domain: blockchain
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [blockchain-forensics, defi-threats]
tools:
  - name: Python
    version: 3.12
---

Consensus attacks target the chain itself: rewriting history,
censoring transactions, or double spending by controlling block
production. This skill gives the working knowledge and assessment
method: how each attack works, what it costs, and how to evaluate a
chain's resistance. It is analytical and defensive; you do not attack
live chains.

## Quick Workflow

1. Identify the consensus mechanism: PoW, PoS variant, BFT, or hybrid.
2. Measure decentralization: hash rate or stake distribution, client
   diversity, and geographic spread.
3. Compute the attack cost: what it takes to rent or buy 51 percent.
4. Assess finality: how many confirmations make a rewrite impractical.
5. Review eclipse resistance: peer diversity and protected peers.
6. Check long range attack mitigations on PoS: weak subjectivity,
   checkpoints.
7. Review the incident history: past reorgs and how the community
   responded.
8. Report the security budget honestly with the math shown.

## 1. 51 percent cost estimate

```python
#!/usr/bin/env python3
"""Rough 51 percent attack cost model (public data inputs)."""
# PoW example inputs (fill from public dashboards)
network_hashrate_hs = 600e18      # network total, hashes per second
rent_price_per_hs_day = 1e-18     # rental market price
attacker_share = 0.51
cost_per_day = network_hashrate_hs * attacker_share * rent_price_per_hs_day
print(f"estimated rental cost per day: ${cost_per_day:,.0f}")
print("compare against: exchange confirmation requirements,")
print("value settled per day, and deep reorg history")
```

```bash
# Stake distribution for PoS: who holds what share
# Use a public explorer API; flag if top 3 validators exceed 33 percent
# (BFT safety threshold) or 51 percent (liveness/majority)
python3 - << 'PY'
print("fetch validator set from explorer API")
print("compute Nakamoto coefficient: min entities to reach 51 percent")
print("low coefficient = cheap bribe or compromise target")
PY
```

## 2. Attack pattern reference

```bash
# Selfish mining: attacker withholds blocks, releases strategically
# Needs roughly 33 percent+ hash to be profitable; hurts chain fairness
# Double spend: attacker sends tx, receives goods, reorgs it away
# Needs confirmations < reorg depth the attacker can afford
# Eclipse: isolate a victim's node, feed it a false chain view
# Needs control of the victim's peer connections
# Long range (PoS): rewrite from far back using old keys
# Mitigated by checkpoints and weak subjectivity periods
echo "for each: cost, required share, and which chains are exposed"
```

## Edge cases

- The chain has checkpointing by a foundation. That centralizes
  trust; note who holds the checkpoint key.
- Mining rental markets are thin for the algorithm. Cost estimates
  are rough; say so and give a range.
- The assessment is for a new chain design. Focus on the mechanism's
  known attack classes and the team's mitigations, not live metrics.

## Escalation

- Active reorg or double spend in progress: alert exchanges and the
  chain team immediately; this is incident response, not assessment.
- Deep design review needed: bring in consensus specialists; this
  skill covers assessment, not novel mechanism design.

## Detection and defender view

Exchanges detect consensus attacks with confirmation requirements
scaled to the chain's security budget, reorg monitors, and deposit
holds during anomalies. Chain teams defend with checkpointing,
diverse clients, and community coordination plans. The durable truth
is economic: a chain is secure when attacking it costs more than the
attacker gains, so confirmation policy must track the live cost.

## Key references

- "Majority is not Enough" (selfish mining paper).
- Ethereum PoS specifications: finality and weak subjectivity.
- Exchange confirmation policy frameworks.
