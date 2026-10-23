![AgentArsenal](assets/banner-keeper.png)

# AgentArsenal | 285 Powerful Skills | 25 Agents

<!-- SKILLCOUNT:START -->
![skills](https://img.shields.io/badge/skills-285-A78BFA)
<!-- SKILLCOUNT:END -->
[![sub-skills](https://img.shields.io/badge/sub--skills-227-536DFE)](MINDMAP.md)
[![agents](https://img.shields.io/badge/agents-25-A78BFA)](agents/README.md)
[![brains](https://img.shields.io/badge/brains-16-536DFE)](brains/README.md)
[![platforms](https://img.shields.io/badge/platforms-19-A78BFA)](platforms/PLATFORM_SUPPORT.md)
[![tools](https://img.shields.io/badge/CLI%20tools-47-536DFE)](tools/README.md)
[![quality](https://img.shields.io/badge/avg%20quality-96.1-171923)](scores.json)
[![validation](https://img.shields.io/badge/validation-passing-7E6BF5)](scripts/validate.py)
[![license](https://img.shields.io/badge/license-MIT-A78BFA)](LICENSE)

**AgentArsenal is a unified agent-skills repo that goes deep on software engineering craft and offensive security practice, with quality enforced by machines, not vibes.**

Every skill carries a version, a freshness date, and a lifecycle state. A 14-check CI harness and a 0 to 100 quality scorer keep the bar high. One manifest drives the installer, the docs site, and the Claude Code marketplace integration.

```diff
+ 285 skills across 29 domains, every one versioned, scored, and CI-checked
+ 227 sub-skills that drill into the 69 highest-value parent skills
+ 25 named agents, 16 reasoning brains, 8 engagement playbooks, 4 multi-agent workflows
+ 47 stdlib-only CLI operator tools, zero third-party dependencies
+ 19 agent platforms supported from one SKILL.md standard
- No scattered blog posts, no untested snippets, no stale one-off prompts
```

![AgentArsenal stats](assets/stats-strip.svg)

## Table of contents

- [What is AgentArsenal](#what-is-agentarsenal)
- [Who is it for](#who-is-it-for)
- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Install for your platform](#install-for-your-platform)
- [Command reference](#command-reference)
- [Skill catalog](#skill-catalog)
- [Sub-skills](#sub-skills)
- [Agents](#agents)
- [Brains](#brains)
- [Memory system](#memory-system)
- [Decision docs](#decision-docs)
- [Playbooks](#playbooks)
- [Workflows](#workflows)
- [CLI tools](#cli-tools)
- [Quality and benchmarks](#quality-and-benchmarks)
- [Learning paths](#learning-paths)
- [FAQ](#faq)
- [Project stats](#project-stats)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## What is AgentArsenal

AgentArsenal is a curated library of **skills** for AI coding agents, plus the machinery that keeps them trustworthy: **agents** (named operators), **brains** (reusable reasoning patterns), **sub-skills** (drill-down modules), **playbooks** (end-to-end engagement runbooks), **workflows** (multi-agent coordination patterns), **decision docs** (escalation and risk policy), a **memory system** (schema plus a SQLite CLI), and **47 CLI tools** (stdlib-only operator utilities).

A skill is a folder with a `SKILL.md` file. The file starts with YAML frontmatter whose `description` field is a **trigger**: a dense paragraph that says exactly when the agent should load the skill ("Use when ..."). The body then gives the agent a numbered Quick Workflow, per-phase procedures with exact commands, edge cases, escalation paths, a defender view, and key references. Supporting files ride along: `scripts/` for executable code, `references/` for deep material, `assets/` for templates. They load only when the skill body points at them.

What makes this repo different from a folder of prompts:

- **Per-skill versioning.** Every skill carries semver plus a changelog entry. You can pin `web-sqli@1.0.0` and know exactly what you installed.
- **Machine-enforced quality.** `scripts/validate.py` runs 14 checks in CI (frontmatter standard, naming rules, dependency acyclicity, freshness dates). `scripts/score.py` grades every skill 0 to 100 on trigger density, command quality, edge cases, and references. Merging requires 70 or higher. The repo average is 95.6 and the lowest scored artifact is 92.
- **Dependency graph.** Skills declare `requires`, `extends`, and `relates` edges. The installer resolves the full dependency closure automatically, and CI fails on dangling references or cycles. The graph is visualized in [MINDMAP.md](MINDMAP.md) and `docs/graph.html`.
- **Freshness tracking.** Every skill carries a `last_verified` date. CI flags impossible or outdated dates, so stale skills cannot hide.
- **Lifecycle states.** Skills are `experimental`, `stable`, or `deprecated`. Deprecated skills stay readable but are excluded from new bundles.
- **Offline bundles.** `scripts/bundle.py` packs skills into a single portable archive with a manifest for air-gapped environments.
- **Rollback.** Every release is a git tag plus a changelog entry, and `install.sh` backs up the target before touching it. A bad skill reverts cleanly.
- **Marketplace manifest.** `.claude-plugin/marketplace.json` exposes every skill to Claude Code directly.

![How AgentArsenal works](assets/how-it-works-strip.svg)

![AgentArsenal vs typical skill repos](assets/comparison-strip.svg)

| Capability | AgentArsenal | Typical skill repo |
| --- | --- | --- |
| Per-skill versioning | :white_check_mark: Semver plus a changelog entry on every skill | :x: No version tracking |
| Testing harness | :white_check_mark: 14-check CI harness (`scripts/validate.py`) | :x: No automated checks |
| Quality scores | :white_check_mark: 0 to 100 per skill, merge requires 70+ | :x: No scoring |
| Dependency graph | :white_check_mark: Validated and visualized skill relationships | :x: No dependency model |
| Freshness tracking | :white_check_mark: `last_verified` dates, CI flags stale skills | :x: No freshness data |
| Lifecycle states | :white_check_mark: experimental, stable, deprecated | :x: No lifecycle states |
| Offline bundles | :white_check_mark: Portable single-archive bundles with manifest | :x: No bundling |
| Rollback | :white_check_mark: Git tags plus changelog entries per release | :x: No release discipline |
| Marketplace manifest | :white_check_mark: Direct Claude Code marketplace integration | :x: No marketplace integration |

## Who is it for

Full audience guide: [AUDIENCES.md](AUDIENCES.md). Every name below is a real artifact in this repo. Install starters with the sparse installer, for example `./install.sh --version nmap-methodology@1.0.0` or `./install.sh --category web`.

### :mortar_board: Cyber students
**What you get:** a structured path from first principles to a full methodology, with every procedure written as numbered operator steps and exact commands. Skills replace scattered blog posts with one curated source that a quality scorer already graded.
**Start with:** skills `recon-passive`, `recon-active`, `nmap-methodology`, `linux-hardening`, `web-sqli`, `webapp-pentest-methodology`, `python-cli-tooling`, `git-workflows`; agent `recon-agent`; brain `scientific-debugging`.

### :crossed_swords: Pentesters
**What you get:** full engagement methodology, from recon to reporting, with dependency-aware install (a skill's `requires` chain installs automatically) and escalation paths when the standard path fails.
**Start with:** skills `webapp-pentest-methodology`, `ad-enumeration`, `bloodhound-methodology`, `privesc-linux`, `privesc-windows`, `network-pivoting`, `c2-fundamentals`, `password-attacks`, `api-security-testing`; agents `recon-agent`, `web-exploitation-agent`, `pentest-reporter-agent`.

### :rotating_light: SOC analysts
**What you get:** triage runbooks, detection content, and DFIR procedures written as checklists your agent can execute during a live shift.
**Start with:** skills `siem-detections`, `sigma-rules`, `suricata-ids`, `threat-hunting`, `dfir-timeline`, `soc-triage-day` playbook; agent `soc-analyst-agent`; brain `opa-decision-loop`.

### :computer: Developers
**What you get:** engineering craft skills that make your agent a better pair programmer: secure coding, code review, debugging methodology, CI/CD, containers, and testing strategies.
**Start with:** skills `secure-coding`, `code-reviewer`, `debugging-methodology`, `git-workflows`, `docker-deep`, `testing-strategies`; agent `code-review-agent`; brain `scientific-debugging`.

### :microscope: Security researchers
**What you get:** deep-dive material on binary exploitation, cryptography, hardware, and AI security, with references and edge cases instead of surface summaries.
**Start with:** skills `pwn-fundamentals`, `rop-chains`, `heap-exploitation`, `ghidra-basics`, `rsa-attacks`, `llm-red-teaming`; agent `binary-exploitation-agent`; brain `hypothesis-driven-testing`.

### :teacher: Educators
**What you get:** a ready-made curriculum spine. The [learning paths](docs/learning-paths/BEGINNER.md) order skills beginner to expert, and every skill has the same body skeleton (Quick Workflow, Edge cases, Key references) so lesson plans write themselves.
**Start with:** the `recon` and `network` domains, brain `scientific-debugging`, and the `soc-triage-day` playbook for blue team labs.

### :moneybag: Bug bounty hunters
**What you get:** a systematic hunting workflow and report templates that get accepted and paid, plus the web and API attack skills that cover the most common bounty targets.
**Start with:** skills `bug-bounty-workflow`, `webapp-pentest-methodology`, `api-security-testing`, `recon-active`; agent `bug-bounty-hunter-agent`; playbook `bug-bounty-sprint`.

### :shield: Blue teams
**What you get:** detection engineering, hardening baselines, incident playbooks, and purple team exercises that prove detections work instead of assuming they do.
**Start with:** skills `detection-as-code`, `sigma-rules`, `endpoint-hardening-baseline`, `incident-playbooks`, `purple-team-exercises`; agent `purple-team-agent`; brain `defender-mindset`.

### :rocket: Startup founders
**What you get:** a pragmatic security baseline without hiring a team: SDLC rollout, cloud review, secrets management, and privacy engineering, sized for small teams.
**Start with:** skills `secure-sdlc-rollout` playbook, `cloud-security-basics`, `secrets-in-code`, `gdpr-engineering`; agent `secure-architect-agent`; brain `cost-of-attack`.

## How it works

Deep dive: [HOW_IT_WORKS.md](HOW_IT_WORKS.md). The short version:

### :zap: Skill loading (progressive disclosure)
At session start, the agent reads only the `name` and `description` of each installed skill. This costs almost no context. When your prompt matches a description, the agent loads the full skill body: the framing paragraph, the numbered Quick Workflow, per-phase procedures with exact commands, edge cases, escalation paths, the defender view, and key references. A good `description` decides whether a skill ever fires, which is why the quality scorer grades trigger density.

### :link: Composition and the dependency graph
Skills compose through three edge types in frontmatter:

- `requires`: hard prerequisites. `webapp-pentest-methodology` requires `recon-active`, `web-sqli`, `web-xss`, and `auth-attacks`. The installer resolves the full `requires` plus `extends` closure and installs the whole chain.
- `extends`: specialization. A skill extends a broader one when it drills into one of its phases.
- `relates`: see-also links. `web-sqli` relates to `web-xss` and `api-security-testing`. These guide discovery, not installation.

Sub-skills add one more edge: `parent`. A sub-skill lives at `skills/<domain>/<skill>/sub/<sub>/SKILL.md` and its `parent` field must name the enclosing top-level skill. The validator enforces two rules on the whole graph: every name must resolve to a real artifact, and the `requires` plus `extends` plus `parent` edges must form no cycles. A cycle or a dangling reference fails CI.

### :busts_in_silhouette: Agents bind skills plus brains plus memory
Each agent is an `agents/<name>/AGENT.md` file with a fixed frontmatter contract: a role, the skills it loads, the brains it reasons with, a memory mode (`stateless` or `persistent`), an escalation file, and hard constraints it never breaks. Agents are operational roles you can run: `recon-agent` turns unknown targets into a scoped inventory, `pentest-reporter-agent` turns raw findings into reports executives trust.

### :brain: Brains are reusable reasoning patterns
Brains like `attacker-mindset` (think in attack graphs, take the cheapest path), `evidence-chain` (every claim traces to a source), and `threat-modeling` (asset-first, trust boundaries, STRIDE-style enumeration) plug into any agent. Sixteen brains cover offensive reasoning, defensive reasoning, debugging, incident command, and decision making under pressure.

### :floppy_disk: Memory has a schema, not just vibes
Agent memory follows [memory/MEMORY_SCHEMA.md](memory/MEMORY_SCHEMA.md): episodic entries (timestamped events, TTL 30 days), semantic entries (durable facts), and procedural entries (how things are done). [memory/LIFECYCLE.md](memory/LIFECYCLE.md) defines capture, consolidation, and expiry; [memory/HYGIENE.md](memory/HYGIENE.md) keeps it clean. The [memory-store](tools/memory-store/) CLI is a small SQLite store agents use to read and write memory.

### :scroll: Decisions set the guardrails
Five standing decision docs in [decisions/](decisions/): escalation policy, risk matrix, go/no-go gates, ADR template, and cost-benefit analysis. Agents point at these files in their frontmatter, so "when do I stop and ask a human" is policy, not improvisation.

### :clipboard: Playbooks run the engagement
A playbook binds agents, skills, brains, and decisions into an ordered runbook with phases, entry and exit criteria, roles and handoffs, stop conditions, and artifacts produced. Eight playbooks cover AD assessments, webapp assessments, external pentests, bug bounty sprints, cloud reviews, SOC triage days, malware outbreaks, and secure SDLC rollouts.

### :white_check_mark: CI gates keep the bar
`scripts/validate.py` runs 14 checks over every artifact: required frontmatter fields, name-slug matching the directory, trigger-dense descriptions, semver versions, valid lifecycle values, sane `last_verified` dates, dependency resolution, graph acyclicity, required body headings (Quick Workflow, Edge cases, Key references), sub-skill parent edges, agent/brain/playbook contracts, manifest consistency, and no em dashes in content. `scripts/score.py` then grades quality 0 to 100. Merge needs 70+. Anything red fails the build.

![AgentArsenal architecture](assets/architecture.svg)

![AgentArsenal ecosystem](assets/ecosystem.svg)

## Quick start

```bash
git clone https://github.com/mizazhaider-ceh/AgentArsenal.git
cd AgentArsenal
./install.sh --list            # show domains with skill counts, then exit
./install.sh --dry-run         # print what would be copied, change nothing
./install.sh                   # copy stable skills into your agent skills directory
```

Targeted installs:

```bash
./install.sh --category web --dry-run        # preview one domain
./install.sh --category web                  # install the whole web domain
./install.sh --version web-sqli@1.0.0        # pin one skill at one version
./install.sh --platform opencode --all       # install for OpenCode (19 platforms supported)
./install.sh --list-platforms                # print the supported platform table
./install.sh --rollback                      # restore the pre-install backup
./install.sh --help                          # all options
```

Full flag reference: [COMMANDS.md](COMMANDS.md).

## Install for your platform

One `SKILL.md` standard, every major agent. The platform name is the value for `install.sh --platform`. Full paths, per-platform quirks (such as OpenCode per-skill permissions), and each platform agent memory file: [platforms/PLATFORM_SUPPORT.md](platforms/PLATFORM_SUPPORT.md).

| Platform | Install command | Skills folder |
| --- | --- | --- |
| Claude Code | `./install.sh --platform claude-code --all` | `~/.claude/skills/` |
| OpenCode | `./install.sh --platform opencode --all` | `~/.config/opencode/skills/` |
| Codex CLI | `./install.sh --platform codex-cli --all` | `~/.agents/skills/` |
| Gemini CLI | `./install.sh --platform gemini-cli --all` | `~/.gemini/skills/` |
| Cursor | `./install.sh --platform cursor --all` | `~/.cursor/skills/` |
| GitHub Copilot | `./install.sh --platform github-copilot --all` | `~/.copilot/skills/` |
| Amp | `./install.sh --platform amp --all` | `~/.agents/skills/` |
| Goose | `./install.sh --platform goose --all` | `~/.agents/skills/` |
| Cline | `./install.sh --platform cline --all` | `~/.agents/skills/` |
| Roo Code | `./install.sh --platform roo-code --all` | `~/.agents/skills/` |
| Kilo Code | `./install.sh --platform kilo-code --all` | `~/.agents/skills/` |
| Zed | `./install.sh --platform zed --all` | `~/.agents/skills/` |
| Warp | `./install.sh --platform warp --all` | `~/.agents/skills/` |
| Windsurf | `./install.sh --platform windsurf --all` | `~/.agents/skills/` |
| Kiro | `./install.sh --platform kiro --all` | `~/.kiro/skills/` |
| Qwen Code | `./install.sh --platform qwen-code --all` | `~/.qwen/skills/` |
| Crush | `./install.sh --platform crush --all` | `~/.agents/skills/` |
| Continue | `./install.sh --platform continue --all` | `~/.agents/skills/` |
| Aider | `./install.sh --platform aider` prints a pointer snippet | no skills support (uses `AGENTS.md`) |

:bulb: **Tip:** run any command with `--dry-run` first to preview exactly what gets copied. The installer backs up your existing skills before touching them.

## Command reference

Complete reference with verified examples: [COMMANDS.md](COMMANDS.md). Summary:

<details>
<summary><strong>Expand the command summary</strong></summary>

### install.sh (the sparse installer)

Copies chosen skill folders into a platform skills directory, resolving `requires`/`extends` chains from `arsenal-manifest.json`. Backs up the target before touching it.

| Flag | What it does |
| --- | --- |
| `--all` | Install every skill in the manifest |
| `--category <name>` | Install one domain (see `--list` for names) |
| `--version <skill@ver>` | Install one skill at a pinned version, fails on mismatch |
| `--platform <name>` | Set the target to a platform skills folder |
| `--target <dir>` | Custom install target directory |
| `--list` | Print domains with skill counts, then exit |
| `--list-platforms` | Print the supported platform table, then exit |
| `--dry-run` | Print what would be copied, change nothing |
| `--rollback` | Restore the most recent backup of the target |
| `--help` | All options |

### scripts/

| Script | What it does |
| --- | --- |
| `scripts/validate.py` | 14-check CI validator over every artifact, exits non-zero on any failure |
| `scripts/score.py` | Quality scorer 0 to 100 per artifact (merge needs 70+) |
| `scripts/bundle.py` | Pack skills into a portable offline archive with a manifest |
| `scripts/derive_manifest.py` | Regenerate `arsenal-manifest.json` from the repo tree |
| `scripts/gen_readme_catalog.py` | Regenerate the README skill-count badge and catalog from the manifest |
| `scripts/gen_marketplace.py` | Regenerate `.claude-plugin/marketplace.json` |
| `scripts/generate_docs.py` | Build the browsable docs site under `docs/` |
| `scripts/new_skill.py` | Scaffold a new skill with valid frontmatter and body skeleton |
| `scripts/test_tools.py` | Test harness for the 47 CLI tools |

### tools/ (47 stdlib-only CLIs)

```bash
python3 tools/port-scanner/port-scanner.py scanme.example.com -p 1-1024
python3 tools/file-hasher/file-hasher.py document.pdf
python3 tools/subnet-calculator/subnet-calculator.py 192.168.1.0/24
```

Every tool accepts `--help`, exits 0 on success, 2 on usage errors. Full table in [CLI tools](#cli-tools).

</details>

## Skill catalog

<!-- CATALOG:START -->
285 skills across 29 domains. Regenerated from `arsenal-manifest.json` by `scripts/gen_readme_catalog.py`.

<details>
<summary><strong>Expand the full catalog: 285 skills, one line each</strong></summary>

### :key: ad (8 skills)

*Active Directory attack paths, from enumeration to ticket forging, for authorized internal assessments.*

- `ad-enumeration`: mapping an authorized Active Directory environment during an internal assessment or assumed breach exercise. AD enumeration with kerbrute for Kerberos user discovery, ldapsearch for direct LDAP queries, NetExec modules for SMB, LDAP, and WinRM enumeration, and BloodHound with SharpHound for attack path analysis.
- `ad-trust-attacks`: assessing Active Directory trust relationships on an authorized engagement. Covers trust enumeration, SID history abuse, cross forest Kerberos attacks, and trust direction review.
- `asreproasting`: testing Active Directory for AS-REP roasting on an authorized engagement. Covers finding accounts with Kerberos preauthentication disabled, requesting crackable AS-REP responses with GetNPUsers.py from impacket 0.12.0 and Rubeus 2.x, and offline cracking of krbasrep5 hashes with hashcat 6.2.6 mode 18200 or John the Ripper 1.9.0-jumbo-1.
- `bloodhound-methodology`: mapping Active Directory attack paths on an authorized engagement.
- `dcsync`: pulling Active Directory credential material through directory replication on an authorized engagement.
- `golden-ticket`: forging Kerberos tickets on an authorized Active Directory engagement after recovering the krbtgt account hash.
- `gpo-abuse`: assessing Group Policy security on an authorized AD engagement. Covers GPO enumeration, dangerous settings review, GPO based privilege escalation paths, and delegation review.
- `kerberoasting`: testing Active Directory for Kerberoasting on an authorized engagement. Covers SPN enumeration, TGS ticket requests with GetUserSPNs.py and Rubeus, offline cracking of krb5tgs hashes with hashcat 6.2.6, and targeted Kerberoasting against accounts you can write SPNs to.

### :robot: ai-security (8 skills)

*Attacking and defending LLM and AI agent systems: prompt injection, red teaming, guardrails, supply chain.*

- `agent-hijacking`: testing an AI agent that can call tools or take actions on an authorized engagement. Covers tool output poisoning, confused deputy attacks, excessive agency, and prompt driven abuse of email, calendar, code execution, and browser tools.
- `ai-incident-response`: responding to a suspected security incident involving an AI system: a hijacked agent, a poisoned model, leaked prompts, or abusive use of inference infrastructure.
- `ai-supply-chain`: reviewing the supply chain of an AI system on an authorized assessment: model weights, datasets, base images, and third party integrations. Covers model provenance checks, poisoned dataset detection, dependency review for ML pipelines, and signing of artifacts.
- `guardrail-bypass-testing`: testing whether an LLM application's safety guardrails can be bypassed on an authorized engagement. Covers refusal classifier evasion, encoding tricks, roleplay framing, low resource language pivots, and multi step decomposition of refused requests.
- `llm-red-teaming`: running a structured red team exercise against an LLM application with authorization. Covers scoping, attack categorization (jailbreak, data extraction, insecure output, excessive agency), systematic test matrices, and scoring findings by impact.
- `model-extraction`: assessing whether a machine learning model behind an API can be stolen or copied on an authorized engagement. Covers prediction API scraping, membership inference, model inversion, and functionality stealing through systematic querying.
- `prompt-injection`: testing an LLM powered application for prompt injection on an authorized assessment. Covers direct and indirect injection, system prompt extraction, instruction override, delimiter smuggling, and multi-turn manipulation against chatbots, copilots, and agents.
- `rag-security`: assessing a retrieval augmented generation system on an authorized engagement. Covers document poisoning, embedding inversion, retrieval manipulation, context window stuffing, and access control gaps between the retriever and the user.

### :electric_plug: api (3 skills)

*Testing and reviewing APIs: security testing, gRPC, OpenAPI review, rate limit abuse.*

- `api-security-testing`: testing REST, GraphQL, or internal APIs on an authorized engagement.
- `grpc-security`: assessing gRPC services on an authorized engagement. Covers service enumeration via reflection, auth review, message validation, and intercepting gRPC traffic.
- `openapi-security-review`: reviewing an OpenAPI specification for security issues on an authorized engagement. Covers contract vs implementation drift, auth scheme review, schema validation gaps, and finding hidden endpoints.

### :lock: auth (4 skills)

*Breaking and fixing authentication: credential attacks, session handling, WebAuthn.*

- `auth-attacks`: testing authentication on an authorized engagement.
- `password-attacks`: cracking password hashes or auditing password strength on an authorized engagement. Covers hash identification, hashcat 6.2.6 and John the Ripper 1.9.0-jumbo-1 workflows, wordlist strategy, rule-based mutation, mask and hybrid attacks, and interpreting results for the report.
- `session-management-security`: assessing session management on an authorized web engagement. Covers cookie attributes, session fixation, timeout and rotation, concurrent session handling, and logout completeness.
- `webauthn-security`: assessing or implementing WebAuthn and passkeys on an authorized engagement. Covers registration and authentication ceremonies, attestation review, common implementation flaws, and fallback security.

### :car: automotive (8 skills)

*Vehicle security: CAN bus, ECUs, keyless entry, ISO 21434, V2X.*

- `automotive-ethernet`: assessing automotive Ethernet on a vehicle or bench setup you own or have authorization to test. Covers BroadR-Reach and 100BASE-T1 basics, SOME/IP service discovery, DoIP diagnostics, and VLAN segmentation in zonal architectures.
- `automotive-threat-model`: building a threat model for a vehicle or automotive component on an authorized engagement. Covers asset and attacker profiling, attack surface mapping across interfaces, attack trees for key scenarios, and prioritizing testing from the model.
- `can-bus-security`: assessing CAN bus security on a vehicle or bench setup you own or have authorization to test. Covers CAN sniffing with SocketCAN, message reverse engineering, injection testing, and gateway segmentation review.
- `ecu-firmware`: analyzing ECU firmware on an authorized assessment or your own bench hardware. Covers firmware extraction from ECUs, update package analysis, UDS flashing flows, and static review of automotive code.
- `iso21434-basics`: you need working knowledge of ISO/SAE 21434 for automotive cybersecurity work. Covers the standard's structure, TARA (threat analysis and risk assessment), cybersecurity planning, and how assessments map to its clauses.
- `keyless-entry-attacks`: assessing keyless entry and immobilizer systems on vehicles you own or have authorization to test, in a lab setting. Covers relay attack concepts, rolling code analysis, and defensive review of key fob protocols.
- `telematics-security`: assessing a telematics unit or connected car backend on an authorized engagement. Covers TCU architecture, cellular attack surface, backend API review, and remote command flows.
- `v2x-security`: assessing vehicle to everything communication on an authorized engagement or lab setup. Covers DSRC and C-V2X basics, message types (BSM, CAM, DENM), PKI and certificate review, and misbehavior detection concepts.

### :nut_and_bolt: binary (13 skills)

*Reverse engineering and exploitation: pwn basics, ROP, heap, shellcode, Ghidra, angr.*

- `angr-basics`: you need symbolic execution to explore program paths automatically, typically for CTF binaries, crackmes, or vulnerability research on code you are authorized to analyze.
- `binary-anti-analysis-bypass`: a binary under authorized lab analysis resists analysis resists debugging or sandboxing, covering debugger detection, timing checks, VM and sandbox fingerprinting, or stalling tricks.
- `binary-patching`: patching binaries in a lab on authorized targets: your own software, CTF binaries, or client approved test builds. Covers byte patching, assembly level fixes, and verifying patches.
- `binary-patching-techniques`: you need to modify a compiled binary's behavior in an authorized lab, covering bypassing a license or trial check, neutralizing an anti-analysis routine, correcting a buggy code path, or testing how a program reacts to altered logic.
- `firmware-analysis`: analyzing a firmware image from a device you own or are authorized to test. Covers Binwalk scanning and extraction, entropy analysis, SquashFS and archive recovery, bootloader and kernel identification, hunting hardcoded credentials and keys, and reverse engineering extracted binaries with Ghidra.
- `format-strings`: you need to exploit a format string vulnerability on an authorized target, such as a CTF pwn challenge or lab binary that passes user input directly to printf or a similar function.
- `ghidra-basics`: you need to reverse engineer a compiled binary on an authorized task, such as a CTF reversing challenge, malware triage in a lab, or auditing a binary you have permission to analyze.
- `heap-exploitation`: you need to exploit a heap memory bug on an authorized target, such as a CTF pwn challenge with use-after-free, heap overflow, or double free, or a lab binary using malloc and free unsafely.
- `kernel-exploit-basics`: learning kernel exploitation fundamentals in a lab with your own vulnerable VMs. Covers kernel attack surface, common bug classes, SMEP/SMAP/KASLR bypass concepts, and safe lab practices.
- `pwn-fundamentals`: you need to exploit a classic stack buffer overflow on an authorized target, such as a CTF pwn challenge or a lab binary you have permission to test.
- `rop-chains`: you need to build a Return Oriented Programming chain on an authorized target, such as a CTF pwn challenge with NX enabled and no easy win function.
- `shellcode-basics`: you need to write or use position-independent machine code payloads on an authorized target, such as a CTF pwn challenge where NX is disabled, a buffer you can execute, or a ROP chain that made memory writable and executable.
- `srop-attacks`: learning Sigreturn Oriented Programming in a lab on CTF style binaries you own. Covers sigreturn mechanics, frame forging, and chaining syscalls without gadgets.

### :link: blockchain (8 skills)

*Smart contract audits, DeFi threats, bridge attacks, wallets, on-chain forensics.*

- `blockchain-forensics`: tracing cryptocurrency in an investigation on an authorized case. Covers address clustering, transaction graph analysis, exchange attribution, and following funds through mixers and bridges at the methodology level.
- `bridge-attacks`: assessing cross chain bridge security on an authorized engagement. Covers bridge architectures, validator and relayer trust models, message verification flaws, and the classic bridge hack patterns.
- `consensus-attacks`: you need working knowledge of consensus layer attacks for blockchain security assessments. Covers 51 percent attacks, selfish mining, long range attacks on PoS, eclipse attacks, and finality concepts.
- `dao-governance-risks`: assessing DAO governance security on an authorized engagement. Covers vote buying, flash loan governance attacks, proposal thresholds, timelock review, and multisig versus token vote tradeoffs.
- `defi-threats`: assessing DeFi protocols for economic and technical attacks on an authorized engagement. Covers flash loan attacks, oracle manipulation, sandwich attacks, and governance takeovers at the design level.
- `nft-fraud`: assessing NFT projects, marketplaces, or fraud patterns on an authorized engagement. Covers wash trading detection, metadata and minting flaws, phishing against collectors, and marketplace logic review.
- `smart-contract-audit`: auditing Solidity smart contracts on an authorized engagement or for your own project. Covers static analysis with Slither, manual review of access control and arithmetic, reentrancy testing, and upgradeability review.
- `wallet-security`: reviewing cryptocurrency wallet security for users or on an authorized product assessment. Covers seed phrase handling, hardware versus software wallets, transaction signing risks, and common theft techniques to defend against.

### :moneybag: bugbounty (5 skills)

*Running a bug bounty workflow end to end, from recon to paid report.*

- `bug-bounty-workflow`: hunting on a bug bounty program and you need a repeatable, professional methodology from scope to payout.
- `bugbounty-duplicate-avoidance`: a finding is validated on an in-scope bug bounty target and you need to check it is not already known before writing the report.
- `bugbounty-methodology`: hunting on an in-scope bug bounty program and you need a complete, repeatable methodology that takes you from scope reading to payout.
- `bugbounty-report-writing`: a validated in-scope finding needs to become a report that gets triaged fast and paid fairly.
- `bugbounty-scope-recon`: starting a new in-scope bug bounty program and you need reconnaissance that stays strictly inside the authorized scope.

### :satellite: c2 (1 skills)

*Command and control fundamentals for authorized red team operations.*

- `c2-fundamentals`: designing the command and control layer of an authorized red team or adversary emulation exercise.

### :cloud: cloud (16 skills)

*Cloud attack surface: AWS, Azure, GCP enumeration, IAM privilege escalation, containers, Kubernetes, serverless.*

- `aws-enumeration`: enumerating an AWS environment during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `azure-enumeration`: enumerating a Microsoft Azure tenant or subscription during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `ci-secrets-management`: reviewing how CI/CD pipelines handle secrets on an authorized assessment. Covers secret storage in pipeline config, log leakage, pull request exposure, and OIDC versus long lived tokens.
- `cloud-cost-attack-surface`: assessing cloud cost as an attack surface on an authorized engagement. Covers denial of wallet, resource exhaustion billing, free tier abuse, and cost anomaly detection.
- `cloud-forensics`: doing forensics in cloud environments on an authorized investigation. Covers log sources per provider, snapshot and disk acquisition, volatile evidence in ephemeral workloads, and timeline building from cloud audit trails.
- `cloud-security-basics`: reviewing cloud security posture at concept level across AWS, GCP, and Azure, when checking IAM for least privilege and wildcard grants, when hunting public storage buckets and open security groups.
- `container-escape`: testing container escape during an authorized security assessment, CTF, or lab exercise.
- `container-image-security`: assessing container image security on an authorized engagement or in your own pipeline. Covers image scanning, base image choice, secret leakage in layers, and signing with Cosign.
- `gcp-enumeration`: enumerating a Google Cloud project, folder, or organization during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `iam-privesc`: assessing AWS IAM privilege escalation paths during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `k8s-pentest`: penetration testing Kubernetes clusters on an authorized engagement. Covers cluster enumeration, RBAC abuse, pod escape to node, etcd access, and service account token theft.
- `kubernetes-rbac`: enumerating and testing Kubernetes RBAC during an authorized cloud or cluster assessment, bug bounty engagement, or lab exercise.
- `multi-cloud-iam`: reviewing identity across multiple cloud providers on an authorized engagement. Covers federated identity design, cross cloud role assumptions, consistent least privilege, and finding the weakest provider.
- `s3-misconfigurations`: testing Amazon S3 buckets for misconfigurations during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `saas-security-review`: reviewing the security of a SaaS application your organization uses or builds. Covers SSO and SCIM, data residency, tenant isolation, admin controls, and offboarding.
- `serverless-security`: assessing serverless applications (Lambda, Cloud Functions, Azure Functions) on an authorized engagement. Covers function enumeration, event injection, IAM role abuse, and insecure dependencies.

### :closed_lock_with_key: crypto (9 skills)

*Applied cryptography attacks: RSA, padding oracles, hash cracking, TLS analysis.*

- `crypto-fundamentals`: you face hashes, tokens, or ciphertext on an authorized test, CTF, or code review and need an operator-grade crypto workflow.
- `ecc-crypto-attacks`: assessing elliptic curve cryptography on an authorized engagement. Covers weak curve parameters, invalid curve attacks, nonce reuse in ECDSA, and implementation review.
- `hash-cracking`: you need to recover plaintexts from password hashes on an authorized engagement, such as cracking NTLM hashes from a domain dump, testing password strength after extracting hashes in scope, or solving CTF crypto challenges.
- `hash-length-extension`: testing for hash length extension attacks on an authorized assessment. Covers Merkle Damgard hashes, forging authenticated payloads with hashpump style extension, and reviewing MAC constructions.
- `padding-oracle`: you encounter CBC-mode ciphertext with distinguishable padding errors on an authorized test, CTF, or code review, and need to decrypt or forge messages without the key.
- `post-quantum-basics`: you need working knowledge of post quantum cryptography for planning and assessment. Covers the threat model, NIST standardized algorithms, hybrid deployments, and migration planning.
- `rng-attacks`: assessing random number generation on an authorized engagement. Covers weak PRNGs, seed prediction, VM snapshot issues, and reviewing randomness sources in code. Also use when tokens, keys, or nonces look predictable.
- `rsa-attacks`: you face an RSA challenge or misconfigured RSA on an authorized test, CTF, or code review and need an operator workflow for the classic attacks.
- `tls-analysis`: assessing the TLS configuration of a service you own or are authorized to test, or when decrypting your own captured traffic for troubleshooting. Covers certificate chain validation with openssl, protocol and cipher enumeration, testssl.sh comprehensive scans, TLS keylog decryption in Wireshark, and JA3/JA4 fingerprinting for detection.

### :triangular_flag_on_post: ctf (7 skills)

*Capture-the-flag competition skills: pwn, reversing, web, forensics, crypto, and competition playbooks.*

- `ctf-competition-playbook`: preparing for, competing in, or reviewing a CTF competition as an individual or team. Covers pre-competition setup (tooling, notes, environment), team roles and communication, challenge triage and point strategy, time management across the event, solver scripting discipline, flag submission hygiene, and post-event review.
- `ctf-crypto-challenges`: competing in a CTF cryptography challenge, practicing in a lab, or analyzing cryptographic constructions you are authorized to examine.
- `ctf-forensics-challenges`: competing in a CTF forensics challenge, practicing in a lab, or analyzing evidence you are authorized to handle.
- `ctf-osint-challenges`: competing in a CTF OSINT challenge, practicing in a lab, or researching information you are authorized to collect.
- `ctf-pwn-basics`: competing in a CTF pwn (binary exploitation) challenge, practicing in a lab, or testing a binary on systems you are authorized to test.
- `ctf-reversing-basics`: competing in a CTF reverse engineering challenge, practicing in a lab, or analyzing a binary you are authorized to examine.
- `ctf-web-challenges`: competing in a CTF web challenge, practicing in a lab, or testing a web application you are authorized to test.

### :shield: defensive (7 skills)

*Blue team craft: EDR basics, hardening baselines, phishing defense, ransomware response.*

- `backup-security`: designing or auditing backup security. Covers the 3-2-1 rule, immutability against ransomware, encryption, and restore testing. Also use when ransomware readiness needs the recovery side verified, not just assumed.
- `edr-basics`: deploying, operating, or triaging with Endpoint Detection and Response tooling on systems you are authorized to defend.
- `endpoint-hardening-baseline`: building or auditing endpoint hardening baselines for Windows, macOS, or Linux fleets. Covers CIS benchmark adaptation, practical control selection, compliance checking, and exception handling.
- `incident-playbooks`: preparing for or running a security incident as a defender: writing and maintaining incident response playbooks, defining severity levels and SLAs, assigning roles, running communications, executing scenario playbooks for malware, business email compromise, data theft, and denial of service, and running tabletop exercises.
- `phishing-defense`: defending an organization against phishing: hardening email authentication with SPF, DKIM, and DMARC, writing gateway and mailbox detection rules, triaging user-reported phish, analyzing headers URLs and attachments safely, running takedowns of phishing sites, and measuring resilience with simulations.
- `ransomware-response`: preparing for or responding to a ransomware incident as a defender. Covers pre-incident readiness (backups, segmentation, EDR), identifying the ransomware family, containment of encryption and lateral spread, evidence preservation, eradication, recovery from backups, decryptor checks, ransom decision factors, and post-incident hardening.
- `security-awareness-program`: building or improving a security awareness program. Covers phishing simulations, role based training, metrics that matter, and building a reporting culture.

### :wrench: engineering (41 skills)

*Software engineering craft: git, CI/CD, Docker, Kubernetes, secure coding, debugging, performance.*

- `accessibility-security`: reviewing the intersection of accessibility and security in web applications. Covers how assistive tech interacts with security controls, CAPTCHA alternatives, and avoiding accessibility versus security tradeoffs.
- `ansible-basics`: automating server configuration with Ansible on an authorized engineering task. Covers inventory files, ad-hoc commands, playbook structure with plays tasks and handlers, idempotent modules, variables and vault-encrypted secrets, roles for reuse, and check mode plus diff for safe runs.
- `api-versioning`: designing or reviewing API versioning strategy. Covers URL vs header versioning, breaking change policy, deprecation process, and contract testing.
- `bash-advanced`: writing production-grade Bash 5.2 scripts: strict mode (set -euo pipefail), safe quoting and word splitting, arrays and associative arrays, parameter expansion, traps and cleanup handlers, getopts argument parsing.
- `chaos-engineering`: running chaos experiments to prove resilience. Covers hypothesis driven experiments, blast radius control, steady state metrics, and game days. Also use when "highly available" is claimed but never tested under failure.
- `cicd-security`: securing a CI/CD pipeline on an authorized engineering task.
- `code-reviewer`: reviewing code or pull requests for correctness, security, and maintainability, when auditing a codebase for vulnerabilities such as injection, broken authentication, insecure cryptography, and leaked secrets.
- `database-migrations`: designing or reviewing database migration practices. Covers migration authoring, zero downtime patterns, rollback strategy, and migration security review.
- `debugging-methodology`: diagnosing a bug or failure systematically: building a reproduction case, bisecting with git bisect, reading logs and stack traces, tracing syscalls with strace, debugging with gdb 15 or pdb, analyzing core dumps, forming and testing hypotheses one variable at a time, or writing a postmortem after an incident.
- `devsecops-pipeline`: designing or improving a DevSecOps delivery pipeline on an authorized engineering task. Covers pipeline stage design (build, test, scan, sign, deploy), placing SAST DAST and SCA gates, environment promotion with approvals, artifact promotion instead of rebuilds, SBOM generation, deployment strategies, and pipeline observability.
- `docker-deep`: building, hardening, or debugging Docker containers on an authorized engineering task. Covers multi-stage Dockerfiles, layer caching, minimal base images, non-root users, Compose for multi-service stacks, volumes and networks, image scanning, resource limits, and troubleshooting with logs, exec, and inspect.
- `feature-flags`: implementing or reviewing feature flags. Covers flag lifecycle, targeting rules, kill switches, and flag hygiene. Also use when a release needs gradual rollout or instant rollback without a redeploy.
- `git-workflows`: choosing a branching model for a team, when writing clean atomic commits, when rebasing a feature branch or resolving rebase conflicts, when running a disciplined pull request review.
- `github-actions`: writing or debugging GitHub Actions workflows on an authorized engineering task. Covers workflow triggers, jobs and steps, matrix builds, caching dependencies, artifacts, reusable workflows, pinning third-party actions by SHA, OIDC authentication to clouds, and local testing with act 0.2.71.
- `gitops-workflows`: implementing or reviewing GitOps for Kubernetes deployments. Covers repo structure, Argo CD or Flux setup, promotion between environments, secret handling, and drift detection.
- `go-basics`: writing, building, or reviewing Go programs on an authorized engineering task. Covers module setup with go mod, building and cross-compiling, gofmt and go vet hygiene, unit testing with the testing package, error handling idioms, goroutines and channels for concurrency, the race detector, and static binaries for deployment.
- `jq-mastery`: processing JSON on the command line with jq 1.7.1: selecting and filtering fields, transforming API responses, building JSON objects, aggregating with map/select/reduce, converting JSON to CSV or TSV, handling raw text input with slurp mode, parsing logs that contain JSON, or debugging why a filter returns null.
- `kubernetes-basics`: deploying or troubleshooting workloads on Kubernetes on an authorized engineering task. Covers kubectl 1.31 context and namespace handling, Pods, Deployments, Services, ConfigMaps and Secrets, resource requests and limits, liveness and readiness probes, rolling updates and rollbacks, logs and port-forward debugging, and basic RBAC.
- `load-testing`: load testing a system you own or are authorized to test. Covers test design, ramp profiles, bottleneck analysis, and interpreting results.
- `make-basics`: writing or fixing Makefiles with GNU Make 4.4: understanding targets, prerequisites, and recipes, using automatic variables ($@, $<, $^), writing pattern rules, declaring .PHONY targets.
- `nginx-hardening`: hardening an nginx 1.27 web server or reverse proxy: writing secure server blocks, disabling version banners, configuring modern TLS, adding security headers (HSTS, CSP, X-Frame-Options), rate limiting with limit_req.
- `performance-tuning`: making a system faster on purpose: establishing a baseline benchmark with hyperfine 1.18, profiling Python with cProfile, finding CPU, memory, disk, or network bottlenecks on Linux, tuning database queries and caches.
- `postgresql-tuning`: diagnosing or improving PostgreSQL performance on an authorized engineering task. Covers EXPLAIN ANALYZE reading, index design and bloat checks, pg_stat_statements for slow query hunting, autovacuum tuning, connection pooling, key postgresql.conf settings, and backup verification.
- `prometheus-monitoring`: setting up or debugging Prometheus monitoring on an authorized engineering task. Covers Prometheus 3.1 server config and targets, PromQL queries for RED and USE metrics, recording rules, Alertmanager 0.28 routing and silences, node_exporter 1.8 host metrics, Grafana 11.5 dashboards, and alert runbook practices.
- `python-advanced`: writing or reviewing advanced Python code on an authorized engineering task.
- `python-cli-tooling`: building command-line tools in Python using only the standard library, when designing an argparse interface with subcommands, when adding --help, --version, --sample, and --output json conventions to a script.
- `redis-basics`: operating Redis 7.4 in development or production: installing and configuring a server, choosing data types (strings, hashes, lists, sets, sorted sets, streams), writing and reading keys with redis-cli, setting TTLs.
- `regex-mastery`: writing or debugging regular expressions: choosing between BRE, ERE, and PCRE flavors, crafting grep, sed, and awk patterns, using character classes, anchors, quantifiers, groups, backreferences, and lookarounds.
- `rest-api-design`: designing a REST API from scratch or reviewing an existing one: naming resources and URIs, choosing HTTP methods and status codes correctly, versioning the API, designing pagination, filtering, and sorting.
- `rust-basics`: writing, building, or reviewing Rust programs on an authorized engineering task.
- `secrets-in-code`: finding and removing secrets from source code on an authorized codebase. Covers scanner setup, historical cleanup, rotation after exposure, and preventing recurrence with pre commit hooks.
- `secure-coding`: writing or fixing code that handles untrusted input, when choosing safe APIs for SQL, shell, and file access, when implementing password hashing, session tokens, and output encoding.
- `sqlite-deep`: working with SQLite databases on an authorized engineering task. Covers the sqlite3 CLI, schema design, index strategy, WAL mode and pragmas for performance and durability, parameterized queries, online backup API, integrity checks, and debugging locked databases.
- `ssh-hardening`: hardening OpenSSH 9.8 servers and clients: writing a secure sshd_config (key-only auth, no root login, modern ciphers and key exchange), auditing the effective config with sshd -T, managing host keys.
- `systemd-deep`: working deeply with systemd 256 on Linux: writing and debugging service, timer, socket, and target units, using systemctl and journalctl effectively, replacing cron jobs with systemd timers.
- `technical-writing`: writing documentation people actually read: planning a doc for its audience, structuring tutorials, how-to guides, reference, and explanations (Diataxis), writing clear plain-English procedures with verifiable steps.
- `terraform-basics`: writing or operating Terraform infrastructure as code on an authorized engineering task. Covers init plan apply workflow, HCL resource and variable syntax, outputs, state management and locking, remote backends, modules, workspaces, fmt and validate checks, and safe destroy procedures.
- `testing-strategies`: building a test strategy for a Python project: choosing what to test at each level of the test pyramid, writing pytest unit tests with fixtures and parametrize, mocking external services, measuring coverage, writing integration and end-to-end tests, fixing flaky tests, running tests in CI, or reviewing whether a codebase is under-tested.
- `tmux-workflows`: working with tmux 3.4 for persistent terminal sessions: creating and managing sessions, windows, and panes, customizing key bindings and the status bar in tmux.conf, using copy mode to search and copy scrollback.
- `typescript-basics`: writing, building, or reviewing TypeScript on an authorized engineering task. Covers strict tsconfig setup, type and interface modeling, unions and narrowing, generics, async and await patterns, DOM-free Node.js scripting, npm scripts, ESLint checks, and compiling to clean JavaScript.
- `vim-mastery`: editing text at speed with Vim 9.1: learning motions, operators, and text objects, combining them into composable editing commands, managing buffers, windows, and tabs, recording and replaying macros.

### :mag: forensics (7 skills)

*Digital forensics: disk, memory, browser, email, mobile, and log forensics.*

- `browser-forensics`: analyzing browser artifacts in an authorized investigation. Covers history, cookies, cache, downloads, and session artifacts for Chrome, Firefox, Edge, and Safari. Also use when web activity is the key timeline source.
- `disk-forensics`: examining a disk image or forensic copy of a drive during an investigation. Covers The Sleuth Kit and Autopsy workflows: partition layout, file carving, deleted file recovery, timeline generation, hash analysis, and keyword search.
- `email-forensics`: investigating a suspicious email during phishing triage or incident response. Covers full header analysis, Received chain tracing, SPF/DKIM/DMARC verification with dig, attachment extraction and hashing, URL and indicator extraction, and telling spoofing from compromise.
- `forensics-fundamentals`: you must investigate a disk image, memory dump, or compromised host under proper legal authority, on an authorized incident response engagement, lab, or CTF.
- `log-forensics`: reconstructing an incident from system and application logs you are authorized to analyze. Covers Linux journald and syslog, JSON log filtering with jq, Windows EVTX triage, authentication log hunting for brute force and lateral movement, detecting log tampering and gaps, and building a cross-source timeline.
- `memory-forensics`: analyzing a RAM dump or live memory image during incident response or a forensic investigation.
- `mobile-forensics`: doing forensics on mobile devices in an authorized investigation. Covers acquisition methods, iOS and Android artifacts, app data analysis, and handling encryption.

### :computer: hardware (8 skills)

*Hardware hacking: UART and JTAG, glitching, side channels, firmware extraction.*

- `emi-emc-basics`: you need working knowledge of electromagnetic interference and compatibility for security hardware work. Covers how emissions leak information, how to reduce a device's emission profile in the lab, and what EMC concepts matter when probing or shielding a target you own.
- `firmware-extraction`: you need to get firmware off a device or out of an update file on an authorized assessment. Covers update package unpacking, SPI flash reading with flashrom, binwalk carving, and filesystem extraction from images you own or have permission to test.
- `glitching-attacks`: assessing fault injection resistance of a device you own or have authorization to test. Covers voltage glitching concepts, clock glitching concepts, fault models, and reviewing firmware for missing fault checks.
- `hardware-reversing`: reverse engineering an embedded device you own or have authorization to test. Covers board teardown and documentation, firmware analysis workflow, protocol sniffing between chips, and building a full picture from hardware plus software.
- `pcb-analysis`: analyzing a printed circuit board on an authorized hardware assessment or in your own lab. Covers visual inspection, component identification, power rail mapping, signal tracing with a multimeter, and spotting hardware implants or tampering.
- `secure-boot-bypass`: assessing secure boot implementations on devices you own or have authorization to test. Covers boot chain mapping, signature verification review, rollback protection checks, and common bypass classes at the design level.
- `side-channels`: assessing a device for side channel leakage on an authorized hardware engagement or in your own lab. Covers power analysis basics, timing attack measurement, electromagnetic probing concepts, and simple countermeasure review.
- `uart-jtag`: working with embedded hardware on an authorized assessment or lab device you own. Covers finding UART consoles with a logic analyzer, getting a root shell over serial, identifying JTAG and SWD headers, and dumping memory with OpenOCD.

### :factory: ics-scada (8 skills)

*Industrial control systems: Modbus, DNP3, PLCs, SCADA network segmentation.*

- `dnp3-basics`: you need working knowledge of DNP3 for an OT assessment or lab. Covers DNP3 architecture (master and outstation), addressing, function codes, Secure Authentication basics, and where DNP3 appears in electric utility and water networks.
- `historian-security`: assessing a process historian on an authorized OT engagement. Covers historian architecture, the IT to OT data path, access control on trend and alarm data, and injection of false data.
- `ics-incident-response`: responding to a suspected incident in an OT or SCADA environment. Covers safety first triage, OT evidence collection without disrupting processes, working with operations, and recovery that respects physical constraints.
- `modbus-security`: assessing Modbus TCP or Modbus RTU on an authorized OT engagement or lab. Covers device discovery, function code enumeration, register mapping, detecting unsafe writes, and reviewing Modbus exposure.
- `opc-ua-security`: assessing OPC UA servers on an authorized OT engagement or lab. Covers endpoint discovery, security policy review, certificate handling, anonymous access checks, and node enumeration.
- `plc-basics`: you need working knowledge of programmable logic controllers for an OT assessment or lab. Covers PLC architecture, scan cycle, ladder logic reading, common vendors and protocols, and how PLCs fit into the Purdue model.
- `safety-systems`: you need to understand safety instrumented systems for OT security work. Covers what SIS does, why it is separate from process control, the security boundaries around it, and how to assess without ever endangering people.
- `scada-network-seg`: designing or assessing network segmentation for OT and SCADA environments on an authorized engagement. Covers the Purdue model, conduit and zone design per IEC 62443, firewall rule review between IT and OT, and validating that segmentation actually holds.

### :rotating_light: incident (6 skills)

*Incident response: the IR process, tabletop exercises, crisis communications.*

- `crisis-communications`: planning or executing communications during a security incident. Covers holding statements, stakeholder mapping, notification timelines, and working with legal and PR.
- `incident-breach-scoping`: you must determine the full blast radius of a confirmed intrusion on systems you are authorized to defend.
- `incident-containment-playbooks`: a security incident is confirmed on systems you are authorized to defend and you must stop the bleeding without destroying evidence.
- `incident-response`: a security incident is suspected or confirmed and you need a disciplined response on authorized systems. Covers the NIST 800-61 lifecycle: preparation, detection and analysis, containment, eradication, recovery, and lessons learned.
- `incident-timeline-analysis`: you need to reconstruct what happened and when during an authorized incident investigation.
- `tabletop-exercises`: planning and running incident response tabletop exercises. Covers scenario design, facilitation, injects, and turning findings into playbook fixes. Also use when the IR plan exists on paper but has never been tested.

### :penguin: linux (6 skills)

*Linux security: hardening, eBPF security, container hardening.*

- `ebpf-security`: assessing eBPF usage on Linux systems you own or are authorized to review. Covers eBPF program inventory, capability review, malicious eBPF detection, and safe development practices.
- `linux-container-hardening`: hardening Linux containers you run. Covers runtime options, seccomp and AppArmor profiles, capability drops, read only filesystems, and user namespaces. Also use when a container deployment needs a security baseline.
- `linux-hardening`: hardening a Linux server for production, when locking down SSH with key-only authentication, when writing a default-deny firewall with ufw or nftables, when disabling unneeded services.
- `linux-hardening-baseline`: building a defensive Linux hardening baseline for a server fleet, audit, or compliance review.
- `linux-log-intrusion-analysis`: investigating a Linux host for signs of intrusion using its logs, in a defensive incident response or threat hunting role.
- `linux-systemd-security`: securing systemd on a Linux server from a defensive posture across unit files, sandboxing, and logging.

### :bug: malware (10 skills)

*Malware analysis: static triage, dynamic sandboxing, packers, YARA rules.*

- `dynamic-sandbox`: a suspicious file needs to be executed to reveal its behavior, and only inside an isolated sandbox or disposable VM with no route to production networks.
- `malware-behavioral-analysis`: you need to understand what malware does at runtime beyond a sandbox summary, covering API call sequences, process injection chains, persistence installation order, and defense evasion in action.
- `malware-config-extraction`: you need the malware's embedded configuration, covering C2 addresses, encryption keys, campaign IDs, mutex names, and operational parameters, pulled from the binary without full reverse engineering.
- `malware-packer-triage`: a malware sample appears packed, obfuscated, or otherwise resistant to static analysis and you need to identify the packer and recover the original payload.
- `malware-sandbox-analysis`: you need to detonate a malware sample safely and extract structured behavioral evidence, covering process trees, file and registry activity, network traffic, and MITRE ATT&CK-mapped capabilities.
- `malware-static-triage`: a suspicious file lands in the queue and you need a fast, safe verdict without executing it, covering what it is, what it can do, and how urgent it is.
- `malware-yara-writing`: you need a production-quality YARA rule written from malware triage findings and validated against clean and malicious corpora.
- `packer-analysis`: static triage finds a packed or encrypted executable and you need the real payload underneath. Covers packer identification with Detect It Easy, the trivial UPX case, entropy and section analysis to map the packed regions, manual unpacking concepts using memory dumps, overlay data handling, and re-triaging the unpacked binary.
- `static-triage`: you receive a suspicious file and must decide what it is without executing it. Covers the full static triage pipeline in an isolated lab: hashing and file identification, strings and entropy analysis, import and section inspection, YARA scanning, packer detection, and headless Ghidra function listing.
- `yara-rules`: you need to write, test, or tune YARA rules for malware detection and hunting. Covers rule anatomy, string types and modifiers, condition logic, the pe/elf/math/hash/dotnet modules, testing against clean and malicious corpora, measuring false positives, atom quality for performance, and YARA-X differences.

### :floppy_disk: memory (5 skills)

*Agent memory skills: capture, recall, consolidation, hygiene, and state.*

- `agent-state`: an agent needs to save where it is in a long task so it can resume later, or when handing a task to another agent without losing context. Covers checkpointing progress as episodic entries, restoring state with targeted recall, writing handover notes that another agent can act on, and cleaning up stale checkpoints when the task finishes.
- `memory-capture`: an agent needs to record what it learned so future runs can reuse it, or when an operator wants durable notes from a task that took real effort.
- `memory-consolidation`: duplicate or overlapping memory entries pile up, or when repeated episodic observations should become one durable semantic fact. Covers dry-run review of merge candidates, merging near-duplicates safely, promoting episodic observations to semantic knowledge with raised confidence, and resolving which entry survives a merge.
- `memory-hygiene`: the memory store needs a health check: removing duplicates safely, resolving contradictory entries, decaying stale confidence, redacting secrets that slipped in, keeping an audit trail, or enforcing size budgets.
- `memory-recall`: an agent needs to look up what it already knows before doing new work, or when an operator wants the facts behind a past decision. Covers query patterns (keyword choice, kind filters, tag and agent filters), how the memory-store relevance ranking works, interpreting confidence and staleness, and recalling procedural knowledge mid-task.

### :iphone: mobile (8 skills)

*Mobile security: Android static and dynamic analysis, iOS basics, hardening.*

- `android-dynamic`: you need to test a running Android app on an authorized engagement, such as a client mobile app pentest or a CTF APK that only reveals behavior at runtime.
- `android-hardening`: hardening Android apps you build or review. Covers network security config, root and tamper detection, secure storage, and anti reverse engineering appropriate to the risk.
- `android-static`: you need to reverse engineer an Android APK you are authorized to test, such as a client mobile application on a penetration test or a CTF challenge APK.
- `ios-basics`: you need to assess an iOS application you are authorized to test, such as a client iPhone app on a penetration test or a CTF challenge IPA.
- `ios-dynamic-analysis`: dynamically analyzing iOS apps on an authorized engagement with a test device you own. Covers jailbreak lab setup, Frida instrumentation, traffic interception, and runtime data inspection.
- `mobile-android-dynamic`: you need to analyze a running Android app during an authorized engagement, such as a client mobile pentest or your own organization's release candidate.
- `mobile-frida-scripting`: you need to write custom Frida instrumentation for mobile apps during an authorized test, on Android or iOS.
- `mobile-ios-static`: you need to statically analyze an iOS application during an authorized engagement, such as a client mobile app pentest or a review of your own organization's App Store build.

### :globe_with_meridians: network (19 skills)

*Network attacks and analysis: Nmap, DNS, SMB, VLAN hopping, wireless, pivoting.*

- `arp-spoofing`: performing authorized man-in-the-middle testing on a local network segment.
- `bgp-security`: assessing BGP security on an authorized network engagement or lab. Covers route hijack concepts, RPKI validation review, BGP monitoring, and peer configuration audits.
- `bluetooth-le`: assessing Bluetooth Low Energy devices on authorized engagements, such as beacons, locks, wearables, or IoT sensors in scope.
- `dhcp-attacks`: assessing DHCP security on an authorized network or lab. Covers rogue DHCP servers, DHCP starvation, option injection, and DHCP snooping review.
- `dns-enumeration`: enumerating DNS on authorized engagements, internal or external. Covers forward and reverse lookups, record harvesting (A, MX, TXT, SRV, NS, SOA), zone transfer (AXFR) attempts, DNSSEC NSEC zone walking, subdomain brute forcing with curated wordlists, and wildcard detection with dig, host, dnsrecon, and nmap.
- `firewall-evasion`: nmap scans are blocked, filtered, or rate limited by firewalls and IDS on authorized engagements. Covers packet fragmentation, MTU games, decoy scans, source port spoofing, idle (zombie) scans, timing and delay tuning, bad checksums, data length padding, and tunneling scans through proxies.
- `ipv6-attacks`: testing IPv6 on authorized engagements, especially dual-stack networks where IPv6 is enabled but unmonitored.
- `ipv6-deep-dive`: assessing IPv6 on an authorized network engagement. Covers IPv6 discovery, extension header abuse, rogue router advertisements, and reviewing dual stack parity.
- `llmnr-poisoning`: capturing authentication hashes on authorized Windows LAN segments. Covers how LLMNR and NBT-NS name resolution can be poisoned, running Responder to answer victim queries, capturing NetNTLMv1 and NetNTLMv2 hashes, relaying safely within scope, cracking captured hashes with hashcat, and the Group Policy fixes that stop it.
- `netflow-analysis`: analyzing NetFlow, sFlow, or IPFIX data for security investigations or baselining. Covers flow collection review, beaconing detection, data exfiltration spotting, and building baselines.
- `network-pivoting`: an authorized engagement gives you a foothold host and you must reach deeper network segments through it. Pivoting with SSH local, remote, and dynamic port forwarding, proxychains routing for proxyless tools, chisel TCP and UDP tunnels, ligolo-ng tun interfaces for full layer 3 access, and socat relays.
- `nmap-methodology`: planning or running nmap scans during authorized engagements: host discovery options, TCP SYN, connect, UDP, NULL, FIN, Xmas, and ACK scan types, service and OS detection, timing templates T0 to T5.
- `sdwan-security`: assessing SD-WAN deployments on an authorized engagement. Covers overlay security, controller and orchestrator review, branch device hardening, and segmentation across the WAN.
- `smb-enumeration`: enumerating SMB services on authorized Windows or Samba targets. Covers finding SMB hosts, testing null sessions, reading share listings, checking SMB signing, enumerating users and groups with rpcclient and Impacket, riding RIDs to dump usernames, and searching shares for sensitive files with smbclient.
- `snmp`: enumerating SNMP services on authorized targets, typically UDP 161. Covers finding SNMP hosts, testing default and common community strings, walking MIB trees with snmpwalk and snmpbulkwalk for system info, interfaces, routes, users, and running processes, probing SNMP write access safely, and handling SNMPv3 auth.
- `stp-attacks`: assessing Spanning Tree Protocol on an authorized network or lab. Covers STP root takeover, BPDU guard review, and topology manipulation. Also use when reviewing switch hardening on enterprise or campus networks.
- `vlan-hopping`: testing VLAN segmentation on an authorized network assessment or lab. Covers switch spoofing, double tagging, DTP negotiation abuse, and validating that VLANs actually isolate.
- `wireless-wpa`: testing Wi-Fi security on authorized engagements with written permission covering the wireless network.
- `zero-trust-networking`: designing or assessing zero trust network architectures on an authorized engagement. Covers identity based access, microsegmentation review, policy engine assessment, and validating that implicit trust is actually gone.

### :eyes: osint (9 skills)

*Open source intelligence: domains, usernames, images, social media, threat intel.*

- `domain-osint`: investigating domains, DNS history, certificates, and hosting infrastructure from public sources on an authorized engagement. Covers RDAP and WHOIS lookups, DNS enumeration past and present, certificate transparency mining, passive DNS pivoting, ASN and BGP analysis, and infrastructure link analysis.
- `image-osint`: extracting intelligence from images on an authorized investigation. Covers metadata analysis, reverse image search, geolocation from visual clues, and authenticity checks.
- `osint-breach-data`: you need to work with breach data during an authorized investigation or defensive security review.
- `osint-image-geolocation`: you need to determine where a photograph was taken during an authorized investigation, using only the image and public sources.
- `osint-methodology`: planning and running an open source intelligence collection effort against public sources only. Covers the OSINT cycle, defining collection requirements, building a collection plan, source evaluation, operational security for researchers, sock puppet hygiene, documentation and evidence handling, and reporting.
- `osint-username-enumeration`: you need to find accounts and profiles tied to a username or handle across the internet during an authorized investigation.
- `social-media-osint`: researching publicly visible social media content on an authorized engagement. Covers profile analysis and attribution, timeline and network mapping, image and video metadata, geolocation from public posts, sock puppet OPSEC, and lawful limits.
- `threat-intel`: working with cyber threat intelligence on a defensive team: collecting IOCs, evaluating feeds, running a MISP instance, writing STIX/TAXII sharing packages, scoring and aging indicators, and turning intel into detections and blocks.
- `username-osint`: investigating a username across platforms on an authorized investigation. Covers username enumeration, profile correlation, timeline building, and operational security.

### :bust_in_silhouette: privacy (8 skills)

*Privacy engineering: GDPR, anonymization, differential privacy, impact assessments.*

- `anonymization-techniques`: you need to anonymize a dataset for sharing or analysis. Covers k-anonymity, l-diversity, generalization and suppression, re identification risk assessment, and why naive masking fails.
- `consent-management`: implementing or auditing consent for data processing: cookie banners, app permissions, and marketing opt ins. Covers consent records, withdrawal handling, dark pattern avoidance, and verifying that backend processing respects the choice.
- `data-minimization`: reducing personal data collection and storage in a system you build or review. Covers purpose mapping, field level audits, replacing identifiers with pseudonyms, and safe defaults.
- `differential-privacy`: you need to publish statistics or train models on sensitive data without exposing individuals. Covers epsilon budgets, Laplace and Gaussian noise, composition, and the practical limits of the guarantee.
- `dsr-automation`: automating data subject requests: access, erasure, portability, and rectification at scale. Covers request intake and identity verification, orchestration across datastores, processor propagation, and SLA tracking.
- `gdpr-engineering`: building or reviewing systems for GDPR compliance from the engineering side. Covers data mapping, lawful basis in code, retention automation, and data subject rights implementation.
- `privacy-impact-assessment`: running a privacy impact assessment (DPIA) for a new feature or system. Covers when a DPIA is required, the assessment steps, risk scoring, mitigation planning, and getting sign off.
- `privacy-threat-model`: building a privacy threat model for a system you design or review. Covers LINDDUN methodology, attacker profiling for privacy, linkability and identifiability analysis, and turning the model into engineering requirements.

### :arrow_up: privesc (6 skills)

*Privilege escalation on Linux and Windows, step by step.*

- `privesc-container-escape`: authorized testing lands you inside a container and you need to determine whether escape to the host is possible.
- `privesc-kernel-triage`: authorized privilege escalation has exhausted misconfiguration vectors and the kernel is the remaining path, or when you need to rule the kernel out quickly.
- `privesc-linux`: you hold a low-privilege Linux shell on an authorized engagement, lab, or CTF and need a reliable path to root.
- `privesc-linux-vectors`: you hold a low-privilege Linux shell on an authorized penetration test, lab, or CTF and need a systematic map of every local privilege escalation vector before you exploit anything.
- `privesc-windows`: you hold a low-privilege Windows shell on an authorized engagement, lab, or CTF and need a path to SYSTEM or Administrator.
- `privesc-windows-vectors`: you hold a low-privilege Windows shell or session on an authorized penetration test, lab, or CTF and need a systematic map of every local privilege escalation vector before you exploit anything.

### :telescope: recon (6 skills)

*Reconnaissance: passive and active target discovery before you touch anything.*

- `recon-active`: you have written authorization and need to directly probe the target: DNS zone transfer attempts, authoritative NS interrogation, subdomain brute forcing, reverse DNS sweeps, ICMP and TCP host discovery, and initial service discovery with dig, nmap, masscan, gobuster, and ffuf.
- `recon-asn-netblock`: authorized reconnaissance needs to move from domain names to the organization's network infrastructure.
- `recon-cert-transparency`: you want to mine certificate transparency logs for authorized reconnaissance on a target domain.
- `recon-passive`: starting authorized reconnaissance on a target domain or organization while staying off the target's own infrastructure. Passive reconnaissance with whois, dig against public resolvers, crt.sh certificate transparency logs, Shodan, Censys, theHarvester, Sublist3r, and Amass in passive mode.
- `recon-subdomain-enumeration`: starting authorized reconnaissance on a target domain and you need the complete subdomain enumeration playbook.
- `recon-subdomain-takeover`: authorized reconnaissance finds DNS records pointing at third-party services and you need to check for subdomain takeover.

### :police_car: soc (14 skills)

*Security operations: SIEM, Sigma rules, Suricata, threat hunting, DFIR timelines, purple team.*

- `dark-web-monitoring`: setting up monitoring for your organization's data on criminal forums and marketplaces. Covers collection strategy, credential leak monitoring, brand and executive exposure, and operational security for the monitoring itself.
- `detection-as-code`: building detections as versioned, tested code. Covers Sigma rule authoring, detection pipelines, unit testing detections, and CI for the SOC.
- `dfir-timeline`: building a forensic timeline for an authorized investigation. Covers evidence source collection, timestamp normalization, super timeline creation with Plaso, and analyzing the merged timeline for attacker activity.
- `edr-evasion-detection`: reviewing whether attacker techniques evade the deployed EDR on an authorized assessment. Covers common evasion classes, detection gap testing with atomic tests, and tuning recommendations.
- `honeypot-ops`: deploying and operating honeypots for detection and intelligence on your own network. Covers honeypot types, deployment safety, alert tuning, and turning captures into detections.
- `memory-malware-hunting`: hunting malware in memory images on an authorized investigation. Covers Volatility 3 workflows, process and injection detection, network artifact recovery, and finding fileless malware.
- `purple-team-exercises`: running purple team exercises that pair offense and defense on authorized systems. Covers exercise design, TTP selection, detection validation, and turning results into improved detections.
- `siem-detections`: building, tuning, or operating SIEM detections on an authorized blue team engagement or in a lab SOC. Covers log source inventory, normalization, writing Splunk SPL and Elastic detection rules, correlation and threshold logic, alert tuning to cut false positives, detection coverage mapping to MITRE ATT&CK, and measuring MTTD and MTTR.
- `sigma-rules`: writing, converting, or testing Sigma detection rules for a defensive detection program. Covers Sigma rule structure, logsource taxonomy, detection selection syntax, modifiers, conditions, testing with the Sigma CLI, and converting one rule to Splunk SPL, Elastic, and other backends.
- `suricata-ids`: deploying, tuning, or troubleshooting Suricata as a network intrusion detection sensor on a network you are authorized to monitor.
- `threat-actor-profiling`: building or reviewing threat actor profiles for intelligence or defense planning. Covers TTP mapping to MITRE ATT&CK, infrastructure patterns, victimology, and turning profiles into detection priorities.
- `threat-hunting`: proactively hunting for undetected intruders in an environment you are authorized to defend.
- `velociraptor-basics`: you need fast, targeted forensic collection across many endpoints during incident response or proactive hunting. Covers deploying the Velociraptor server, enrolling clients, running artifact collections from the GUI, writing basic VQL queries, launching hunts across the fleet, and using the offline collector for dead-box triage.
- `wazuh-basics`: deploying or operating Wazuh for host-based intrusion detection on infrastructure you are authorized to defend. Covers manager and agent architecture, agent enrollment, file integrity monitoring, security configuration assessment, custom rules and decoders, vulnerability detection, active response, and agent health monitoring.

### :spider_web: web (27 skills)

*Web application attacks: SQLi, XSS, SSRF, SSTI, JWT, OAuth, GraphQL, plus the full pentest methodology.*

- `api-rate-limit-bypass`: testing API rate limits on an authorized assessment. Covers limit discovery, header and IP spoofing bypasses, endpoint and method variations, and distinguishing real enforcement from cosmetic headers.
- `cache-deception`: testing for web cache deception on an authorized assessment. Covers path confusion, cache key analysis, authenticated content caching, and proving cross user cache poisoning safely.
- `cache-poisoning`: testing web cache poisoning and web cache deception on an authorized engagement.
- `cors-misconfig`: testing cross-origin resource sharing (CORS) configuration on an authorized engagement.
- `csrf`: testing a web application for Cross-Site Request Forgery on an authorized engagement. Covers mapping state-changing requests, detecting missing or weak anti-CSRF tokens, building HTML proof-of-concept exploits, testing SameSite cookie behavior, bypassing Referer and Origin checks, and attacking login CSRF and token-validation flaws.
- `deserialization-attacks`: testing for insecure deserialization on an authorized assessment. Covers identifying serialization formats, Java, Python pickle, PHP, .NET, and Node.js vectors, plus safe proof of concept practices.
- `dom-clobbering`: testing for DOM clobbering on an authorized web assessment. Covers named element clobbering, clobbering to XSS escalation, and code patterns that are vulnerable.
- `file-upload-attacks`: testing file upload functionality on an authorized engagement.
- `graphql-security`: testing a GraphQL API on an authorized engagement. Covers finding the endpoint, abusing introspection for full schema dumps, enumerating queries and mutations, authorization testing on every field, batching attacks for brute force, nested query denial of service, IDOR through global IDs, and subscription abuse.
- `header-injection`: testing for HTTP header injection and response splitting on an authorized web assessment. Covers CRLF injection in reflected headers, cache poisoning via headers, log injection, and request smuggling adjacencies.
- `http-request-smuggling`: testing for HTTP request smuggling (desync) between a front-end proxy and a back-end server on an authorized engagement.
- `jwt-attacks`: testing JSON Web Token handling on an authorized engagement. Covers decoding and structure analysis, algorithm confusion (none algorithm, RS256 to HS256 key confusion), weak HMAC secret brute forcing, kid and jku/x5u header injection, claim tampering (sub, role, exp), and jwk injection.
- `lfi-rfi`: testing a web application for Local and Remote File Inclusion on an authorized engagement.
- `nosql-injection`: testing NoSQL-backed applications (MongoDB, CouchDB, Redis) for injection on an authorized engagement.
- `oauth-attacks`: testing OAuth 2.0 and OpenID Connect logins on an authorized engagement.
- `oauth2-deep-dive`: assessing OAuth 2.0 and OpenID Connect implementations on an authorized engagement. Covers flow selection, redirect URI validation, code and token theft, PKCE review, and common misconfigurations.
- `open-redirect`: testing for unvalidated redirects and forwards on an authorized engagement.
- `postmessage-security`: assessing postMessage communication between windows and iframes on an authorized engagement. Covers origin validation flaws, message handler review, and cross origin data leaks.
- `prototype-pollution`: testing JavaScript applications for prototype pollution on an authorized assessment. Covers detection via __proto__ payloads, gadget hunting, pollution to XSS escalation, and server side pollution in Node.js.
- `race-conditions`: testing for race conditions (time-of-check to time-of-use flaws) on an authorized engagement.
- `ssrf`: testing a web application for Server-Side Request Forgery on an authorized engagement.
- `ssti`: testing a web application for Server-Side Template Injection on an authorized engagement.
- `web-sqli`: testing a web application for SQL injection on an authorized engagement. Covers detection and confirmation probes, UNION-based extraction, boolean and time-based blind techniques, error-based extraction, second-order injection, and sqlmap 1.9.2 automation plus full manual fallback when automation is blocked.
- `web-xss`: testing a web application for cross-site scripting on an authorized engagement. Covers reflected, stored, and DOM-based XSS, context-aware payload crafting (HTML, attribute, JavaScript, and URL contexts), filter and WAF bypass techniques, and Content Security Policy analysis with safe proof-of-concept callbacks.
- `webapp-pentest-methodology`: planning or running a full web application penetration test on an authorized engagement.
- `websocket-security`: an application uses WebSockets (ws:// or wss://) on an authorized engagement.
- `xxe`: testing a web application for XML External Entity injection on an authorized engagement.

</details>

<!-- CATALOG:END -->

## Sub-skills

227 drill-down modules under 69 high-value parent skills, at `skills/<domain>/<skill>/sub/<sub>/SKILL.md`. A sub-skill carries the standard frontmatter plus a `parent:` field and the full body skeleton, so a big skill like `web-sqli` splits into focused modules (`sqli-detection`, `sqli-union-extraction`, `sqli-blind`, `sqli-out-of-band`, `sqli-manual-fallback`, `sqlmap-automation`) that load only when needed.

| Parent skill | Sub-skills | Count |
| --- | --- | --- |
| `ad-enumeration` | `gpo-analysis`, `kerberos-enum`, `ldap-enumeration`, `trust-mapping` | 4 |
| `api-security-testing` | `api-discovery`, `authz-testing`, `mass-assignment`, `rest-fuzzing` | 4 |
| `auth-attacks` | `credential-stuffing`, `mfa-bypass-testing`, `password-reset-abuse`, `session-hijacking` | 4 |
| `aws-enumeration` | `ec2-metadata-abuse`, `iam-enumeration`, `s3-enumeration` | 3 |
| `bloodhound-methodology` | `bloodhound-collection`, `bloodhound-custom-queries`, `bloodhound-path-analysis` | 3 |
| `bug-bounty-workflow` | `duplicate-avoidance`, `recon-for-bounty`, `report-writing-bounty` | 3 |
| `c2-fundamentals` | `c2-channel-setup`, `c2-opsec`, `c2-payload-staging` | 3 |
| `cloud-security-basics` | `cloud-asset-inventory`, `cloud-iam-review`, `cloud-logging-checks` | 3 |
| `code-reviewer` | `reviewer-auth-flaws`, `reviewer-crypto-misuse`, `reviewer-sqli-patterns`, `reviewer-xss-patterns` | 4 |
| `crypto-fundamentals` | `encoding-vs-encryption`, `hash-identification`, `tls-misconfig-checks` | 3 |
| `disk-forensics` | `deleted-file-carving`, `filesystem-timeline`, `partition-recovery` | 3 |
| `forensics-fundamentals` | `artifact-parsing`, `evidence-handling`, `timeline-basics` | 3 |
| `incident-playbooks` | `data-breach-playbook-run`, `phishing-playbook-run`, `ransomware-playbook-run` | 3 |
| `incident-response` | `ir-containment`, `ir-eradication`, `ir-lessons-learned`, `ir-scoping` | 4 |
| `kerberoasting` | `asrep-roast-execution`, `kerberoast-execution`, `ticket-analysis` | 3 |
| `linux-hardening` | `auditd-baseline`, `kernel-hardening`, `service-minimization`, `ssh-baseline` | 4 |
| `memory-forensics` | `malware-in-memory`, `process-memory-triage`, `volatility-workflow` | 3 |
| `network-pivoting` | `port-forwarding-chains`, `socks-proxies`, `ssh-pivoting` | 3 |
| `nmap-methodology` | `nmap-evasion`, `nmap-host-discovery`, `nmap-port-scanning`, `nmap-scripting`, `nmap-service-detection` | 5 |
| `osint-methodology` | `breach-data-osint`, `infra-osint`, `people-osint` | 3 |
| `password-attacks` | `dictionary-attacks`, `mask-attacks`, `password-spraying`, `rule-based-mangling` | 4 |
| `privesc-linux` | `container-breakout-checks`, `cron-abuse`, `kernel-exploits`, `sudo-misconfig`, `suid-binaries` | 5 |
| `privesc-windows` | `alwaysinstallelevated`, `dll-hijacking`, `token-impersonation`, `unquoted-service-paths` | 4 |
| `recon-active` | `dns-bruteforce`, `os-fingerprinting`, `port-service-enum`, `web-tech-fingerprint` | 4 |
| `rsa-attacks` | `rsa-common-mistakes`, `rsa-padding-oracles`, `rsa-small-exponent` | 3 |
| `secure-coding` | `authz-checks`, `input-validation-patterns`, `output-encoding`, `secret-handling` | 4 |
| `threat-hunting` | `baseline-deviation`, `hunt-with-sigma`, `hypothesis-hunting` | 3 |
| `web-sqli` | `sqli-blind`, `sqli-detection`, `sqli-manual-fallback`, `sqli-out-of-band`, `sqli-union-extraction`, `sqlmap-automation` | 6 |
| `web-xss` | `xss-csp-bypass`, `xss-dom`, `xss-filter-bypass`, `xss-reflected`, `xss-stored` | 5 |
| `webapp-pentest-methodology` | `pentest-exploitation-phase`, `pentest-mapping`, `pentest-reporting`, `pentest-scoping` | 4 |

Visual map: [MINDMAP.md](MINDMAP.md).

## Agents

25 named operators in [agents/](agents/). Each binds skills plus brains, declares a memory mode, an escalation policy, and hard constraints. Quality gate: `scripts/score.py` must grade every agent 70 or higher (repo average is 95.2).

| Agent | Role |
| --- | --- |
| `ad-attack-agent` | Maps Active Directory attack paths and proves privilege escalation from any starting credential. |
| `ai-redteam-agent` | Breaks AI systems the way real adversaries do: through the prompt, the tools, and the data. |
| `api-security-agent` | Breaks APIs at the object, function, and logic level, then proves it with requests. |
| `binary-exploitation-agent` | Turns crashes in compiled binaries into proven, controlled exploits. |
| `bug-bounty-hunter-agent` | Hunts bounties systematically and writes reports that get accepted and paid. |
| `c2-operator-agent` | Operates red team C2 infrastructure with discipline, stealth, and full accountability. |
| `cloud-attack-agent` | Finds cloud misconfigurations and proves the privilege escalation path from any starting credential. |
| `code-review-agent` | Finds security flaws in source code and hands developers findings they can fix. |
| `crypto-analyst-agent` | Tests whether the cryptography is real protection or just decoration. |
| `devsecops-agent` | Secures the pipeline, the containers, and the platform they run on. |
| `forensics-agent` | Reconstructs what happened from digital evidence with a defensible chain of custody. |
| `hardware-hacker-agent` | Opens up hardware and firmware to find what the software layer hides. |
| `incident-commander-agent` | Owns the incident response from declaration to recovery, keeping every team coordinated. |
| `malware-triage-agent` | Classifies suspicious binaries fast and extracts the indicators that matter. |
| `mobile-assessment-agent` | Tests mobile apps the way an attacker with the APK and a rooted device would. |
| `osint-agent` | Collects and verifies open-source intelligence with every claim sourced. |
| `pentest-reporter-agent` | Turns raw findings into reports executives trust and developers can act on. |
| `phishing-defense-agent` | Defends the human layer: analyzes phish, trains users, and tightens email defenses. |
| `privacy-engineer-agent` | Engineers privacy into systems: less data collected, better protected, provably handled. |
| `purple-team-agent` | Runs the red and blue sides of one exercise so detections get proven, not assumed. |
| `recon-agent` | Turns unknown targets into a scoped, evidence-backed target inventory before active testing begins. |
| `secure-architect-agent` | Designs security into systems from the start and hardens what already exists. |
| `soc-analyst-agent` | Triages alerts fast, separates real incidents from noise, and drives the response by the playbook. |
| `threat-hunter-agent` | Hunts for hidden adversaries with hypotheses, telemetry, and proof, not just alerts. |
| `web-exploitation-agent` | Proves web vulnerabilities are real by exploiting them safely inside scope and documenting every step. |

## Brains

16 reusable reasoning patterns in [brains/](brains/). Agents compose them: an offensive agent loads `attacker-mindset`, a reporting agent loads `evidence-chain`, a design agent loads `threat-modeling`.

| Brain | What it provides |
| --- | --- |
| `assume-breach` | an agent must design or operate as if the adversary is already inside: planning network segmentation, writing hunting hypotheses, reviewing internal trust assumptions. |
| `attacker-mindset` | an agent needs to reason like an attacker: planning a penetration test, prioritizing recon targets, choosing which vulnerability to exploit first, reviewing a design for. |
| `blast-radius-thinking` | an agent must limit how far a failure can spread: designing deployments, choosing credential scope, planning rollouts, reviewing single points of failure, or preparing. |
| `cost-of-attack` | an agent must think in attacker economics: prioritizing which vulnerabilities to fix first, deciding where a limited security budget goes, evaluating whether a control. |
| `defender-mindset` | an agent needs to reason like a defender: designing security controls, reviewing an architecture for defensive gaps, prioritizing fixes under a limited budget, writing. |
| `detection-engineering-mindset` | an agent must build or improve detections: writing detection rules for a SIEM, deciding what to alert on, tuning noisy alerts, hunting for attacker techniques, or. |
| `evidence-chain` | an agent must prove something happened and show its work: building a forensic timeline, writing an incident report, justifying a finding to a skeptical reviewer, or. |
| `hypothesis-driven-testing` | an agent must test instead of guess: probing whether a vulnerability is real, validating a detection rule, debugging a flaky behavior, or running any experiment where. |
| `incident-command-mindset` | an agent must run or support a coordinated response: leading a security incident, organizing a multi-person outage response, structuring war-room communication, or. |
| `least-privilege-design` | an agent must design or review access control: assigning permissions to users, services, or automation; reviewing IAM policies and API keys; designing CI/CD pipelines. |
| `opa-decision-loop` | an agent must act under time pressure with incomplete information: live incident response, active defense decisions, prioritizing containment vs investigation, or any. |
| `root-cause-analysis` | an agent must find why something really failed: post-incident review after a breach or outage, a recurring bug that keeps coming back, a security control that failed. |
| `scientific-debugging` | an agent must find the cause of a malfunction: a bug that will not reproduce reliably, a system behaving differently than expected, a failing test with an unclear cause. |
| `secure-defaults` | an agent must choose defaults for a system, product, or configuration: shipping a new service, writing installation guides, reviewing a vendor's out-of-box settings, or. |
| `threat-modeling` | an agent must reason about what can go wrong before it does: designing a new system or feature, reviewing an architecture for security gaps, preparing for a security. |
| `zero-trust-reasoning` | an agent must design or evaluate access in a world without a trusted network: architecting service-to-service auth, reviewing VPN-based access, planning remote work. |

## Memory system

Agents need memory with rules, not a junk drawer. Three docs plus one CLI:

- [memory/MEMORY_SCHEMA.md](memory/MEMORY_SCHEMA.md): the three memory kinds. Episodic (timestamped events, TTL 30 days), semantic (durable facts), procedural (how things are done).
- [memory/LIFECYCLE.md](memory/LIFECYCLE.md): capture, consolidation, and expiry. Duplicate entries merge, stale entries age out.
- [memory/HYGIENE.md](memory/HYGIENE.md): hygiene rules that keep memory small, sourced, and trustworthy.
- [tools/memory-store/](tools/memory-store/): `memory-store`, a small SQLite CLI agents use to read and write memory. Every tool in `tools/` is stdlib-only and accepts `--help`.

![Memory flow](assets/memory-flow.svg)

## Decision docs

Five standing policy docs in [decisions/](decisions/) that agents reference instead of improvising:

| Doc | Purpose |
| --- | --- |
| `decisions/ESCALATION_POLICY.md` | When an agent must stop and ask a human |
| `decisions/RISK_MATRIX.md` | How to score likelihood times impact before acting |
| `decisions/GO_NO_GO_GATES.md` | Gates that decide whether an engagement proceeds |
| `decisions/ADR_TEMPLATE.md` | Template for architecture decision records |
| `decisions/COST_BENEFIT.md` | How to weigh attack cost against defender cost |

## Playbooks

8 end-to-end engagement runbooks in [playbooks/](playbooks/). Each playbook binds agents, skills, brains, and decision docs into ordered phases with entry and exit criteria, roles and handoffs, stop conditions, and artifacts produced.

| Playbook | Run it when... |
| --- | --- |
| `ad-assessment` | you need an Active Directory security assessment, from anonymous enumeration to domain compromise paths, mapped attack chains, and a hardening roadmap. Covers network. |
| `bug-bounty-sprint` | you need to run a focused, time-boxed bug bounty sprint against a program's scope, from OSINT and target mapping through vulnerability discovery to clean, high-signal. |
| `cloud-review` | you need a security review of AWS, Azure, or GCP environments, covering identity, storage, network exposure, and container platforms, ending with an architecture. |
| `external-pentest` | you need a full external penetration test against an in-scope company, from public recon through exploitation to an executive and technical report. Covers passive OSINT. |
| `malware-outbreak` | malware is suspected or confirmed in the environment and you need coordinated triage, forensic analysis, containment, and eradication. Covers sample triage, sandbox. |
| `secure-sdlc-rollout` | you need to roll out a secure software development lifecycle across an engineering organization, from threat modeling and secure design through code review gates, CI/CD. |
| `soc-triage-day` | you need to run a full day of security operations triage, from alert intake and prioritization through investigation, threat hunting, and escalation to incident command. |
| `webapp-assessment` | you need a deep security assessment of a web application and its APIs, from threat modeling through manual and automated testing to remediation-ready findings. Covers. |

## Workflows

4 multi-agent coordination patterns in [workflows/](workflows/):

| Workflow | Pattern |
| --- | --- |
| `workflows/pipeline.md` | Stages in sequence, each feeding the next |
| `workflows/coordinator-fanout.md` | One coordinator fans tasks out to workers, then merges |
| `workflows/reviewer-gate.md` | A reviewer must approve before the next stage runs |
| `workflows/evidence-gate.md` | Claims advance only with attached evidence |

## CLI tools

47 small, single-purpose Python CLI tools in [tools/](tools/). Every tool uses the Python standard library only, accepts `--help` with examples, exits 0 on success and 2 on usage errors, and is covered by `scripts/test_tools.py`.

<details>
<summary><strong>Expand the full tools table (47 tools)</strong></summary>

| Tool | What it does |
| port-scanner | TCP connect scan of a host for open ports (scan only what you may test) |
| banner-grabber | Connect to a TCP port and read the service banner |
| hash-identifier | Guess a hash type from its format (never cracks it) |
| subnet-calculator | Show network, broadcast, mask, and host range for a CIDR |
| password-generator | Generate random passwords with the secrets module |
| base64-codec | Encode text to base64 or decode base64 to text |
| hex-codec | Encode text to hex, decode hex, or hex-dump a file |
| log-grep-analyzer | Search a log with regex and summarize the matches |
| json-formatter | Pretty-print, minify, and validate JSON |
| url-encoder | URL-encode, URL-decode, or parse a query string |
| jwt-decoder | Decode a JWT header and payload (does NOT verify the signature) |
| dns-resolver | Resolve A/AAAA records or do a reverse lookup with the system resolver |
| http-header-checker | Fetch a URL and report response headers plus a security checklist |
| ssl-cert-checker | Show the TLS certificate of a host: subject, issuer, dates, SANs |
| file-hasher | Hash files with MD5, SHA-1, and SHA-256 using chunked reads |
| string-extractor | Pull printable strings out of a binary file (a simple strings clone) |
| cron-explainer | Explain a five-field cron schedule in plain English |
| regex-tester | Test a regex against text and show matches and named groups |
| caesar-cipher | Encode, decode, or brute-force the Caesar letter-shift cipher |
| rot13-codec | Apply ROT13 to text (encoding and decoding are the same) |
| morse-codec | Encode text to Morse code or decode Morse code to text |
| uuid-generator | Generate UUIDs (versions 1, 3, 4, 5) |
| timestamp-converter | Convert Unix timestamps to dates and dates to timestamps |
| entropy-checker | Measure Shannon entropy of text or a file in bits per byte |
| csv-column-extractor | Extract CSV columns by name or index, with dedupe and counts |
| cidr-merger | Collapse overlapping or adjacent CIDR ranges into the minimal set |
| port-list-expander | Expand a port spec like 80,443,8000-8005 into a full list |
| http-status-lookup | Look up the meaning of HTTP status codes |
| unicode-inspector | Show codepoint, name, category, and UTF-8 bytes per character |
| checksum-verifier | Verify a file against an expected checksum (auto-detects the algo) |
| diceware-generator | Build a passphrase from random words with the secrets module |
| totp-generator | Generate or verify TOTP codes (RFC 6238) from a base32 secret |
| email-header-analyzer | Parse email headers: addresses, Received hops, spoofing signs |
| iban-validator | Validate IBANs with a format check and the mod-97 checksum |
| luhn-checker | Validate numbers with the Luhn checksum or compute a check digit |
| semver-compare | Compare semantic versions and test simple version ranges |
| crontab-validator | Validate crontab files: time fields, @specials, and commands |
| markdown-toc | Generate a table of contents from Markdown headings |
| wordlist-mutator | Mutate wordlist entries: case, leet, years, symbols, numbers |
| url-parser | Break a URL into parts and flag suspicious traits |
| phone-parser-basic | Normalize and inspect a phone number (basic heuristic parser) |
| color-converter | Convert a color between HEX, RGB, and HSL |
| unit-converter | Convert length, mass, temperature, data size, and time units |
| random-sample-picker | Pick N random items from a list, with or without replacement |
| text-stats | Count lines, words, characters, and top words in text |
| diff-word | Show a word-level diff of two text files |

</details>

## Quality and benchmarks

Quality is measured, not claimed. Two machine gates run in CI:

**Gate 1: `scripts/validate.py` (14 checks).** Validates every skill, sub-skill, agent, brain, playbook, and workflow: required frontmatter fields, name matching the directory slug, trigger-dense descriptions, semver versions, valid lifecycle values, sane `last_verified` dates, dependency references that resolve, an acyclic dependency graph, required body headings (`## Quick Workflow`, `## Edge cases`, `## Key references`), sub-skill `parent` edges, agent/brain/playbook frontmatter contracts, manifest consistency, and content hygiene (no em dashes). Any failure exits non-zero and fails the build.

**Gate 2: `scripts/score.py` (0 to 100).** Grades every artifact on trigger density, command quality, edge cases, and references. Merge requires 70 or higher. Current repo scores (from `scores.json`, 512 scored artifacts: 285 skills plus 227 sub-skills):

| Metric | Value |
| --- | --- |
| Artifacts scored | 512 (285 skills + 227 sub-skills) |
| Average score | 96.1 / 100 |
| Lowest score | 85 / 100 |
| Artifacts at 90+ | 356 (100%) |
| Merge gate | 70+ |
| Agents average | 95.2 / 100 (25 agents, lowest 95) |

```diff
+ 100% of scored artifacts clear 90+, far above the 70 merge gate
+ Zero validation failures: every dependency resolves, the graph is acyclic
! Scores measure skill authoring quality (triggers, commands, edge cases), not live exploit success
```

![Skill lifecycle](assets/skill-lifecycle.svg)

## Learning paths

Ordered tracks through the repo, beginner to expert, each with milestones:

- [:green_book: Beginner](docs/learning-paths/BEGINNER.md): recon, Linux, and first web attacks. Milestone: run a scoped webapp assessment with `webapp-assessment`.
- [:orange_book: Practitioner](docs/learning-paths/PRACTITIONER.md): APIs, privilege escalation, Active Directory, malware triage, SOC workflows. Milestone: own an external pentest phase end to end.
- [:closed_book: Expert](docs/learning-paths/EXPERT.md): AD trust attacks, binary exploitation, AI red teaming, detection engineering, incident command. Milestone: lead a purple team exercise with proven detections.

![Learning path](assets/learning-path.svg)

## FAQ

<details>
<summary><strong>Expand the FAQ (18 questions)</strong></summary>

### What exactly is a skill?
A folder with a `SKILL.md` file: YAML frontmatter (name, trigger description, version, domain, lifecycle, dependencies) plus a body with a numbered Quick Workflow, per-phase procedures with exact commands, edge cases, escalation paths, a defender view, and key references. Optional `scripts/`, `references/`, and `assets/` folders ride along.

### How does a skill load into my agent?
Progressive disclosure. At session start the agent sees only each skill name and description, which costs almost no context. When your prompt matches a description, the agent loads the full body. That is why descriptions are written as dense "Use when ..." triggers and why the scorer grades trigger density.

### What is the difference between skills, sub-skills, agents, brains, playbooks, and workflows?
Skills are procedures. Sub-skills are drill-down modules inside a parent skill. Agents are named operators that bind skills plus brains into a repeatable role. Brains are reusable reasoning patterns (attacker-mindset, evidence-chain). Playbooks are ordered engagement runbooks with phases and stop conditions. Workflows are multi-agent coordination patterns (pipeline, reviewer-gate).

### Which platforms are supported?
19 platforms, one `SKILL.md` standard: Claude Code, OpenCode, Codex CLI, Gemini CLI, Cursor, GitHub Copilot, Amp, Goose, Cline, Roo Code, Kilo Code, Zed, Warp, Windsurf, Kiro, Qwen Code, Crush, Continue, and Aider (pointer snippet via `AGENTS.md`, since Aider has no skills support). See [Install for your platform](#install-for-your-platform).

### How do I install only what I need?
Use the sparse installer: `./install.sh --category web` for one domain, `./install.sh --version web-sqli@1.0.0` for one pinned skill. Dependencies resolve automatically from `arsenal-manifest.json`. Preview anything with `--dry-run`.

### What does the quality score mean?
`scripts/score.py` grades each artifact 0 to 100 on trigger density, command quality, edge cases, and references. Merge requires 70+. The repo average is 95.6 and every scored artifact is at 92 or above. It measures authoring quality, not live exploit success.

### How are dependencies handled?
Skills declare `requires` (hard prerequisites), `extends` (specialization), and `relates` (see-also). The installer resolves the full `requires` plus `extends` closure and installs the whole chain. CI fails on dangling references or cycles.

### Can I use this offline?
Yes. `scripts/bundle.py` packs skills into a single portable archive with a manifest for air-gapped environments.

### Is offensive content in scope here? Is this legal to use?
**Authorized security work only.** Red team engagements with written authorization, bug bounty programs within scope, CTF competitions, security research on your own systems, and training labs. See [SECURITY.md](SECURITY.md) for the explicit rejection list. Agents carry hard constraints (for example: never scan infrastructure you are not authorized to test) and the escalation policy decides when a human must step in.

### How do I contribute a skill?
Read [CONTRIBUTING.md](CONTRIBUTING.md) for the frontmatter standard and body skeleton, scaffold with `scripts/new_skill.py`, then run `scripts/validate.py` and `scripts/score.py` locally. Your skill must pass all 14 validation checks and score 70+ to merge.

### What is a playbook, and when do I run one?
A playbook is a fixed operational sequence for a repeatable engagement: it binds agents, skills, brains, and decision docs into ordered phases with entry/exit criteria, roles and handoffs, stop conditions, and artifacts produced. Run one when the work is a full engagement (webapp assessment, AD assessment, SOC triage day), not a single technique.

### How does agent memory work?
Memory follows a schema (episodic, semantic, procedural), a lifecycle (capture, consolidate, expire), and hygiene rules, in `memory/`. The `memory-store` CLI (SQLite, stdlib-only) is what agents use to read and write it. Agents declare `stateless` or `persistent` memory modes in their frontmatter.

### How do I roll back a bad install or a bad skill?
`install.sh` backs up the target before every install; `./install.sh --rollback` restores the most recent backup. Every release is a git tag plus a changelog entry, so a bad skill reverts cleanly with git too.

### What happens when a skill goes stale?
Every skill carries a `last_verified` date. CI fails on impossible or outdated dates, which surfaces stale skills as build failures instead of silent rot. Lifecycle states (`experimental`, `stable`, `deprecated`) tell you what to trust.

### My agent has no skills support. Can I still use this?
Yes. For Aider, `./install.sh --platform aider` prints a pointer snippet for `AGENTS.md`. Any agent that reads markdown can also load a skill file directly; the frontmatter contract is plain YAML and the body is plain markdown.

### How is this different from awesome lists and other skill repos?
Awesome lists link out; AgentArsenal ships the procedures. Other skill repos ship markdown; this repo adds per-skill versioning, a 14-check CI harness, 0 to 100 quality scoring with a merge gate, a validated dependency graph, freshness tracking, lifecycle states, offline bundles, rollback discipline, and a marketplace manifest. See the comparison table and strip at the top.

### Who maintains this and how is it versioned?
Releases are git tags with changelog entries ([CHANGELOG.md](CHANGELOG.md) follows Keep a Changelog and SemVer). Every skill is versioned independently in its frontmatter, so you can pin exactly what you installed.

### Where is the browsable docs site?
Run `python3 scripts/generate_docs.py` to build it, then open `docs/index.html`. It covers all domains and skills with the dependency graph and quality scores.

</details>

## Project stats

The repo currently holds **285 skills**, **227 sub-skills**, **25 agents**, **16 brains**, **8 playbooks**, **4 workflows**, **47 CLI tools**, and **19 supported platforms** (counted 2026-10-23; the catalog above is regenerated from the manifest).

| Artifact | Count | Location | Quality signal |
| --- | --- | --- | --- |
| Skills | 285 | `skills/<domain>/<name>/SKILL.md` | avg 96.0/100, min 90 |
| Sub-skills | 227 | `skills/<domain>/<skill>/sub/<sub>/SKILL.md` | avg 96.2/100 |
| Agents | 25 | `agents/<name>/AGENT.md` | avg 95.2/100, min 95 |
| Brains | 16 | `brains/<name>/BRAIN.md` | validated contracts |
| Playbooks | 8 | `playbooks/<name>/PLAYBOOK.md` | validated bindings |
| Workflows | 4 | `workflows/*.md` | validated |
| CLI tools | 47 | `tools/<tool>/<tool>.py` | stdlib-only, test harness |
| Platforms | 19 | `platforms/PLATFORM_SUPPORT.md` | paths from vendor docs |
| Decision docs | 5 | `decisions/` | referenced by agents |

## Roadmap

Planned, subject to change. Items land when they pass the same gates as everything else (14 validation checks, 70+ quality score).

- [ ] Freshness automation: scheduled re-verification passes that refresh `last_verified` dates with evidence.
- [ ] Community skill submissions with the same CI gates for external contributors.
- [ ] Docs site search and per-skill version history pages.
- [ ] More platform coverage as new agent CLIs adopt the `SKILL.md` standard.
- [ ] Translations of core docs (Spanish and French READMEs already in `translations/`).
- [ ] Video walkthroughs: install, first skill load, and one full playbook run.
- [ ] MCP server exposing the skill catalog and memory-store to MCP clients.

Suggestions are welcome as issues or pull requests.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the frontmatter standard, the body skeleton every skill must follow, and how to add a new skill with `scripts/new_skill.py`. The short version:

```bash
python3 scripts/new_skill.py --domain web --name my-skill   # scaffold
# ... write the skill ...
python3 scripts/validate.py   # must pass all 14 checks
python3 scripts/score.py      # must score 70+
```

Rules: original content only, authorized security work only, simple direct English, no em dashes in content (CI checks for U+2014).

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Built with original content. The infrastructure ideas it follows were learned from two MIT-licensed projects; see [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) for the full, factual attribution.

