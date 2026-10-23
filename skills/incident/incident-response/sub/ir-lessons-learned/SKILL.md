---
name: ir-lessons-learned
description: Use after an incident closes to extract improvements from
  what happened. Covers blameless post-incident reviews, timeline
  reconstruction, action item tracking, and turning findings into
  defensive improvements. Use when the incident is resolved, when the
  team needs to improve, when management asks what changed, or when
  building the institutional memory that prevents repeats.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-response
requires: [incident-response]
extends: []
relates: [threat-hunting, incident-playbooks]
tools:
  - name: Python
    version: 3.12
---

Lessons learned turns an incident's cost into future capability: the
review that finds what to fix, the actions that fix it, and the tracking
that proves it happened. This skill covers running blameless
post-incident reviews and converting them into real improvements. Skip
this phase and the organization pays for the same incident twice.

## Quick Workflow

1. Schedule the review within two weeks of closure, while memory is
   fresh.
2. Reconstruct the full timeline from the incident records.
3. Run a blameless review: what happened, what worked, what did not.
4. Write action items with owners and deadlines, not suggestions.
5. Track actions to completion; report status to leadership.
6. Update playbooks, detections, and runbooks from the findings.
7. Share the sanitized lessons with the wider team.

## 1. Timeline reconstruction

```bash
# Build the master timeline from the incident ticket, logs, and notes:
# - First indicator (when the attacker actually arrived, not when
#   the alert fired: the dwell time is the key metric)
# - Detection point and detection method
# - Each response action with its timestamp
# - Containment, eradication, recovery milestones

# Metrics to compute:
# - Dwell time: first activity to detection
# - Response time: detection to containment
# - Recovery time: containment to normal operations

python3 - <<'EOF'
print("Example metrics review:")
print("dwell: 34 days (target: < 7) -> detection gap confirmed")
print("detect->contain: 6 hours (target: < 4) -> containment tooling slow")
print("Each gap becomes an action item with an owner.")
EOF
```

The timeline is the review's factual base: opinions about the response
are cheap, timestamps are not. Reconstruct it before the meeting, not
during.

## 2. Blameless review

```bash
# Review structure (60-90 minutes):
# 1. Timeline walkthrough (20 min): what happened, in order
# 2. What worked (15 min): name the good explicitly so it repeats
# 3. What did not (25 min): systems and processes, never people
# 4. Action items (20 min): owners, deadlines, in the ticket system

# Ground rules, stated at the start:
# - No blame: the question is what allowed it, not who allowed it
# - Rank-and-file speak first; leadership listens
# - Every claim ties to the timeline
```

Blameless is not soft; it is accurate. People hide mistakes when blame
is on the table, and hidden mistakes do not get fixed. The review that
finds the uncomfortable process failure is the one that worked.

## 3. Action tracking

```bash
# Action item quality bar (each item needs all four):
# - Specific: "deploy EDR to the 40 uncovered servers" not "improve coverage"
# - Owned: one named person accountable
# - Dated: a deadline, not "ASAP"
# - Verifiable: how we confirm it is done

# Track in the normal ticket system, not a side spreadsheet;
# report completion to leadership monthly until all are closed
```

Action items die in side documents. Put them where work is tracked,
review them where leadership watches, and close them with evidence.
An incident review whose actions all stall was theater.

## Edge cases

- The incident is still politically sensitive. Run the review anyway;
  delay degrades memory faster than sensitivity fades, and the
  facilitator can handle the room.
- Key people have left. Reconstruct from the records; the timeline and
  ticket carry what memory lost.
- The review finds nothing new. That is a finding about detection
  maturity worth stating; or the review was too shallow, try again
  with the timeline as the guide.
- Multiple incidents need one review. Do it per incident; patterns
  across incidents get their own analysis afterward.

## Escalation

- Leadership wants the report: give them the timeline, the metrics,
  the actions with owners, and the residual risks; keep the technical
  depth in the appendix.
- Actions need budget: the review's cost framing (what the incident
  cost versus what the fix costs) is the business case; write it.
- The lessons apply industry-wide: sanitize and share through the
  sector's sharing channels.

## Detection and defender view

Lessons learned is the defender's compounding interest: each review
makes the next incident cheaper. The artifacts it produces (updated
playbooks, new detections, fixed gaps) are the measurable output of
the security program. Organizations that skip this phase do not have an
incident response capability; they have incident response incidents.

## Key references

- NIST SP 800-61 (lessons learned phase).
- SANS Incident Handler's Handbook.
- "Blameless postmortems" practice (SRE workbook concepts).
