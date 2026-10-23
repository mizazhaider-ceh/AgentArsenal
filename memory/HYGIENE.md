# Memory Hygiene

Hygiene keeps the memory store trustworthy: no duplicates, no unresolved
contradictions, no stale confidence, no secrets, a visible audit trail,
and a bounded size. Run these checks on the same schedule as
consolidation (see `memory/LIFECYCLE.md`).

## Deduplication

Duplicates come from two agents recording the same event, one agent
re-recording after a retry, or copy-pasted payloads. Rules:

- Before storing, `recall` the topic. If an equivalent entry exists,
  do not store a second one. Raise the existing entry's confidence
  instead (corroboration).
- `memory-store.py consolidate --dry-run` lists merge candidates
  weekly. Merge only entries that agree; contradictions are handled
  below, not merged.
- One idea per entry makes duplicates easy to spot and merge safely.

## Contradiction handling

Two entries contradict when both claim the same fact and both cannot be
true (e.g. "port 22 open on 10.0.1.5" vs "port 22 closed on 10.0.1.5").

Procedure:

1. Recall both entries. Note ids, timestamps, source agents, confidence.
2. Trust recency first: the newer observation usually wins, because
   systems change.
3. Trust direct observation over hearsay: an entry recorded by the
   agent that ran the scan beats one copied from a chat message.
4. Resolve by recording a new entry that states the resolution, e.g.
   "Re-scanned 10.0.1.5 on 2026-10-23: port 22 is closed. Earlier entry
   (id 871, open) is superseded." Then delete or expire the losing
   entry with `forget --id`.
5. Never silently edit another agent's entry. Add your own entry and
   link it by id.

If you cannot resolve it (both agents are credible and recent), keep
both, raise neither confidence, and tag both `disputed` until fresh
evidence arrives.

## Confidence decay

Confidence rots when the world changes and memory does not. Policy:

- Episodic entries lose 0.1 confidence per month after their TTL
  passes, and are deleted at TTL anyway by `forget --expired`.
- Semantic entries are re-verified on a yearly cadence. If nobody
  confirms a semantic entry within its TTL, lower confidence to 0.5
  and tag it `stale`, then re-confirm or delete.
- Procedural entries are reviewed when the tool or environment changes
  version. A procedure written for nmap 7.80 gets re-checked against
  nmap 7.98 before it is trusted again.
- Every corroboration (independent re-observation) raises confidence
  by 0.05, capped at 0.98. Nothing is ever 1.0; keep the last grain
  of doubt.

## PII redaction rules

The memory store must never hold: passwords, API keys, session tokens,
private keys, full credit card numbers, government ID numbers, or exact
home addresses of private individuals.

- Redact at capture time: replace secrets with `[REDACTED]` before
  calling `store`.
- Scan stored entries monthly for patterns that look like secrets:

```bash
# Dump and eyeball for suspicious patterns (keys, tokens)
memory-store.py recall --query "key token secret password" --limit 50
```

- If a secret slipped in: rotate the secret on the real system FIRST,
  then `forget --id` the entry. Deleting does not un-leak a live key.
- Names of people and internal hostnames are allowed; they are
  operational facts, not PII in this context. When in doubt, prefer
  role labels ("the on-call engineer") over names.

## Audit trail

Every mutation of the store must be traceable:

- `store`, `consolidate`, and `forget` all record the invoking agent
  in `source_agent`, so `who did what` is answerable from the data
  itself.
- Privacy deletions get a one-line note in the operator log with the
  date, the id, and the reason. No content of the deleted entry is
  kept in the log.
- Consolidation runs print a summary (how many merged, how many
  skipped as contradictory). Save the summary alongside the run date.

## Size budgets

Memory is cheap, unbounded memory is not. Budgets per agent database:

- Total entries: aim under 50,000. Above that, shorten episodic TTL.
- Episodic share: should stay under 80 percent of rows. If it creeps
  higher, consolidate and promote more aggressively.
- Single payload: keep under 2,000 characters. Longer content belongs
  in a file; memory stores the conclusion plus the file path.

Check monthly:

```bash
memory-store.py stats
```

If the store grows faster than the budget, the fix is almost always
the same: lower the episodic TTL, consolidate weekly instead of
monthly, and promote repeated observations to semantic sooner.
