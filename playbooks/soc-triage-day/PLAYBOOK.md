---
name: soc-triage-day
kind: playbook
description: Use when you need to run a full day of security operations triage, from alert intake and prioritization through investigation, threat hunting, and escalation to incident command. Covers SIEM alert review, log and email forensics, detection tuning, and handoff to formal incident response. Load this playbook when staffing a SOC shift or running a triage exercise and you need ordered phases, owners, skills, brains, and decision gates for consistent daily operations.
version: 1.0.0
---

# SOC Triage Day Playbook

Defensive work only. This playbook handles alerts and investigations inside the organization's own environment. Follow the organization's data handling rules for any personal or sensitive data encountered.

## Objective

Process the day's security alerts efficiently, investigate the ones that matter, hunt for what the alerts missed, and escalate real incidents with clean handoffs. Success is zero unreviewed high-severity alerts at end of shift, documented dispositions for everything touched, and detections improved by what the day taught.

## Phase table

| phase | owner agent | skills used | brains used | decision gates | exit criteria |
|-------|-------------|-------------|-------------|----------------|---------------|
| 1. Shift start and queue review | soc-analyst-agent | siem-detections, incident-playbooks | defender-mindset, opa-decision-loop | GO_NO_GO_GATES | Queue prioritized, shift notes from previous shift read |
| 2. Alert triage and investigation | soc-analyst-agent | log-forensics, email-forensics, phishing-defense, edr-basics, threat-intel | defender-mindset, evidence-chain, scientific-debugging | ESCALATION_POLICY | Every high and critical alert dispositioned with evidence |
| 3. Threat hunting sweep | threat-hunter-agent | threat-hunting, sigma-rules, suricata-ids, memory-forensics, wazuh-basics | hypothesis-driven-testing, assume-breach | RISK_MATRIX | Hunt hypotheses tested, new leads or confirmed clean |
| 4. Detection tuning | threat-hunter-agent | sigma-rules, siem-detections, suricata-ids | detection-engineering-mindset, root-cause-analysis | COST_BENEFIT | Noisy rules tuned, gaps turned into new detections |
| 5. Escalation and handoff | incident-commander-agent | incident-response, incident-playbooks, ransomware-response | incident-command-mindset, evidence-chain | ESCALATION_POLICY | Incidents declared with severity, shift handoff written |

## Detailed phases

### Phase 1. Shift start and queue review

Steps:
1. Read the previous shift's handoff notes and any open investigations.
2. Pull the alert queue. Sort by severity, then by asset criticality.
3. Check sensor health: SIEM ingestion, EDR coverage, IDS status. Note any blind spots.
4. Set the shift plan: who owns which queue slice, hunt focus for the day, escalation contact on call.

Evidence to collect: handoff notes, prioritized queue snapshot, sensor health check, shift plan.

### Phase 2. Alert triage and investigation

Steps:
1. Work the queue top down. For each alert, gather the raw log, the asset context, and the user context.
2. Check threat intelligence for the indicators: first seen, related campaigns, confidence.
3. For email alerts, analyze headers, attachments, and URLs in the sandbox before touching the endpoint.
4. Disposition each alert: true positive, benign positive, false positive, or needs escalation. Write the reason and the evidence link for every one.

Commands (where relevant):
```bash
# example: pull raw events for one alert id from the SIEM export
jq -r 'select(.alert_id=="<id>")' /var/log/siem/alerts.jsonl
```

Evidence to collect: alert dispositions with reasons, raw log excerpts, threat intel lookups, sandbox reports for email cases.

### Phase 3. Threat hunting sweep

Steps:
1. Pick one or two hypotheses for the day, based on recent threat intel or gaps found in triage.
2. Write the hunt query, run it across the log sources, and document the logic so it can become a detection.
3. Review the results. Confirm hits with endpoint or memory data before declaring a finding.
4. If the hunt finds nothing, record the coverage: what was checked, over what time window, with what query.

Evidence to collect: hunt hypothesis, queries used, result sets, confirmation data, coverage notes for clean hunts.

### Phase 4. Detection tuning

Steps:
1. List the noisiest rules from the shift: high volume, low true positive rate.
2. Tune with allowlists, thresholds, or correlation, testing the change against historical data first.
3. Turn hunt findings into new detections: Sigma rule, SIEM content, or IDS signature as appropriate.
4. Record the before and after: alert volume, true positive rate, and the reason for each change.

Evidence to collect: tuning change log, new detection rules, historical test results, volume metrics.

### Phase 5. Escalation and handoff

Steps:
1. For each confirmed incident, declare severity, scope, and the containment steps already taken.
2. Hand off to incident command with the evidence package: timeline, indicators, affected assets, actions taken.
3. Write the shift handoff: open items, watchlist, pending escalations, sensor issues.
4. Log lessons: what slowed triage, what detection gap mattered, what to fix before the next shift.

Evidence to collect: incident declarations, evidence packages, shift handoff notes, lessons log.

## Decision gates

- **GO_NO_GO_GATES** (decisions/GO_NO_GO_GATES.md): used in Phase 1. Checks: previous handoff read, sensors healthy, escalation contact reachable. Degraded sensors trigger the reduced-coverage plan.
- **ESCALATION_POLICY** (decisions/ESCALATION_POLICY.md): used in Phases 2 and 5. Confirmed compromise, ransomware indicators, or scope beyond the SOC's authority: declare incident and hand off to incident command immediately.
- **RISK_MATRIX** (decisions/RISK_MATRIX.md): used in Phase 3. Hunts that touch production endpoints or broad data collection are scored for performance and privacy risk before running.
- **COST_BENEFIT** (decisions/COST_BENEFIT.md): used in Phase 4. Tuning effort is prioritized by alert volume reduced versus true positive risk, so the noisiest safe rules get tuned first.

## Deliverables

1. Prioritized alert queue with dispositions and evidence links.
2. Investigation notes for true positives with timelines.
3. Hunt hypotheses, queries, and results.
4. Detection tuning log with new rules.
5. Incident declarations with evidence packages.
6. Shift handoff notes and lessons log.
