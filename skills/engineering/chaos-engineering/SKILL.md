---
name: chaos-engineering
description: Use when running chaos experiments to prove resilience.
  Covers hypothesis driven experiments, blast radius control, steady
  state metrics, and game days. Also use when "highly available" is
  claimed but never tested under failure.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [devsecops-pipeline, prometheus-monitoring, incident-response]
tools:
  - name: Python
    version: 3.12
---

Chaos engineering breaks things on purpose to learn: kill a pod,
partition the network, expire a certificate, and watch whether the
system heals. This skill covers the disciplined method: hypothesis,
controlled blast radius, steady state metrics, and learning. Run only
in environments you own with explicit approval; chaos in production
needs a written plan and an abort path.

## Quick Workflow

1. Define steady state: the metrics that prove the system is healthy.
2. Form a hypothesis: "killing one AZ keeps error rate under 0.1%".
3. Design the smallest experiment that tests it, with a tight blast
   radius.
4. Get approval: who is on call, how to abort, and the time box.
5. Run and observe: steady state metrics plus the new failure.
6. Abort if steady state breaks beyond the hypothesis bounds.
7. Analyze: what actually happened versus the hypothesis.
8. Fix the weakness and re run to prove the fix.

## 1. Experiment design

```bash
# Experiment card template:
# hypothesis: cache node failure does not raise p99 above 500ms
# blast radius: one cache node in staging
# steady state: p99 < 300ms, error rate < 0.05%
# method: terminate the node, wait 5 min, observe
# abort: p99 > 800ms for 60s, or any data loss signal
# rollback: restart the node; traffic shifts back automatically
cat > /tmp/chaos/exp_cache_node.md << 'MD'
# Experiment: cache node termination
MD
```

```bash
# Steady state check before the experiment (prometheus as tooling)
# curl the query API for the key SLIs; record the baseline numbers
# Only proceed if the baseline is green; chaos on a sick system teaches nothing
echo "baseline: p99, error rate, saturation for the affected service"
```

## 2. Common experiments

```bash
# Safe starter set (staging first, production only with approval):
# - kill a random pod (tests restart and readiness)
# - add 200ms latency between services (tests timeouts)
# - fill a disk to 90% (tests alerting and handling)
# - expire a test certificate (tests rotation)
# - partition one AZ (tests multi AZ design)
echo "each experiment needs the abort condition defined up front"
```

## Edge cases

- The experiment finds nothing. That is a result: the hypothesis
  held, and you have evidence for the resilience claim.
- Blast radius escapes (the tool hits the wrong target). Abort
  immediately, fix the targeting, and review before retrying.
- Stateful systems (databases) need extra care: test failover, not
  data destruction, unless the backup restore is the hypothesis.

## Escalation

- Steady state breaks badly: abort, restore, and run the incident
  process; the experiment becomes a real incident with a head start.
- Repeated failures of the same hypothesis: this is an
  architectural finding, not bad luck; redesign, don't retry.

## Detection and defender view

Chaos is defensive: it finds resilience gaps before attackers or
accidents do. From a security view, chaos validates the controls
that incidents rely on: failover, backups, and alerting. Misuse
looks like unapproved experiments in production. The durable
practice is regular game days with the on call team, where the
hypotheses come from past incidents and threat models.

## Key references

- "Chaos Engineering" (O'Reilly): principles and practice.
- Related skills: prometheus-monitoring, incident-response.
