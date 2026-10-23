---
name: zero-trust-networking
description: Use when designing or assessing zero trust network
  architectures on an authorized engagement. Covers identity based
  access, microsegmentation review, policy engine assessment, and
  validating that implicit trust is actually gone. Also use when a
  "zero trust" deployment needs verification against the claim.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [vlan-hopping, firewall-evasion]
tools:
  - name: Python
    version: 3.12
  - name: nmap
    version: 7.98
---

Zero trust means no implicit trust by network location: every access
decision uses identity, device posture, and context. This skill covers
authorized assessment and design review: checking the policy engine,
testing whether flat trust remains, and reviewing microsegmentation.
It tests the architecture, not just the marketing slide.

## Quick Workflow

1. Learn the claimed architecture: policy engine, policy
   administrator, and enforcement points.
2. Map identity sources: IdP, device inventory, and posture signals.
3. Test the core claim: from a compromised position, what can you
   reach without fresh authentication.
4. Review microsegmentation: are workloads actually isolated by
   policy.
5. Check the policy engine: default deny, least privilege, and
   context aware rules.
6. Test device posture enforcement: non compliant devices blocked.
7. Review logging: every decision logged and auditable.
8. Report the remaining implicit trust with proof.

## 1. Implicit trust testing (authorized)

```bash
# From an authorized test host inside the "untrusted" zone:
# 1. try to reach a sensitive service with no credentials
curl -s -o /dev/null -w "%{http_code}\n" https://db.internal/
# 2. try with valid user creds but non compliant device posture
# 3. try lateral: from a compromised test workload, scan neighbors
sudo nmap -sS -T3 --max-retries 1 10.20.0.0/24 -oN /tmp/zt_lateral.txt
grep -c open /tmp/zt_lateral.txt
# Any open service reachable without policy approval = implicit trust remains
```

```bash
# Policy review: dump and grade the rules
# - default deny present?
# - rules by identity (user, workload) not just IP?
# - time and posture conditions used?
# - stale rules for departed users or decommissioned workloads?
echo "review: policy export, last change dates, orphaned rules"
```

## 2. Microsegmentation validation

```python
#!/usr/bin/env python3
"""Segmentation matrix check: allowed vs observed flows."""
# intended: dict of (src_zone, dst_zone) -> allowed bool
intended = {("web", "db"): True, ("web", "backup"): False,
            ("user", "db"): False, ("user", "web"): True}
# observed: fill from flow data or authorized tests
observed = {("web", "db"): True, ("web", "backup"): False,
            ("user", "db"): False, ("user", "web"): True}
for flow, want in intended.items():
    got = observed.get(flow, False)
    if got != want:
        print(f"MISMATCH {flow}: intended {want}, observed {got}")
print("every mismatch is a finding; every untested flow is a gap")
```

## Edge cases

- Legacy systems cannot do identity auth. They need compensating
  controls (isolated enclave, gateway); verify the compensations.
- The policy engine is a single point of failure. Check its HA and
  what happens when it is down (fail closed expected).
- "Zero trust" is only on the VPN replacement. Internal flat
  networks remain; scope the claim honestly.

## Escalation

- Implicit trust found: demonstrate the path, then recommend the
  specific policy change.
- Architecture review only: grade against NIST 800-207 tenets and
  report the gaps.

## Detection and defender view

Zero trust architectures detect well because every access is a
policy decision: anomalies are visible as denied requests and
unusual grants. Attackers adapt by stealing valid identities and
devices, so the detection focus shifts to identity and posture
signals. The durable design keeps policies tight, logs everything,
and treats the policy engine as critical infrastructure.

## Key references

- NIST SP 800-207: Zero Trust Architecture.
- CWE-862 (Missing Authorization): policy gaps.
- Related: firewall-evasion (tests the enforcement).
