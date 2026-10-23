# ADR Template

Architecture Decision Records capture decisions that are hard to reverse.
Write one whenever you choose a tool, a schema, a protocol, or a process
that later work will depend on. One decision per file:
`decisions/adr-<nnnn>-<slug>.md`.

## Template (copy from here)

```markdown
# ADR-<NNNN>: <short title>

Date: YYYY-MM-DD
Status: proposed | accepted | rejected | superseded by ADR-<NNNN>
Deciders: <who made the call>

## Context

<What forces the decision. Facts, constraints, deadlines. No opinions yet.>

## Decision

<What we chose, stated plainly. One paragraph.>

## Alternatives considered

1. <Option A>: <one-line summary> - rejected because <reason>.
2. <Option B>: <one-line summary> - rejected because <reason>.

## Consequences

- Good: <what this buys us>
- Bad: <what this costs us>
- Neutral: <what changes as a side effect>

## Compliance

<How we check we are following this decision. A command, a CI check, a
review step.>
```

## Rules

- Status starts at `proposed`. It becomes `accepted` only after the deciders
  sign off. A rejected ADR stays in the repo; deleting it deletes the lesson.
- A superseded ADR keeps its file and gets `superseded by ADR-<NNNN>`; the
  new ADR links back to it.
- ADRs are numbered sequentially. Never reuse a number.

## Filled example

```markdown
# ADR-0007: memory-store uses SQLite, stdlib only

Date: 2026-10-23
Status: accepted
Deciders: izaz, memory team lead

## Context

Agents need persistent memory across runs. The store must work on any
machine with Python 3 and no pip installs (lab machines, jump hosts,
air-gapped clients). Concurrent writes are rare: one agent writes at a
time, many read.

## Decision

The memory-store tool persists entries in a SQLite database accessed only
through the Python stdlib `sqlite3` module. No external database, no ORM.

## Alternatives considered

1. JSON files per entry: simple, but concurrent recall-while-writing
   corrupts files, and full-text search has to be hand-rolled anyway -
   rejected because durability and search matter more than simplicity.
2. PostgreSQL: real database semantics, but requires a server install and
   breaks the stdlib-only, works-anywhere rule - rejected because the
   deployment constraint is non-negotiable.

## Consequences

- Good: zero-dependency install, atomic writes, real queries for recall
  ranking.
- Bad: no built-in replication; multi-machine sync needs an export/import
  step.
- Neutral: schema migrations are SQL scripts checked into the repo.

## Compliance

`scripts/test_tools.py` runs the memory-store CLI; the memory team reviews
any PR that adds a non-stdlib import to `tools/memory-store/`.
```
