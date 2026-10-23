---
name: incident-timeline-analysis-super-timeline-analysis
description: Use when multiple host timelines must be merged into one
  incident narrative during an authorized investigation. Covers
  merging Plaso 20241006 storage files with psort.py, aligning
  timezones and correcting clock skew across hosts, reading the
  merged timeline for attacker working hours and dwell patterns with
  Python 3.12, identifying first and last activity with confidence,
  gap analysis for missing evidence, and presenting the super-timeline
  to stakeholders. Use when the parent incident-timeline-analysis
  workflow has per-host timelines, when scoping needs the full
  incident span, or when the report requires one defensible sequence.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-timeline-analysis
requires: [incident-timeline-analysis]
extends: []
relates: [incident-timeline-analysis]
tools:
  - name: Plaso
    version: 20241006
  - name: Python
    version: 3.12
  - name: jq
    version: 1.7
---

Super-timeline analysis merges every host's timeline into one sorted
sequence and reads it as a whole: the attacker's path across
machines, their working hours, the quiet gaps, and the true first
and last events. Individual timelines show trees; the super-timeline
shows the forest. This sub-skill covers the merge mechanics, the
skew corrections that make the merge trustworthy, and the analytical
reading that extracts the incident narrative. Authorized
investigations only.

## Quick Workflow

1. Collect per-host Plaso storage files with confirmed timezones
   and measured skew.
2. Export each host to deduped CSV in UTC with psort.
3. Merge into one super-timeline CSV, sorted by timestamp.
4. Correct skew: shift each host's events by its measured offset.
5. Read the merged timeline in phases: initial access, foothold,
   lateral movement, actions on objectives.
6. Extract working hours, dwell time, and gaps.
7. Establish first and last attacker activity with confidence
   levels.
8. Produce the narrative timeline for the report.

## 1. Merging with psort

```bash
# Export each host in UTC, deduplicated
for h in web-03 ws-11 db-01; do
  psort.py -o csv --dedup -w ${h}-utc.csv ${h}.plaso
done

# Merge: keep one header, concatenate the rest
head -1 web-03-utc.csv > super-timeline.csv
for h in web-03 ws-11 db-01; do
  tail -n +2 -q ${h}-utc.csv >> super-timeline.csv
done
wc -l super-timeline.csv

# Sort by the datetime column (verify the column name first)
head -1 super-timeline.csv | tr ',' '\n' | grep -n -i datetime
python3 - <<'EOF'
import csv
rows = list(csv.DictReader(open('super-timeline.csv')))
rows.sort(key=lambda r: r['datetime'])
with open('super-sorted.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print(f"{len(rows)} events sorted")
EOF
```

Example output shape:

```
412,508 events sorted
# super-sorted.csv head:
# datetime,host,source,parser,message,...
# 2026-10-18 06:12:44,web-03,syslog,...
```

## 2. Skew correction across hosts

```bash
# skew.txt: measured offsets from the source inventory (parent skill)
cat skew.txt
# web-03 +0s
# ws-11 -47s
# db-01 +12s
```

```python
# skew-correct.py: shift each host's events by its measured offset
import csv
from datetime import datetime, timedelta

skew = {'web-03': 0, 'ws-11': -47, 'db-01': 12}
rows = list(csv.DictReader(open('super-sorted.csv')))
for r in rows:
    host = r.get('host', '')
    if host in skew and skew[host]:
        ts = datetime.strptime(r['datetime'][:19], "%Y-%m-%d %H:%M:%S")
        ts += timedelta(seconds=-skew[host])  # correct to true time
        r['datetime'] = ts.strftime("%Y-%m-%d %H:%M:%S") + r['datetime'][19:]
        r['skew_corrected'] = 'yes'
rows.sort(key=lambda r: r['datetime'])
with open('super-corrected.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)
print("skew corrected and re-sorted")
```

Without this step, a 47-second skew makes ws-11's events appear
before web-03's causally prior events. The corrected timeline is the
one the report uses; keep the uncorrected file too, for audit.

## 3. Reading attacker working hours

```python
# working-hours.py: when is the attacker active (attacker-attributed events)
import csv, re
from collections import Counter

attacker_ips = {'198.51.100.23'}
hours = Counter()
days = Counter()
for row in csv.DictReader(open('super-corrected.csv')):
    msg = row.get('message', '')
    if any(ip in msg for ip in attacker_ips):
        h = row['datetime'][11:13]
        hours[h] += 1
        days[row['datetime'][:10]] += 1

print("Active hours (UTC):")
for h in sorted(hours):
    print(f"  {h}:00  {'#' * min(hours[h], 50)} {hours[h]}")
print("Active days:", dict(sorted(days.items())))
```

Example output shape:

```
Active hours (UTC):
  02:00  ######################################## 41
  03:00  ############################## 30
  04:00  ############ 12
Active days: {'2026-10-20': 8, '2026-10-21': 75}
```

Interpretation: concentrated 02:00-04:00 UTC activity on one day
suggests a manual operator in a UTC-adjacent timezone working a
single intrusion session, not a persistent implant beaconing around
the clock. That shapes the scoping: look for what was done in that
window, not for weeks of beaconing.

## 4. Phase reading: the narrative pass

Read the corrected timeline once, start to finish, tagging phases:

```bash
# Extract the incident window for the narrative read
awk -F, '$1 >= "2026-10-20 00:00:00" && $1 <= "2026-10-23 12:00:00"' \
  super-corrected.csv > narrative-window.csv
wc -l narrative-window.csv
```

Tag each significant event with its phase and ATT&CK technique:

```
2026-10-20 22:41:03 | vpn-01   | VPN login svc-deploy from 198.51.100.23
  PHASE: initial access | T1078 | confidence: high
2026-10-21 03:12:44 | web-03   | sshd Accepted ops from 198.51.100.23
  PHASE: lateral movement | T1021 | confidence: high
2026-10-21 03:14:02 | web-03   | cron /tmp/.x/sysd created
  PHASE: persistence | T1053 | confidence: high
2026-10-21 03:31:19 | db-01    | SMB session from web-03 as ops
  PHASE: lateral movement | T1021.002 | confidence: medium (single source)
2026-10-21 04:02:51 | db-01    | /tmp/.x/dump.sql written (2.1 GB)
  PHASE: collection | T1005 | confidence: high
2026-10-21 04:20:13 | web-03   | 2.1 GB outbound to 198.51.100.23:443
  PHASE: exfiltration | T1048 | confidence: high
```

The phase tags turn the timeline into the scoping input: each phase
is a question (how did they persist, where did they go next) with
its evidence attached.

## 5. Gap analysis

```python
# gaps.py: find quiet periods in attacker-attributed activity
import csv
from datetime import datetime

times = []
for row in csv.DictReader(open('super-corrected.csv')):
    if '198.51.100.23' in row.get('message', ''):
        times.append(datetime.strptime(row['datetime'][:19], "%Y-%m-%d %H:%M:%S"))
times.sort()
for a, b in zip(times, times[1:]):
    gap = (b - a).total_seconds() / 3600
    if gap > 2:
        print(f"gap {gap:.1f}h between {a} and {b}")
```

Example output shape:

```
gap 19.4h between 2026-10-20 22:41:03 and 2026-10-21 03:12:44
```

A 19-hour gap between VPN access and the next action: either the
attacker waited, or activity happened where you have no logs.
Investigate both: check for log gaps on the hosts (missing events
suggest deletion, T1070) and consider that the VPN session may have
been established by an accomplice or an automated check.

## 6. First and last activity with confidence

```
First attacker activity: 2026-10-20 22:41:03 UTC (VPN login, high confidence)
  Caveat: VPN logs retained 90 days; earlier access cannot be excluded.
Last attacker activity: 2026-10-21 04:20:13 UTC (exfiltration complete, high)
  Caveat: persistence (cron) may still be present; eradication pending.
Dwell time: ~5.6 hours of active operation.
```

"First observed" is not "first occurred": state the retention
limits that bound the claim. The scoping skill uses these bounds
to decide how far back the investigation must reach.

## Edge cases

- Hosts in different timezones with daylight saving transitions
  mid-incident. Convert each host's local times using its actual
  zone rules for that date, not a fixed offset.
- The merged timeline is dominated by noise (millions of routine
  events). Filter to attacker-attributed entities first, then
  expand around their timestamps; do not read millions of lines.
- Two hosts have the same hostname after a rebuild. Disambiguate
  by MAC, serial, or IP history before merging, or the timeline
  interleaves two machines' lives.
- Skew was never measured and hosts are gone (reimaged). Note
  the uncorrected merge as approximate; event order within a
  minute is unreliable.
- The attacker manipulated timestamps (timestomping). Clusters of
  identical improbable timestamps are the tell; escalate to
  forensics rather than trusting the order.
- Gaps align exactly with log rotation schedules. That is
  retention, not attacker action; verify against the rotation
  config before theorizing.

## Escalation

- The super-timeline shows the attacker touched systems outside
  the current scope. Escalate immediately; scoping expands and
  containment may need another wave.
- First activity predates all retention. Escalate the blind spot
  to the commander and consider external forensics for deeper
  recovery; do not silently truncate the timeline.
- The timeline supports two incompatible narratives (insider
  versus external). Present both with evidence for each;
  choosing is the commander's call, with legal aware.
- Stakeholders want the timeline "simplified" for executives.
  Provide the one-page narrative plus the annotated data as an
  appendix; never let the simplification drop the caveats.

## Detection and defender view

The super-timeline is the defender's best teacher: it shows every
detection that should have fired and did not. After the incident,
walk the timeline with the detection team and write a rule for each
missed step: the VPN login from a new ASN, the cron persistence,
the 2 GB outbound transfer. The peacetime investments that make
super-timelines trustworthy are NTP everywhere, centralized logging
with long retention, and consistent host naming. A timeline you can
build in an hour is a capability; one that takes a week is a
project.

## Key references

- Parent workflow: incident-timeline-analysis (this repo)
- Plaso and psort: https://plaso.readthedocs.io/
- Timesketch: https://timesketch.org/
- NIST SP 800-86: https://csrc.nist.gov/publications/detail/sp/800-86/final
- MITRE ATT&CK: https://attack.mitre.org/
- SANS FOR508 (timeline methods):
  https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training/
