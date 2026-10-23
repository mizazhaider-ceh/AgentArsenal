# Agents

Each agent lives in `agents/<agent-name>/AGENT.md`. Agents are operational
roles: they bind skills and brains into a repeatable way of working, declare
their memory mode, their constraints, and where they escalate.

Frontmatter standard (enforced by `scripts/validate.py`):

```yaml
---
name: agent-slug            # must match the directory name
kind: agent
description: Trigger-dense paragraph. States exactly when to load this agent ("Use when ..."). 80 to 1500 chars.
version: 1.0.0
role: One-line string naming the job this agent performs.
skills:                    # list of real skill names (top-level or sub-skill)
  - nmap-methodology
brains:                    # list of real brain names
  - threat-model-brain
memory_mode: stateless      # or persistent
escalation: decisions/ESCALATION_POLICY.md   # repo-relative path to a decisions file
constraints:               # list of strings, hard rules the agent never breaks
  - Never scan infrastructure you are not authorized to test.
---
```

Body sections: `## Mission`, `## Operating loop`, `## Inputs and outputs`,
`## Escalation triggers`, `## Quality bar`. Quality gate:
`scripts/score.py` must give the agent 70 or higher out of 100.

Agents are written by the agent content team. This directory currently holds
only this stub.
