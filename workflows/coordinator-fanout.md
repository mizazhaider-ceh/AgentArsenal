---
name: coordinator-fanout
kind: workflow
description: Use when one coordinator must split a large task across several worker agents that can run in parallel and then merge their results. Fits playbooks where phases produce independent artifacts, such as scoping multiple targets or running parallel assessments. Load this pattern when the work divides cleanly, the workers do not depend on each other, and one agent must own the final merge.
version: 1.0.0
---

# Coordinator Fanout

## When to use it

Use coordinator fanout when a single task splits into independent pieces that different agents can work at the same time. The coordinator plans the split, launches the workers, waits for all of them, then merges the results into one artifact. Do not use it when workers depend on each other's output. For that, use the pipeline pattern instead.

## Diagram

The pattern has three levels, shown as nested lists:

- Coordinator
  - Plans the split and assigns one slice per worker
  - Worker A
    - Produces artifact slice A
  - Worker B
    - Produces artifact slice B
  - Worker C
    - Produces artifact slice C
  - Coordinator collects all slices
    - Merges slices into one final artifact
    - Resolves conflicts and removes duplicates

## Step sequence

1. The coordinator reads the task and defines the slices. Each slice has a clear boundary, for example one target, one domain, or one asset group per worker.
2. The coordinator writes the slice assignment down: worker, slice, expected artifact, and deadline. No slice overlaps another.
3. The coordinator launches all workers with the same context: the task brief, their slice, the output format, and where to write results.
4. Workers run independently. They do not talk to each other. If a worker needs something outside its slice, it reports back to the coordinator instead of reaching across.
5. The coordinator collects each worker's artifact as it arrives and checks it: format correct, slice complete, evidence attached.
6. The coordinator merges the slices into the final artifact: one report, one inventory, one map. Duplicates are removed, conflicts are resolved with the evidence on record.
7. The coordinator runs the final quality check and delivers.

## Failure handling

- A worker fails or times out: the coordinator retries it once with the same slice. If it fails again, the coordinator reassigns the slice to another worker or marks it as uncovered in the final artifact. Never silently drop a slice.
- A worker returns an artifact in the wrong format: the coordinator sends it back once with the format spec. If it still fails, the coordinator normalizes what it can and flags the gap.
- A worker finds something outside its slice that changes the plan: it reports to the coordinator immediately. The coordinator decides whether to expand a slice, add a worker, or stop and replan.
- Two workers return conflicting results: the coordinator compares the evidence, keeps the better-evidenced version, and notes the conflict in the final artifact.
- The coordinator itself fails: the merge state must be recoverable from the written slice artifacts, so a new coordinator can pick up the merge without rerunning the workers.

## Artifact kinds orchestrated

- Task briefs: the coordinator's slice assignments with boundaries and deadlines.
- Slice artifacts: per-worker outputs such as target inventories, scan results, or assessment sections.
- Merge logs: which slices arrived, what was deduplicated, how conflicts were resolved.
- Final artifacts: the merged report, map, or inventory delivered to the requester.
