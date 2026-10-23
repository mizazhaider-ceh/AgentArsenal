# skills.sh compatibility

How AgentArsenal works with skills.sh and the `npx skills` CLI, what we
verified, and what we fixed.

## What skills.sh is

skills.sh is an open directory for discovering and installing reusable
AI agent skills. It is backed by the `skills` npm CLI (built by Vercel
Labs): `npx skills add <owner/repo>` fetches skills from a public
GitHub repo and installs them into the agent's skills directory
(`~/.claude/skills/`, `.agents/skills/`, and so on, depending on the
agent). GitHub is the registry; `SKILL.md` is the package entry point.

## What we found (researched 2026-10-23)

1. **There is no formal submission form.** skills.sh operates as an open
   directory: repos appear on the leaderboard automatically once users
   install them with the CLI (anonymous install telemetry drives the
   all-time and 24h trending rankings). Publishing the repo to GitHub
   and making it installable is the requirement.
2. **Multi-skill repos are supported.** A repo does not need one
   SKILL.md at root. `npx skills add <owner/repo> --list` discovers
   every skill directory in the repo; `npx skills add <owner/repo>
   --skill <name>` installs one; without `--skill` it installs all.
3. **Frontmatter must be strict YAML.** Each SKILL.md needs `name` and
   `description` in YAML frontmatter. The CLI's YAML parser (js-yaml)
   rejects unquoted plain scalars containing a colon followed by a
   space (`: `), which Anthropic's own skill spec also warns about.
4. **Root manifest convention.** Some catalog repos (for example
   shikanime-labs/skills) ship a `skills.json` manifest at the repo
   root so npm-based skill managers can discover skills without
   scanning the tree.

## What AgentArsenal needed, and what we changed

**Problem found by testing.** Running
`npx skills add mizazhaider-ceh/AgentArsenal --list` against the
published repo skipped 38 skills with:

```
Skipped .../SKILL.md - YAML parse error: Nested mappings are not
allowed in compact mappings at line 2, column 14
```

Root cause: 38 frontmatter descriptions were unquoted plain scalars
containing `: ` (for example "raw Cypher: shortest paths"). Valid for
loose parsers, invalid for strict YAML.

**Fix (commit "skills.sh compatibility"):**

- `scripts/fix_frontmatter_quotes.py`: rewrites any top-level unquoted
  plain scalar containing `: ` as a double-quoted single-line string.
  38 SKILL.md files fixed; the repo's own `scripts/validate.py` still
  passes (its scalar parser unquotes correctly).
- `scripts/derive_manifest.py` re-run, so `arsenal-manifest.json`
  sha256 hashes match the rewritten files.
- `scripts/gen_skills_json.py` (new): generates `skills.json` at the
  repo root with name, description, path, version, domain, and lifecycle
  per skill, for npm-based skill manager discovery.

**Verification:**

- Strict `yaml.safe_load` of all 356 SKILL.md frontmatter blocks: 0
  problems.
- `npx skills add /home/hatch/workspace/agent-arsenal --list` (local
  tree with the fix): **246 skills discovered, 0 skipped.** (The 110
  sub-skills under `sub/` are drill-down modules, not top-level skills,
  and are intentionally not listed.)
- Note: the GitHub-published copy still shows the skips until these
  commits are pushed.

## Install commands users will run

```bash
# List every skill in the repo
npx skills add mizazhaider-ceh/AgentArsenal --list

# Install one skill globally
npx skills add mizazhaider-ceh/AgentArsenal --skill linux-hardening -g

# Install all 246 skills globally (no prompt)
npx skills add mizazhaider-ceh/AgentArsenal -g -y

# Install for specific agents only
npx skills add mizazhaider-ceh/AgentArsenal -g -a claude-code -a cursor -y
```

If the CLI was cached from an older release, force the latest with
`npx skills@latest add ...`. Telemetry can be disabled with
`SKILLS_NO_TELEMETRY=1`.

## Listing submission text

skills.sh has no submission form, so there is nothing to file. If a
form appears later, or for any other directory that asks for a listing,
use this exact text:

- **Repo name:** mizazhaider-ceh/AgentArsenal
- **Link:** https://github.com/mizazhaider-ceh/AgentArsenal
- **Category:** Security / Developer Tools
- **Title:** AgentArsenal
- **Description:** 246 versioned agent skills across 28 domains,
  covering software engineering craft and offensive security practice,
  with machine-enforced quality: per-skill semver, a 14-check CI
  harness, 0 to 100 quality scores, validated dependency graph,
  freshness dates, and lifecycle states. Installs with
  `npx skills add mizazhaider-ceh/AgentArsenal`.
- **License:** MIT

## Maintenance

After any change to a SKILL.md description, re-run
`python3 scripts/fix_frontmatter_quotes.py --check` in CI or before
release. Exit code 1 means a file needs quoting. Then re-run
`scripts/derive_manifest.py` and `scripts/gen_skills_json.py` so the
manifest hashes and `skills.json` stay in sync.
