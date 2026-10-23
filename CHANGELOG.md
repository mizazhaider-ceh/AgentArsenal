# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
