---
name: feature-flags
description: Use when implementing or reviewing feature flags. Covers
  flag lifecycle, targeting rules, kill switches, and flag hygiene.
  Also use when a release needs gradual rollout or instant rollback
  without a redeploy.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [devsecops-pipeline, testing-strategies, secure-coding]
tools:
  - name: Python
    version: 3.12
---

Feature flags separate deploy from release: code ships dark, then a
flag turns it on for a percentage, a cohort, or everyone. This skill
covers doing it safely: flag types, targeting, kill switches, and the
hygiene that prevents flag sprawl. Done well, flags are the fastest
rollback you have; done badly, they are hidden complexity.

## Quick Workflow

1. Choose flag types: release flags (temporary), experiment flags,
   ops flags (kill switches, permanent), and permission flags.
2. Design targeting: percentage rollout, cohorts, and allowlists,
   evaluated consistently.
3. Make every flag have an owner and a planned removal date, except
   true ops flags.
4. Test both states: flag on and flag off are both production code
   paths.
5. Monitor flag evaluations: who sees what, and error rates per
   cohort.
6. Use flags as kill switches for risky features: one click off.
7. Clean up: remove the flag and the dead code path after full
   rollout.
8. Audit flag changes: who flipped what, when, and why.

## 1. Implementation basics

```python
#!/usr/bin/env python3
"""Flag evaluation sketch: consistent bucketing per user."""
import hashlib

def flag_on(flag_key, user_id, rollout_pct):
    h = hashlib.sha256(f"{flag_key}:{user_id}".encode()).hexdigest()
    bucket = int(h[:8], 16) % 100
    return bucket < rollout_pct

for uid in ["u1", "u2", "u3", "u4"]:
    print(uid, "new_checkout:", flag_on("new_checkout", uid, 25))
# Consistent: same user always gets the same bucket for the flag
```

```bash
# Flag hygiene queries (against your flag system):
# - flags older than 90 days without a removal ticket: review
# - flags at 100% for 30 days: remove the flag, keep the code path
# - flags with no owner: assign or delete
echo "hygiene review monthly; stale flags are tech debt with blast radius"
```

## 2. Kill switch pattern

```bash
# Every risky feature gets an ops flag defaulting to safe:
# - payment flow v2: flag off = old flow
# - new search backend: flag off = old backend
# Incident runbook: "turn off flag X" before "roll back the deploy"
echo "kill switches need no deploy, no approval chain, just the flag UI"
```

## Edge cases

- Flag evaluation in the client can be tampered with. Security
  decisions stay server side; client flags are UX only.
- Percentage rollouts with sticky sessions: bucket by user ID, not
  by request, or users flap between versions.
- Flag systems go down. Define the default (usually off/safe) and
  cache evaluations briefly.

## Escalation

- Flag sprawl out of control: run a cleanup sprint with the rule
  "every temporary flag older than 90 days gets a removal PR".
- Incident needs instant rollback: flip the flag, then investigate;
  the deploy rollback can follow.

## Detection and defender view

Flag misuse looks like unauthorized flag flips, flags left at
partial rollout forever, and security sensitive behavior gated only
by a client side flag. Defenders (the engineering org) monitor flag
change audit logs and alert on flips outside change windows. The
durable practice is treating flags as production config: reviewed,
audited, and cleaned up.

## Key references

- Feature flag best practice literature (Martin Fowler's bliki).
- Related skills: testing-strategies, devsecops-pipeline.
