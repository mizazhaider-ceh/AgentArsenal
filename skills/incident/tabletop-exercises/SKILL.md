---
name: tabletop-exercises
description: Use when planning and running incident response tabletop
  exercises. Covers scenario design, facilitation, injects, and
  turning findings into playbook fixes. Also use when the IR plan
  exists on paper but has never been tested.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, incident-playbooks, crisis-communications]
tools:
  - name: Python
    version: 3.12
---

Tabletops test the plan without the outage: the team talks through a
scenario, makes decisions, and finds the gaps while it is cheap.
This skill covers running them well: realistic scenarios, good
injects, honest facilitation, and follow through on the findings.
It is for teams that own incident response.

## Quick Workflow

1. Set the objective: which plan and which capability is under
   test.
2. Write the scenario: realistic, specific to your environment, and
   hard enough to matter.
3. Plan injects: timed complications that force decisions.
4. Invite the right people: IR, IT, legal, comms, and leadership
   as the scenario needs.
5. Facilitate: keep it moving, draw out the quiet, note the gaps
   without blame.
6. Capture findings live: decisions, gaps, and action items.
7. Fix the playbook within two weeks while memory is fresh.
8. Schedule the next one; one tabletop is a start, not a program.

## 1. Scenario and injects

```bash
# Scenario template (fill for your environment):
# - trigger: EDR alert at 02:00, ransomware on 30 workstations
# - facts given: which systems, what the SOC sees
# - unknowns: is it spreading, are backups intact, who is the actor
# Injects (reveal on schedule):
# T+20m: the backup admin's credentials were used at 01:30
# T+40m: a journalist calls asking about the outage
# T+60m: the CEO demands systems back in 2 hours for a client demo
echo "injects test decisions, not just knowledge"
```

```python
#!/usr/bin/env python3
"""Finding tracker: gap, owner, due date."""
findings = [
    ("no after hours contact for the backup vendor", "IR lead", "2026-11-06"),
    ("legal not in the escalation path", "CISO", "2026-11-06"),
    ("comms has no holding statement", "comms lead", "2026-11-13"),
]
for gap, owner, due in findings:
    print(f"[ ] {gap} -- {owner} by {due}")
print("review at the next exercise: which findings actually closed")
```

## 2. Facilitation notes

```bash
# Ground rules to state up front:
# - this is a safe space; no blame, no performance review
# - answer as your role, with the tools you really have at 2am
# - "we would call X" is not an answer; who is X and what is the number
# - the facilitator is not a participant; they keep time and score gaps
echo "the best finding is 'we assumed someone else does that'"
```

## Edge cases

- Leadership will not attend. Run it anyway with the working
  team, and send leadership the findings; they attend the next one.
- The scenario is too easy. Add an inject that breaks the plan's
  assumption (backups are gone, the lead is unreachable).
- Remote participants multitask. Require cameras on and a
  dedicated 90 minutes.

## Escalation

- Exercise reveals no usable plan: the outcome is a project to
  write one, with the exercise findings as requirements.
- Real incident during the exercise: pause and respond; the
  tabletop can wait.

## Detection and defender view

Tabletops are readiness detection: they find the missing phone
numbers, the unclear authorities, and the untested assumptions
before the attacker does. The findings feed the playbooks, the
contact lists, and the tooling gaps. The durable program runs
them quarterly, rotates scenarios across threat types, and tracks
finding closure like vulnerabilities.

## Key references

- NIST SP 800-61: incident handling (exercise context).
- CISA tabletop exercise packages.
- Related skills: incident-playbooks, crisis-communications.
