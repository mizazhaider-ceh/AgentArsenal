---
name: database-migrations
description: Use when designing or reviewing database migration
  practices. Covers migration authoring, zero downtime patterns,
  rollback strategy, and migration security review. Also use when a
  deploy needs a schema change without breaking the running app.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [postgresql-tuning, secure-coding, devsecops-pipeline]
tools:
  - name: PostgreSQL
    version: 17
  - name: Python
    version: 3.12
---

Database migrations change the schema under a running application:
done badly, they lock tables, lose data, or break the deploy. This
skill covers the safe practice: writing reversible migrations,
expanding before contracting, and reviewing migrations for security
and performance. It applies to any relational database with a
migration tool.

## Quick Workflow

1. Write migrations as small, reversible steps, one concern each.
2. Follow expand then contract: add the new, migrate the data,
   remove the old in separate deploys.
3. Make every migration runnable online: no long exclusive locks.
4. Test against a production like dataset, not an empty database.
5. Review for data loss: drops and type changes need explicit
   sign off.
6. Plan rollback for each migration before merging it.
7. Run migrations in CI and in the deploy pipeline, same tool.
8. Monitor the deploy: lock waits and error rates during migration.

## 1. Safe patterns

```sql
-- Expand: add the new column as nullable first (no lock issues)
ALTER TABLE users ADD COLUMN email_verified_at timestamptz;

-- Backfill in batches (not one giant UPDATE that locks the table)
-- UPDATE users SET email_verified_at = ... WHERE id BETWEEN ...;

-- Contract (a later deploy): make it NOT NULL after the app writes it
-- ALTER TABLE users ALTER COLUMN email_verified_at SET NOT NULL;
```

```bash
# Migration hygiene checks before merge:
# - is it reversible (down migration or forward fix documented)?
# - does it run in under the lock timeout on prod sized data?
# - was it tested on a copy of production data?
# - does the app code handle both schemas during the deploy window?
echo "checklist in the PR template; the DBA or reviewer signs off"
```

## 2. Dangerous operations review

```bash
# Flag for extra review:
grep -riE "DROP (TABLE|COLUMN)|ALTER.*TYPE|CREATE INDEX[^C]" migrations/ | head -20
# - DROP: needs backup + sign off
# - TYPE change: rewrites the table; use USING carefully, or a new column
# - CREATE INDEX: use CONCURRENTLY on Postgres to avoid write locks
```

```sql
-- Safe index creation on a live table (PostgreSQL)
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);
```

## Edge cases

- The migration must run on multiple database flavors. Test each;
  SQL dialects differ on locking and defaults.
- Zero downtime is impossible for some changes (type rewrites).
  Schedule a maintenance window honestly instead of pretending.
- The migration tool runs as a superuser. Scope its credentials to
  migrate only, and audit its use.

## Escalation

- Migration stuck holding a lock in production: kill it per the
  runbook, verify no partial state, and fix the pattern.
- Data loss suspected: stop, restore from backup to a scratch
  instance, and assess before proceeding.

## Detection and defender view

Migration misuse looks like unreviewed schema changes in
production, dropped columns with live data, and migration
credentials used outside the pipeline. From a security view,
migrations are code that runs as a privileged user: review them
like code, with attention to SQL injection in dynamic migration
scripts and to who can author them. The durable practice is the
pipeline: reviewed, tested, reversible, and monitored.

## Key references

- PostgreSQL documentation: locking and CONCURRENTLY.
- Expand/contract pattern literature.
- Related skills: postgresql-tuning, devsecops-pipeline.
