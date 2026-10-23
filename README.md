![AgentArsenal](assets/banner.svg)

# AgentArsenal

<!-- SKILLCOUNT:START -->
![skills](https://img.shields.io/badge/skills-127-blue)
<!-- SKILLCOUNT:END -->
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![validation](https://img.shields.io/badge/validation-passing-brightgreen)](scripts/validate.py)

AgentArsenal is a unified agent-skills repo that goes deep on both software engineering craft and offensive security practice, with quality enforced by machines, not vibes. Every skill carries a version, a freshness date, and a lifecycle state; a 14-check CI harness and a 0 to 100 quality scorer keep the bar high; and a single manifest drives the installer, the docs site, and the Claude Code marketplace integration.

## Features

- **Per-skill versioning**: every skill carries semver plus a changelog entry.
- **Testing harness**: `scripts/validate.py` runs 14 checks in CI covering the frontmatter standard, directory and naming rules, and dependency acyclicity.
- **Quality scores**: `scripts/score.py` grades every skill 0 to 100 on trigger density, command quality, edge cases, and references. Merging requires 70+.
- **Dependency graph**: `requires`, `extends`, and `relates` edges between skills are validated and visualized.
- **Freshness tracking**: `last_verified` dates flag stale skills; CI fails on impossible or outdated dates.
- **Lifecycle states**: experimental, stable, deprecated. Deprecated skills stay readable but are excluded from new bundles.
- **Offline bundles**: `scripts/bundle.py` packs skills into a single portable archive with a manifest.
- **Rollback**: every release is a git tag plus a changelog entry, so a bad skill can be reverted cleanly.
- **Marketplace manifest**: `.claude-plugin/marketplace.json` exposes every skill to Claude Code directly.

## How it compares

| Capability | AgentArsenal | Typical skill repo |
| --- | --- | --- |
| Per-skill versioning | Semver plus a changelog entry on every skill | No version tracking |
| Testing harness | 14-check CI harness (`scripts/validate.py`) | No automated checks |
| Quality scores | 0 to 100 per skill, merge requires 70+ | No scoring |
| Dependency graph | Validated and visualized skill relationships | No dependency model |
| Freshness tracking | `last_verified` dates, CI flags stale skills | No freshness data |
| Lifecycle states | experimental, stable, deprecated | No lifecycle states |
| Offline bundles | Portable single-archive bundles with manifest | No bundling |
| Rollback | Git tags plus changelog entries per release | No release discipline |
| Marketplace manifest | Direct Claude Code marketplace integration | No marketplace integration |

## Architecture

![AgentArsenal architecture](assets/architecture.svg)

## Quick install

```bash
./install.sh            # copy stable skills into your agent's skill directory
./install.sh --list     # show domains with skill counts, then exit
./install.sh --dry-run  # print what would be copied, change nothing
./install.sh --help     # all options
```

To regenerate the catalog below from `arsenal-manifest.json`:

```bash
python3 scripts/gen_readme_catalog.py
```

## Skill catalog

<!-- CATALOG:START -->
| Domain | Skills |
| --- | --- |
| ad | ad-enumeration, asreproasting, bloodhound-methodology, dcsync, golden-ticket, kerberoasting |
| api | api-security-testing |
| auth | auth-attacks, password-attacks |
| binary | angr-basics, firmware-analysis, format-strings, ghidra-basics, heap-exploitation, pwn-fundamentals, rop-chains, shellcode-basics |
| bugbounty | bug-bounty-workflow |
| c2 | c2-fundamentals |
| cloud | aws-enumeration, azure-enumeration, cloud-security-basics, container-escape, gcp-enumeration, iam-privesc, kubernetes-rbac, s3-misconfigurations |
| crypto | crypto-fundamentals, hash-cracking, padding-oracle, rsa-attacks, tls-analysis |
| defensive | edr-basics, incident-playbooks, phishing-defense, ransomware-response |
| engineering | ansible-basics, bash-advanced, cicd-security, code-reviewer, debugging-methodology, devsecops-pipeline, docker-deep, git-workflows, github-actions, go-basics, jq-mastery, kubernetes-basics, make-basics, nginx-hardening, performance-tuning, postgresql-tuning, prometheus-monitoring, python-advanced, python-cli-tooling, redis-basics, regex-mastery, rest-api-design, rust-basics, secure-coding, sqlite-deep, ssh-hardening, systemd-deep, technical-writing, terraform-basics, testing-strategies, tmux-workflows, typescript-basics, vim-mastery |
| forensics | disk-forensics, email-forensics, forensics-fundamentals, log-forensics, memory-forensics |
| incident | incident-response |
| linux | linux-hardening |
| malware | dynamic-sandbox, packer-analysis, static-triage, yara-rules |
| mobile | android-dynamic, android-static, ios-basics |
| network | arp-spoofing, bluetooth-le, dns-enumeration, firewall-evasion, ipv6-attacks, llmnr-poisoning, network-pivoting, nmap-methodology, smb-enumeration, snmp, wireless-wpa |
| osint | domain-osint, osint-methodology, social-media-osint, threat-intel |
| privesc | privesc-linux, privesc-windows |
| recon | recon-active, recon-passive |
| soc | siem-detections, sigma-rules, suricata-ids, threat-hunting, velociraptor-basics, wazuh-basics |
| web | cache-poisoning, cors-misconfig, csrf, file-upload-attacks, graphql-security, http-request-smuggling, jwt-attacks, lfi-rfi, nosql-injection, oauth-attacks, open-redirect, race-conditions, ssrf, ssti, web-sqli, web-xss, webapp-pentest-methodology, websocket-security, xxe |
| **Total** | **127 skills across 21 domains** |
<!-- CATALOG:END -->

## Docs

Open `docs/index.html` in a browser for the full browsable reference: all domains, skills, dependency graph, and quality scores.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the frontmatter standard, the body skeleton every skill must follow, and how to add a new skill with `scripts/new_skill.py`.

## Scope

**Authorized security work only.** Red team engagements with written authorization, bug bounty programs within scope, CTF competitions, security research on your own systems, and training labs. See [SECURITY.md](SECURITY.md) for the explicit rejection list.

## Credits

Built with original content. The infrastructure ideas it follows were learned from two MIT-licensed projects; see [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) for the full, factual attribution.
