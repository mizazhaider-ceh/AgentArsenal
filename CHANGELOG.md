# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
