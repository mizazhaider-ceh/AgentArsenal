---
name: secure-sdlc-rollout
kind: playbook
description: Use when you need to roll out a secure software development lifecycle across an engineering organization, from threat modeling and secure design through code review gates, CI/CD security, and purple team validation. Covers architecture standards, reviewer training, pipeline controls, and measuring adoption. Load this playbook when leadership approves an SSDLC program and you need ordered phases, owners, skills, brains, and decision gates for a rollout engineers will actually follow.
version: 1.0.0
---

# Secure SDLC Rollout Playbook

Build work only. This playbook improves the organization's own development process. All testing of controls happens against staging or dedicated test projects, never against production customer data.

## Objective

Embed security into every stage of software delivery: design, code, build, and deploy, with validation that the controls work and metrics that prove adoption. Success is measurable: threat models on new features, review gates passing, pipelines blocking bad builds, and fewer vulnerabilities reaching production.

## Phase table

| phase | owner agent | skills used | brains used | decision gates | exit criteria |
|-------|-------------|-------------|-------------|----------------|---------------|
| 1. Baseline and goals | secure-architect-agent | technical-writing, testing-strategies | threat-modeling, root-cause-analysis | GO_NO_GO_GATES | Current state mapped, goals and metrics agreed with leadership |
| 2. Secure design standards | secure-architect-agent | secure-coding, rest-api-design, terraform-basics, technical-writing | secure-defaults, least-privilege-design, zero-trust-reasoning | COST_BENEFIT | Design checklist and threat model template published |
| 3. Code review gates | code-review-agent | code-reviewer, secure-coding, git-workflows | secure-defaults, root-cause-analysis | GO_NO_GO_GATES | Review checklist live, reviewers trained, gate enforced on pilot repos |
| 4. Pipeline security | devsecops-agent | devsecops-pipeline, cicd-security, github-actions, container-escape, kubernetes-basics | secure-defaults, least-privilege-design | RISK_MATRIX | SAST, SCA, secrets scanning, and image checks blocking in CI |
| 5. Purple team validation | purple-team-agent | siem-detections, sigma-rules, api-security-testing | detection-engineering-mindset, attacker-mindset | ESCALATION_POLICY | Controls tested by attack simulation, gaps turned into fixes |
| 6. Measure and expand | secure-architect-agent | technical-writing, testing-strategies | incident-command-mindset, cost-of-attack | COST_BENEFIT | Metrics dashboard live, rollout expanded beyond pilot |

## Detailed phases

### Phase 1. Baseline and goals

Steps:
1. Map the current state: how code flows from commit to production, what reviews exist, what the pipeline already checks.
2. Pull the last quarter of vulnerability data: where bugs were found, how long they took to fix, which classes repeat.
3. Agree the goals with leadership: for example, threat models on all new high-risk features, zero hardcoded secrets in main, pipeline gates on every repo within two quarters.
4. Define the metrics: time to remediate by severity, vulnerabilities per release, gate pass rate, reviewer coverage.

Evidence to collect: current state map, vulnerability baseline, signed goals document, metric definitions.

### Phase 2. Secure design standards

Steps:
1. Write the secure design checklist: authentication, authorization, input handling, cryptography, logging, and error handling defaults.
2. Create the lightweight threat model template: data flow, trust boundaries, top threats, mitigations, residual risk.
3. Publish secure defaults engineers can copy: approved libraries, configuration snippets, and infrastructure templates.
4. Pilot the template on one upcoming feature and refine it based on engineer feedback.

Evidence to collect: design checklist, threat model template, secure defaults library, pilot feedback and revisions.

### Phase 3. Code review gates

Steps:
1. Build the security review checklist per language and framework used in the organization.
2. Train the reviewers: walk through real past vulnerabilities and how the checklist would have caught them.
3. Enforce the gate on pilot repositories: security review required before merge for high-risk changes.
4. Track review outcomes: findings per review, false positive rate, and time added to the merge cycle.

Evidence to collect: review checklists, training records, gate configuration, review metrics for the pilot.

### Phase 4. Pipeline security

Steps:
1. Add static analysis, software composition analysis, secrets scanning, and container image checks to the CI pipeline.
2. Set the gates to blocking for high severity, with a documented exception process that expires.
3. Harden the pipeline itself: least-privilege build identities, protected secrets, signed artifacts, and branch protection.
4. Test the gates with known-bad commits in a test project before enforcing them on real repositories.

Evidence to collect: pipeline configuration, gate test results, exception log, build identity inventory.

### Phase 5. Purple team validation

Steps:
1. Plan attack simulations against the new controls: can a malicious commit pass the gates, can a vulnerable dependency reach production.
2. Run the simulations with the detection team watching, and record what was caught, what was missed, and how fast.
3. Turn every miss into a fix: a tighter rule, a new check, or a process change, with an owner and a date.
4. Repeat quarterly. The controls are only as good as the last test.

Evidence to collect: simulation plans, detection results with timelines, gap register with owners, retest confirmations.

### Phase 6. Measure and expand

Steps:
1. Build the metrics dashboard: vulnerability trends, gate performance, review coverage, remediation times.
2. Review with leadership: what improved, what stalled, what the next investment should be.
3. Expand beyond the pilot: onboard the next set of teams with the refined templates and training.
4. Publish the wins internally: teams adopt faster when they see the program working.

Evidence to collect: metrics dashboard, leadership review notes, expansion plan, internal communications.

## Decision gates

- **GO_NO_GO_GATES** (decisions/GO_NO_GO_GATES.md): used in Phases 1 and 3. Checks: leadership sign-off on goals, pilot teams committed, reviewer capacity confirmed. The code review gate does not go live before reviewers are trained.
- **COST_BENEFIT** (decisions/COST_BENEFIT.md): used in Phases 2 and 6. Each control is weighed by engineering cost versus vulnerability reduction, so the highest-value controls ship first and expansion follows proven wins.
- **RISK_MATRIX** (decisions/RISK_MATRIX.md): used in Phase 4. Pipeline gates are scored for breakage risk before enforcement: a gate that blocks all builds is worse than the vulnerability it catches.
- **ESCALATION_POLICY** (decisions/ESCALATION_POLICY.md): used in Phase 5. Simulations that could affect shared staging or production-adjacent systems need explicit approval and a rollback plan.

## Deliverables

1. Current state map and vulnerability baseline.
2. Signed goals document with metrics.
3. Secure design checklist and threat model template.
4. Code review checklists, training records, and gate configuration.
5. Pipeline security configuration with gate test results.
6. Purple team simulation reports and gap register.
7. Metrics dashboard and expansion plan.
