# Beginner learning path

A guided track from zero to your first full assessment. Work through the
phases in order: each step names the exact skill, agent, brain, playbook, or
tool to load and one line on why it comes now. Suggested pace: one phase per
study session.

All artifact paths are real. Skills live under `skills/<domain>/<name>/`,
agents under `agents/<name>/`, brains under `brains/<name>/`, playbooks under
`playbooks/<name>/`, tools under `tools/<name>/`.

## Phase 1: Foundations (how to work like an operator)

1. `skills/engineering/git-workflows` : version control first, because every
   lab, finding, and report you produce lives in git from day one.
2. `skills/engineering/bash-advanced` : the shell is your primary interface;
   strict mode and safe quoting before you automate anything.
3. `skills/engineering/python-cli-tooling` : write small tools the way this
   repo does (the 47 tools in `tools/` are your examples).
4. `brains/scientific-debugging` : the reasoning pattern for everything
   below. Reproduce first, change one variable at a time, instrument before
   guessing.
5. `tools/file-hasher`, `tools/hash-identifier`, `tools/url-encoder` : tiny
   wins that teach you the tool workflow (`--help`, exit codes, stdlib only).

**Milestone 1:** You can set up a lab repo, script a repetitive task in bash
or Python, and debug a failure methodically instead of guessing.

## Phase 2: See the target (recon and Linux)

6. `skills/recon/recon-passive` : learn everything about a target without
   touching it. Passive first is both safer and more professional.
7. `skills/recon/recon-active` and its sub-skills (`recon-active/sub/*`) :
   careful active enumeration once you have authorization and scope.
8. `skills/network/nmap-methodology` : the core scanning skill. Drill into
   the sub-skills in order: `sub/nmap-host-discovery`,
   `sub/nmap-port-scanning`, `sub/nmap-service-detection`,
   `sub/nmap-scripting`, `sub/nmap-evasion`.
9. `skills/osint/osint-methodology` plus its sub-skills (`sub/breach-data-osint`,
   `sub/infra-osint`, `sub/people-osint`) : verify what you find against
   multiple sources.
10. `skills/linux/linux-hardening` and its sub-skills (`sub/kernel-hardening`,
    `sub/service-minimization`, `sub/ssh-baseline`, `sub/auditd-baseline`) :
    understand what a hardened Linux box looks like, so you recognize what is
    missing later.
11. `skills/engineering/ssh-hardening` : the first service you will meet on
    every box; learn its secure shape.
12. `agents/recon-agent` : run a guided recon end to end and compare your
    manual notes against the agent's target inventory.

**Milestone 2:** Given a lab target and written authorization, you can produce
a scoped, evidence-backed target inventory: hosts, ports, services, and OSINT
notes, all sourced.

## Phase 3: First blood (web basics)

13. `skills/auth/password-attacks` and its sub-skills : credential attacks are
    the most common real-world foothold; learn them before exotic bugs.
14. `skills/web/web-sqli` : start with `sub/sqli-detection`, then
    `sub/sqli-union-extraction`, `sub/sqli-blind`, and
    `sub/sqlmap-automation`. SQL injection is still everywhere.
15. `skills/web/web-xss` : `sub/xss-reflected`, `sub/xss-stored`,
    `sub/xss-dom`, `sub/xss-filter-bypass`. The second classic, and the DOM
    variant teaches you to think in browsers.
16. `skills/web/webapp-pentest-methodology` : the full methodology that ties
    recon, mapping, exploitation, and reporting together. Read its sub-skills
    `sub/pentest-scoping`, `sub/pentest-mapping`,
    `sub/pentest-exploitation-phase`, `sub/pentest-reporting` in order.
17. `brains/attacker-mindset` : now learn to think like the adversary: attack
    graphs, cheapest path, chaining small weaknesses.
18. `brains/evidence-chain` : every claim traces to a source. Start writing
    findings this way now and reporting later is easy.

**Milestone 3:** You can run a scoped webapp assessment on a training target
and write it up with reproducible steps and evidence per finding.

## Phase 4: Think blue (defense and response)

19. `skills/defensive/phishing-defense` : the human layer is where most
    intrusions start; learn how defenders see it.
20. `skills/defensive/incident-playbooks` and its sub-skills, including
    `sub/ransomware-playbook-run` : what happens after a finding becomes an
    incident.
21. `skills/engineering/secure-coding` and its sub-skills : learn to fix the
    bug classes you just learned to exploit.
22. `playbooks/webapp-assessment` : run the full engagement runbook once,
    phases in order, with entry and exit criteria.
23. `playbooks/soc-triage-day` : spend a day in the defender's seat triaging
    alerts with `agents/soc-analyst-agent`.

**Milestone 4 (graduate):** You can take a small authorized assessment from
scoping to report, explain each finding's evidence chain, and describe the fix
from the defender's side. Next stop:
[PRACTITIONER.md](PRACTITIONER.md).

## Quick install for this track

```bash
./install.sh --category recon --dry-run
./install.sh --category recon
./install.sh --category network
./install.sh --category web
./install.sh --version web-sqli@1.0.0
```
