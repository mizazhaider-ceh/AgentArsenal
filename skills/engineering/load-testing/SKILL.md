---
name: load-testing
description: Use when load testing a system you own or are authorized
  to test. Covers test design, ramp profiles, bottleneck analysis, and
  interpreting results. Also use when a launch needs capacity proof or
  when performance regressions need a baseline.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [performance-tuning, prometheus-monitoring, api-rate-limit-bypass]
tools:
  - name: Python
    version: 3.12
---

Load testing answers "what breaks first and when": ramp users up,
watch latency and errors, and find the bottleneck before customers
do. This skill covers the method for systems you own: realistic
scenarios, careful ramps, and honest analysis. Never load test
systems you do not own; that is a DDoS.

## Quick Workflow

1. Define the goal: capacity number, regression check, or breaking
   point.
2. Build realistic scenarios from production traffic patterns, not
   just one endpoint.
3. Start with a smoke test: one user, verify the script works.
4. Ramp gradually: find where latency degrades and errors start.
5. Watch the system, not just the test: CPU, memory, DB, and
   downstream.
6. Identify the bottleneck: the resource that saturates first.
7. Fix or scale, then retest to confirm.
8. Keep the baseline: future runs compare against it.

## 1. Test design and execution

```bash
# Scenario mix from production (example: 70% browse, 20% search, 10% checkout)
# Ramp: 10 -> 100 -> 500 -> 1000 users over 30 minutes, hold, then down
# Abort: error rate > 1% sustained, or p99 > SLA for 2 minutes
echo "write the plan down; ad hoc load tests produce ad hoc conclusions"
```

```python
#!/usr/bin/env python3
"""Load test result analyzer: finds the knee from a results CSV."""
import csv, statistics

# rows: ts, users, rps, p50_ms, p99_ms, errors
rows = list(csv.DictReader(open("/tmp/load/results.csv")))
print(f"{'users':>6} {'p99':>8} {'err%':>6}")
for r in rows[::max(1, len(rows) // 12)]:
    err = float(r["errors"]) / max(1, float(r["rps"])) * 100
    print(f"{r['users']:>6} {r['p99_ms']:>8} {err:>5.2f}%")
print("the knee: where p99 climbs steeply = the bottleneck region")
```

## 2. Bottleneck analysis

```bash
# During the run, watch the suspects in order:
# 1. app CPU/memory (saturation = scale or optimize)
# 2. database (slow queries, locks, connection pool)
# 3. downstream APIs (their limits become yours)
# 4. network and load balancer (rarely first, check last)
# Correlate: the metric that saturates as p99 climbs is the bottleneck
echo "fix one bottleneck at a time; retest after each fix"
```

## Edge cases

- The test environment is smaller than production. Scale the
  conclusions carefully and note the difference.
- Caches warm up during the test. Discard the warmup period or the
  numbers lie.
- Third party rate limits cap your test. That is their limit, not
  your capacity; mock or stub them for the system test.

## Escalation

- Production load test needed: run at low traffic hours with the
  full incident team on standby and a one click abort.
- Results disputed: share the raw data and the scenario mix;
  methodology arguments are settled with data.

## Detection and defender view

Load testing overlaps with security: the same traffic that finds
capacity finds missing rate limits (see api-rate-limit-bypass) and
expensive endpoints (see cloud-cost-attack-surface). Defenders
watch for load test patterns from unexpected sources as possible
attacks. The durable practice is regular testing in CI for
regressions plus periodic full capacity runs before big events.

## Key references

- Performance testing methodology literature.
- Related skills: performance-tuning, api-rate-limit-bypass.
