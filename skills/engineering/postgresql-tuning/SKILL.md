---
name: postgresql-tuning
description: Use when diagnosing or improving PostgreSQL performance on an
  authorized engineering task. Covers EXPLAIN ANALYZE reading, index
  design and bloat checks, pg_stat_statements for slow query hunting,
  autovacuum tuning, connection pooling, key postgresql.conf settings,
  and backup verification. Use when queries are slow, connections are
  exhausted, disk grows unexplained, or when reviewing a database for
  performance and safety.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding]
tools:
  - name: PostgreSQL
    version: 16
---

PostgreSQL 16 is fast when it is configured and indexed for the
workload, and slow in confusing ways when it is not. This skill
covers the operator loop: find the slow queries, read their plans,
fix the indexing or the query, tune vacuum and connections, and
verify backups. Every command targets PostgreSQL 16.

## Quick Workflow

1. Enable `pg_stat_statements` and find the queries burning the
   most total time.
2. Run `EXPLAIN (ANALYZE, BUFFERS)` on the worst offenders and read
   the plan before changing anything.
3. Add the missing indexes the plan asks for; remove indexes that
   cost more on writes than they save on reads.
4. Check autovacuum health and bloat on the busiest tables.
5. Size connections with a pooler; never let apps open hundreds of
   direct connections.
6. Tune the small set of `postgresql.conf` settings that matter
   (`shared_buffers`, `work_mem`, `maintenance_work_mem`,
   `effective_cache_size`).
7. Verify backups restore, not just that they run.
8. Re-measure: the same `pg_stat_statements` query should show the
   improvement.

## 1. Find the slow queries

```bash
# Enable the extension once per database (needs shared_preload_libraries)
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Top 10 queries by total time
sudo -u postgres psql -x -c "
SELECT query, calls, round(total_exec_time::numeric,1) AS total_ms,
       round(mean_exec_time::numeric,1) AS mean_ms, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;"
```

```bash
# Reset stats before a benchmark window, compare after
sudo -u postgres psql -c "SELECT pg_stat_statements_reset();"
# ... run workload ...
sudo -u postgres psql -c "
SELECT query, calls, round(mean_exec_time::numeric,1) AS mean_ms
FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;"
```

`pg_stat_statements` needs `shared_preload_libraries =
'pg_stat_statements'` in postgresql.conf and a restart to start
collecting. Total time matters more than mean time: a query that is
fast but runs a million times hurts more than a slow one-off.

## 2. Read the plan

```bash
sudo -u postgres psql -c "
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders WHERE customer_id = 42 ORDER BY created_at DESC LIMIT 20;"
```

What to look for in the output:

- `Seq Scan` on a large table with a selective filter: the classic
  missing-index signal. A sequential scan reading 10 million rows to
  return 20 is the problem.
- `Nested Loop` with a huge outer row count: the join order or the
  inner index is wrong.
- `Buffers: shared hit` vs `read`: high `read` means the working
  set does not fit in cache; high `hit` with slow time means CPU or
  lock contention.
- `Sort` with `Sort Method: external merge Disk`: `work_mem` is too
  small for the sort; data spilled to disk.
- Actual rows far from estimated rows: stale statistics; run
  `ANALYZE` on the table and re-check.

```bash
# The fix for the classic case: index the filter plus the ordering
sudo -u postgres psql -c "
CREATE INDEX CONCURRENTLY idx_orders_customer_created
ON orders (customer_id, created_at DESC);"

# Verify the plan changed
sudo -u postgres psql -c "
EXPLAIN SELECT * FROM orders WHERE customer_id = 42 ORDER BY created_at DESC LIMIT 20;"
```

`CREATE INDEX CONCURRENTLY` avoids locking writes on production
tables; a plain `CREATE INDEX` blocks writes until it finishes.

## 3. Index hygiene

```bash
# Unused indexes: candidates for removal (they tax every write)
sudo -u postgres psql -x -c "
SELECT schemaname, relname AS table, indexrelname AS index
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%pkey%'
ORDER BY relname;"

# Duplicate and overlapping indexes
sudo -u postgres psql -c "
SELECT indexrelid::regclass, indrelid::regclass, indkey
FROM pg_index WHERE indisvalid ORDER BY 2;" | head -20

# Index bloat estimate: indexes much larger than the data they index
sudo -u postgres psql -c "
SELECT relname, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes ORDER BY pg_relation_size(indexrelid) DESC LIMIT 10;"

# Drop safely: first make invisible to the planner, then drop after a week
sudo -u postgres psql -c "ALTER INDEX idx_old RENAME TO idx_old_retired;"
```

Every index speeds reads and slows writes; a table with 15 indexes
that are never scanned is paying write tax for nothing. Drop in two
steps (rename, wait, drop) so a surprise regression is reversible.

## 4. Vacuum, bloat, and dead tuples

```bash
# Tables with the most dead tuples waiting for vacuum
sudo -u postgres psql -x -c "
SELECT relname, n_live_tup, n_dead_tup,
       round(100.0*n_dead_tup/(n_live_tup+n_dead_tup+1),1) AS dead_pct,
       last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;"

# Aggressive manual vacuum on one bloated table (blocks briefly)
sudo -u postgres psql -c "VACUUM (VERBOSE, ANALYZE) orders;"

# Check for transaction ID wraparound risk (the scary one)
sudo -u postgres psql -c "
SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY 2 DESC;"
```

Autovacuum settings that matter on write-heavy tables:

```bash
# Per-table tuning for a hot table (in psql)
sudo -u postgres psql -c "
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.02);
ALTER TABLE orders SET (autovacuum_analyze_scale_factor = 0.01);"
```

Defaults vacuum too rarely on huge tables; scale factors of 0.02
vacuum after 2 percent of the table changes instead of 20. A
database approaching transaction ID wraparound stops accepting
writes, so monitor `age(datfrozenxid)` and never disable autovacuum.

## 5. Connections and pooling

```bash
# Current connections by state and application
sudo -u postgres psql -x -c "
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"

# Who holds the most connections
sudo -u postgres psql -c "
SELECT usename, application_name, count(*)
FROM pg_stat_activity GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10;"

# Kill a runaway query (use pg_terminate_backend only for the backend)
sudo -u postgres psql -c "
SELECT pg_cancel_backend(pid) FROM pg_stat_activity
WHERE state = 'active' AND query_start < now() - interval '10 minutes'
AND usename != 'postgres';"
```

PostgreSQL uses one process per connection; 500 direct connections
waste memory and context-switch time. Put PgBouncer in transaction
pooling mode in front, keep `max_connections` modest (100 to 200),
and let the pooler multiplex thousands of app connections onto a
small backend pool.

## 6. The settings that matter

```bash
# Show current values and their sources
sudo -u postgres psql -c "
SELECT name, setting, unit, context FROM pg_settings
WHERE name IN ('shared_buffers','work_mem','maintenance_work_mem',
  'effective_cache_size','max_connections','checkpoint_timeout')
ORDER BY name;"
```

Sane starting points for a dedicated database server with 16 GB RAM:

```bash
# In postgresql.conf (then restart or reload as noted)
# shared_buffers = 4GB            # 25% of RAM, restart required
# effective_cache_size = 12GB     # 75% of RAM, planner hint, reload
# work_mem = 64MB                 # per sort/hash op, reload; careful: per operation
# maintenance_work_mem = 1GB      # vacuum/index builds, reload
# max_connections = 200           # with a pooler in front, restart required
# checkpoint_timeout = 15min      # fewer, larger checkpoints
# random_page_cost = 1.1          # SSDs: lower than the 4.0 default
```

Change one setting at a time and re-measure. `work_mem` is per
operation per connection: 64 MB times 100 concurrent sorts is 6.4
GB, which is how people OOM their database with one config line.

## 7. Backup verification

```bash
# Logical backup (small databases, portable)
pg_dump -U appuser -Fc appdb > /backups/appdb-$(date +%F).dump

# Physical base backup for point-in-time recovery (needs archive_mode on)
pg_basebackup -U replicator -D /backups/base-$(date +%F) -Ft -z -P

# The only backup test that counts: restore somewhere and query it
pg_restore -U postgres -d restoredb /backups/appdb-2026-10-23.dump
sudo -u postgres psql -d restoredb -c "SELECT count(*) FROM orders;"

# Verify WAL archiving is actually producing files
ls -lh /backups/wal/ | tail -5
```

An untested backup is a rumor. Restore monthly to a scratch host,
run the app's smoke queries, and time the restore so the RTO in the
runbook is real.

## Edge cases

- `EXPLAIN ANALYZE` on a write query actually executes it. Wrap in
  a transaction and roll back (`BEGIN; EXPLAIN ANALYZE UPDATE ...;
  ROLLBACK;`), or use plain `EXPLAIN` without ANALYZE.
- `CREATE INDEX CONCURRENTLY` fails inside a transaction block.
  Run it as its own statement; it cannot be rolled back, so a
  failure can leave an INVALID index to drop and retry.
- Autovacuum cannot keep up and dead tuples grow. Lower the scale
  factors per table, raise `autovacuum_max_workers`, and schedule
  manual VACUUM in low-traffic windows for the worst tables.
- `pg_stat_statements` shows normalized queries (`$1`, `$2`).
  That is by design (it groups by query shape); join with
  `pg_stat_activity` for live parameter values when debugging one
  session.
- Connection storm after a deploy: every app instance opens its
  pool at once. Stagger deploys, cap pool sizes per instance, and
  let PgBouncer absorb the spike.
- Query got slower after adding an index. The planner chose the
  new index wrongly due to stale stats; run `ANALYZE`, and check
  for skewed data the planner misestimates.
- Disk fills from WAL files. Check `archive_command` failures and
  replication slot lag (`pg_replication_slots`); a stuck slot
  retains WAL forever. Fix the archiver or drop the dead slot.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. A misconfigured PostgreSQL listens on all
interfaces with `trust` authentication, runs outdated minor
versions with known CVEs, and logs no connections or DDL. Detect
misuse by auditing `pg_hba.conf` for trust and overly broad host
lines, alerting on new superusers and on `COPY ... FROM PROGRAM`
(which executes shell commands), and watching for sudden full
table dumps at odd hours. `pg_stat_statements` doubles as a
detection source: unfamiliar query shapes from application users
can indicate SQL injection probing. Long-running transactions
holding locks open (`idle in transaction` for hours) are both a
performance and a correctness risk; alert on them.

## Key references

- PostgreSQL 16 documentation: https://www.postgresql.org/docs/16/
- EXPLAIN and query planning:
  https://www.postgresql.org/docs/16/using-explain.html
- pg_stat_statements:
  https://www.postgresql.org/docs/16/pgstatstatements.html
- Server configuration:
  https://www.postgresql.org/docs/16/runtime-config.html
- CWE-89 (SQL Injection): the reason apps use parameterized
  queries against this database.
- CWE-400 (Uncontrolled Resource Consumption): unbounded queries
  and missing statement timeouts.
- CWE-798 (Use of Hard-coded Credentials): passwords in
  connection strings and config files.
