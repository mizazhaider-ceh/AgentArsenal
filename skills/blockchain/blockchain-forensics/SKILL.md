---
name: blockchain-forensics
description: Use when tracing cryptocurrency in an investigation on an
  authorized case. Covers address clustering, transaction graph
  analysis, exchange attribution, and following funds through mixers
  and bridges at the methodology level. Also use when a client needs
  to know where stolen funds went.
version: 1.0.0
domain: blockchain
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [nft-fraud, wallet-security, log-forensics]
tools:
  - name: Python
    version: 3.12
---

Blockchain forensics follows money on a public ledger: clustering
addresses that belong together, tracing hops from the theft, and
identifying where funds meet the regulated world. This skill covers
the methodology for authorized investigations: evidence handling,
clustering heuristics, tracing workflow, and attribution. It does not
replace licensed chain analysis tools, but it gives a sound manual
method.

## Quick Workflow

1. Define the case: the theft or fraud, the seed addresses, and the
   legal basis for the investigation.
2. Preserve evidence: record transaction hashes, block numbers, and
   the data source for everything.
3. Cluster addresses using co spend and change heuristics.
4. Trace forward from the seed: follow the funds hop by hop.
5. Identify attribution points: exchanges, mixers, bridges, and known
   services.
6. Trace backward where useful: where did the attacker's funding come
   from.
7. Document the flow with a clear diagram and an address list.
8. Prepare the findings for legal: chain of custody for digital
   evidence.

## 1. Clustering heuristics

```python
#!/usr/bin/env python3
"""Address clustering: co-spend heuristic on transaction data."""
import json, collections

# txs: list of {txid, inputs:[addrs], outputs:[addrs]}
txs = [json.loads(l) for l in open("/tmp/chain/txs.jsonl")]

parent = {}
def find(a):
    while parent.get(a, a) != a:
        a = parent[a] = parent.get(parent[a], parent[a])
    return a
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb

for t in txs:
    ins = t["inputs"]
    for a in ins[1:]:
        union(ins[0], a)  # co-spend: inputs to one tx, one owner

clusters = collections.defaultdict(set)
for t in txs:
    for a in t["inputs"] + t["outputs"]:
        clusters[find(a)].add(a)
print("clusters found:", len(clusters))
big = sorted(clusters.values(), key=len, reverse=True)[:5]
for c in big:
    print(len(c), "addresses, sample:", list(c)[:3])
```

## 2. Tracing workflow

```bash
# Forward trace: from the theft address, follow outputs
# At each hop record: txid, amounts, new addresses, service tags
# Stop expanding when you hit: a known exchange cluster, a mixer
# pool, or a bridge contract (note which and continue on the other chain)
python3 - << 'PY'
print("trace log columns: hop, txid, from, to, amount, tag, notes")
print("rules: follow the largest output first, note peel chains,")
print("flag round amounts (possible OTC or exchange deposits)")
PY
```

```bash
# Attribution: check addresses against your case's known service list
grep -F -f /tmp/chain/known_exchanges.txt /tmp/chain/trace_addresses.txt | head
# Mixer interaction: note entry and exit, timing, and amounts;
# full deanonymization is often not possible, document the limits
```

## Edge cases

- Privacy coins or shielded pools break the trace. Document where
  visibility ends; do not overclaim.
- The attacker uses many small hops (peel chain). Automate the
  following; manual tracing misses branches.
- Exchange attribution needs legal process. Your trace identifies
  the deposit; unmasking needs the proper request.
- Cross chain bridges split the trail. Continue the trace on the
  destination chain with the bridge's event logs.

## Escalation

- Funds hit an exchange: notify the exchange's compliance team
  promptly with the transaction evidence.
- Active laundering in progress: speed matters; escalate to counsel
  and law enforcement per the case plan.
- Trace goes cold at a mixer: pivot to timing and amount correlation,
  and to the attacker's operational mistakes (reuse, funding).

## Detection and defender view

Defenders (exchanges, protocols) detect illicit flows with
transaction monitoring, sanctions list screening, and behavioral
alerts on deposit patterns. They defend with withdrawal holds,
proof of source checks, and information sharing. For investigators,
the durable practices are evidence preservation, conservative
clustering (better to under cluster than over), and clear
documentation of every heuristic's limits.

## Key references

- FATF guidance on virtual assets and investigations.
- CoinJoin and mixer tracing research literature.
- Chain analysis methodology publications.
