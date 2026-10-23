---
name: siem-detections
description: Use when building, tuning, or operating SIEM detections on an
  authorized blue team engagement or in a lab SOC. Covers log source
  inventory, normalization, writing Splunk SPL and Elastic detection rules,
  correlation and threshold logic, alert tuning to cut false positives,
  detection coverage mapping to MITRE ATT&CK, and measuring MTTD and MTTR.
  Use when the team needs new detections for an attack technique, when
  alerts are noisy, or when a rule must be validated against real telemetry.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, forensics-fundamentals]
tools:
  - name: Splunk
    version: 9.x
  - name: Sysmon
    version: 15.x
  - name: Python
    version: 3.12
---

A SIEM (Security Information and Event Management) platform collects logs
from across the environment, normalizes them, and fires alerts when rule
logic matches attacker behavior. This skill covers the defensive detection
engineering workflow: choosing log sources, writing reliable detection
logic in Splunk SPL and Elastic query language, correlating events,
tuning out false positives, and mapping coverage to MITRE ATT&CK. It is
blue-team only work. Run it against your own infrastructure, a client
environment you are authorized to monitor, or a lab.

## Quick Workflow

1. Inventory the log sources you actually receive (Windows events, Sysmon,
   firewall, proxy, EDR, authentication logs) and note what is missing.
2. Normalize field names so one rule works across sources (for example
   always use `user`, `src_ip`, `dest_ip`, `process_name`).
3. Pick one MITRE technique and write a single precise detection for it,
   starting with a known-good IOC or behavior pattern.
4. Test the rule against 30 days of historical data before it goes live.
5. Set severity, response SLA, and a runbook link on every alert.
6. Route alerts to a queue, assign an owner, and track true positive rate.
7. Tune weekly: suppress known-good patterns, add allowlists with
   expiration dates, never delete a rule silently.
8. Map every rule to MITRE ATT&CK and review coverage gaps quarterly.

## 1. Log source inventory

A detection is only as good as its data. Before writing rules, list every
source, its volume, and its gaps.

```bash
# Splunk: list all indexes and their event counts over the last 24 hours
index=* | stats count by index | sort -count

# Check the newest and oldest event per index to spot ingestion gaps
| tstats max(_time) as newest min(_time) as oldest where index=* by index
| eval gap_hours=round((now()-newest)/3600,1) | sort - gap_hours

# Elastic: check data streams and document counts
GET /_cat/indices/*winlogbeat*,*sysmon*?v&s=index
```

Minimum viable log set for a Windows-heavy shop:

- Windows Security event log (4624 logon, 4625 failed logon, 4672 special
  privileges, 4688 process creation, 4720 account creation, 4732 group
  membership change)
- Sysmon with a tuned config (process create, network connect, file create,
  registry, DNS query, process tamper)
- Firewall and proxy logs for egress visibility
- Authentication logs from the identity provider (Entra ID sign-in logs,
  VPN, RDP gateway)
- EDR telemetry if you have it

If Sysmon Event ID 1 (process creation) is missing, you cannot reliably
detect living-off-the-land binaries. Fix the log source before writing
the rule.

## 2. Normalization

Rules break when field names differ per source. Normalize at ingest or in
the rule with aliases. A common convention:

| Canonical field | Splunk source field | Elastic ECS field |
|---|---|---|
| user | user / Account_Name | user.name |
| src_ip | src_ip / IpAddress | source.ip |
| dest_ip | dest_ip | destination.ip |
| process_name | process / Image | process.name |
| parent_process | ParentImage | process.parent.name |
| command_line | CommandLine | process.command_line |

```bash
# Splunk: normalize inline with eval before the detection logic
index=wineventlog EventCode=4688
| eval process_name=lower(mvindex(split(New_Process_Name,"\\"),-1))
| eval command_line=Process_Command_Line, user=lower(TargetUserName)
```

Keep a field mapping document next to the rule repo so every analyst
knows which canonical name to use.

## 3. Writing a Splunk SPL detection

Anatomy of a good rule: narrow filter, explicit exclusions, aggregation,
and a severity assignment. Example: detect suspicious use of rundll32
(MITRE T1218.011).

```bash
index=wineventlog EventCode=4688
| eval process_name=lower(mvindex(split(New_Process_Name,"\\"),-1))
| where process_name="rundll32.exe"
| eval cmd=lower(Process_Command_Line)
| where NOT match(cmd,"^\"?c:\\\\windows\\\\(sysnative|system32)\\\\rundll32\.exe\"?\\s+\\S+\\.cpl")
| where NOT match(cmd,"javascript:")=0
| stats count values(cmd) as command_lines values(ComputerName) as hosts by user
| where count < 50
| eval severity="medium", mitre="T1218.011", rule="rundll32_suspicious_use"
```

Example: impossible travel on VPN logons.

```bash
index=vpn action=login success=true
| iplocation src_ip
| table user, src_ip, Country, _time
| sort 0 user, _time
| streamstats current=f last(Country) as prev_country last(_time) as prev_time by user
| where Country!=prev_country AND (_time - prev_time) < 3600
| eval severity="high", mitre="T1078", rule="impossible_travel"
```

Example: mass 4625 failed logons (password spraying, T1110).

```bash
index=wineventlog EventCode=4625
| bin _time span=10m
| stats dc(TargetUserName) as unique_users count as attempts by _time, src_ip
| where unique_users > 10 AND attempts > 20
| eval severity="high", mitre="T1110.001", rule="password_spray"
```

## 4. Writing an Elastic detection

Elastic Security rules use KQL or EQL. The same rundll32 idea in EQL:

```eql
process where event.type == "start" and
  process.name == "rundll32.exe" and
  not process.command_line regex~ """(?i)^"?(C:\\Windows\\(System32|Sysnative)\\)?rundll32\.exe"?\s+\S+\.cpl"""
```

Threshold rule for brute force in KQL (run every 5 minutes, look back
15 minutes):

```kql
event.code: "4625" and winlog.event_data.IpAddress: *
```

Then configure the threshold: group by
`winlog.event_data.IpAddress`, alert when count is greater than 20 and
cardinality of `winlog.event_data.TargetUserName` is greater than 10.

Sequence rule for a classic intrusion chain (EQL):

```eql
sequence by host.id with maxspan=30m
  [process where event.type == "start" and process.name == "powershell.exe"
    and process.command_line like~ "* -enc *"]
  [file where event.type == "creation" and file.extension == "ps1"]
  [network where event.type == "connection" and destination.port == 443
    and not destination.ip like~ "10.*"]
```

## 5. Correlation and thresholds

Single events are noisy. Correlate:

- Join authentication logs with asset inventory so alerts on servers
  score higher than on workstations.
- Require two weak signals before paging: for example a new external IP
  in proxy logs AND a first-seen process hash on the same host within
  one hour.
- Use risk-based alerting: add points per finding, alert when the score
  crosses a threshold instead of firing on each rule.

```bash
# Splunk: risk-based example, sum risk scores per user over 24h
index=risk_events
| bin _time span=1d
| stats sum(risk_score) as total_risk values(rule) as rules by user, _time
| where total_risk > 100
| eval severity="high", rule="risk_threshold_breach"
```

## 6. Alert tuning

Every alert gets a disposition: true positive, benign true positive,
false positive. Track the false positive rate per rule weekly.

```bash
# Measure precision per rule over the last 7 days
index=alert_triage
| stats count(eval(disposition="true_positive")) as tp
        count(eval(disposition="false_positive")) as fp by rule
| eval precision=round(tp/(tp+fp),2) | sort precision
```

Tuning order of operations:

1. Fix the logic (wrong field, wrong event code) before suppressing.
2. Add narrow exclusions with a comment and a ticket number, for example
   exclude the backup service account by name, not by wildcard.
3. Put time-bound suppressions on noisy-but-legit admin activity, and let
   them expire.
4. If precision stays below 0.2 after two tuning rounds, disable the rule
   and rewrite it rather than muting it forever.

Never suppress by source IP alone. Attackers pivot to new IPs; suppress
by the combination of user, process, and behavior.

## 7. Detection coverage mapping

Map every rule to MITRE ATT&CK and plot the matrix. The goal is to see
which techniques have zero coverage.

```bash
# Export rule to technique mapping and count coverage per tactic
index=detection_inventory
| stats dc(rule) as rule_count by tactic, technique
| sort tactic, technique
```

Prioritize new rules by:

- Techniques your threat model says are likely (phishing, valid accounts,
  ransomware behaviors).
- Techniques with zero coverage in Initial Access, Execution, and Impact.
- Techniques where you already have the log source but no rule.

Review the map quarterly. Archive rules for techniques that no longer
apply and note why.

## 8. Validating a rule safely

Never ship an untested rule to the paging queue.

```bash
# Splunk: backtest over 30 days, compare alert volume to capacity
index=wineventlog EventCode=4688 earliest=-30d@d latest=@d
| eval process_name=lower(mvindex(split(New_Process_Name,"\\"),-1))
| where process_name="rundll32.exe"
| bin _time span=1d | stats count by _time
```

Steps:

1. Run the logic over 30 days of history and record daily alert volume.
2. Manually review a sample of hits and label them.
3. Deploy in shadow mode (log only, no ticket) for one week.
4. Enable ticketing only when precision is acceptable.

## Edge cases

- Clock skew between forwarders makes correlation windows wrong. Monitor
  forwarder time drift and alert when any host is more than 5 minutes off.
- Sysmon config differences across hosts cause blind spots. Version your
  Sysmon config in git and audit deployed configs monthly.
- Log volume spikes during incidents can drop events. Set an alert on
  ingestion drop per source, not just on total volume.
- Case sensitivity: Windows process names vary in case. Always lowercase
  before comparing.
- NAT hides the true source IP in firewall logs. Correlate with VPN or
  proxy logs that record the real client address.
- Detections that join on hostname break when machines are renamed or
  reimaged. Join on a stable host ID where the platform provides one.
- Time zones: store and compare in UTC only. A rule that mixes local and
  UTC timestamps will miss or double count.

## Escalation

- A rule fires hundreds of times an hour: check for a logic error first
  (missing exclusion, wrong event code), then look for a real incident,
  then throttle with a per-host suppression while you investigate.
- No telemetry for a technique you must cover: add the log source (deploy
  Sysmon, enable PowerShell Script Block Logging 4104, turn on DNS
  logging) instead of writing a weak proxy rule.
- Splunk search is too slow for the schedule: narrow the index and
  sourcetype, add an indexed field, or convert to a data model
  acceleration. As a last resort, lengthen the schedule and widen the
  lookback.
- Stakeholders ignore alerts: attach the MITRE technique, the affected
  asset value, and the last true positive date to every alert. Data
  beats nagging.
- You suspect the SIEM itself is tampered with: compare forwarder
  configs against git, check admin audit logs for rule changes, and
  verify log hashes if you ship to immutable storage.

## Detection and defender view

This is the defender's own craft, so the "attacker view" here is how
attackers evade these detections, and how to tune against evasion:

- Attackers rename LOLBins (copy rundll32.exe to svch0st.exe). Detect by
  image path plus original filename from Sysmon, or by parent-child
  process anomalies, not by name alone.
- Attackers clear logs (T1070.001, Event ID 1102). Alert on 1102 itself
  and on gaps in the event sequence per host.
- Attackers slow down password sprays to stay under thresholds. Add a
  second rule with a 24 hour window and a lower per-IP threshold, keyed
  on unique usernames.
- Attackers use valid accounts (T1078), which look like normal logons.
  Hunt for first-seen source IPs, unusual logon hours, and logon type
  changes per user.
- EQL and SPL logic that matches on full command lines can be evaded
  with argument obfuscation. Add a parallel rule on parent-child process
  pairs and on network behavior.
- Tune with attacker cost in mind: force them to be slower, quieter, or
  to use noisier techniques, then detect the new behavior.

## Key references

- MITRE ATT&CK T1218.011 (Rundll32), T1110.001 (Password Guessing),
  T1078 (Valid Accounts), T1070.001 (Clear Windows Event Logs),
  T1059.001 (PowerShell), T1021 (Remote Services).
- Splunk Security Content (ESCU): detection research and SPL examples,
  https://research.splunk.com/
- Elastic detection rules repository:
  https://github.com/elastic/detection-rules
- Sigma rule format (convertible to SPL and Elastic):
  https://github.com/SigmaHQ/sigma
- MITRE ATT&CK matrix: https://attack.mitre.org/
- SANS SEC555: SIEM with Tactical Analytics (course reference).
