# Memory Lifecycle

Memory moves through four stages: capture, consolidate, recall, forget.
This document defines when each stage runs and what it does, with the
exact `memory-store` commands to use. Field definitions live in
`memory/MEMORY_SCHEMA.md`; storage hygiene rules live in
`memory/HYGIENE.md`.

## 1. Capture (when and what to record)

Capture is the act of writing an entry. Record memory when one of these
happens:

- Something surprising or newsworthy occurred (episodic). Examples: a
  scan finished, an alert fired, a host behaved oddly, a plan changed.
- A fact that will matter later became clear (semantic). Examples: a
  host's role, an API limit, a team's working hours.
- A lesson was learned the hard way (procedural). Examples: a command
  that avoids a pitfall, an order of operations that works.

Do NOT record:

- Raw output dumps. Store the conclusion, link the artifact path.
- Secrets of any kind (keys, tokens, passwords). See HYGIENE.md.
- Things that are already memory. Check with `recall` first.

Commands:

```bash
# Episodic: something happened
memory-store.py store --kind episodic --agent hunter-01 \
  --text "Completed nmap sweep of 192.168.11.0/24: 14 hosts up, 3 with port 22 open." \
  --confidence 0.8 --tags "nmap,subnet,scan"

# Semantic: a durable fact
memory-store.py store --kind semantic --agent analyst-02 \
  --text "The staging API rejects tokens older than 15 minutes." \
  --confidence 0.9 --tags "api,staging,auth"

# Procedural: how-to
memory-store.py store --kind procedural --agent operator-izaz \
  --text "Run sqlmap with --batch and --threads=2 on fragile targets to avoid interactive prompts and overload." \
  --confidence 0.95 --tags "sqlmap,web"
```

Kind check before storing: ask "will this be true next month?" If yes,
prefer semantic. "Did this just happen?" Episodic. "Does this tell me
how to do something better?" Procedural. When unsure, store as episodic
with low confidence; promotion handles the rest.

## 2. Consolidate (merge duplicates, promote episodic to semantic)

Consolidation runs on a schedule (daily for busy agents, weekly
otherwise) and does two jobs.

### 2a. Merge near-duplicates

The same observation recorded twice (by two agents, or by one agent
re-running a check) wastes space and muddies recall. `consolidate` finds
entries of the same kind with highly similar payloads and merges them:
the earliest entry survives, keeps the highest confidence, and gains a
`merged_from` list in its metadata.

```bash
# Dry run first: see what would merge
memory-store.py consolidate --dry-run

# Merge for real
memory-store.py consolidate
```

Review the dry run. Merging is safe when payloads agree; if two
"similar" entries disagree (contradiction), do not merge, handle per
HYGIENE.md instead.

### 2b. Promote episodic to semantic

When three or more episodic entries from different times describe the
same durable fact, promote it. Promotion creates one new semantic entry
with confidence raised (usually 0.85+) and leaves the originals in
place (they still document the observations).

```bash
# Find repeated observations about one topic
memory-store.py recall --query "staging API token expiry" --kind episodic --limit 20
```

Promotion steps:

1. Recall the repeated observations.
2. Write the distilled fact as a new semantic entry, citing the
   observation count in the text, e.g. "Observed 5 times between
   2026-10-18 and 2026-10-23: the staging API rejects tokens older than
   15 minutes."
3. Tag it `promoted` so the trail is visible.

```bash
memory-store.py store --kind semantic --agent analyst-02 \
  --text "Observed 5 times between 2026-10-18 and 2026-10-23: the staging API rejects tokens older than 15 minutes." \
  --confidence 0.9 --tags "api,staging,auth,promoted"
```

## 3. Recall (query patterns, relevance ranking)

Recall answers "what do I already know about X?" before doing new work.
Query patterns:

```bash
# Free text search, newest most relevant first
memory-store.py recall --query "login brute force" --limit 10

# Restrict to one kind
memory-store.py recall --query "token expiry" --kind semantic

# Filter by tag and agent
memory-store.py recall --query "scan" --tags nmap --agent hunter-01
```

Relevance ranking (what the CLI does internally):

1. Kind filter first, then tag/agent filters.
2. Score by query token overlap with the payload text (more distinct
   tokens matched = higher rank).
3. Tie-break by confidence, then by recency (newer first).
4. Expired entries never appear in recall results.

Query tips: use 2 to 4 keywords, not full sentences. Try synonyms on a
miss ("auth" vs "login"). If a search returns nothing, store the new
knowledge after you learn it so the next query hits.

## 4. Forget (ttl expiry, explicit deletion, privacy rules)

Forgetting is as important as remembering. Three mechanisms:

### TTL expiry

Every kind has a default TTL (episodic 30 days, semantic 365, procedural
730). Expired entries are hidden from recall and removed by:

```bash
memory-store.py forget --expired
```

Run this on the same schedule as consolidation.

### Explicit deletion

Delete a single bad entry by id, or everything about a topic:

```bash
# Delete one entry
memory-store.py forget --id 1042

# Find, then delete, entries about a decommissioned host
memory-store.py recall --query "old-jenkins" --limit 50
memory-store.py forget --id 1051 --id 1058
```

### Privacy rules

Delete immediately, no waiting for TTL, when an entry contains:

- A secret that slipped in (rotate the secret first, then delete).
- Personal data about someone who asked to be removed.
- Data recorded without authorization (wrong scope, wrong system).

```bash
memory-store.py forget --id 1099
```

After a privacy deletion, run `memory-store.py stats` to confirm the row
count dropped, and note the deletion in the audit log (see HYGIENE.md).
