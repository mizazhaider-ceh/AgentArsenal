# Who AgentArsenal is for

AgentArsenal serves anyone who works with AI coding agents and wants
repeatable, quality-checked expertise on tap. Skills load on demand:
the agent sees the trigger description and pulls the full procedure
only when the task matches. Start with your audience below, install
the starter set, and expand from there.

Install the starters with the sparse installer, for example:

```bash
./install.sh --version nmap-methodology@1.0.0
./install.sh --version webapp-pentest-methodology@1.0.0
```

Or copy whole domains:

```bash
./install.sh --category web
```

Every name below is a real artifact in this repo. Skill and sub-skill
names live under `skills/<domain>/<name>/`, agents under
`agents/<name>/`, brains under `brains/<name>/`, playbooks under
`playbooks/<name>/`.

## Cyber students

**What you get:** a structured path from first principles to a full
methodology, with every procedure written as numbered operator steps
and exact commands. Skills replace scattered blog posts with one
curated source that a quality scorer already graded.

**Start with:**

- Skills: `recon-passive`, `recon-active`, `nmap-methodology`,
  `linux-hardening`, `web-sqli`, `webapp-pentest-methodology`,
  `python-cli-tooling`, `git-workflows`
- Agent: `recon-agent` (a guided recon run you can follow step by step)
- Brain: `scientific-debugging` (how to form hypotheses and test them
  instead of guessing)

Study one skill per session. Read the Quick Workflow, run the
commands in your lab, then read the Edge cases section to learn what
goes wrong in the real world.

## Pentesters

**What you get:** full engagement methodology, from recon to reporting,
with dependency-aware install (a skill's `requires` chain installs
automatically) and escalation paths when the standard path fails.

**Start with:**

- Skills: `webapp-pentest-methodology`, `ad-enumeration`,
  `bloodhound-methodology`, `privesc-linux`, `privesc-windows`,
  `network-pivoting`, `c2-fundamentals`, `password-attacks`,
  `api-security-testing`
- Agents: `recon-agent`, `web-exploitation-agent`,
  `pentest-reporter-agent` (structures findings into a client-ready
  report)
- Brains: `attacker-mindset`, `threat-modeling`
- Playbooks: `external-pentest`, `webapp-assessment`, `ad-assessment`

Bind the playbook for the engagement type you are running; its phase
table names the owner agent, skills, brains, and decision gates for
each phase.

## SOC analysts

**What you get:** detection content and triage procedures that read
like runbooks: what to look for, how to confirm it, and when to
escalate.

**Start with:**

- Skills: `siem-detections`, `sigma-rules`, `suricata-ids`,
  `threat-hunting`, `wazuh-basics`, `incident-playbooks`
- Agents: `soc-analyst-agent`, `threat-hunter-agent`,
  `incident-commander-agent`
- Brains: `detection-engineering-mindset`, `incident-command-mindset`,
  `evidence-chain`
- Playbook: `soc-triage-day`

Use the decisions files as standing references:
`decisions/ESCALATION_POLICY.md` for SEV-1 to SEV-4 response tiers
and `decisions/RISK_MATRIX.md` for likelihood x impact scoring.

## Developers

**What you get:** secure-coding guidance that loads exactly when you
are writing risky code (auth, crypto, input handling, CI pipelines),
plus review procedures you can run on your own pull requests.

**Start with:**

- Skills: `secure-coding`, `code-reviewer`, `api-security-testing`,
  `cicd-security`, `devsecops-pipeline`, `jwt-attacks`,
  `oauth-attacks`
- Agents: `code-review-agent`, `secure-architect-agent`
- Brains: `least-privilege-design`, `secure-defaults`,
  `threat-modeling`

Tip: bind `secure-coding` relates edges (`code-reviewer`,
`web-sqli`, `web-xss`) form a natural review cluster. Install one
and the installer suggests the rest through the dependency graph.

## Security researchers

**What you get:** deep, single-topic procedures with worked edge
cases, real tool versions pinned in frontmatter, and honest defender
views, so you can reproduce and extend instead of starting from
zero.

**Start with:**

- Skills: `llm-red-teaming`, `prompt-injection`, `agent-hijacking`,
  `binary` domain skills (`angr-basics`, `ghidra-basics`,
  `rop-chains`), `yara-rules`, `static-triage`, `dynamic-sandbox`
- Agents: `ai-redteam-agent`, `malware-triage-agent`,
  `binary-exploitation-agent`, `forensics-agent`
- Brains: `attacker-mindset`, `hypothesis-driven-testing`,
  `root-cause-analysis`

Check each skill's `tools` frontmatter for the exact tool versions
the procedure was verified against, and `last_verified` for
freshness.

## Educators

**What you get:** a curriculum-ready library with consistent
structure (every skill has the same body skeleton: framing, Quick
Workflow, phases, Edge cases, Escalation, defender view, Key
references), which makes lesson planning and grading rubrics easy.

**Start with:**

- Skills: `webapp-pentest-methodology` (capstone-shaped),
  `incident-response` (tabletop exercise material),
  `forensics-fundamentals`, `crypto-fundamentals`, `nmap-methodology`
- Agents: `soc-analyst-agent`, `incident-commander-agent` (drive
  classroom simulations with the escalation policy)
- Brains: `threat-modeling`, `evidence-chain` (teach structured
  thinking, not just tools)
- Decisions: `decisions/GO_NO_GO_GATES.md` (authorization and safety
  checks make a good ethics lesson)

The per-artifact quality scores in `scores.json` give you a
ready-made difficulty signal: higher-scored, stable-lifecycle
skills are safer starting points for beginners.

## Bug bounty hunters

**What you get:** a repeatable recon-to-report loop with
methodology skills that chain through dependencies, so a new target
starts from a checklist instead of a blank page.

**Start with:**

- Skills: `bug-bounty-workflow`, `recon-passive`, `recon-active`,
  `api-security-testing`, `web-sqli`, `web-xss`, `ssrf`,
  `jwt-attacks`
- Agents: `bug-bounty-hunter-agent`, `recon-agent`, `osint-agent`
- Brain: `cost-of-attack` (prioritize targets where your time pays)
- Playbook: `bug-bounty-sprint`

`bug-bounty-workflow` requires `recon-passive` and
`webapp-pentest-methodology`, so installing it pulls the
prerequisites automatically.

## Blue teams

**What you get:** incident response and forensics procedures,
hardening baselines, and defensive detections, all with a
"Detection and defender view" section and real MITRE ATT&CK and
CWE references.

**Start with:**

- Skills: `incident-response`, `incident-playbooks`,
  `forensics-fundamentals`, `memory-forensics`, `disk-forensics`,
  `ransomware-response`, `phishing-defense`, `edr-basics`,
  `linux-hardening`
- Agents: `incident-commander-agent`, `forensics-agent`,
  `soc-analyst-agent`, `phishing-defense-agent`
- Brains: `defender-mindset`, `incident-command-mindset`,
  `blast-radius-thinking`
- Playbook: `malware-outbreak`

Pair with `decisions/ESCALATION_POLICY.md` so the whole team shares
one definition of SEV tiers and response times.

## Startup founders

**What you get:** the minimum viable security program: what to
harden first, what to monitor, and how to ship features without
shipping vulnerabilities, sized for teams without a security hire.

**Start with:**

- Skills: `secure-coding`, `cloud-security-basics`,
  `linux-hardening`, `cicd-security`, `api-security-testing`
- Agents: `secure-architect-agent`, `code-review-agent`,
  `devsecops-agent`
- Brain: `threat-modeling` (one page of threat modeling beats a
  year of incident response)
- Playbook: `secure-sdlc-rollout`
- Decisions: `decisions/COST_BENEFIT.md` (frame security spending in
  terms the business understands)

Run the `secure-sdlc-rollout` playbook once per quarter as a
checkup: its phase table turns "do security" into owned tasks with
decision gates.
