---
name: incident-timeline-analysis
description: Use when you need to reconstruct what happened and when
  during an authorized incident investigation. Covers building
  timelines with Plaso and log2timeline, normalizing timezones and
  clock skew, correlating authentication, proxy, and EDR logs with
  Python 3.12 and jq 1.7, super-timeline analysis across multiple
  hosts, and presenting attacker activity as a defensible narrative.
  Use when the incident-response workflow needs a verified sequence
  of events, when scoping depends on knowing first and last attacker
  activity, or when preparing the timeline for the post-incident
  report. Authorized systems only.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, log-forensics, memory-forensics]
tools:
  - name: Plaso
    version: 20241006
  - name: Python
    version: 3.12
  - name: jq
    version: 1.7
  - name: Wireshark
    version: 4.2
---

Timeline analysis reconstructs the incident as a sequence: first
access, lateral movement, persistence, exfiltration, each with a
timestamp and a source. Without a timeline, an investigation is a
pile of logs; with one, it is a story you can defend. This skill
covers building timelines with Plaso, correlating across log
sources, handling timezones and skew, and the super-timeline review
that finds the attacker's working hours. Authorized systems only,
and every timestamp gets a source citation.

## Quick Workflow

1. Inventory the log sources: hosts, central syslog, EDR, proxy,
   firewall, cloud trail.
2. Record each source's timezone and any known clock skew.
3. Build per-host timelines with Plaso's log2timeline.
4. Merge into a super-timeline with psort and a common timezone.
5. Correlate: join authentication, network, and process events on
   time and entity.
6. Annotate attacker actions with ATT&CK techniques and confidence.
7. Identify first and last activity, gaps, and working-hour
   patterns.
8. Export the narrative timeline for the report with source
   citations.

## 1. Source inventory and time hygiene

```bash
cat > sources.md <<'EOF'
## Timeline sources: INC-2026-1042
| Source | Host | TZ | Skew | Notes |
|---|---|---|---|---|
| /var/log/auth.log | web-03 | UTC | +0s (NTP ok) | local copy + SIEM |
| Security.evtx | ws-11 | UTC+2 | -47s (measured) | exported via wevtutil |
| EDR telemetry | fleet | UTC | +0s | console export |
| Squid proxy | proxy-01 | UTC | +0s | 90-day retention |
| CloudTrail | aws | UTC | +0s | confirm no gaps |
EOF
```

Measure skew before you trust ordering: compare `date -u` on the
host against a reference at capture time, and record the offset.
A 47-second skew reorders events that happened within a minute of
each other; without the correction, your "attacker did X then Y"
may be backwards.

## 2. Building timelines with Plaso

```bash
# Install Plaso (20241006) per the project docs; then:
# Build a timeline from a disk image or a log directory
log2timeline.py --storage-file web-03.plaso /evidence/INC-2026-1042/disk-sda.img

# Or from collected log files directly
log2timeline.py --storage-file logs.plaso /evidence/INC-2026-1042/*.log

# Check what the storage file contains
pinfo.py web-03.plaso | head -30
```

Example output shape from pinfo:

```
Events generated: 184,203
First event: 2026-10-18 06:12:44 UTC
Last event: 2026-10-23 09:41:02 UTC
Parsers: syslog, apache_access, chrome_history, ...
```

Filter to the incident window with psort:

```bash
# Export the incident window as CSV in UTC
psort.py -o csv --slice "2026-10-20 00:00:00" "2026-10-23 12:00:00" \
  -w timeline-window.csv web-03.plaso

# Narrow to security-relevant parsers
psort.py -o csv -w auth-events.csv "--filter" "parser is 'syslog' and message contains 'sshd'" \
  web-03.plaso
```

The plaso-timelines sub-skill covers parser selection, storage
management, and large-timeline performance.

## 3. Log correlation across sources

One source rarely tells the story. Join them on time and entity:

```bash
# SSH logins on web-03 around the suspected intrusion
grep -E "Accepted|Failed password" /evidence/INC-2026-1042/auth.log | head -20
```

```python
# correlate.py: join proxy requests with auth logins by time window
import re
from datetime import datetime, timedelta

def parse_auth(line):
    m = re.search(r'(\w{3}\s+\d+ \d+:\d+:\d+).*Accepted \w+ for (\w+) from ([\d.]+)', line)
    if m:
        return datetime.strptime(f"2026 {m.group(1)}", "%Y %b %d %H:%M:%S"), m.group(2), m.group(3)

logins = [parse_auth(l) for l in open('auth.log')]
logins = [l for l in logins if l]

# Proxy log format: timestamp, src_ip, method, url (adapt to yours)
for line in open('proxy.log'):
    parts = line.split()
    ts = datetime.strptime(parts[0] + ' ' + parts[1], "%Y-%m-%d %H:%M:%S")
    for login_ts, user, ip in logins:
        if parts[2] == ip and abs((ts - login_ts).total_seconds()) < 600:
            print(f"{ts} {user}@{ip} -> {parts[4]}  (within 10 min of login)")
            break
```

Example output shape:

```
2026-10-21 03:12:44 ops@198.51.100.23 -> http://evil.example.com/stage2.ps1  (within 10 min of login)
```

A login from an unusual IP followed minutes later by a download
from an attacker domain is the correlation that turns two log lines
into an intrusion narrative. The log-correlation sub-skill covers
join patterns for EDR process trees, firewall flows, and cloud
trail.

## 4. Super-timeline analysis

Merge host timelines into one view and read it like an analyst, not
a grep:

```bash
# Merge multiple plaso storage files into one sorted timeline
psort.py -o csv -w super-timeline.csv web-03.plaso ws-11.plaso db-01.plaso

# Sort and dedupe, then look at the incident window hour by hour
python3 - <<'EOF'
import csv
from collections import Counter
hours = Counter()
with open('super-timeline.csv') as f:
    for row in csv.DictReader(f):
        hours[row['datetime'][:13]] += 1
for h in sorted(hours):
    print(f"{h}:00  {'#' * min(hours[h]//10, 60)} {hours[h]}")
EOF
```

Example output shape:

```
2026-10-21 02:00  ######################################## 412
2026-10-21 03:00  ########## 98
2026-10-21 04:00  ## 21
```

Attacker working hours emerge: bursts of activity at 02:00-04:00
local time, quiet during business hours. Gaps matter too: a
six-hour silence between initial access and lateral movement
suggests manual operation, while seconds-apart events suggest
automation. Annotate the bursts with what happened in each.

## 5. Annotation and confidence

Every timeline entry that supports a claim gets an annotation:

```
2026-10-21 03:12:44 UTC | web-03 | sshd Accepted password for ops from 198.51.100.23
  -> T1078 Valid Accounts (initial access candidate). Confidence: medium.
     Source: auth.log (local) corroborated by SIEM. Note: ops denies this login.
2026-10-21 03:14:02 UTC | web-03 | cron entry added for /tmp/.x/sysd
  -> T1053 Scheduled Task (persistence). Confidence: high.
     Source: disk image timeline + file hash matches known malware family.
```

Confidence rules: high needs two independent sources or one source
plus corroborating context; medium is a single reliable source;
low is inference. Never promote a low-confidence entry to a
report claim without saying so.

## 6. Exporting the narrative

The report timeline is not the raw CSV; it is the curated sequence
with one line per attacker action, each cited:

```
## Incident timeline (UTC, times verified against NTP)
- Oct 20 22:41: initial access, VPN login for svc-deploy from 198.51.100.23 (T1078)
- Oct 21 03:12: SSH to web-03 as ops, password auth (T1021)
- Oct 21 03:14: persistence via cron on web-03 (T1053)
- Oct 21 03:31: lateral movement to db-01 over SMB (T1021.002)
- Oct 21 04:02: database dump to /tmp/.x/dump.sql (T1005)
- Oct 21 04:20: exfiltration to 198.51.100.23:443, 2.1 GB (T1048)
- Oct 23 09:00: detection, analyst triage begins
```

First activity to last: 30 hours. Dwell time, data volume, and the
technique chain go in the executive summary; the annotated CSV goes
in the appendix.

## Edge cases

- Logs are missing for part of the window (rotation, deletion).
  Mark the gap explicitly on the timeline; a gap during attacker
  activity hours is itself evidence (T1070).
- Two sources disagree on order by seconds. Apply the measured
  skew; if still ambiguous, present both orders and note the
  uncertainty rather than picking one silently.
- The timeline has millions of events. Filter by the incident
  hosts and window first, then by attacker-controlled entities
  (IPs, usernames, file paths); do not read it linearly.
- Timestamps are in local time with no zone info (Windows evtx
  before conversion). Convert everything to UTC at import and
  record the conversion.
- The attacker's activity blends with admin activity (stolen
  admin credentials). Distinguish by source IP, unusual hours,
  and tooling (admin uses the jump host; the attacker does not).
- CloudTrail shows gaps. Check whether logging was disabled
  (T1562) versus retention expiry; the distinction changes the
  investigation.

## Escalation

- The timeline shows data exfiltration before detection. Escalate
  to legal and leadership immediately; notification clocks may be
  running and the scope just changed.
- First activity predates your log retention. State the blind
  spot plainly, preserve what exists, and consider engaging
  external forensics for deeper recovery (carving, backups).
- The timeline implicates an insider (valid credentials, business
  hours, knowledge of internals). Handle with extra care: limit
  who sees the draft, involve HR and legal per policy, and do not
  confront the individual yourself.
- Multiple plausible narratives fit the timeline. Present each
  with its supporting and contradicting evidence; the
  commander's job is to choose, yours is to keep the options
  honest.

## Detection and defender view

Timeline analysis is the defender's rear-view mirror: it tells you
how the attacker moved so you can close each path. The peacetime
investments that make timelines possible are centralized,
time-synchronized logging with retention that exceeds your
detection time, and EDR process telemetry that fills the gaps
between log lines. After every incident, the timeline's gaps become
detection engineering tasks: each missing log source is a sensor to
deploy, each manual correlation is a SIEM rule to write.

## Key references

- Plaso documentation: https://plaso.readthedocs.io/
- log2timeline and psort usage: https://plaso.readthedocs.io/en/latest/
- NIST SP 800-86 (timeline analysis in forensics):
  https://csrc.nist.gov/publications/detail/sp/800-86/final
- MITRE ATT&CK (technique annotation): https://attack.mitre.org/
- Companion skills: incident-containment-playbooks,
  incident-breach-scoping (this repo)
- Timesketch (collaborative timeline analysis):
  https://timesketch.org/
- SANS FOR508 (timeline analysis methods):
  https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training/
