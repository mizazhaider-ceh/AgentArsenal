# Expert learning path

You can own an engagement phase end to end. This track is about depth,
leadership, and proof: advanced exploitation, AI red teaming, detection
engineering, purple teaming, and incident command. Every phase ends with work
that must survive hostile review.

Prerequisite: [PRACTITIONER.md](PRACTITIONER.md) graduate, or equivalent
professional experience. Authorized work only, always.

## Phase 1: Advanced Active Directory

1. `skills/ad/ad-trust-attacks` : trust relationships are where domain-wide
   compromise hides. Enumeration to exploitation across forest boundaries.
2. `skills/ad/dcsync` : pulling credential material through directory
   replication. Understand exactly what it touches and what it logs.
3. `skills/ad/golden-ticket` : forging Kerberos tickets after krbtgt
   recovery. The full attack, plus how defenders catch it.
4. `skills/ad/gpo-abuse` : Group Policy as an attack vector and as forensic
   evidence.
5. `agents/ad-attack-agent` with `brains/attacker-mindset` and
   `brains/blast-radius-thinking` : plan domain compromise the way an
   adversary would, then scope containment the way a defender must.
6. `decisions/ESCALATION_POLICY.md` and `decisions/GO_NO_GO_GATES.md` : at
   this level, knowing when to stop and ask is the skill.

**Milestone 1:** You can design an AD assessment plan that a client CISO can
sign, execute it, and explain both the attack path and the detection gaps it
exposed.

## Phase 2: Binary exploitation

7. `skills/binary/pwn-fundamentals` : the base. If this is shaky, nothing
   above it holds.
8. `skills/binary/shellcode-basics` : position-independent payloads before
   you need them under pressure.
9. `skills/binary/rop-chains` and `skills/binary/srop-attacks` : code reuse
   when NX takes the easy road away.
10. `skills/binary/heap-exploitation` : the allocator is the real target in
    modern binaries.
11. `skills/binary/format-strings` : the bug class that keeps coming back.
12. `skills/binary/ghidra-basics` and `skills/binary/angr-basics` : static
    and symbolic analysis for binaries you cannot just run.
13. `skills/binary/binary-patching` and `skills/binary/firmware-analysis` :
    modify and analyze at the byte level.
14. `skills/binary/kernel-exploit-basics` : ring 0 changes every assumption.
15. `agents/binary-exploitation-agent` with
    `brains/hypothesis-driven-testing` : turn crashes into controlled,
    proven exploits.
16. `skills/hardware/uart-jtag`, `skills/hardware/firmware-extraction`,
    `skills/hardware/glitching-attacks` : when the target is silicon, not
    just software.

**Milestone 2:** You can take an unknown binary in a lab, analyze it, develop
a working exploit, and document the vulnerability with a severity argument a
vendor will accept.

## Phase 3: AI red teaming and advanced web

17. `skills/ai-security/prompt-injection` : the entry point for AI attacks.
18. `skills/ai-security/llm-red-teaming` : systematic red teaming of language
    models, not one-off jailbreak screenshots.
19. `skills/ai-security/guardrail-bypass-testing` : test the defenses, not
    just the model.
20. `skills/ai-security/agent-hijacking` : when the AI has tools, the attack
    surface explodes. Learn it before your targets do.
21. `skills/ai-security/ai-supply-chain` and
    `skills/ai-security/model-extraction` : the rest of the AI attack
    surface.
22. `skills/blockchain/smart-contract-audit` : high-value code with
    irreversible consequences. Audit methodology, not hype.
23. `agents/ai-redteam-agent` : the dedicated operator for this domain.

**Milestone 3:** You can scope and execute an AI system security review:
threat model the system, test prompt, tool, and supply chain layers, and
report findings with reproduction steps.

## Phase 4: Detection engineering and purple team

24. `skills/soc/detection-as-code` : detections as versioned, tested code.
25. `skills/soc/sigma-rules` : portable detection logic.
26. `skills/soc/edr-evasion-detection` : know the evasions to catch the
    evasions.
27. `skills/soc/purple-team-exercises` : run both sides so detections get
    proven, not assumed.
28. `skills/defensive/edr-basics` and `skills/defensive/ransomware-response`
    : the defender's reality check.
29. `agents/purple-team-agent` with `brains/detection-engineering-mindset`
    and `brains/defender-mindset` : build the exercise, run it, measure it.
30. `brains/cost-of-attack` : prioritize like an economist. Which findings
    actually change attacker cost?

**Milestone 4:** You can run a purple team exercise that ends with merged
detection rules, measured coverage, and a report both teams trust.

## Phase 5: Incident command and strategy

31. `skills/incident/incident-response` and its sub-skills
    (`sub/ir-scoping`, `sub/ir-containment`, `sub/ir-eradication`,
    `sub/ir-lessons-learned`) : the full IR lifecycle.
32. `skills/incident/tabletop-exercises` : practice the incident before it
    happens.
33. `skills/incident/crisis-communications` : the part of IR that fails most
    often has nothing to do with technology.
34. `skills/defensive/incident-playbooks` (all three playbook-run sub-skills)
    : the runbooks you will actually open at 3 AM.
35. `agents/incident-commander-agent` with
    `brains/incident-command-mindset` and `brains/opa-decision-loop` : own
    the response from declaration to recovery under time pressure with
    incomplete information.
36. `playbooks/malware-outbreak` : the coordinated end-to-end run.
37. `brains/assume-breach`, `brains/zero-trust-reasoning`,
    `brains/least-privilege-design` : the strategic layer. Design as if the
    adversary is already inside.
38. `workflows/evidence-gate.md` and `workflows/reviewer-gate.md` : at
    expert level, your process is the product. Claims advance only with
    evidence, and a reviewer signs off.
39. `playbooks/secure-sdlc-rollout` and `playbooks/cloud-review` :
    engineering-scale security: rolling out SDLC and reviewing cloud estates.
40. `agents/secure-architect-agent` and `agents/pentest-reporter-agent` :
    design security in from the start, and write the reports that move
    budgets.

**Milestone 5 (graduate):** You can lead: scope an engagement, run the team,
command an incident, prove detections with a purple team, and brief
executives on risk in their language. You are the person others escalate to.

## Quick install for this track

```bash
./install.sh --category binary
./install.sh --category ai-security
./install.sh --category hardware
./install.sh --category blockchain
./install.sh --category incident
./install.sh --category defensive
./install.sh --all --dry-run   # review the full arsenal before going all in
```
