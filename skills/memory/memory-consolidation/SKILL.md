---
name: memory-consolidation
description: Use when duplicate or overlapping memory entries pile up,
  or when repeated episodic observations should become one durable
  semantic fact. Covers dry-run review of merge candidates, merging
  near-duplicates safely, promoting episodic observations to semantic
  knowledge with raised confidence, and resolving which entry survives
  a merge. Use when running the weekly or daily hygiene pass, when
  recall returns the same fact twice, or when three or more events
  clearly describe one lasting truth.
version: 1.0.0
domain: memory
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [memory-recall, memory-hygiene]
tools:
  - name: memory-store
    version: 1.0.0
  - name: SQLite
    version: 3.45.1
  - name: Python
    version: 3.12
---

Consolidation turns a pile of raw observations into a smaller, sharper
store. It has two jobs: merging near-duplicate entries so recall stays
clean, and promoting repeated episodic observations into semantic facts
so durable knowledge survives TTL expiry. This skill covers both, with
the dry-run habit that keeps merges safe. Lifecycle context is in
memory/LIFECYCLE.md.

## Quick Workflow

1. Run `consolidate --dry-run` and read every proposed merge.
2. Merge only entries that agree; kick contradictions out to hygiene.
3. Run the real `consolidate` and note how many entries merged.
4. Look for repeated episodic observations about one fact.
5. Promote those to semantic with a `promoted` tag and raised
   confidence.
6. Verify with `stats` that the store shrank and per-kind shares look
   healthy.

## 1. Dry run and review

Never merge blind. The dry run lists candidates; you decide.

```bash
# See what would merge, change nothing
memory-store.py consolidate --dry-run
```

Read each candidate pair. Merge when both entries say the same thing
in different words ("scan finished, 14 hosts up" vs "completed nmap
sweep, 14 hosts up"). Do NOT merge when:

- The entries disagree on a fact (different host counts, different
  ports). That is a contradiction, handled per memory-hygiene.
- The entries are about different time windows and the difference
  matters ("14 hosts up in March" vs "11 hosts up in October" is a
  trend, not a duplicate).
- Either entry is tagged `disputed`.

When in doubt, skip the pair. An unmerged duplicate is clutter; a
wrongly merged contradiction is corruption.

## 2. Merge for real

```bash
# Merge the reviewed candidates
memory-store.py consolidate
```

The merge keeps the earliest entry, takes the highest confidence of
the pair, and records the absorbed ids in `merged_from` so the audit
trail survives. Typical output:

```bash
merged id 214 into id 209
merged 1 duplicate entry (37 merge candidate groups checked)
```

Follow up with recall on the merged topic to confirm only one entry
remains:

```bash
memory-store.py recall --query "nmap sweep 192.168.11" --limit 5
```

## 3. Promote episodic observations to semantic

Promotion is the payoff of consolidation: many events, one fact. When
three or more episodic entries from different times describe the same
durable truth, write it as semantic.

```bash
# Find the repeated observations
memory-store.py recall --query "staging API token" --kind episodic --limit 20
```

Then record the distilled fact. Cite the evidence in the text so the
promotion is auditable:

```bash
memory-store.py store --kind semantic --agent analyst-02 \
  --text "Observed 5 times between 2026-10-18 and 2026-10-23: the staging API rejects tokens older than 15 minutes." \
  --confidence 0.9 --tags "api,staging,auth,promoted"
```

Leave the original episodic entries in place; they are the evidence.
Set promoted-entry confidence at 0.85 or higher, never below the best
observation. Tag every promotion `promoted` so later audits can tell
promoted facts from first-hand ones.

Good promotion candidates: host roles, API limits, team schedules,
recurring scan results, stable network facts. Bad candidates: one-off
incidents, opinions, anything still changing weekly.

## 4. Verify the result

```bash
# Confirm the store shrank and shares look healthy
memory-store.py stats
```

Healthy signs: total entries dropped or stayed flat, episodic share is
under 80 percent, and each promotion added exactly one semantic entry.
If episodic keeps growing faster than promotion absorbs it, shorten
the episodic TTL or consolidate more often (see memory-hygiene size
budgets).

## Edge cases

- Merge candidates that are similar but about different hosts. Token
  overlap can false-positive on template text ("scan of X finished"
  vs "scan of Y finished"). The dry run exists for exactly this:
  read the ids, not just the count.
- Promotion when observations only half agree. "Tokens expire after
  15 minutes" observed 4 times and "after 30 minutes" once: promote
  the majority reading, keep the outlier entry, and tag the promoted
  fact `disputed` until the outlier is explained.
- Consolidation run by two agents at once. The second run finds
  nothing left to merge and exits cleanly. Merges are idempotent;
  running twice is harmless.
- A merge absorbed the wrong entry. The `merged_from` field records
  which ids went where, but deleted rows are gone. For high-value
  stores, back up the SQLite file before consolidating.

## Escalation

- Dry run proposes hundreds of merges. The store has a capture
  discipline problem: agents are re-recording instead of recalling.
  Merge in batches, then fix the habit (recall before store) rather
  than the data.
- Promotion target has 2 observations, not 3. Wait for a third, or
  record the pattern as episodic with a `pattern?` tag. Two data
  points are a coincidence until the third confirms.
- Contradictions block most merges. Stop consolidating and run the
  memory-hygiene contradiction procedure first; merging on top of
  unresolved contradictions hides them.
- The SQLite file grows between runs with no new entries. Check for
  a runaway agent writing in a loop, then delete the looped entries
  by id range after review.

## Detection and defender view

Bad consolidation is a quiet integrity attack surface: over-aggressive
merging deletes evidence (merging "port open" with "port closed"
destroys the contradiction), and fake promotions launder guesses into
high-confidence "facts". Detect misuse by reviewing merge summaries
(counts that spike), by spot-checking `merged_from` trails, and by
requiring promoted entries to cite their observation count in the
text. A promotion with no cited evidence is rejected on sight.

## Key references

- CWE-922 (Insecure Storage of Sensitive Information): the store file
  itself deserves access controls.
- SQLite documentation: https://sqlite.org/docs.html
- Python sqlite3 module: https://docs.python.org/3/library/sqlite3.html
- memory/MEMORY_SCHEMA.md and memory/LIFECYCLE.md in this repo.
