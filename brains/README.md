# Brains

Each brain lives in `brains/<brain-name>/BRAIN.md`. Brains are reusable
analytical frameworks: mental models, checklists, and decision heuristics that
agents load to think better. A brain has no tools of its own; it lends
judgment to the skills an agent executes.

Frontmatter standard (enforced by `scripts/validate.py`):

```yaml
---
name: brain-slug           # must match the directory name
kind: brain
description: Trigger-dense paragraph. States exactly when to load this brain ("Use when ..."). 80 to 1500 chars.
version: 1.0.0
provides:                  # list of strings, the frameworks/heuristics it gives
  - STRIDE threat-modeling checklist
  - Attack-path prioritization heuristic
used_by: []                # optional list of agent names that bind this brain
---
```

Body sections: `## Mental models`, `## Heuristics`, `## Anti-patterns`,
`## Worked example`. Quality gate: `scripts/score.py` must give the brain
70 or higher out of 100.

Brains are written by the brain content team. This directory currently holds
only this stub.
