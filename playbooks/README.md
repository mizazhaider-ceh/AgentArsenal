# Playbooks

Each playbook lives in `playbooks/<playbook-name>/PLAYBOOK.md`. A playbook is
a fixed operational sequence for a repeatable engagement: it binds one or more
agents, skills, brains, and decisions files into an ordered runbook.

Frontmatter standard (enforced by `scripts/validate.py`):

```yaml
---
name: playbook-slug        # must match the directory name
kind: playbook
description: Trigger-dense paragraph. States exactly when to run this playbook ("Use when ..."). 80 to 1500 chars.
version: 1.0.0
bindings:                  # every binding must resolve, or validation fails
  - agent:triage-agent              # agents/<name>/AGENT.md must exist
  - skill:incident-response         # a real skill or sub-skill name
  - brain:threat-model-brain        # brains/<name>/BRAIN.md must exist
  - decisions:decisions/ESCALATION_POLICY.md   # repo-relative path, must exist
---
```

Body sections: `## Objective`, `## Phases` (numbered, ordered steps with
entry and exit criteria per phase), `## Roles and handoffs`,
`## Stop conditions`, `## Artifacts produced`.

Playbooks are written by the playbook content team. This directory currently
holds only this stub.
