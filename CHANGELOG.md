# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 110 sub-skills under `skills/<domain>/<parent>/sub/<sub>/` decomposing 30
  high-value parent skills (3 to 6 sub-skills each), each with the standard
  frontmatter plus a `parent:` field, the full body skeleton, and manifest
  registration: web-sqli (6), web-xss (5), recon-active (4),
  nmap-methodology (5), auth-attacks (4), password-attacks (4),
  privesc-linux (5), privesc-windows (4), ad-enumeration (4), kerberoasting
  (3), bloodhound-methodology (3), c2-fundamentals (3), network-pivoting
  (3), webapp-pentest-methodology (4), api-security-testing (4),
  forensics-fundamentals (3), memory-forensics (3), disk-forensics (3),
  incident-response (4), incident-playbooks (3), secure-coding (4),
  code-reviewer (4), cloud-security-basics (3), aws-enumeration (3),
  crypto-fundamentals (3), rsa-attacks (3), linux-hardening (4),
  bug-bounty-workflow (3), osint-methodology (3), threat-hunting (3).
  `arsenal-manifest.json` regenerated via `scripts/derive_manifest.py` so all
  110 sub-skills are registered with matching sha256.

### Added (previous)

- Wave 3 architecture (Team A): new artifact kinds agents
  (`agents/<name>/AGENT.md`, 25 so far), brains (`brains/<name>/BRAIN.md`,
  16 so far), sub-skills (`skills/<domain>/<skill>/sub/<sub>/SKILL.md`, 20
  so far), playbooks (`playbooks/<name>/PLAYBOOK.md`, 8 so far), workflows
  (`workflows/*.md`, 4 so far), plus standing decisions
  (`decisions/ESCALATION_POLICY.md`, `RISK_MATRIX.md`, `GO_NO_GO_GATES.md`,
  `ADR_TEMPLATE.md`, `COST_BENEFIT.md`). `tools/memory-store/` reserved for
  the memory team.
- 7 new domains: ai-security, hardware, ics-scada, blockchain, automotive,
  privacy, memory (28 domains total).
- `scripts/validate.py`: validates sub-skills (parent field, parent cycle
  edges), agents, brains, playbooks (bindings resolve from frontmatter or
  phase tables), and workflows (title plus phase sections); tolerates
  missing artifact directories.
- `scripts/derive_manifest.py`: keeps the `skills` key shape frozen for
  install.sh and gen_readme_catalog.py; adds `sub_skills`, `agents`,
  `brains`, `playbooks`, `workflows`; `--check` covers all keys.
- `scripts/score.py`: adds 0-100 scoring for agents and brains (gate 70);
  `scores.json` is now `{"skills": {...}, "agents": {...}, "brains": {...}}`.
- `scripts/generate_docs.py`: per-agent, per-brain, and per-playbook pages,
  an agents index section, sub-skill trees on parent skill pages, and
  agent to skill to brain edges in the dependency graph.
- `scripts/gen_readme_catalog.py`: catalog now also lists agent, brain,
  sub-skill, playbook, and workflow counts.
- SPEC.md (new frontmatter standards, 7 new domains, Wave 3 artifact kinds),
  CONTRIBUTING.md (agent/brain/sub-skill/playbook/workflow templates and
  quality gates), and MINDMAP.md (new sections) updated for Wave 3.
- New `memory` domain with 5 skills: memory-capture, memory-recall, memory-consolidation, memory-hygiene, agent-state (lifecycle capture/recall/consolidate/hygiene plus agent task-state checkpoints), with docs in memory/ (MEMORY_SCHEMA.md, LIFECYCLE.md, HYGIENE.md) and a stdlib-only SQLite CLI at tools/memory-store/memory-store.py (store, recall, consolidate, forget, stats).
- 103 new skills (127 total) across 21 domains, adding 6 new domains: mobile (android-static, android-dynamic, ios-basics), binary (pwn-fundamentals, shellcode-basics, rop-chains, heap-exploitation, format-strings, angr-basics, ghidra-basics, firmware-analysis), malware (static-triage, dynamic-sandbox, yara-rules, packer-analysis), soc (threat-hunting, siem-detections, sigma-rules, suricata-ids, wazuh-basics, velociraptor-basics), osint (osint-methodology, domain-osint, social-media-osint, threat-intel), defensive (edr-basics, incident-playbooks, phishing-defense, ransomware-response), plus deep coverage of ad, cloud, crypto, forensics, incident, linux, network, privesc, recon, web, engineering, bugbounty, c2, api, auth.
- 46 operator tools under tools/ with `scripts/test_tools.py` harness (all 46 passing).
- Premium README with generated skill-count badge and domain-grouped catalog table via `scripts/gen_readme_catalog.py`; assets/banner.svg and assets/architecture.svg stat chips updated.
- docs/ site rebuilt from scratch for all 127 skills with verified internal links.
- `.claude-plugin/marketplace.json` now lists all 127 skills, matching arsenal-manifest.json exactly.
- MINDMAP.md regenerated with all 21 domains and 127 skills.

## [1.0.0] - 2026-10-23

Wave-1 launch.

### Added

- 24 skills across 15 domains: 12 offensive (recon-passive, recon-active, nmap-methodology, web-sqli, web-xss, auth-attacks, password-attacks, privesc-linux, privesc-windows, ad-enumeration, network-pivoting, c2-fundamentals) and 12 engineering (code-reviewer, incident-response, python-cli-tooling, git-workflows, linux-hardening, api-security-testing, cloud-security-basics, webapp-pentest-methodology, crypto-fundamentals, forensics-fundamentals, bug-bounty-workflow, secure-coding).
- `install.sh` installer that copies stable skills into the agent skill directory.
- Testing harness: `scripts/validate.py` (frontmatter, naming, dependency acyclicity, dates) and `scripts/score.py` (0-100 quality scores, 70 merge bar), both stdlib only.
- `scripts/bundle.py` for offline skill bundles with manifest; `scripts/new_skill.py` for scaffolding new skills.
- `docs/index.html` browsable reference with domains, skills, dependency graph, and quality scores.
- `.claude-plugin/marketplace.json` exposing all 24 wave-1 skills to Claude Code.
- Root policy files: README.md, SECURITY.md, CONTRIBUTING.md, ACKNOWLEDGEMENTS.md, MINDMAP.md, LICENSE (MIT).
