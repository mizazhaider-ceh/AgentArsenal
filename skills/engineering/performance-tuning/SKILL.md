---
name: performance-tuning
description: Use when making a system faster on purpose: establishing a
  baseline benchmark with hyperfine 1.18, profiling Python with cProfile,
  finding CPU, memory, disk, or network bottlenecks on Linux, tuning
  database queries and caches, sizing connection pools and workers,
  interpreting load test results, or deciding whether an optimization is
  worth the complexity. Use when the task mentions slow endpoints,
  profiling, benchmarking, latency, throughput, load testing, or
  performance regression.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening]
tools:
  - name: hyperfine
    version: 1.18
  - name: Python
    version: 3.12
  - name: perf
    version: 6.8
---

Performance tuning without measurement is superstition. The discipline is:
define the metric, measure the baseline, find the actual bottleneck,
change one thing, re-measure, and keep the change only if the numbers
improve. This skill covers that loop with hyperfine 1.18 for benchmarking,
cProfile and Linux perf for profiling, bottleneck triage across CPU,
memory, disk, and network, and the standard fixes: caching, pooling,
query tuning, and concurrency. Scope is measurement-driven tuning;
rewriting architecture is out of scope.

## Quick Workflow

1. Define the metric and target: p99 latency under X, or Y requests per
   second at Z concurrent users.
2. Benchmark the current state with hyperfine; save the numbers as the
   baseline.
3. Profile under realistic load; find where time is actually spent.
4. Classify the bottleneck: CPU, memory, disk I/O, network, or lock
   contention.
5. Apply the cheapest fix for that bottleneck first (cache, index,
   pool, batch).
6. Re-benchmark with the identical command and workload; keep only real
   wins.
7. Load test at 2x expected peak to confirm headroom.
8. Record the baseline, the change, and the delta so the next person
   does not re-tune blindly.

## 1. Benchmarking with hyperfine

```bash
# Install (or cargo install hyperfine)
sudo apt install -y hyperfine

# Baseline: 10 warmup runs, 30 measured runs, exported for later
hyperfine --warmup 10 --runs 30 \
  --export-json /tmp/baseline.json \
  'curl -s -o /dev/null http://127.0.0.1:8080/api/users'

# Compare before/after on the same machine, same load
hyperfine --warmup 5 --runs 20 \
  --export-json /tmp/after.json \
  'curl -s -o /dev/null http://127.0.0.1:8080/api/users'

# Statistical comparison
hyperfine --warmup 0 --runs 1 'true'  # placeholder; use the compare script:
python3 - <<'EOF'
import json
b = json.load(open('/tmp/baseline.json'))['results'][0]
a = json.load(open('/tmp/after.json'))['results'][0]
print(f"before: {b['mean']*1000:.1f}ms  after: {a['mean']*1000:.1f}ms")
print(f"delta: {(a['mean']/b['mean']-1)*100:+.1f}%")
EOF
```

Benchmark rules: same machine, same background load, multiple runs,
warmup included, and never benchmark on a laptop on battery with the
fan screaming.

## 2. Profiling Python with cProfile

```bash
# Profile a script, sort by cumulative time
python3 -m cProfile -s cumulative app.py 2>&1 | head -30

# Save stats and explore the hot callers
python3 -m cProfile -o /tmp/prof.out app.py
python3 - <<'EOF'
import pstats
p = pstats.Stats('/tmp/prof.out')
p.sort_stats('cumulative').print_stats(15)
p.sort_stats('tottime').print_stats(15)   # time IN the function itself
EOF
```

Read it right: `tottime` shows where CPU burns (optimize these),
`cumtime` shows the call path (understand these). A function with high
cumtime but low tottime is a dispatcher; the cost is in its children.

```python
# Targeted timing without a full profiler
import time
from contextlib import contextmanager

@contextmanager
def timer(label):
    t0 = time.perf_counter()
    yield
    print(f"{label}: {(time.perf_counter()-t0)*1000:.1f}ms")

with timer("db query"):
    rows = db.execute("SELECT ...")
```

## 3. Linux: find the bottleneck layer

```bash
# CPU saturated? (watch %us + %sy; >80% sustained is hot)
top -bn1 | head -15
mpstat -P ALL 1 3

# Which process burns CPU, and is it user or iowait?
pidstat -u 1 3 | tail -10

# Memory pressure: si/so (swap in/out) should be ~0
vmstat 1 5
free -h

# Disk I/O: await (ms per op) and %util (100% = saturated device)
iostat -x 1 3 | grep -E 'Device|sd|nvme'

# Network: retransmits, buffer errors
ss -s
cat /proc/net/snmp | grep -i retrans
```

Decision tree: CPU hot -> profile the code. iowait high -> disk or
swapping; check iostat await and vmstat si/so. Network retransmits ->
congestion or loss, not code. Load average high but CPU idle -> tasks
blocked on I/O or locks.

```bash
# Flame graph via perf for native/CPU-bound code (needs debug symbols
# for best output; sample 30s of the target PID)
sudo perf record -F 99 -p 1234 -g -- sleep 30
sudo perf script | head -5
```

## 4. Database query tuning (the usual suspect)

```bash
# Postgres: find the slowest queries
sudo -u postgres psql -c "
SELECT query, calls, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;"

# Explain the bad one: look for Seq Scan on big tables
sudo -u postgres psql -c "EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE user_id = 42 ORDER BY created_at DESC LIMIT 20;"
```

Fixes in order: add the missing index (`CREATE INDEX CONCURRENTLY`),
fix N+1 queries (one JOIN or batched fetch instead of a query per row),
select only needed columns, add pagination, cache the hot read. Measure
with EXPLAIN ANALYZE before and after; "it feels faster" is not a
result.

## 5. Caching: the highest-leverage fix

```bash
# Cache the hot read in Redis with a TTL (see redis-basics)
redis-cli SET user:42:profile '{"name":"Izaz"}' EX 300

# Measure hit rate over a minute
redis-cli INFO stats | grep -E 'keyspace_hits|keyspace_misses'
```

Cache rules: cache reads, not writes; every entry gets a TTL; cache
aside (app checks cache, falls back to DB, populates cache) is the
default pattern; invalidate on write or accept staleness explicitly.
Watch for the thundering herd: use short jittered TTLs or request
coalescing when a hot key expires.

## 6. Concurrency and pooling

```bash
# How many workers? Start with 2x CPU cores for sync workers, tune by load test
nproc
# gunicorn example: sync workers
gunicorn app:server --workers 5 --threads 2 --timeout 30

# Database pool sizing: small is usually right (pool = cores * 2 + spindles)
# Check for pool exhaustion in the app metrics or logs:
grep -i 'pool.*exhaust\|timeout.*acquir' /var/log/app.log | tail -5
```

Symptoms: latency climbs with concurrency but CPU is idle -> pool or
lock contention; add pool metrics (checked-out count, wait time) before
raising limits. Async helps I/O-bound workloads; it does not make CPU
work faster.

## 7. Load testing for headroom

```bash
# vegeta: constant-rate load (install from GitHub releases)
echo "GET http://127.0.0.1:8080/api/users" | \
  vegeta attack -rate=200 -duration=60s | vegeta report

# Watch the server during the run (second terminal)
vmstat 1 | awk '{print $13, $14}'   # us, sy CPU columns
ss -s | head -5                      # socket pressure
```

Read the report: p50/p95/p99 latencies, success rate, and where the
curve bends (the knee is your real capacity). Test at 2x expected peak;
if the knee is below peak, you do not have headroom.

## 8. Quick wins checklist

- Enable compression (gzip/br) on text responses at the reverse proxy.
- Set far-future cache headers on static assets with fingerprinted
  names.
- Turn on HTTP keep-alive between proxy and backends (see
  nginx-hardening).
- Batch N+1 queries; add the obvious missing index.
- Move work out of the request path: queues for email, thumbnails,
  webhooks.
- Raise obviously tiny defaults: DB pool size, worker count, file
  descriptor limits (`ulimit -n`).

## Edge cases

- Optimization makes the benchmark faster but production slower: the
  benchmark did not match production (different data size, concurrency,
  or cache warmth). Benchmark with production-shaped data.
- p99 improved, p50 unchanged: you fixed a tail problem (GC pause, lock
  convoy); confirm the tail was the actual complaint.
- Caching made stale data visible: TTL too long or invalidation
  missing; shorten TTL or invalidate on write, and document the
  staleness contract.
- More workers made it slower: contention moved to the DB or a lock;
  workers are not free, profile again at the new shape.
- hyperfine shows huge variance: background process interference;
  pin CPUs (`taskset`), close browsers, rerun.

## Escalation

- Profile says "everything is slow, nothing is hot": the bottleneck is
  outside the profiled code (network, DNS, TLS handshake per request);
  measure with curl timing breakdown (`curl -w` with time_namelookup,
  time_connect, time_appconnect, time_starttransfer).
- Latency spikes correlate with deploys: check for cold caches and JIT
  warmup; warm the cache and let the process settle before measuring.
- Memory grows unbounded: take heap snapshots over time (Python:
  tracemalloc) and diff; fix the leak, do not raise the limit.
- Still slow after the obvious fixes: question the workload itself;
  can the feature do less (smaller pages, fewer joins, deferred work)?

## Detection and defender view

Performance tooling doubles as reconnaissance: profiling and load
testing look like attacks from the outside. Detect misuse and
misconfig with:

```bash
# Unexpected load generators on the host
ps aux | grep -E 'vegeta|wrk|ab |locust|hyperfine' | grep -v grep

# A "benchmark" that is actually a DoS: connection floods in logs
ss -s | head -3
awk '$9 ~ /^5/ {print $1}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head

# perf left recording (overhead + info leak via symbols)
ps aux | grep 'perf record' | grep -v grep
```

Defensive rules: run load tests only against staging or with explicit
permission and a kill switch; never benchmark production at peak;
restrict `perf` to privileged users (`kernel.perf_event_paranoid=2`
or higher); treat sudden latency or 5xx spikes during "testing" as a
possible attack until proven otherwise. Misconfig signal: caches with
no TTL, pools sized by guesswork, and no baseline recorded anywhere.

## Key references

- hyperfine 1.18: https://github.com/sharkdp/hyperfine
- Python profilers docs: https://docs.python.org/3/library/profile.html
- Linux perf wiki: https://perf.wiki.kernel.org/
- Brendan Gregg's USE method: https://www.brendangregg.com/usemethod.html
- vegeta: https://github.com/tsenart/vegeta
- CWE-400 (Uncontrolled Resource Consumption): missing limits that
  tuning should add.
- CWE-770 (Allocation Without Limits): unbounded pools and queues.
