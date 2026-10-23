---
name: crisis-communications
description: Use when planning or executing communications during a
  security incident. Covers holding statements, stakeholder mapping,
  notification timelines, and working with legal and PR. Also use
  when the technical response is ready but nobody knows what to say.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, tabletop-exercises, ransomware-response]
tools:
  - name: Python
    version: 3.12
---

In a breach, what you say matters as much as what you fix: customers,
regulators, and staff all need timely honest communication. This skill
covers the plan and the execution: stakeholder maps, holding
statements, notification clocks, and the legal and PR partnership.
It is for teams that may face the press, the regulator, or the board.

## Quick Workflow

1. Map stakeholders before the crisis: customers, staff, board,
   regulators, and media, with owners per group.
2. Prepare holding statements: short, honest, and ready to send in
   the first hour.
3. Start the notification clocks at detection: GDPR 72 hours and
   other deadlines are real.
4. Establish the single source of truth: one approved status page
   or update channel.
5. Brief spokespeople: who talks, what they can say, what is
   privileged.
6. Update on a rhythm: regular updates beat silence, even with
   little new.
7. Coordinate with legal on every external statement.
8. Review after: what the communication got right and wrong.

## 1. Templates and clocks

```bash
# Holding statement template (fill the brackets, keep it short):
# "We detected [what] on [when]. We contained it by [action].
#  We are investigating with [who]. Updates at [channel] every [interval].
#  If you are affected: [action]."
echo "never say: no evidence of (early), sophisticated attack (excuse),"
echo "or promise what the investigation has not proven yet"
```

```python
#!/usr/bin/env python3
"""Notification clock tracker."""
from datetime import datetime, timedelta, timezone
detected = datetime(2026, 10, 23, 2, 15, tzinfo=timezone.utc)
clocks = [
    ("GDPR supervisory authority (72h)", detected + timedelta(hours=72)),
    ("customer notification (contract: 48h)", detected + timedelta(hours=48)),
    ("board briefing (24h)", detected + timedelta(hours=24)),
]
now = datetime.now(timezone.utc)
for name, due in clocks:
    left = due - now
    print(f"{name}: due {due:%Y-%m-%d %H:%M} UTC ({left} left)")
```

## 2. Execution discipline

```bash
# During the incident:
# - all external comms through the comms lead; no freelancing
# - log every statement with time and approver
# - internal updates before external where possible (staff hear it first)
# - social media monitored for rumors; correct with the status page link
echo "one voice, one channel, regular rhythm"
```

## Edge cases

- Ransomware with a leak threat. Do not negotiate publicly; follow
  counsel's guidance on every word.
- The facts change. Update and correct openly; changing the story
  without acknowledging it destroys trust.
- Executives want to minimize. Legal and comms align on honest and
  minimal: say what is known, what is being done, when the next
  update comes.

## Escalation

- Regulator inquiry arrives: legal takes the lead with the
  prepared timeline and evidence.
- Media has the story first: accelerate the holding statement;
  being second with the truth beats being first with a denial.

## Detection and defender view

Crisis comms is incident response for trust: the detection side is
monitoring for leaks, rumors, and stakeholder confusion during the
event. The durable asset is the plan: stakeholder maps, templates,
and clocks, rehearsed in tabletops so the first real use is not the
first run.

## Key references

- GDPR Articles 33, 34: breach notification.
- Related skills: incident-response, tabletop-exercises.
