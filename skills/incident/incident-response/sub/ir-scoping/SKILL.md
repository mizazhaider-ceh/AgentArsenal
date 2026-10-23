---
name: ir-scoping
description: Use when an incident is declared and you need to define what
  is affected, how bad it is, and what happens next. Covers severity
  classification, scope determination, stakeholder notification, and
  standing up the response structure. Use when the SOC escalates an alert,
  when a breach is suspected, when deciding the response level, or when
  the first hour decides the outcome.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-response
requires: [incident-response]
extends: []
relates: [forensics-fundamentals, threat-hunting]
tools:
  - name: Python
    version: 3.12
---

Incident scoping is the first hour done right: decide what happened, how
far it reaches, and who needs to know, before the response scatters. This
skill covers the scoping discipline: severity classification, rapid scope
determination, notifications, and setting up the response so the later
phases have something to work with. Scoping errors compound; every later
phase inherits them.

## Quick Workflow

1. Capture the initial report: what was seen, when, by whom, on what.
2. Classify severity with the organization's scale.
3. Determine the initial scope: affected hosts, users, data.
4. Notify stakeholders per the severity's notification list.
5. Stand up the response: lead, channel, tracking ticket.
6. Set the next decision point and the information needed for it.
7. Log everything from minute one.

## 1. Severity classification

```bash
# Severity scale (adapt to the organization's, but have one):
# SEV-1: active breach, data theft, ransomware spreading: all hands
# SEV-2: confirmed compromise, contained host: response team
# SEV-3: suspicious, unconfirmed: analyst investigation
# SEV-4: informational: log and watch

# Classification inputs, gathered in the first 30 minutes:
# - Is attacker activity ongoing right now?
# - Is sensitive data involved or reachable?
# - How many hosts/users are affected?
# - Is there business impact (outage, defacement)?

cat > /tmp/ir_scope.txt <<'EOF'
Incident: <id> opened <UTC time>
Reporter: <name>, <how detected>
Severity: SEV-<n> (rationale: <one line>)
Affected: <hosts/users/data, as known>
Attacker active: [ ] yes [ ] no [ ] unknown
Next decision: <time>, needs <information>
EOF
```

Classify fast and reclassify freely: an initial SEV-3 that becomes a
SEV-1 in an hour is normal. The failure is not reclassifying, not the
first guess.

## 2. Rapid scope determination

```bash
# First-pass scope questions, answered from logs and the reporter:
# - Which hosts show the indicator? (search the SIEM for the IOC)
# - Which users authenticated from those hosts recently?
# - What data do those hosts and users touch?
# - Is there lateral movement evidence (new hosts in the last 24h)?

# Time-box the first pass: 60 minutes, then decide on the known scope
# and keep expanding in parallel with containment
```

Scope is a living answer, not a one-time deliverable. The first pass
sets the containment boundary; the investigation keeps refining it. Say
"scope as currently known" in every update so nobody mistakes it for
final.

## 3. Notifications and structure

```bash
# Notification list per severity (define before the incident):
# SEV-1: CISO, legal, comms, IT leadership, within 1 hour
# SEV-2: security management, IT ops, within 4 hours
# SEV-3: security team channel
# Never notify customers or regulators without legal; that decision
# belongs to leadership, not the response team

# Response structure, stood up immediately:
# - Incident lead (one person, decides)
# - Comms lead (one voice outward)
# - Tracking ticket (every action logged with timestamps)
# - War channel (one place, no side channels for decisions)
```

One lead, one channel, one ticket. Incidents fail on coordination more
than on technique; the structure is the technique at this stage.

## Edge cases

- The report is vague ("something weird on a server"). Treat it as
  SEV-3 and investigate; vague reports are how real incidents start.
- Multiple incidents at once. Triage them into one tracking structure
  with separate scopes; do not let them share a lead.
- The scope keeps growing. That is expected in the first hours; expand
  the response (more analysts, higher severity) instead of defending
  the first scope.
- Business pressure to downplay. The severity reflects the facts;
  document the facts and let leadership own the risk decision.

## Escalation

- Severity reaches SEV-1: invoke the full incident plan, including
  legal and executive notification, per the playbook.
- You need outside help (forensics firm, law enforcement): that
  decision belongs to leadership with legal counsel; prepare the facts
  they need to decide.
- Scoping stalls on missing data: decide on the known scope and note
  the gaps explicitly rather than waiting for perfect information.

## Detection and defender view

This sub-skill IS the defender's view at hour zero: scoping well is
what separates a response from a panic. The preparation that pays off
is the severity scale, the notification lists, and the practiced
first-hour routine. Every minute spent deciding who leads is a minute
the attacker keeps. Tabletop exercises exist to make this hour boring.

## Key references

- NIST SP 800-61 (Computer Security Incident Handling Guide).
- SANS Incident Handler's Handbook.
- MITRE ATT&CK (understand what the scoped activity maps to).
