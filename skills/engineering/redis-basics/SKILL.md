---
name: redis-basics
description: "Use when operating Redis 7.4 in development or production: installing and configuring a server, choosing data types (strings, hashes, lists, sets, sorted sets, streams), writing and reading keys with redis-cli, setting TTLs, configuring RDB and AOF persistence, setting up ACL users and passwords, tuning eviction and memory limits, taking backups, reading INFO and SLOWLOG output, or diagnosing a slow or unreachable Redis instance. Use when the task mentions caching, sessions, queues, leaderboards, rate limiting, or pub/sub with Redis."
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening]
tools:
  - name: Redis
    version: 7.4
  - name: redis-cli
    version: 7.4
---
Redis is an in-memory data structure server used as a cache, session store,
message queue, and primary data store. It speaks a simple text protocol
(RESP), persists optionally to disk, and exposes rich atomic commands for
each data type. This skill covers operating Redis 7.4: installation,
everyday data-type commands, persistence, access control, memory tuning,
backups, and troubleshooting. Scope is single-instance and basic
replication operation; cluster resharding internals are out of scope.

## Quick Workflow

1. Install Redis 7.4 and verify the server starts with the expected config
   file.
2. Connect with redis-cli, run PING, and confirm the protected-mode and
   bind settings.
3. Create an ACL user for the application and disable the default user or
   give it a strong password.
4. Choose the right data type per use case (string for cache, hash for
   objects, list or stream for queues, sorted set for leaderboards).
5. Set TTLs on every cache key so stale data expires on its own.
6. Enable AOF plus periodic RDB snapshots for durability, and verify the
   files are written.
7. Set maxmemory and an eviction policy that matches the workload.
8. Back up dump.rdb and appendonlydir regularly and test a restore.
9. Monitor INFO stats, SLOWLOG, and memory usage on a schedule.
10. Lock down networking: bind to localhost or a private interface, firewall
    the port, never expose 6379 to the internet.

## 1. Install and first connection

Install from your distribution or the official Redis packages, then confirm
the version.

```bash
# Debian/Ubuntu (official Redis APT repo recommended for 7.4)
sudo apt update && sudo apt install -y redis-server
redis-server --version

# Start and check status
sudo systemctl enable --now redis-server
sudo systemctl status redis-server --no-pager

# Connect locally and run the smoke test
redis-cli ping
# Expected: PONG
```

Confirm which config file the running server uses, and that protected mode
is on:

```bash
redis-cli CONFIG GET protected-mode
redis-cli CONFIG GET bind
redis-cli INFO server | grep -E 'redis_version|config_file|process_id'
```

Key files on Debian: config at `/etc/redis/redis.conf`, data dir at
`/var/lib/redis`, logs via journald (`journalctl -u redis-server`).

## 2. Core data types and everyday commands

Strings are the default: use them for cache entries, counters, and flags.

```bash
# Cache entry with a 10 minute TTL (single atomic command)
redis-cli SET session:abc123 '{"user":"izaz"}' EX 600
redis-cli GET session:abc123
redis-cli TTL session:abc123

# Atomic counters for rate limits or stats
redis-cli INCR api:hits:2026-10-23
redis-cli INCRBY inventory:sku42 -3

# Set only if missing (simple distributed lock primitive)
redis-cli SET lock:deploy worker-1 NX EX 30
```

Hashes store objects field by field without serializing the whole thing:

```bash
redis-cli HSET user:1001 name "Izaz" role "student" logins 7
redis-cli HGET user:1001 name
redis-cli HGETALL user:1001
redis-cli HINCRBY user:1001 logins 1
```

Lists are queues and stacks. LPUSH plus BRPOP gives a blocking worker
queue:

```bash
redis-cli LPUSH jobs '{"task":"render","id":9}'
redis-cli LPUSH jobs '{"task":"email","id":10}'
redis-cli LRANGE jobs 0 -1
# Worker side: block up to 5s for the next job
redis-cli BRPOP jobs 5
```

Sets give uniqueness; sorted sets give ranked data:

```bash
redis-cli SADD tags:post77 linux redis tutorial
redis-cli SISMEMBER tags:post77 redis
redis-cli SMEMBERS tags:post77

# Leaderboard: member -> score, ZRANGE with REV for top N
redis-cli ZADD leaderboard 1500 alice 2300 bob 900 cara
redis-cli ZREVRANGE leaderboard 0 2 WITHSCORES
redis-cli ZRANK leaderboard bob
```

Streams are the durable log/queue type with consumer groups:

```bash
# Append an event (server assigns the ID)
redis-cli XADD events * type signup user izaz

# Consumer group reads each message exactly once per group
redis-cli XGROUP CREATE events workers 0 MKSTREAM
redis-cli XREADGROUP GROUP workers w1 COUNT 1 BLOCK 5000 STREAMS events '>'
redis-cli XACK events workers 1750000000000-0
```

Scan keys safely. Never use KEYS * on a production instance with many
keys; it blocks the server:

```bash
# Iterate in small batches instead
redis-cli --scan --pattern 'session:*' | head -20
redis-cli --scan --pattern 'user:*' | wc -l
```

## 3. Persistence: RDB snapshots and AOF log

RDB is a point-in-time snapshot (compact, fast restarts). AOF logs every
write (more durable, larger). Run both in production.

```bash
# Check current persistence settings
redis-cli CONFIG GET 'save|appendonly|dir|dbfilename' 

# Snapshot now and confirm the file timestamp moves
redis-cli BGSAVE
ls -l /var/lib/redis/dump.rdb
redis-cli LASTSAVE

# AOF settings in /etc/redis/redis.conf
# appendonly yes
# appendfsync everysec
```

Recommended `redis.conf` persistence block:

```bash
# /etc/redis/redis.conf (edit, then restart)
save 3600 1 300 100 60 10000
appendonly yes
appendfsync everysec
```

After editing, restart and verify:

```bash
sudo systemctl restart redis-server
redis-cli CONFIG GET appendonly
redis-cli INFO persistence | grep -E 'rdb_last_bgsave_status|aof_enabled|aof_last_rewrite_time_sec'
```

## 4. Access control: passwords and ACL users

Redis 7.4 keeps the legacy `requirepass` but ACL users are the right tool:
per-user passwords plus command and key restrictions.

```bash
# Create an app user limited to its own key prefix, no dangerous commands
redis-cli ACL SETUSER appuser on '>S3cure-App-Pass' \
  '+@all -@dangerous -DEBUG -MONITOR -CONFIG' \
  'resetkeys' '+@all' '~app:*' '~session:*'

# Verify and list users
redis-cli ACL LIST
redis-cli ACL WHOAMI

# Disable the default user if everything authenticates as appuser
redis-cli ACL SETUSER default off

# Persist ACLs to /etc/redis/users.acl so they survive restarts
redis-cli ACL SAVE
```

In `redis.conf`, point at the ACL file instead of inline passwords:

```bash
# /etc/redis/redis.conf
# requirepass oldstylepassword   (avoid; use ACLs)
aclfile /etc/redis/users.acl
```

Application connection strings then use the ACL user:

```bash
redis-cli --user appuser --pass 'S3cure-App-Pass' --askpass PING
```

## 5. Memory limits and eviction

Redis keeps everything in RAM, so cap it and pick an eviction policy.
Without a cap, Redis grows until the OOM killer steps in.

```bash
# Set a 2 GB cap and LRU eviction of keys with TTLs
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy volatile-lru
redis-cli CONFIG REWRITE   # persist to redis.conf

# Check memory pressure
redis-cli INFO memory | grep -E 'used_memory_human|maxmemory_human|mem_fragmentation_ratio'
redis-cli INFO stats | grep evicted_keys
```

Policy guide: `volatile-lru` for cache with TTLs (most common),
`allkeys-lru` when keys have no TTL, `volatile-ttl` when expiry order
matters, `noeviction` for a primary store (writes fail instead of evicting,
so monitor closely).

## 6. Backup and restore

```bash
# Backup: copy the RDB snapshot and AOF directory (stop writes briefly
# or accept a slightly inconsistent copy; prefer BGSAVE first)
redis-cli BGSAVE
sleep 2
sudo cp /var/lib/redis/dump.rdb /backup/redis/dump-$(date +%F).rdb
sudo tar -czf /backup/redis/aof-$(date +%F).tar.gz -C /var/lib/redis appendonlydir

# Restore: stop server, replace files, fix ownership, start
sudo systemctl stop redis-server
sudo cp /backup/redis/dump-2026-10-23.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo systemctl start redis-server
redis-cli DBSIZE
```

Test restores on a scratch instance before you trust them.

## 7. Monitoring and slow query diagnosis

```bash
# One-page health summary
redis-cli INFO replication
redis-cli INFO stats | grep -E 'instantaneous_ops_per_sec|total_commands_processed|rejected_connections'

# Find slow commands (threshold in microseconds, default 10000)
redis-cli CONFIG SET slowlog-log-slower-than 5000
redis-cli SLOWLOG GET 10
redis-cli SLOWLOG LEN
redis-cli SLOWLOG RESET

# Live command stream for debugging (NEVER in production, it leaks data
# and hurts performance)
redis-cli MONITOR
# Ctrl-C to stop
```

Latency spikes often come from: `KEYS *`, large `SMEMBERS`/`HGETALL` on
huge collections, `BGSAVE` on a machine without enough RAM (fork latency),
or AOF fsync stalls on slow disks.

## 8. Basic replication

One replica gives read scaling and a warm standby:

```bash
# On the replica's redis.conf
# replicaof 10.0.0.5 6379
# replica-serve-stale-data yes
# replica-read-only yes

sudo systemctl restart redis-server
redis-cli INFO replication | grep -E 'role|master_link_status|connected_slaves'
```

Promote a replica manually when the primary dies:

```bash
redis-cli REPLICAOF NO ONE
```

For automatic failover use Redis Sentinel or a managed setup; manual
promotion is fine for small deployments with runbooks.

## Edge cases

- `CONFIG SET` changes vanish after restart. Always follow with
  `CONFIG REWRITE` or edit `redis.conf` directly.
- `BGSAVE` fails with "fork: Cannot allocate memory". The fork needs
  virtual memory headroom; set `vm.overcommit_memory = 1` via sysctl and
  make sure free RAM plus swap covers the dataset.
- AOF file corrupt after a crash. Run `redis-check-aof --fix
  /var/lib/redis/appendonlydir/*.aof` (Redis 7 uses a multi-part AOF
  manifest; check the manifest file too).
- `OOM command not allowed when used memory > maxmemory`. Either raise
  maxmemory, switch to an eviction policy, or delete cold keys. For a
  primary store with `noeviction`, this is the expected backpressure.
- Replication full resync on every replica restart. Caused by a too-small
  `repl-backlog-size`; raise it so brief disconnects resync partially.
- Latency spikes every N minutes. Usually RDB `save` points or AOF
  rewrite; check `INFO persistence` for `rdb_bgsave_in_progress` and
  `aof_rewrite_in_progress` during the spike.

## Escalation

- Server will not start: run `redis-server /etc/redis/redis.conf` in the
  foreground to see the fatal error (bad directive, permission on the data
  dir, port already in use). Check `journalctl -u redis-server -n 50`.
- Suspected data loss: compare `INFO keyspace` DBSIZE against the last
  backup manifest, inspect `dump.rdb` timestamps, and check whether AOF
  was actually enabled (`aof_enabled:1`).
- Replica lag growing: check `master_repl_offset` vs the replica's
  `slave_repl_offset` in `INFO replication`, look for network drops, and
  consider raising `repl-timeout`.
- Authentication chaos after ACL changes: keep one SSH session with a
  working redis-cli while you edit ACLs, and keep a backup of
  `users.acl` before `ACL SAVE`.
- Still stuck: `redis-check-rdb /var/lib/redis/dump.rdb` validates the
  snapshot file itself.

## Detection and defender view

An exposed or weakly authenticated Redis is a classic intrusion path:
attackers scan for port 6379, try no-auth access, then write SSH keys via
`CONFIG SET dir /root/.ssh` tricks or drop cron jobs. Detect
misconfiguration and misuse by watching for:

```bash
# Connections from unexpected hosts (run on the Redis host)
sudo ss -tnp | grep ':6379'

# Auth failures and dangerous commands in the log
sudo journalctl -u redis-server | grep -iE 'auth|denied|config set|flushall' | tail -20

# Unexpected keys that look like attacker artifacts
redis-cli --scan --pattern '*ssh*' | head
redis-cli --scan --pattern '*cron*' | head
```

Hardening checklist for defenders: bind to 127.0.0.1 or a private IP,
`protected-mode yes`, firewall 6379, ACL users with least privilege,
disable or rename dangerous commands (`FLUSHALL`, `CONFIG`, `DEBUG`,
`EVAL` if unused) via `rename-command`, keep Redis patched, and alert on
`CONFIG SET dir`/`dbfilename` changes which signal persistence abuse.
Misuse signal: `MONITOR` running unexpectedly, or a new unknown ACL user
in `ACL LIST`.

## Key references

- Redis 7.4 documentation: https://redis.io/docs/latest/
- redis.conf annotated example (7.4): https://redis.io/docs/latest/operate/oss_and_stack/management/config/
- Redis ACL guide: https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/
- Redis persistence: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
- Redis security checklist: https://redis.io/docs/latest/operate/oss_and_stack/management/security/
- CWE-306 (Missing Authentication for Critical Function): unauthenticated
  Redis instances.
- CWE-798 (Use of Hard-coded Credentials): passwords baked into configs
  instead of ACL files with tight permissions.
