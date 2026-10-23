---
name: threat-actor-profiling
description: Use when building or reviewing threat actor profiles for
  intelligence or defense planning. Covers TTP mapping to MITRE
  ATT&CK, infrastructure patterns, victimology, and turning profiles
  into detection priorities. Also use when an intrusion needs
  attribution informed defense, not just cleanup.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [threat-intel, threat-hunting, dark-web-monitoring]
tools:
  - name: Python
    version: 3.12
---

Threat actor profiling turns incident data into reusable defense:
who they are, how they work, and what to detect next time. This skill
covers the method for authorized intelligence work: collecting TTPs,
mapping to ATT&CK, profiling infrastructure and victimology, and
converting the profile into detection priorities. It informs defense;
it is not a license for hack back.

## Quick Workflow

1. Collect the raw material: incident timelines, malware, and
   infrastructure from your authorized cases.
2. Extract TTPs and map each to MITRE ATT&CK technique IDs.
3. Profile infrastructure: domains, IPs, certificates, and reuse
   patterns.
4. Profile victimology: sectors, regions, and company sizes hit.
5. Assess sophistication and resources: what the TTPs imply about
   the actor.
6. Write the profile: summary, TTPs, infrastructure, and confidence
   levels.
7. Convert to defense: detection rules and hunt hypotheses from the
   TTPs.
8. Share per policy: TLP markings and need to know.

## 1. TTP extraction and mapping

```python
#!/usr/bin/env python3
"""TTP map builder: observations to ATT&CK with confidence."""
ttps = [
    ("spearphish with malicious macro", "T1566.001", "high"),
    ("rundll32 for execution", "T1218.011", "high"),
    ("mimikatz credential dump", "T1003.001", "medium"),
    ("data staged in recycle bin", "T1074", "medium"),
    ("exfil over HTTPS to VPS", "T1048.003", "high"),
]
for obs, tid, conf in ttps:
    print(f"{tid} [{conf}] {obs}")
print("\nprofile the cluster: which techniques co occur across incidents")
```

```bash
# Infrastructure pivot points (from your case data):
# - domain registration patterns (registrar, naming, timing)
# - certificate reuse across infrastructure
# - VPS provider and payment patterns (where legally obtained)
# - overlap with public reporting (match TTPs, not just names)
echo "confidence rule: one indicator is a clue, clusters are a profile"
```

## 2. From profile to defense

```bash
# Detection priorities: the actor's favorite techniques become your
# top detections and hunts, tuned to your environment
# - top 5 TTPs -> sigma rules or EDR analytics
# - infrastructure patterns -> blocklists and DNS monitoring
# - victimology -> which business units get the briefing
echo "review quarterly: actors evolve, profiles must too"
```

## Edge cases

- Attribution confidence is low. Say so; a weak attribution used
  for strong decisions is worse than none.
- Multiple actors share tooling (RaaS affiliates). Profile the
  behavior cluster, not just the malware family.
- Public reporting conflicts with your data. Trust your evidence,
  note the conflict, and share back through proper channels.

## Escalation

- Active targeting of your organization: brief leadership and
  raise monitoring on the profiled TTPs immediately.
- Need finished intelligence: hand to the intel team with your
  TTP package; profiling feeds their process.

## Detection and defender view

Profiling is defensive intelligence: it tells you which techniques
deserve your detection budget. The profile's consumers are the SOC
(detections), threat hunting (hypotheses), and leadership (risk).
The durable practice is keeping profiles current and tied to
detections: a profile nobody hunts on is trivia.

## Key references

- MITRE ATT&CK: technique and group knowledge base.
- Diamond Model of Intrusion Analysis.
- TLP (Traffic Light Protocol) for sharing.
