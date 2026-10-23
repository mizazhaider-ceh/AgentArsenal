---
name: incident-response
description: "Use when a security incident is suspected or confirmed and you need a disciplined response on authorized systems. Covers the NIST 800-61 lifecycle: preparation, detection and analysis, containment, eradication, recovery, and lessons learned. Includes Linux and Windows triage commands (processes, network connections, persistence mechanisms, authentication logs), evidence preservation that pairs with forensics-fundamentals, containment playbooks (host isolation, account disablement, credential rotation), eradication and recovery validation, stakeholder communication, and post-incident review. Works with Sysmon, osquery, and Velociraptor telemetry."
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [forensics-fundamentals]
tools:
  - name: sysmon
    version: 15.0
  - name: osquery
    version: 5.12.1
  - name: velociraptor
    version: 0.72
---
Incident response is the structured handling of a suspected or confirmed security incident, from first detection to lessons learned. This skill follows the NIST 800-61 lifecycle: preparation, detection and analysis, containment, eradication, recovery, and lessons learned. It gives you triage commands for Linux and Windows, containment playbooks, and communication discipline. Forensics owns the evidence; this skill owns the decisions. Never destroy evidence in the rush to recover, and never skip containment because eradication feels faster.

## Quick Workflow

1. Detect and declare: confirm the signal is real, open an incident ticket, assign an incident commander.
2. Triage the affected hosts with the Linux and Windows command sets below; preserve volatile evidence first.
3. Scope the incident: which hosts, which accounts, which data, how the attacker got in.
4. Contain: isolate hosts, disable accounts, rotate credentials, block indicators at the perimeter.
5. Eradicate: remove persistence, close the entry vector, patch or reimage affected systems.
6. Recover: restore from known-good backups or gold images, validate, and return to production in stages.
7. Lessons learned: blameless post-incident review, update detections and runbooks within days, not months.

## Phase 1: Preparation

Preparation is the phase you do before anything burns. Minimum viable readiness:

- An incident runbook with contact lists, escalation paths, and decision authority (who can authorize isolating a production host at 3 AM).
- Log centralization that attackers cannot easily reach: syslog forwarding for Linux, Windows Event Forwarding or a SIEM for Windows, with retention that covers your investigation window.
- EDR or telemetry deployed: Sysmon with a tuned config on Windows, osquery or auditd on Linux, Velociraptor for fleet-wide hunting.
- Known-good baselines: gold images, backup verification (tested restores, not just backup jobs), and an asset inventory so you know what is missing.
- Pre-staged tooling: a jump bag with write blockers, imaging tools, and the triage commands in this skill tested on your own fleet.

Run tabletop exercises quarterly. An untested runbook is a rumor.

## Phase 2: Detection and analysis, Linux triage

Confirm the signal before declaring. Then triage: who is logged in, what is running, what is listening, what persists, what the logs say. Work fast but do not alter the system more than necessary; capture volatile data first.

```bash
uptime; who; w; last -n 20
ps auxf --sort=-%cpu | head -40
ss -tulpn
lsof -i -P -n | head -30
```

Persistence and accounts:

```bash
cat /etc/passwd | grep -vE "nologin|false$"
lastlog | grep -v "Never"
crontab -l; ls -la /etc/cron.d/ /var/spool/cron/crontabs/ 2>/dev/null
systemctl list-timers --all 2>/dev/null | head -20
ls -la /etc/systemd/system/ | grep -vE "^d" | head -20
```

Suspicious files and logs:

```bash
find /tmp /var/tmp /dev/shm -type f -ls 2>/dev/null
ls -lat /etc/ | head -15
journalctl --since "2 hours ago" --priority=warning | tail -40
grep -iE "accepted|failed password" /var/log/auth.log 2>/dev/null | tail -30
```

If EDR is present, query it before manual triage; osquery makes fleet-wide checks one command:

```bash
osqueryi "SELECT name, path, cmdline FROM processes WHERE on_disk = 0;"
osqueryi "SELECT * FROM listening_ports WHERE port NOT IN (22,80,443);"
```

Capture memory and a disk image for forensics-fundamentals before containment actions that would destroy state (reboots, kills). Note the incident ID on every artifact.

## Phase 3: Detection and analysis, Windows triage

Same questions, Windows tooling. Prefer PowerShell remoting or Velociraptor for fleet scale; use local commands for single hosts.

```powershell
Get-Process | Sort-Object CPU -Descending | Select-Object -First 20 Name, Id, Path
Get-NetTCPConnection -State Established | Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, OwningProcess
Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Select-Object TaskName, State
Get-Service | Where-Object {$_.StartType -eq 'Automatic' -and $_.Status -ne 'Running'}
```

Accounts and logons:

```powershell
Get-LocalUser | Where-Object {$_.Enabled -eq $true} | Select-Object Name, LastLogon
Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4624} -MaxEvents 20 | Select-Object TimeCreated, Message
Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4625} -MaxEvents 20 | Select-Object TimeCreated
Get-WinEvent -FilterHashtable @{LogName='System'; ID=7045} -MaxEvents 20 | Select-Object TimeCreated, Message
```

Event ID 4624 is successful logon, 4625 is failed logon, 7045 is new service installation. With Sysmon deployed, query its log for process creation chains:

```powershell
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Sysmon/Operational'; ID=1} -MaxEvents 30 | Select-Object TimeCreated, Message
```

Autoruns (Sysinternals) covers persistence comprehensively when you can run it. As on Linux, preserve memory and disk images before destructive containment.

## Phase 4: Containment

Contain first, in a way that preserves evidence and does not tip off the attacker prematurely if you are still scoping. Short-term containment buys time; long-term containment holds the line.

Host isolation (keep the host powered on for memory forensics unless the incident commander orders otherwise):

```bash
iptables -A OUTPUT -d <siem-and-edr-ips> -j ACCEPT
iptables -A OUTPUT -j DROP
iptables -A INPUT -j DROP
```

On Windows, use host firewall rules or EDR network isolation rather than pulling cables when memory capture is still pending.

Account and credential actions:

```bash
passwd -l <compromised-user>
usermod -s /usr/sbin/nologin <compromised-user>
```

```powershell
Disable-LocalUser -Name "compromised-user"
```

Rotate credentials for every account the attacker touched, plus service accounts and API keys in the blast radius. Assume the attacker read everything the account could read.

Perimeter actions: block attacker IPs and domains at the firewall and DNS layer, revoke OAuth grants and sessions, and disable VPN access for affected users. Record every containment action with a timestamp; the timeline will need it.

Do not reimage or rebuild during containment if forensic analysis is still open, unless the business risk of waiting exceeds the evidence value. That tradeoff belongs to the incident commander, in writing.

## Phase 5: Eradication

Eradication removes the attacker's footholds and closes the entry vector. It starts only after scoping is complete; eradicating early on a partially scoped incident just teaches the attacker to hide better.

- Remove persistence: malicious cron entries, systemd units, scheduled tasks, Run keys, rogue services, planted SSH keys (`~/.ssh/authorized_keys` on every host in scope).
- Kill malicious processes and delete their binaries, but only after forensic copies exist.
- Close the entry vector: patch the exploited vulnerability, fix the misconfiguration (weak service ACLs, unquoted paths, exposed admin panels), remove the phishing-delivered payload path.
- Reset every credential in the blast radius, including ones that look clean. Attackers harvest broadly.
- For deeply compromised hosts, rebuild from gold images rather than cleaning. Cleaning is for workstations with adware; rebuilding is for servers with rootkits.

Validate eradication with the same triage commands from Phases 2 and 3, plus EDR hunts for the indicators of compromise across the whole fleet. One clean host means nothing if three siblings still beacon.

## Phase 6: Recovery and lessons learned

Recover in stages, most critical systems first, with enhanced monitoring on everything restored. Restore from known-good backups (verified before the incident, not assumed), or from gold images. Change all passwords again at recovery time if there is any doubt about the eradication window.

Validation before returning to production:

- Vulnerability that allowed entry is patched and verified.
- EDR and logging are healthy on restored hosts.
- No indicators of compromise fire for a defined observation period.
- Business owners sign off on restored data integrity.

Then the lessons learned review, within days, blameless by rule:

1. Timeline: what happened, when, how it was found.
2. What worked and what failed in detection, containment, and communication.
3. Root cause: the vulnerability or misconfiguration, plus the process gap that let it exist.
4. Action items with owners and deadlines: new detections, patched runbooks, architecture changes.

Track action items like any other commitment. An incident review whose actions die in a document is theater.

Communication discipline throughout: one incident channel, regular status updates to stakeholders, no speculation in writing, and legal or PR involvement before any external statement. Keep a single incident log with timestamps; it becomes the report.

## Edge cases

- The attacker is still active during triage: limit your footprint. Query EDR instead of logging into hosts, and coordinate containment so scoping is not burned by a premature isolation.
- Logs are missing or wiped: pivot to sources the attacker could not reach, like central syslog, firewall records, NetFlow, and EDR telemetry. Treat the gap as a finding and note it.
- The scope keeps growing: freeze eradication until scoping stabilizes. Eradicating a moving target wastes the one surprise you get.
- Business pressure demands instant recovery: get the risk acceptance in writing from whoever overrides the process, and restore to an isolated VLAN with full monitoring rather than straight to production.
- Ransomware with data theft: assume exfiltration happened. Containment includes revoking published data access, and recovery planning includes the extortion timeline, not just the encryption.
- Cloud assets involved: snapshot before terminating, preserve cloud trail and flow logs (they age out), and check for persistence in IAM roles and instance metadata, not just on hosts.

## Escalation

- Triage suggests a nation-state or ransomware affiliate: escalate to legal, executive leadership, and law enforcement liaison immediately. Do not negotiate or pay without that chain.
- Forensic needs exceed in-house skill: engage an external IR retainer before evidence handling mistakes compound. The first call should happen in preparation, not mid-incident.
- Containment fails (attacker re-enters): assume missed persistence or a second entry vector. Re-scope from network telemetry rather than re-running the same host triage.
- Key systems cannot be isolated without business impact: the incident commander weighs evidence value against outage cost, documents the decision, and compensates with enhanced monitoring and narrowed firewall rules.

## Detection and defender view

- This skill is the defender view: every offensive technique in privesc-linux, privesc-windows, and the AD skills should map to a detection (Sysmon rule, osquery query, SIEM correlation) and a runbook entry.
- Measure detection coverage with regular adversary emulation or purple team exercises, not with audit checklists.
- Detections decay: log sources get disabled, Sysmon configs drift, EDR exclusions accumulate. Review telemetry health monthly.
- The cheapest wins remain: centralized tamper-evident logging, MFA everywhere, tested backups, and an incident runbook people have actually rehearsed.

## Key references

- MITRE ATT&CK: use technique IDs per phase, for example T1070 (Indicator Removal) for log wiping, T1562.001 (Disable or Modify Tools) for defense impairment, T1486 (Data Encrypted for Impact) for ransomware, T1021 (Remote Services) for lateral movement, T1048 (Exfiltration Over Alternative Protocol) for data theft.
- CWE: CWE-778 (Insufficient Logging).
- Standards and docs: NIST SP 800-61 Rev. 2 (Computer Security Incident Handling Guide), NIST SP 800-86 (Forensic Techniques in Incident Response), Sysmon configuration guidance (official Sysinternals docs), osquery schema docs, Velociraptor docs.
