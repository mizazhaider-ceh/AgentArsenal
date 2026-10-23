---
name: incident-playbooks
description: Use when preparing for or running a security incident as a
  defender: writing and maintaining incident response playbooks, defining
  severity levels and SLAs, assigning roles, running communications,
  executing scenario playbooks for malware, business email compromise,
  data theft, and denial of service, and running tabletop exercises. Use
  when the SOC needs a repeatable response, when onboarding new analysts,
  or when an incident is declared and the team needs the next steps.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, forensics-fundamentals]
tools:
  - name: TheHive
    version: 5.x
  - name: Python
    version: 3.12
---

A playbook turns incident response from improvisation into procedure:
who does what, in which order, with which tools, and who gets told.
This skill covers building and running defensive playbooks for your
organization: the master playbook structure, severity and SLA model,
role assignments, communications, scenario playbooks, and tabletop
exercises that prove they work.

## Quick Workflow

1. Define severity levels (SEV-1 to SEV-4) with entry criteria and
   response SLAs, and get leadership sign-off.
2. Assign standing roles: incident commander, comms lead, technical
   lead, scribe, legal liaison.
3. Write the master playbook: declare, triage, contain, eradicate,
   recover, lessons learned.
4. Write scenario playbooks for your top risks (malware, BEC, data
   theft, ransomware pointer, DoS).
5. Put playbooks where analysts can reach them during an outage
   (printed copies and offline files, not only the wiki).
6. Run a tabletop exercise per quarter and fix what breaks.
7. On declaration, open the case, start the timeline, and work the
   playbook step by step.
8. Close with a blameless postmortem and update the playbook with
   what you learned.

## 1. Severity model

| Level | Criteria | Response SLA | Who is paged |
|---|---|---|---|
| SEV-1 | Active breach, ransomware, major data theft | 15 min, war room now | IC, CISO, legal, exec |
| SEV-2 | Confirmed malware, compromised account with access | 1 hour | IC, SOC lead, IT |
| SEV-3 | Suspicious activity, likely false positive | 4 hours | SOC analyst |
| SEV-4 | Informational, intel lead | Next business day | Intel analyst |

Entry criteria must be observable facts ("ransomware note on 10+
hosts"), not feelings. Anyone can declare a SEV-2 or higher; the
incident commander can downgrade with a written reason. False alarms
are cheap; late declarations are expensive.

## 2. Roles

- Incident commander (IC): owns the response, makes decisions,
  runs the war room. Does not do technical work.
- Technical lead: directs containment and forensics, owns the
  evidence chain.
- Comms lead: single voice to leadership, users, customers, and
  regulators. Nobody else talks externally.
- Scribe: keeps the timeline. Every action, decision, and timestamp
  goes in the log.
- Legal liaison: engages counsel early for privilege and breach
  notification obligations.

One person, one role. The IC is named in advance with two backups.
If the IC is on vacation, the backup is already the IC.

## 3. Master playbook

Phase 1, declare and triage (first hour):

```text
[ ] Open case in TheHive, set severity, assign IC and scribe
[ ] Start timeline: detection time, declaration time, every action after
[ ] Confirm scope: which hosts, users, data are involved (hypothesis first)
[ ] Preserve evidence: snapshot logs, memory where needed, before containment changes state
[ ] Notify per severity matrix (do not notify customers yet without legal)
```

Phase 2, contain (hours):

```text
[ ] Short-term containment: isolate hosts, disable accounts, block IOCs
[ ] Verify containment worked (host cannot reach C2, account cannot log in)
[ ] Decide: watch briefly to learn scope, or contain hard now (default: contain)
```

Phase 3, eradicate and recover (days):

```text
[ ] Remove attacker artifacts: malware, persistence, rogue accounts, mailbox rules
[ ] Patch or close the initial access vector
[ ] Restore from known-clean backups; verify integrity before reconnecting
[ ] Enhanced monitoring on affected systems for 30 days
```

Phase 4, lessons learned (within 2 weeks):

```text
[ ] Blameless postmortem: timeline review, what worked, what failed
[ ] Update playbooks and detections with findings
[ ] Track action items to closure with owners and dates
```

## 4. Scenario: malware on a workstation

```text
Trigger: EDR alert for malicious process on WS-1042, user jdoe.
1. Isolate the host in EDR (network quarantine, keep power on).
2. Collect: process tree, file hashes, persistence locations, recent
   USB and network history. Image memory if ransomware-like.
3. Check: did it spread (same hash on other hosts), did it steal
   credentials (LSASS access), did it exfiltrate (proxy logs).
4. Contain: block hash and C2 domain, reset user credentials, revoke
   sessions.
5. Eradicate: reimage from known-good media (preferred over cleaning).
6. Recover: return host after EDR shows clean for 24h, brief the user.
7. Hunt: same TTPs across the fleet for the last 30 days.
```

Prefer reimaging over cleaning. Cleaning leaves doubt; reimaging
removes it.

## 5. Scenario: business email compromise

```text
Trigger: finance reports a payment to a new vendor account after email
  instructions; or alert on external mail forwarding rule.
1. Preserve the mailbox: litigation hold, export message headers.
2. List attacker actions: forwarding rules, deleted mail, OAuth app
   grants, password or MFA changes, sent messages.
3. Contain: reset password, revoke all sessions and app tokens,
   remove rogue rules and grants, block sender infrastructure.
4. Scope: which mailboxes were accessed, which data was read (audit
   log: MailItemsAccessed), were payments issued.
5. Recover: verify with the real vendor over a known phone number
   before reissuing any payment.
6. Notify: finance leadership, legal; check wire recall options with
   the bank immediately (time matters, hours not days).
```

BEC playbooks live or die on the finance verification procedure.
Write it, test it, and make it usable at 2 AM.

## 6. Scenario: suspected data theft

```text
Trigger: DLP alert for large upload, or intel that data is for sale.
1. Identify the data: what left, from where, to where, when.
2. Preserve: proxy and firewall logs, endpoint file access logs,
   cloud audit logs. Extend retention now.
3. Contain: disable the account or key used, block the destination,
   rotate exposed credentials.
4. Assess: classify the data (personal data triggers notification
   law; check GDPR 72-hour clock with legal).
5. Eradicate the access path: close the misconfigured bucket, revoke
   the token, fix the overly broad permission.
6. Notify per legal advice; prepare customer comms with comms lead.
```

Start the legal clock early. Notification deadlines run from
awareness, and arguing about the start date later is painful.

## 7. Communications

Templates prepared in advance, filled during the incident:

- Internal status update (every 2 hours at SEV-1): what happened,
  what is affected, what we are doing, what we need, next update.
- Leadership brief: business impact, customer impact, ETA, decisions
  needed. No jargon.
- Customer notification: drafted with legal, factual, no speculation.
- Regulator notification: owned by legal, on the legal timeline.

Rules: one spokesperson, written updates beat verbal ones, never
speculate in writing, and assume every internal message may become
public.

## 8. Tabletop exercises

A tabletop tests the playbook without a real incident. Quarterly,
90 minutes, one scenario.

```text
Facilitator brief: "It is 09:00. The SOC sees ransomware notes on
  30 hosts in the finance VLAN. The backup server is unreachable.
  Go."
Inject at 09:20: "The CEO's laptop shows the note too."
Inject at 09:40: "A journalist calls asking about the outage."
Observe: who declares, who calls legal, when backups are checked,
  what gets written down, what is forgotten.
Debrief: three things that worked, three that did not, owners and
  dates for fixes.
```

Invite IT, legal, comms, and one executive. The value is in finding
the missing phone number and the unclear authority before the real
thing.

## Edge cases

- The incident starts during a holiday or at night. The on-call
  rotation and the offline playbook copy exist for exactly this.
- Key systems are down, including the wiki with the playbooks. Keep
  printed copies and an offline file with the IC at all times.
- The attacker is still in the environment during recovery. Do not
  restore into a dirty network; verify eradication with hunts first.
- Legal privilege questions stall technical work. Engage counsel in
  the first hour at SEV-1 so the question is answered early.
- The scope keeps growing. Re-declare severity upward rather than
  running a SEV-1 response on a SEV-3 ticket.
- Third parties are involved (MSP, cloud provider). Know their
  incident contacts before you need them, and define who leads.

## Escalation

- Containment fails (malware reappears after reimaging): the
  persistence or initial access vector is still open. Go back to
  scoping, assume a second foothold, and hunt wider.
- Evidence is being destroyed (logs cleared): prioritize
  preservation over cleverness; pull what exists now from central
  copies.
- The incident exceeds internal capability: engage the retainer IR
  firm. That is what the retainer is for; call early.
- Ransom demand arrives: follow the ransomware-response skill and
  involve legal and leadership before any decision.
- Media attention: all statements go through the comms lead and
  legal. Nobody else comments, posts, or speculates.

## Detection and defender view

Playbooks are defensive operations, and attackers exploit slow or
chaotic response:

- Attackers count on slow containment to finish encryption or
  exfiltration. Rehearsed playbooks shrink dwell time, which is the
  metric attackers fear.
- Attackers target backups and playbooks themselves (deleting wiki
  pages, corrupting backups). Keep offline copies and test restores.
- Attackers use your incident chaos for social engineering ("IT
  needs your password to fix the outage"). Brief users during
  incidents.
- After-action findings are attacker intelligence if leaked. Store
  postmortems with appropriate access controls.
- A playbook nobody has exercised is fiction. The tabletop is the
  detection control for your own process.

## Key references

- MITRE ATT&CK (scenario mapping): https://attack.mitre.org/
- CISA incident response playbooks and reporting:
  https://www.cisa.gov/
- NIST SP 800-61 Rev. 2, Computer Security Incident Handling Guide.
- SANS incident response process (PICERL: Preparation,
  Identification, Containment, Eradication, Recovery, Lessons).
- GDPR Article 33 (72-hour breach notification) for EU data.
