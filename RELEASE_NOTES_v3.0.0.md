# AgentArsenal v3.0.0 Release Notes

Release date: 2026-10-23
Previous release: v1.0.0 (2026-10-23)

v3.0.0 is the Wave 4 milestone. It publishes the docs on GitHub Pages and
opens new distribution and community surface, and it folds in everything
built in Waves 2 and 3 since v1.0.0.

Repo: https://github.com/mizazhaider-ceh/AgentArsenal
Docs: https://mizazhaider-ceh.github.io/AgentArsenal/

## New in v3.0.0 (Wave 4)

- GitHub Pages docs site. The reference is published from the `/docs`
  folder on `main`. The landing page lives at `docs/index.html`; the
  generated skill reference (skills, agents, brains, playbooks, decisions,
  dependency graph) lives under `docs/site/`. All 412 generated pages were
  rebuilt for the new paths with zero broken internal links.
- MCP server (done, smoke-tested). `mcp_server/server.py` exposes the
  246-skill catalog over MCP with three read-only tools: `list_skills`,
  `get_skill`, `search_skills`. It reads `arsenal-manifest.json` and the
  `skills/` tree, and also runs from the `.mcpb` bundle. A stdio client
  session confirmed listing, fetching, and searching return real data.
- `.mcpb` bundle (done). One-file install bundle for MCP-compatible
  hosts, carrying a copy of the manifest and the skills tree under
  `server/data/`. `manifest.json` carries name `agent-arsenal`, version
  `3.0.0`, and parses cleanly; setup documented in
  `docs/distribution/mcpb.md`.
- Freshness checks and benchmarks (done). `scripts/freshness_check.py`
  reports skill-date hygiene; `scripts/benchmark.py` scenario-checks all
  356 skills and sub-skills and writes `BENCHMARKS.md`.
- Learning paths (done). `docs/learning-paths/`: BEGINNER, PRACTITIONER,
  and EXPERT tracks with ordered tracks and milestones.
- Translations (done). Full Spanish (`translations/README.es.md`) and
  French (`translations/README.fr.md`) README translations with verified
  anchors and paths.
- Community templates and funding (done). Issue templates under
  `.github/ISSUE_TEMPLATE/` and `.github/FUNDING.yml`.
- skills.sh compatibility (done). `docs/distribution/skills-sh.md`
  documents installation from skills.sh; the em dash it once carried is
  confirmed gone.
- Awesome-list drafts (done). Draft submission entries for six lists in
  `docs/distribution/awesome-lists.md`.
- Skill spotlight (done). `scripts/rotate_spotlight.py` rotates
  `SKILL_OF_THE_WEEK.md`; currently pinned to `nmap-methodology`.

## Since v1.0.0: Wave 3

- 246 skills across 28 domains. Wave 3 added 119 skills and 7 new
  domains: ai-security, hardware, ics-scada, blockchain, automotive,
  privacy, memory.
- 110 sub-skills under `skills/<domain>/<parent>/sub/<sub>/`, decomposing
  30 high-value parent skills (web-sqli, web-xss, nmap-methodology,
  privesc-linux, kerberoasting, and 25 more), each with the standard
  frontmatter plus a `parent:` field.
- 25 agents (`agents/<name>/AGENT.md`): named operators binding skills
  plus brains, each with a role, escalation policy, and constraints.
- 16 brains (`brains/<name>/BRAIN.md`): reusable reasoning patterns
  (attacker-mindset, evidence-chain, threat-modeling) that agents compose.
- Memory system: `memory/` docs (schema, lifecycle, hygiene), 5 memory
  skills, and a stdlib-only SQLite CLI at `tools/memory-store/`
  (store, recall, consolidate, forget, stats).
- 5 decision docs (`decisions/`): escalation policy, risk matrix, go/no-go
  gates, ADR template, cost-benefit analysis.
- 8 playbooks (`playbooks/`): end-to-end engagement scripts, including
  ad-assessment, webapp-assessment, soc-triage-day, malware-outbreak,
  bug-bounty-sprint, cloud-review, external-pentest, secure-sdlc-rollout.
- 4 workflows (`workflows/`): pipeline, coordinator-fanout, reviewer-gate,
  evidence-gate.
- 47 CLI tools in `tools/` (stdlib only) with a passing test harness.
- 19 supported platforms: one `SKILL.md` standard installs into Claude
  Code, OpenCode, Codex CLI, Gemini CLI, Cursor, GitHub Copilot, Amp,
  Goose, Cline, Roo Code, Kilo Code, Zed, Warp, Windsurf, Kiro, Qwen Code,
  Crush, Continue, and Aider (via `AGENTS.md` pointer).
- Infra: manifest generator keeps the `skills` key shape frozen for the
  installer and adds the new artifact keys; `scores.json` now covers
  skills, agents, and brains; the docs generator renders per-agent,
  per-brain, and per-playbook pages plus sub-skill trees and agent edges
  in the dependency graph; new architecture and ecosystem SVGs.

## Since v1.0.0: Wave 2

- 103 new skills (127 total) across 21 domains, adding 6 new domains:
  mobile, binary, malware, soc, osint, defensive.
- 46 operator tools under `tools/` with the `scripts/test_tools.py`
  harness.
- Premium README: generated skill-count badge and domain-grouped catalog
  table via `scripts/gen_readme_catalog.py`, plus new banner and
  architecture assets.
- `.claude-plugin/marketplace.json` listing every skill, matching the
  manifest exactly; docs site rebuilt from scratch with verified internal
  links; `MINDMAP.md` regenerated.

## Wave 1 (v1.0.0)

- 24 original skills across 15 domains: 12 offensive (recon, nmap,
  web-sqli, web-xss, auth attacks, password attacks, Linux and Windows
  privesc, AD enumeration, network pivoting, C2 fundamentals) and 12
  engineering (code reviewer, incident response, Python CLI tooling, git
  workflows, Linux hardening, API security testing, cloud security
  basics, webapp pentest methodology, crypto fundamentals, forensics
  fundamentals, bug bounty workflow, secure coding).
- Core infra: `install.sh` installer, `scripts/validate.py` check harness,
  `scripts/score.py` 0-100 quality scorer (merge bar 70+),
  `scripts/bundle.py` offline bundles, `scripts/new_skill.py` scaffolding,
  per-skill semver with changelog entries, freshness dates, lifecycle
  states (experimental, stable, deprecated), dependency graph validation,
  Claude Code marketplace manifest, and MIT licensing.

## Upgrade notes

- Docs moved: the generated reference moved from `docs/` to
  `docs/site/`. If you linked to `docs/index.html` in the repo, it now
  resolves to the new landing page; the full reference is at
  `docs/site/index.html`.
- No breaking changes to skills, frontmatter, the manifest shape consumed
  by `install.sh`, or the marketplace manifest.
- Install as before: `./install.sh --platform <name> --all` (19 platforms
  supported, run `./install.sh --list-platforms` for the table).
