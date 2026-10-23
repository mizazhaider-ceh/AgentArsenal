---
name: sqlite-deep
description: Use when working with SQLite databases on an authorized
  engineering task. Covers the sqlite3 CLI, schema design, index
  strategy, WAL mode and pragmas for performance and durability,
  parameterized queries, online backup API, integrity checks, and
  debugging locked databases. Use when embedding a database in an app
  or CLI, analyzing a SQLite file during forensics or debugging, or
  tuning SQLite for high-write workloads.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [python-cli-tooling, secure-coding]
tools:
  - name: SQLite
    version: 3.47
---

SQLite is a full SQL database in a single file with zero server to
run, which makes it the default for CLIs, mobile apps, edge services,
and test fixtures. This skill covers operating it well: the CLI for
inspection, schema and index design, the pragmas that control speed
and durability, safe concurrent access, backups, and fixing the
classic "database is locked" error. All examples use SQLite 3.47.

## Quick Workflow

1. Inspect the file with the `sqlite3` CLI: tables, schema, row
   counts, and integrity.
2. Design the schema with proper types, NOT NULL, and foreign keys
   enforced with `PRAGMA foreign_keys = ON`.
3. Enable WAL mode for concurrent readers and one writer.
4. Add indexes for the actual query patterns, verified with
   `EXPLAIN QUERY PLAN`.
5. Always use parameterized queries; never interpolate values into
   SQL strings.
6. Tune `synchronous`, `cache_size`, and `temp_store` for the
   durability and speed the workload needs.
7. Back up with the backup API or `.backup`, never with `cp` on a
   live database.
8. Run `PRAGMA integrity_check` on any database you did not create.

## 1. The sqlite3 CLI

```bash
sqlite3 --version

# Open (or create) a database and explore
sqlite3 app.db <<'EOF'
.tables
.schema users
SELECT count(*) FROM users;
EOF

# Readable output modes for inspection
sqlite3 -header -column app.db "SELECT id, name FROM users LIMIT 5;"
sqlite3 -header -csv app.db "SELECT * FROM users;" > users.csv

# One-liner schema dump for review
sqlite3 app.db .schema

# Database file info: page size, page count, freelist
sqlite3 app.db "PRAGMA page_size; PRAGMA page_count; PRAGMA freelist_count;"
```

`.dump` produces SQL text you can diff, grep, and restore anywhere;
use it for migrations review and for moving data between machines.

```bash
sqlite3 app.db .dump > app.sql
sqlite3 new.db < app.sql
```

## 2. Schema design

```bash
sqlite3 app.db <<'EOF'
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id         INTEGER PRIMARY KEY,
  email      TEXT NOT NULL UNIQUE,
  name       TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scans (
  id         INTEGER PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target     TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'pending'
             CHECK (status IN ('pending','running','done','failed')),
  started_at TEXT,
  finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
EOF
```

Notes that save pain later: `INTEGER PRIMARY KEY` is the rowid alias
and autoincrements efficiently; foreign keys are parsed but NOT
enforced unless `PRAGMA foreign_keys = ON` (set it on every
connection); `CHECK` constraints document valid values where the app
might forget.

## 3. WAL mode and durability pragmas

```bash
sqlite3 app.db <<'EOF'
-- Write-Ahead Logging: readers never block the writer
PRAGMA journal_mode = WAL;

-- Durability vs speed for the journal
-- FULL: safest, slowest. NORMAL: safe with WAL, much faster.
PRAGMA synchronous = NORMAL;

-- Keep more pages in memory (negative value = kibibytes)
PRAGMA cache_size = -64000;

-- Temp tables and indexes in memory instead of temp files
PRAGMA temp_store = MEMORY;

-- Verify what is actually active (some pragmas are no-ops in odd states)
PRAGMA journal_mode;
PRAGMA synchronous;
EOF
```

WAL mode creates `-wal` and `-shm` sidecar files; back up or copy
all three together, or checkpoint first. `synchronous = NORMAL` with
WAL is the recommended production setting: a power loss can lose the
last transaction but cannot corrupt the database. Only use
`synchronous = OFF` for throwaway data like test fixtures.

```bash
# Checkpoint the WAL back into the main file before copying
sqlite3 app.db "PRAGMA wal_checkpoint(TRUNCATE);"
ls -la app.db*
```

## 4. Indexes and query plans

```bash
# Ask the planner what it will actually do
sqlite3 app.db "EXPLAIN QUERY PLAN SELECT * FROM scans WHERE user_id = 7 AND status = 'done';"

# Covering index for the hot query: filter plus the selected columns
sqlite3 app.db "CREATE INDEX idx_scans_user_status ON scans(user_id, status);"
sqlite3 app.db "EXPLAIN QUERY PLAN SELECT id, target FROM scans WHERE user_id = 7;"

# Find missing indexes via the query planner log (compile-time option)
# or simply: any WHERE/JOIN column on a large table without an index

# Measure before and after with a timer
sqlite3 app.db <<'EOF'
.timer on
SELECT count(*) FROM scans WHERE user_id = 7 AND status = 'done';
EOF
```

`SEARCH ... USING INDEX` is good; `SCAN` on a big table without a
good reason is the signal to add an index. Like all databases, each
index taxes writes, so index the queries you actually run, not every
column.

## 5. Parameterized queries (Python example)

```python
import sqlite3

con = sqlite3.connect("app.db")
con.execute("PRAGMA foreign_keys = ON")
con.execute("PRAGMA journal_mode = WAL")

# Parameterized: values never become SQL
user_id = 7
rows = con.execute(
    "SELECT id, target FROM scans WHERE user_id = ? AND status = ?",
    (user_id, "done"),
).fetchall()

# Bulk insert fast: one transaction, executemany
targets = [(user_id, f"10.0.0.{i}") for i in range(1, 500)]
with con:  # commits on success, rolls back on exception
    con.executemany(
        "INSERT INTO scans (user_id, target) VALUES (?, ?)", targets
    )

con.close()
```

Wrapping writes in one transaction (the `with con:` block) turns 500
separate disk syncs into one, often 100x faster. String-interpolated
SQL (`f"SELECT ... {user_id}"`) is SQL injection even in a local
database the moment any value comes from outside.

## 6. Backup and integrity

```bash
# Online backup: safe on a live database (copies all three WAL files' state)
sqlite3 app.db ".backup /backups/app-$(date +%F).db"

# Restore is just opening the backup file
sqlite3 /backups/app-2026-10-23.db "SELECT count(*) FROM scans;"

# Integrity check: run on any database you received from elsewhere
sqlite3 app.db "PRAGMA integrity_check;"
# quick_check is faster and catches most corruption
sqlite3 app.db "PRAGMA quick_check;"

# Reclaim free pages and repack after large deletes
sqlite3 app.db "VACUUM;"
ls -lh app.db
```

Never `cp` a live database file in WAL mode: you can copy the main
file mid-checkpoint and get a corrupt or stale backup. `VACUUM`
rebuilds the file; run it after bulk deletes, not on a schedule.

## 7. Fixing "database is locked"

```bash
# Find who holds the database open
fuser app.db app.db-wal 2>/dev/null
lsof app.db 2>/dev/null | head

# Common causes and fixes:
# 1. A connection with an open write transaction that never committed.
#    Fix: commit/rollback in code; set a busy timeout so waits are bounded.
sqlite3 app.db "PRAGMA busy_timeout = 5000;"

# 2. Two processes writing without WAL mode: only one writer at a time.
#    Fix: PRAGMA journal_mode = WAL (readers proceed during writes).

# 3. A crashed process left a hot journal: SQLite recovers automatically
#    on next open. If recovery seems stuck, open once with the CLI and
#    run a trivial query to trigger it.
sqlite3 app.db "SELECT 1;"
```

In application code, set `busy_timeout` on every connection and keep
write transactions short: begin late, commit early. Long-lived write
transactions are the root cause of most lock contention.

## Edge cases

- `PRAGMA foreign_keys = ON` set once does not persist. It is
  per-connection; every new connection must set it, or foreign keys
  silently stop being enforced.
- WAL files grow without bound. A reader holding an old snapshot
  blocks checkpointing; find the long-lived read transaction and
  close it, then run `PRAGMA wal_checkpoint(TRUNCATE)`.
- Database file copied without `-wal` is stale or corrupt.
  Checkpoint before copying, or use `.backup`, which handles this
  correctly.
- `database is locked` under heavy multithreaded writes. SQLite
  allows one writer; serialize writes through a single thread or
  queue, or move to a server database if write concurrency is the
  actual requirement.
- Integer overflow on 32-bit assumptions. SQLite integers are 64
  bit; code that casts to 32 bit (some ORMs, some C bindings)
  truncates large rowids.
- `.dump` of a huge database exhausts memory in the CLI. Dump
  table by table (`.dump users`) or use the backup API for full
  copies.
- Case-insensitive `UNIQUE` surprises. `UNIQUE` on TEXT is case
  sensitive by default; use `COLLATE NOCASE` in the column
  definition when emails or usernames must compare case
  insensitively.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. SQLite misconfiguration shows up as world-writable
database files, databases stored under the web root and served as
downloads, and `synchronous = OFF` on data that matters. Detect
misuse by checking file permissions on every `.db` file in
production, auditing which processes hold databases open, and
watching for unexpected growth (a sign of runaway logging or an
attack staging data). During forensics, SQLite files are evidence:
`PRAGMA integrity_check` first, then examine `sqlite_sequence`,
freelist pages, and WAL contents for deleted rows; the `strings`
command on the raw file often surfaces data the schema hides.
Ship SQLite files with the application only when the data is truly
static; mutable databases belong on a volume with backups.

## Key references

- SQLite 3.47 documentation: https://www.sqlite.org/docs.html
- Query planner and EXPLAIN: https://www.sqlite.org/eqp.html
- WAL mode: https://www.sqlite.org/wal.html
- Pragma statements: https://www.sqlite.org/pragma.html
- Backup API: https://www.sqlite.org/backup.html
- CWE-89 (SQL Injection): string-interpolated queries.
- CWE-732 (Incorrect Permission Assignment for Critical Resource):
  world-writable database files.
- CWE-665 (Improper Initialization): foreign keys not enforced
  without the per-connection pragma.
