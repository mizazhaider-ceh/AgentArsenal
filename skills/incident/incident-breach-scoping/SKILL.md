---
name: incident-breach-scoping
description: Use when you must determine the full blast radius of a
  confirmed intrusion on systems you are authorized to defend. Covers
  identifying the initial access vector, mapping lateral movement with
  EDR and log evidence, inventorying compromised accounts and
  privileges, sweeping for persistence, assessing data staging and
  exfiltration with Wireshark 4.2 and Zeek 7.0, and writing the scope
  statement with confidence levels. Use when the incident-response
  workflow needs to know how far the attacker got, before eradication
  begins, or when leadership asks the hardest question, what the attacker took.
  Authorized systems only.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, threat-intel, incident-containment-playbooks]
tools:
  - name: Wireshark
    version: 4.2
  - name: Zeek
    version: 7.0
  - name: osquery
    version: 5.12.1
  - name: Velociraptor
    version: 0.72
  - name: Python
    version: 3.12
---

Breach scoping answers the questions eradication depends on: how the
attacker got in, where they went, what they touched, and what they
took. Scope too narrow and eradication misses persistence; scope too
wide and the business bleeds from overreaction. This skill covers
the disciplined scoping method: initial access, lateral movement
mapping, account and privilege inventory, persistence sweep, and
exfiltration assessment, ending in a scope statement with explicit
confidence. Never start eradication on a partially scoped incident;
you will just teach the attacker to hide better.

## Quick Workflow

1. Freeze the current understanding: patient zero, entry vector
   hypothesis, known-affected hosts.
2. Identify initial access: the first attacker-controlled event with
   evidence.
3. Map lateral movement: every host-to-host path with timestamps.
4. Inventory compromised accounts, their privileges, and what each
   could reach.
5. Sweep all in-scope hosts for persistence mechanisms.
6. Assess data staging and exfiltration: what was collected, how
   much left, through which channel.
7. Write the scope statement: confirmed, likely, and excluded, each
   with confidence.
8. Get the commander's sign-off before eradication starts.

## 1. Initial access identification

Work backward from the first known malicious event to the entry:

```bash
# On patient zero: what is the earliest attacker artifact
# Check web logs for exploitation, auth logs for logins, mail for phishing
grep -E "40[034]|50[0-9]" /var/log/apache2/access.log | head -20
grep -iE "accepted|failed password" /var/log/auth.log | head -20

# VPN and remote access logs: first contact often comes from here
grep "198.51.100.23" /var/log/vpn.log | head -5
```

```bash
# EDR hunt: first execution of attacker tooling fleet-wide (Velociraptor pattern)
# Query: processes whose hash matches the known malware, ordered by start time
```

Common entry vectors and their evidence:

- Phishing: email gateway logs, user reports, macro execution in
  EDR (T1566).
- VPN or remote service: auth logs showing a new IP, impossible
  travel, or off-hours access (T1078).
- Web exploitation: WAF and access logs with injection strings,
  followed by a web shell file on disk (T1190).
- Supply chain or trusted relationship: harder; look for the
  earliest anomalous vendor connection.

The initial-access-identification sub-skill covers each vector's
evidence in depth. The entry vector determines the eradication:
patch the vulnerability, fix the phishing path, or rotate the
abused trust.

## 2. Lateral movement mapping

For each compromised host, find where the attacker went next:

```bash
# SSH lateral movement: outbound SSH from a server is suspicious
grep -E "Accepted" /var/log/auth.log | grep -v "from 10.0.0" | head -20

# Windows: network logons (type 3) and RDP (type 10) from the host
# Event 4624, LogonType 10 = RDP; correlate source IPs
```

```bash
# EDR: process ancestry showing remote execution tools
# Hunt for: psexec, wmiexec, smbexec, winrs, ssh with odd parents
osqueryi "SELECT name, cmdline, parent FROM processes WHERE name IN ('psexec.exe','wmic.exe','ssh') AND parent NOT IN ('explorer.exe','sshd');"
```

```bash
# Network: Zeek conn.log for host-to-host flows on admin ports
zeek -r capture.pcap
cat conn.log | zeek-cut id.orig_h id.resp_h id.resp_p proto \
  | awk '$3==445 || $3==3389 || $3==22' | sort | uniq -c | sort -rn | head -20
```

Example output shape:

```
12 192.168.30.15 192.168.30.20 445 tcp
 8 192.168.30.15 192.168.30.31 3389 tcp
```

Build the movement graph: nodes are hosts, edges are timestamped
connections with the technique (SMB, RDP, SSH, WMI). The
lateral-movement-mapping sub-skill details the per-protocol
evidence. Every edge is a host that joins the scope until proven
clean.

## 3. Account and privilege inventory

```bash
# Which accounts did the attacker use or create
# New accounts around the intrusion window
awk -F: '{print $1}' /etc/passwd > passwd-now.txt
# ... compare against a known-good baseline or backup

# Recent password changes and new SSH keys
find /home /root -name "authorized_keys" -newermt "2026-10-20" 2>/dev/null
grep -E "password changed" /var/log/auth.log | head

# Privilege: what could each compromised account reach
# Domain admins, cloud roles, database grants, VPN groups
```

```powershell
# Windows: recent account creation (event 4720) and privilege grants (4728)
Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4720} -MaxEvents 20 |
  Select-Object TimeCreated, Message
```

For each compromised account record: first malicious use, last
malicious use, privilege level, and reachable systems. An
attacker with a domain admin hash for six hours has a different
scope than one with a helpdesk account for six minutes. Assume the
attacker used every privilege the account had.

## 4. Persistence sweep

Check every in-scope host for every persistence mechanism; the
attacker's return ticket hides here:

```bash
# Linux persistence checklist
crontab -l; ls -la /etc/cron.d/ /var/spool/cron/crontabs/ 2>/dev/null
systemctl list-unit-files --state=enabled | grep -vE "^\s*(ssh|network)" | head -20
ls -la /etc/systemd/system/ | grep -v "^d"
grep -r "authorized_keys" /home /root --include="authorized_keys" -l 2>/dev/null
ls -la /etc/ld.so.preload 2>/dev/null; cat /etc/ld.so.preload 2>/dev/null
```

```powershell
# Windows persistence checklist
Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Select-Object TaskName, Author
Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
Get-WinEvent -FilterHashtable @{LogName='System'; ID=7045} -MaxEvents 20
```

Compare against baselines: a scheduled task authored by SYSTEM last
week is normal; one authored yesterday by a compromised account is
not. Unknown persistence found during the sweep expands the scope
to every host sharing the deployment mechanism (GPO, config
management, golden image).

## 5. Data staging and exfiltration assessment

```bash
# Staging: large archives created near the intrusion window
find /tmp /var/tmp /dev/shm -type f -size +100M -newermt "2026-10-20" -ls 2>/dev/null
# Look for archiving tools in EDR process history: 7z, rar, tar with odd args

# Exfiltration: Zeek conn.log byte counts to external hosts
cat conn.log | zeek-cut id.orig_h id.resp_h orig_bytes resp_bytes \
  | awk '$1 ~ /^192\.168\./' | sort -k4 -rn | head -10
```

Example output shape:

```
192.168.30.15  198.51.100.23  1240  2214592512
```

2.2 GB outbound to an external host from a database server is the
exfiltration under assessment. Correlate the volume with the staged
archive size and the database size: matching sizes confirm what
left. The data-exfiltration-assessment sub-skill covers channel
identification (DNS tunneling, cloud uploads, email) and volume
analysis.

## 6. The scope statement

```
## Scope statement: INC-2026-1042 (v3, 2026-10-23 14:00 UTC)
Entry: VPN credential stuffing against svc-deploy (high confidence)
Confirmed compromised: web-03, db-01, ws-11 (forensic evidence)
Likely affected: file-02 (SMB session from web-03, under review)
Excluded: mail-01, vpn-01 (no attacker indicators in 30d of logs)
Accounts: svc-deploy, ops (both disabled, rotated)
Data: customer database (2.1 GB) exfiltrated 2026-10-21 04:20 UTC (high)
  Legal notified: yes, 2026-10-23 11:00 UTC
Persistence found: cron on web-03 (removed), none elsewhere (sweep complete)
Blind spots: VPN logs before 2026-07-25 unavailable (retention)
Eradication: APPROVED by <commander> at 14:05 UTC
```

Version the scope statement; it changes as the investigation
progresses, and the version history shows due diligence. The
commander's sign-off on the scope is what authorizes eradication
to begin.

## Edge cases

- The attacker used legitimate admin tools (LOLBins), leaving
  little malware to find. Scope from behavior (logons, network
  flows, data movement), not from binaries.
- Cloud and on-prem are both involved. Scope both; attackers do
  not respect your architecture diagrams. Check cloud role
  assumptions alongside host logons.
- The initial access vector is never found. Scope from the
  earliest confirmed activity and say so; "entry unknown,
  earliest activity X" is an honest scope, and it drives the
  eradication to cover all plausible entries.
- Dwell time is months, not hours. Expand log sources to backups
  and archives; the scope statement must carry the uncertainty
  of the early window.
- The scope includes a third party (vendor, customer). Involve
  legal before sharing findings; your scope statement may become
  a notification letter.
- Evidence was destroyed (logs wiped, hosts reimaged by
  well-meaning admins). Scope from what survives plus network
  telemetry; mark destroyed areas as unknown, not clean.

## Escalation

- Scoping reveals data theft with regulatory notification clocks.
  Escalate to legal and executive leadership immediately with the
  facts as known; do not wait for perfect certainty.
- The attacker is still active and scoping is incomplete. Freeze
  eradication, extend containment, and brief the commander on the
  tradeoff between speed and completeness.
- Scope keeps expanding with each sweep. Consider engaging
  external forensics; a second team scopes in parallel while
  yours holds containment.
- The scope implicates an insider. Restrict the scope statement's
  distribution, involve HR and legal per policy, and keep the
  investigation team small.

## Detection and defender view

Scoping is where defenders learn the true shape of their exposure:
every lateral path the attacker used is a segmentation failure,
every reused credential is a hygiene failure, every blind spot is a
logging failure. The peacetime program that makes scoping fast is
network diagrams that match reality, credential inventories, EDR
everywhere, and log retention longer than the attacker's dwell
time. After the incident, each scope finding becomes architecture
work: the SMB path gets segmented, the service account gets
scoped down, the log gap gets a forwarder.

## Key references

- NIST SP 800-61 Rev. 2: https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final
- MITRE ATT&CK (technique per scope element):
  https://attack.mitre.org/
- SANS FOR508 (scoping and lateral movement):
  https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training/
- Zeek documentation: https://docs.zeek.org/
- Companion skills: incident-containment-playbooks,
  incident-timeline-analysis (this repo)
- Wireshark documentation: https://www.wireshark.org/docs/
- CISA incident reporting guidance: https://www.cisa.gov/report
