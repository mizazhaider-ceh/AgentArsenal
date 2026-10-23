---
name: edr-basics
description: Use when deploying, operating, or triaging with Endpoint
  Detection and Response tooling on systems you are authorized to defend.
  Covers EDR architecture and telemetry, prevention versus detection
  modes, process tree and Sysmon-equivalent analysis, alert triage
  workflow, host isolation and remediation actions, detection tuning, and
  measuring EDR coverage. Use when the SOC needs endpoint visibility,
  when triaging an EDR alert, or when validating that the EDR fleet is
  healthy and untampered.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, forensics-fundamentals]
tools:
  - name: Sysmon
    version: 15.x
  - name: Velociraptor
    version: 0.7
  - name: Python
    version: 3.12
---

EDR watches what happens on endpoints: processes, file writes,
registry changes, and network connections, and it can stop or isolate
threats automatically. This skill covers operating EDR defensively:
understanding the telemetry, triaging alerts well, using response
actions safely, tuning detections, and keeping the fleet healthy. It
applies to any EDR product and to Sysmon-based telemetry pipelines,
on systems you own or are authorized to defend.

## Quick Workflow

1. Confirm coverage: every in-scope host has a reporting, untampered
   sensor on a supported version.
2. Set policy modes deliberately: prevention on for known-bad,
   detection on for behavioral analytics during rollout.
3. Triage new alerts with the process tree first, then the file,
   then the network, then the user.
4. Isolate the host for confirmed evil, preserving memory and logs
   before remediation.
5. Remediate: kill, quarantine, remove persistence, reset
   credentials, then reimage for serious cases.
6. Hunt the IOCs and TTPs across the fleet for the last 90 days.
7. Tune the detection that fired: add the exclusion with a ticket or
   promote it to a block.
8. Report fleet health weekly: coverage, sensor tampering, policy
   drift, mean time to triage.

## 1. Telemetry model

Know what your sensor records, because you can only detect what is
collected. The standard event set, mapped to Sysmon IDs where people
know them:

| Telemetry | Sysmon ID | Why it matters |
|---|---|---|
| Process creation with full command line and hashes | 1 | execution chains |
| File creation with timestamps | 11 | droppers, staging |
| Network connection with process attribution | 3 | C2, exfiltration |
| DNS queries | 22 | C2 over DNS |
| Registry create/set | 12, 13 | persistence |
| Image load (DLLs) | 7 | injection, hijacking |
| Process access (memory open) | 10 | credential dumping |
| Named pipe creation | 17, 18 | lateral movement, C2 |
| WMI event consumers | 19, 20, 21 | persistence |
| Process tampering | 25 | EDR evasion |

If your EDR does not log full command lines, your LOLBin detections
are blind. Verify the telemetry with a controlled test, not with the
datasheet.

```bash
# Lab verification: generate known events and check they appear
# Run on a test host, then query the EDR console or Sysmon log:
powershell -c "Write-Host test-event-12345"
# Expect: process creation event with the full command line visible
```

## 2. Prevention versus detection modes

- Prevention (block) mode: the sensor kills known-malicious files
  and behaviors. Use for high-confidence signatures and for
  ransomware-like behavior on servers.
- Detection (alert) mode: the sensor logs and alerts but does not
  block. Use during rollout and for behavioral analytics that are
  still being tuned.
- Common rollout: detect-only for 2 weeks, review false positives,
  then enable blocking per policy group (servers first, then
  workstations, executives last or never auto-block).

Never enable aggressive behavioral blocking fleet-wide on day one.
One false positive that kills a business application will get the
whole EDR blamed and possibly disabled.

## 3. Alert triage workflow

Work every alert the same way. Example triage of a suspicious
PowerShell alert:

```text
1. Process tree: powershell.exe <- wmiprvse.exe <- ? 
   Is the parent legitimate for this host and user?
2. Command line: encoded? download cradle? Compare against the
   baseline of normal admin usage.
3. File: hash reputation, signer, first-seen in the fleet.
4. Network: did the process connect out, to where, how much data.
5. User and host: is this an admin, a server, business hours.
6. Verdict: true positive (escalate), benign (document and tune),
   or needs deeper forensics (memory, disk).
```

Use the EDR's process timeline view; attackers hide in the gaps
between single events. Pivot from the alert to the full process
tree before deciding.

```bash
# Sysmon equivalent triage from the SIEM for one host and time window
index=wineventlog ComputerName="WS-1042" earliest="2026-10-23 09:00" latest="2026-10-23 10:00"
| eval proc=lower(mvindex(split(Image,"\\"),-1))
| table _time, EventCode, proc, CommandLine, user
| sort _time
```

## 4. Response actions

Standard actions and when to use them:

- Network isolation (quarantine): confirmed malicious activity,
  host stays powered on for forensics. Keep an allowlist for the
  EDR cloud and domain controllers so the sensor keeps reporting.
- Process kill: stop the bleeding on one process, but assume
  persistence remains.
- File quarantine: remove the payload, record the hash for hunting.
- Host shutdown: last resort; kills memory evidence, use only to
  stop fast-spreading ransomware when isolation is unavailable.

```bash
# After isolation, verify it worked before continuing
# From the EDR console: host shows "isolated". From the SIEM:
index=edr ComputerName="WS-1042" earliest=-15m
| stats count by event_type
# Expect only EDR heartbeat traffic, no user process network events
```

Always collect before you remediate on important hosts: memory
capture and key logs first, then kill and quarantine. Remediation
destroys evidence.

## 5. Hunting from EDR data

EDR telemetry is the best hunting dataset you have: 90 days of
process-level truth.

```bash
# Hunt: processes with no signed image loading from user-writable paths
index=edr event_type=process_create earliest=-30d@d latest=@d
| where NOT signed=true AND match(image, "(?i)\\\\users\\\\|\\\\temp\\\\|\\\\appdata\\\\")
| stats dc(host) as hosts values(image) as examples by file_hash
| where hosts <= 3

# Hunt: living-off-the-land binaries with network connections
index=edr event_type=network earliest=-14d@d latest=@d
| eval proc=lower(file_name)
| where proc IN ("powershell.exe","rundll32.exe","mshta.exe","certutil.exe")
| stats values(dest_ip) as ips values(host) as hosts by proc
```

Save working hunts as scheduled queries or convert them to managed
detections.

## 6. Tuning

Every detection gets the same treatment as SIEM rules: measure
precision, fix logic first, exclude narrowly with tickets.

```bash
# Precision per EDR detection over 30 days (from your triage records)
index=edr_triage
| stats count(eval(verdict="true_positive")) as tp,
        count(eval(verdict="false_positive")) as fp by detection_name
| eval precision=round(tp/(tp+fp),2) | sort precision
```

Tuning patterns:

- Exclude by file hash plus signer for approved software, not by
  path alone (attackers plant files in excluded paths).
- Scope detections to host groups: a developer policy differs from
  a call-center policy.
- Time-bound exclusions for projects and migrations, with expiry.
- If a behavioral detection never produces true positives in 90
  days, demote it to hunt-only rather than paging the SOC.

## 7. Fleet health and tamper resistance

An EDR the attacker can kill is decoration. Monitor:

```bash
# Hosts without a recent heartbeat (SIEM-side check)
index=edr earliest=-24h latest=@h
| stats max(_time) as last_seen by host
| where last_seen < relative_time(now(), "-2h")
```

- Alert on sensor service stops, driver unloads, and tamper-protection
  disables. These are high severity by default.
- Track version drift: sensors more than two versions behind get
  upgraded on a schedule.
- Watch for exclusion sprawl: every exclusion has an owner, a
  ticket, and an expiry. Review quarterly.
- Test tamper resistance in the lab: try to kill the sensor as an
  administrator and confirm it resists or alerts.

## 8. Coverage metrics

Report monthly: percentage of in-scope hosts with a healthy sensor,
mean time to triage, detection precision per policy, number of hosts
isolated and why, and open tuning actions. Trend lines beat
snapshots; a coverage dip after a laptop refresh cycle is normal and
should be visible, not hidden.

## Edge cases

- VDI and non-persistent hosts: sensors must register fast and
  telemetry must attribute to the right session; test the gold
  image, not just persistent hosts.
- macOS and Linux fleets need different policies and have thinner
  telemetry. Do not copy Windows detections over blindly.
- Offline hosts (travel, air-gapped): they report late or never.
  Define the offline tolerance and investigate hosts that exceed it.
- EDR conflicts with existing AV or security tools: pick one
  primary agent per function and test combinations in the lab.
- Cloud workloads are ephemeral: use the cloud workload agent or
  runtime sensor, and keep the asset inventory synced so dead hosts
  do not look like coverage gaps.
- Performance complaints: measure CPU and disk impact per policy
  before and after changes; most impact comes from file scanning
  scope, not behavioral analytics.

## Escalation

- Sensor tampering alert on a production host: treat as a possible
  intrusion, isolate, and investigate before assuming user error.
- Widespread false positive blocking a business app: roll the
  policy back to detect-only for that group immediately, then tune.
- EDR console itself is unreachable: fall back to Sysmon and SIEM
  telemetry, and treat the outage as a security incident until the
  cause is known.
- Suspected EDR bypass in the wild: capture samples, test in the
  lab, engage the vendor, and add compensating detections (network,
  Sysmon) while waiting for the fix.
- Fleet-wide coverage drop (bad update): pause the rollout, roll
  back the affected group, and review the change process.

## Detection and defender view

EDR is the defender's strongest sensor, so attackers invest in
beating it:

- Attackers use bring-your-own-vulnerable-driver techniques to kill
  EDR at the kernel level. Keep tamper protection on, monitor driver
  loads, and block known-vulnerable drivers.
- Attackers patch or unhook user-mode sensors from memory. Prefer
  kernel telemetry and alert on sensor blindness (a host that goes
  quiet mid-incident).
- Attackers test payloads against EDR in their own labs. Assume
  signature evasion and lean on behavioral detections and hunts.
- Attackers abuse legitimate tools the EDR trusts. Tune allowlists
  by hash and signer, and watch trusted tools for unusual parents
  and command lines.
- Your tuning decisions are the attack surface: every exclusion is
  a hole. Review them like firewall rules, with owners and expiry.

## Key references

- MITRE ATT&CK T1562.001 (Disable or Modify Tools), T1014 (Rootkit),
  T1055 (Process Injection), T1003.001 (LSASS Memory), T1218 (System
  Binary Proxy Execution).
- Sysmon documentation and SwiftOnSecurity config reference:
  https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon
- Velociraptor documentation: https://docs.velociraptor.app/
- MITRE Engenuity ATT&CK Evaluations (EDR product test reports).
