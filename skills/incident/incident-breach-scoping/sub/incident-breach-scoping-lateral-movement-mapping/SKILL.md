---
name: incident-breach-scoping-lateral-movement-mapping
description: Use when you must trace the attacker's path between
  hosts during an authorized incident investigation. Covers
  host-to-host connection analysis with Zeek 7.0 and Wireshark 4.2,
  Windows lateral movement evidence (RDP type 10 logons, SMB, WMI,
  PsExec), Linux lateral movement (SSH, credential reuse), EDR
  process ancestry hunts with Velociraptor 0.72 and osquery 5.12.1,
  building the movement graph, and distinguishing attacker movement
  from admin activity. Use when the parent incident-breach-scoping
  workflow reaches movement mapping, when one compromised host
  implies others, or when the scope keeps growing.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-breach-scoping
requires: [incident-breach-scoping]
extends: []
relates: [incident-breach-scoping]
tools:
  - name: Zeek
    version: 7.0
  - name: Wireshark
    version: 4.2
  - name: osquery
    version: 5.12.1
  - name: Velociraptor
    version: 0.72
  - name: Python
    version: 3.12
---

Lateral movement mapping traces every hop the attacker made between
hosts: which protocol, which credentials, when, and what happened
after landing. Each hop is a newly scoped host until proven clean.
This sub-skill covers the per-protocol evidence on Windows and
Linux, the EDR hunts that reveal remote execution, and building the
movement graph that the scope statement is built from. Authorized
investigations on your own infrastructure only.

## Quick Workflow

1. Start from each confirmed compromised host; list its outbound
   connections in the incident window.
2. Classify each connection by protocol and check it against known
   admin patterns.
3. Pull the authentication evidence for each hop (logon events,
   SSH accepts).
4. Hunt EDR for remote execution artifacts (PsExec, WMI, WinRM).
5. Add each reached host to the scope as likely-compromised pending
   triage.
6. Triage reached hosts: look for the attacker's artifacts, not
   just the connection.
7. Build the movement graph with timestamps and techniques.
8. Distinguish attacker hops from legitimate admin activity and
   document the distinction.

## 1. Network evidence with Zeek

```bash
# conn.log: host-to-host flows on lateral movement ports
zeek-cut id.orig_h id.resp_h id.resp_p proto orig_bytes < conn.log | \
  awk '$3==445 || $3==3389 || $3==22 || $3==5985 || $3==135' | \
  sort | uniq -c | sort -rn | head -25
```

Example output shape:

```
  14 192.168.30.15 192.168.30.20 445 tcp 512
   9 192.168.30.15 192.168.30.31 3389 tcp 2048
   3 192.168.30.20 192.168.30.15 22 tcp 8912
```

SMB (445) from a web server to a file server at 03:00 is not normal
web server behavior; RDP (3389) from that web server is even less
so. Baseline what is normal first: pull the same report for the
week before the incident and diff. Admin ports between servers at
odd hours from a compromised host are attacker movement until
proven otherwise.

```bash
# DCE-RPC (135) often precedes WMI-based movement; check what followed it
zeek-cut ts id.orig_h id.resp_h id.resp_p < conn.log | \
  awk '$4==135' | head -10
```

## 2. Windows lateral movement evidence

```powershell
# RDP logons (type 10) and network logons (type 3) on the reached host
Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4624} -MaxEvents 100 |
  Where-Object {$_.Message -match 'Logon Type:\s+(3|10)'} |
  Select-Object TimeCreated, @{n='Type';e={[regex]::Match($_.Message,'Logon Type:\s+(\d+)').Groups[1].Value}},
    @{n='Source';e={[regex]::Match($_.Message,'Source Network Address:\s+(\S+)').Groups[1].Value}}

# PsExec-style service installation (event 7045)
Get-WinEvent -FilterHashtable @{LogName='System'; ID=7045} -MaxEvents 30 |
  Select-Object TimeCreated, Message
```

Example output shape:

```
TimeCreated          Type Source
-----------          ---- ------
2026-10-21 03:31:19  3    192.168.30.15
2026-10-21 03:33:02  10   192.168.30.15
```

Type 3 from web-03 followed by type 10 from the same source: SMB
recon then interactive RDP. Event 7045 with a service name like
`PSEXESVC` is the PsExec fingerprint; a randomly named service
installed at the same time is the attacker's own tool.

WMI movement evidence:

```powershell
# WMI operational log: process creation via WMI
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-WMI-Activity/Operational'; ID=5861} `
  -MaxEvents 20 | Select-Object TimeCreated, Message
```

## 3. Linux lateral movement evidence

```bash
# Outbound SSH from servers is the key signal
grep -E "Accepted" /var/log/auth.log | awk '{print $NF}' | sort | uniq -c | sort -rn | head

# SSH as a client leaves no auth.log entry on the source; check shell history and known_hosts
grep -E "ssh " /home/*/.bash_history /root/.bash_history 2>/dev/null | head
cat /root/.ssh/known_hosts | awk '{print $1}' | sort -u

# EDR/osquery: ssh processes with suspicious parents or targets
osqueryi "SELECT pid, name, cmdline, parent FROM processes WHERE name='ssh' AND cmdline LIKE '%192.168.%';"
```

An `ssh` process spawned by a web application user (www-data) is
lateral movement, full stop. Legitimate automation uses service
accounts from known jump hosts; anything else gets investigated.

## 4. EDR remote execution hunts

```bash
# Velociraptor hunt pattern: remote execution tools fleet-wide
# Artifacts: Windows.System.PsExec, WMI process creation, WinRM operational log

# osquery: services created recently with suspicious binary paths
osqueryi "SELECT name, path FROM services WHERE path LIKE '%\\Temp\\%' OR path LIKE '%\\Users\\Public\\%';"

# osquery: processes whose parent is a remote execution broker
osqueryi "SELECT name, cmdline, parent FROM processes WHERE parent IN ('wmiprvse.exe','svchost.exe') AND name NOT IN ('conhost.exe');"
```

The parent-child relationship is the evidence: `wmiprvse.exe`
spawning `powershell.exe` with an encoded command is WMI lateral
movement, not administration. Capture the full command line; it
often contains the next hop's credentials or payload URL.

## 5. Building the movement graph

```python
# movement-graph.py: nodes and timestamped edges from the evidence
edges = [
    ("vpn-01", "web-03", "2026-10-21 03:12:44", "SSH T1021", "high"),
    ("web-03", "db-01", "2026-10-21 03:31:19", "SMB T1021.002", "high"),
    ("web-03", "ws-11", "2026-10-21 03:33:02", "RDP T1021.001", "medium"),
    ("db-01", "file-02", "2026-10-21 03:47:55", "SMB T1021.002", "low"),
]
print("digraph movement {")
for src, dst, ts, tech, conf in edges:
    print(f'  "{src}" -> "{dst}" [label="{ts}\\n{tech}\\n{conf}"];')
print("}")
```

Render with graphviz for the report, or keep the edge list. Each
edge carries the technique and confidence; "low" edges are the ones
that need triage before the scope closes. The graph usually reveals
the pattern: hub-and-spoke from one beachhead, or a chain where
each host was a stepping stone.

## 6. Attacker versus admin

The same protocols carry both. Distinguish with:

- Source: admin hops come from jump hosts and admin workstations;
  attacker hops come from compromised servers.
- Time: attacker hops cluster in the incident window, often at
  odd hours; admin hops follow change tickets.
- Credentials: attacker hops reuse the compromised accounts;
  correlate the logon account with the compromised list.
- Tooling: admins use RDP clients and SSH normally; attackers
  leave PsExec services, encoded PowerShell, and web shells.
- Change records: a hop with a matching change ticket and the
  admin's normal source is admin activity; document and exclude.

```bash
# Quick check: was there a change ticket for this window? (process, not command)
# Record the answer per edge in the graph notes
```

When in doubt, keep the host in scope. Excluding a host on a hunch
is how persistence survives eradication.

## Edge cases

- The attacker used the same jump host as admins. Then source
  alone does not distinguish; use session timing, tooling, and
  the credentials involved.
- Movement over nonstandard ports or tunneled through the C2
  channel. Network evidence shows only the C2 flow; EDR process
  ancestry is the fallback that reveals the tunneled hops.
- The reached host was already decommissioned or rebuilt. Check
  backups and the hypervisor for its last state; a rebuilt host
  without investigation is a scope hole.
- IPv6 lateral movement bypasses IPv4-focused monitoring. Check
  the IPv6 logs too; attackers use whatever the monitoring
  ignores.
- Cloud: lateral movement via assumed roles and SSM, not SMB.
  Correlate CloudTrail AssumeRole with the on-prem timeline;
  the "hosts" are roles and instances.

## Escalation

- The movement graph reaches a segment you cannot investigate
  (OT, PCI, a subsidiary). Escalate to the commander; that
  segment needs its own investigation team, not your best guess.
- Movement suggests the attacker had domain admin. Assume the
  worst: every domain-joined host is in scope until the
  credential is reset twice (once now, once after eradication)
  and the graph is verified clean.
- A hop targeted the backup infrastructure. Escalate immediately;
  compromised backups change the recovery plan fundamentally.
- The graph keeps growing past your team's capacity. Bring in
  reinforcements or external IR; a movement map that outruns the
  investigators is how incidents become breaches.

## Detection and defender view

Lateral movement is the phase where segmentation and credential
hygiene pay off: a segmented network turns the graph into isolated
nodes, and tiered credentials turn one compromised account into a
dead end instead of a skeleton key. The detections to build from
this analysis are per-protocol anomalies: SMB between servers that
never talk, RDP from servers, SSH from application accounts, and
any PsExec service creation. Baseline first, alert on deviation;
the attacker's movement is only invisible against a network with
no baseline.

## Key references

- Parent scoping workflow: incident-breach-scoping (this repo)
- MITRE ATT&CK lateral movement (T1021, T1047, T1569):
  https://attack.mitre.org/
- Zeek documentation: https://docs.zeek.org/
- Velociraptor hunts: https://docs.velociraptor.app/
- osquery schema: https://osquery.io/schema/
- SANS FOR508 (lateral movement analysis):
  https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training/
