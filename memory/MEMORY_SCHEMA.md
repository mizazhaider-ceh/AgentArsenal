# Memory Schema

This document defines the three memory kinds every agent in AgentArsenal
uses, plus the fields each entry carries. All memory entries are stored as
rows in the `memory-store` SQLite database (see `tools/memory-store/`), and
the schemas below match that table exactly.

## Entry kinds

### Episodic memory

Timestamped events: what happened, when it happened, who did it. Examples:
"2026-10-23 09:14: traffic spike from 10.0.2.41 against the login endpoint",
"run of memory-store consolidate merged 12 duplicate entries".

Episodic entries are the raw log of an agent's life. They are high volume,
low confidence on their own, and they age out fast (default TTL 30 days).

### Semantic memory

Facts that stay true independent of any single event. Examples: "the
staging API rejects tokens older than 15 minutes", "10.0.2.41 is the QA
load-test host". Semantic entries are usually promoted from repeated
episodic observations (see `memory/LIFECYCLE.md`). They age out slowly
(default TTL 365 days) and carry higher confidence.

### Procedural memory

How-to knowledge that improves how work is done. Examples: "scan internal
subnets with --max-rate 200 to avoid IDS alerts", "always run sqlmap with
--batch on unattended hosts". Procedural entries are almost never
auto-promoted; they are recorded deliberately by an operator or agent and
kept until explicitly revised or deleted (default TTL 730 days).

## Shared fields

Every entry, regardless of kind, carries these fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | integer | yes (auto) | Unique row id assigned by the store. |
| `kind` | string | yes | One of `episodic`, `semantic`, `procedural`. |
| `created_at` | string | yes (auto) | UTC timestamp, ISO 8601 (`2026-10-23T09:14:22Z`). |
| `source_agent` | string | yes | Name of the agent (or operator) that recorded the entry, e.g. `hunter-01`. |
| `confidence` | float | yes | 0.0 to 1.0. Direct observation: 0.7+. Promoted/corroborated: 0.85+. Guess: below 0.4. |
| `ttl` | integer | no | Time to live in days. `0` or null means never expire. Defaults: episodic 30, semantic 365, procedural 730. |
| `tags` | string | no | Comma separated keywords for filtering, e.g. `login,bruteforce,staging`. |
| `payload` | string | yes | The actual memory content. Plain text, one idea per entry. |

The store computes `expires_at` from `created_at + ttl` and uses it for the
`forget --expired` command.

## JSON examples

Episodic:

```json
{
  "id": 1042,
  "kind": "episodic",
  "created_at": "2026-10-23T09:14:22Z",
  "source_agent": "hunter-01",
  "confidence": 0.8,
  "ttl": 30,
  "tags": "login,bruteforce,staging",
  "payload": "Saw 400 failed logins in 5 minutes from 10.0.2.41 against the staging login endpoint. Blocked by rate limiter."
}
```

Semantic:

```json
{
  "id": 1043,
  "kind": "semantic",
  "created_at": "2026-10-23T10:02:11Z",
  "source_agent": "analyst-02",
  "confidence": 0.92,
  "ttl": 365,
  "tags": "network,qa",
  "payload": "10.0.2.41 is the QA load-test host. Brute-force looking traffic from it is expected during test windows 09:00 to 11:00."
}
```

Procedural:

```json
{
  "id": 1044,
  "kind": "procedural",
  "created_at": "2026-10-23T11:30:00Z",
  "source_agent": "operator-izaz",
  "confidence": 0.95,
  "ttl": 730,
  "tags": "nmap,ids",
  "payload": "When scanning internal subnets, use --max-rate 200 and spread the scan over two passes. Full speed scans trip the IDS and get the source IP quarantined."
}
```

## Rules of thumb

- One idea per entry. If a paragraph contains two facts, store two entries.
- Never store secrets: API keys, passwords, session tokens, private keys.
  See `memory/HYGIENE.md` for redaction rules.
- Confidence must reflect evidence, not hope. A single observation starts
  at 0.7 at most; it rises only with corroboration.
- Episodic entries that repeat the same fact three or more times are
  candidates for promotion to semantic (see `memory/LIFECYCLE.md`).
