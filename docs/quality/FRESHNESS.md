# Tool Freshness Checking

`scripts/freshness_check.py` watches the `tools:` frontmatter of every
skill for pins that have gone stale. It is the cheapest quality gate in
the repo: no tool installation, no network, pure stdlib.

## What it checks

For each skill it reads `last_verified` and every `tools:` entry
(name + version), then raises flags:

| Flag | Meaning | Review priority |
| ---- | ------- | --------------- |
| FUTURE_TOOL | The pinned version was released after `last_verified`. Likely a typo in the frontmatter. | High |
| RETIRED_TOOL | The pinned version's published support window ended before `last_verified`. Repin and re-verify. | High |
| AGING_TOOL | A newer release is known and the pinned one is more than 12 months older than `last_verified`. | Low for runtimes, higher for fast-moving security tools |
| OLD_VERIFICATION | `last_verified` is more than 12 months in the past. | Medium |

A flag is a hint for a human reviewer, not proof the skill is wrong.
Tool commands often stay correct across versions for years. Never
"fix" a flag by editing the date alone: update `last_verified` only
after a real review of the skill body.

## The release table

Release dates live in `RELEASE_DATES` at the top of the script. Each row
is a `(tool, version)` pair verified against a public release
announcement, with the check date and a note on the source. The table is
deliberately small (it covers the most-used tools first). Tools not in
the table get the `last_verified`-age check only, and the report lists
the most-used uncovered tools so you can see where to extend the table.

Two special cases are documented in the script docstring:

- Burp Suite uses calendar versions (`2026.2` = February 2026), so the
  script can detect impossible FUTURE_TOOL pins for Burp without a
  table row.
- Long-support runtimes (Python, OpenSSL LTS) carry `eol` dates, so a
  pin is only "retired" when support actually ended.

To add a row: find the release date in a public announcement (GitHub
releases page, vendor blog, distro package record), then append a row
with `tool`, `version`, `released`, `verified` (today's date), and a
`note` naming the source. Add `eol` when the vendor publishes one, and
`newer` when a newer release exists but its exact date is not verified.

## Running it

```bash
# Human-readable report on stdout
python3 scripts/freshness_check.py

# Also save a markdown report at the repo root
python3 scripts/freshness_check.py --write

# Save to a custom path
python3 scripts/freshness_check.py --write docs/quality/freshness-report.md

# Fail CI when any flag is raised
python3 scripts/freshness_check.py --strict
```

## Suggested schedule

Run it weekly; it takes a couple of seconds. A cron example that runs
every Monday at 09:00 and keeps the report in the repo:

```cron
# AgentArsenal weekly tool freshness check
0 9 * * 1 cd /home/hatch/workspace/agent-arsenal && /usr/bin/python3 scripts/freshness_check.py --write docs/quality/freshness-report.md >> /var/log/agent-arsenal-freshness.log 2>&1
```

Pair it with the strict flag in CI only if the team is ready to act on
every flag the same week; otherwise weekly runs plus a monthly review
of the report is the calmer option.
