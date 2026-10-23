# memory-store (reserved for the memory team)

This directory will hold the `memory-store` operator tool: the reference
implementation of the memory schemas defined in `memory/MEMORY_SCHEMA.md`.

Convention (matches every tool under `tools/`):

- Library and storage code lives in this package directory.
- One CLI entrypoint is exposed as `memory-store.py` (or `python3 -m
  memory_store`) that accepts `--help`, exits 0 on success, and exits 2 on
  usage errors, stdlib only.
- If the implementation needs multiple modules, keep them inside this
  directory; the entrypoint remains a single `--help`-capable script so
  `scripts/test_tools.py` can exercise it unchanged.
- The CLI must implement the lifecycle in `memory/LIFECYCLE.md`:
  `capture`, `consolidate`, `recall`, `forget`, and enforce the rules in
  `memory/HYGIENE.md` (dedup, redaction, TTL expiry, audit log).

Interface contract (minimum):

```
memory-store.py capture --kind episodic --text "..." --tags a,b
memory-store.py recall --query "..." --kind semantic --limit 5
memory-store.py consolidate --dry-run
memory-store.py forget --id <uuid> --reason "..."
```

Implemented by the memory team (Wave 3). The entrypoint is the single
file `memory-store.py` (stdlib only). `capture` is an alias of `store`;
usage errors exit 2; `--help` exits 0.
