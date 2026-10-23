---
name: timeline-basics
description: Use when building a forensic timeline of events from a disk
  image or live system. Covers filesystem timestamp extraction, timeline
  tooling, event correlation, and reading timelines for attacker activity.
  Use when reconstructing what happened and when, when correlating logs
  with file activity, or when the investigation needs a single ordered
  story.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
parent: forensics-fundamentals
requires: [forensics-fundamentals]
extends: []
relates: [disk-forensics, log-forensics]
tools:
  - name: The Sleuth Kit
    version: 4.12.1
  - name: Python
    version: 3.12
---

A timeline orders every timestamped event into one story: file created,
log written, process started, all in sequence. This skill covers building
basic timelines from filesystem metadata: extracting MAC times, merging
sources, and reading the result for attacker activity. Timelines turn a
pile of artifacts into the narrative the investigation needs.

## Quick Workflow

1. Work from the verified image or read-only mount.
2. Extract filesystem timestamps (MAC times) for the scope.
3. Add log sources: system, application, security logs.
4. Normalize timezones: everything to UTC, then to the local zone.
5. Sort into one timeline and filter to the incident window.
6. Read for attacker patterns: bursts, odd hours, sequences.
7. Annotate the timeline with the investigation's conclusions.

## 1. Extracting filesystem times

```bash
# TSK: list all files with MAC times (image must be acquired already)
fls -r -m / /analysis/case01_work.img > /tmp/bodyfile.txt
head -5 /tmp/bodyfile.txt

# mactime: turn the body file into a sorted timeline
mactime -b /tmp/bodyfile.txt -d > /tmp/timeline.csv
head -10 /tmp/timeline.csv

# Focus on the incident window (example: Oct 20-22)
awk -F',' '$1 >= "2026-10-20" && $1 <= "2026-10-22"' /tmp/timeline.csv \
  > /tmp/window.csv
wc -l /tmp/window.csv
```

MAC times are modified, accessed, changed (metadata), and birth/created.
Attacker activity clusters: look for bursts of creates and modifies at
odd hours, especially in temp directories, startup locations, and web
roots.

## 2. Merging log sources

```bash
# System logs add the process and auth events the filesystem lacks
# Extract auth events into the same CSV shape for merging
grep -E 'sshd|su:|sudo' /mnt/image/var/log/auth.log | head -10

# Python: merge and sort multiple timestamped sources
python3 - <<'EOF'
import csv
from datetime import datetime

events = []
# filesystem timeline rows: date,time,event,path
with open('/tmp/window.csv') as f:
    for row in csv.DictReader(f):
        events.append((row['Date'] + ' ' + row['Time'], 'fs', row['File Name']))

events.sort()
for ts, src, detail in events[:20]:
    print(f"{ts} [{src}] {detail}")
print(f"[*] {len(events)} events in window")
EOF
```

One timeline with filesystem, auth, and application events beats three
separate ones. The correlation is the analysis: a file created two
minutes after a successful SSH login from an odd IP tells the story.

## 3. Reading for attacker activity

```bash
# Hunt patterns in the merged timeline:
# - Executables created in /tmp, /var/tmp, /dev/shm
grep -E '/tmp/|/var/tmp/|/dev/shm/' /tmp/window.csv | grep -i -E '\.sh$|\.py$|\.elf$|\.bin$' | head -10

# - Startup persistence: cron, systemd, registry Run keys, Startup folder
grep -i -E 'cron|systemd|/etc/cron' /tmp/window.csv | head -10

# - Mass file access (staging for exfiltration)
#   many reads in a short window from one directory

# - Timestomping: clusters of identical unlikely timestamps
cut -d',' -f1,2 /tmp/window.csv | sort | uniq -c | sort -rn | head -10
```

Timestomping shows as statistical impossibility: hundreds of files with
the exact same second-precision timestamp. Normal systems do not do
that; attackers covering tracks do.

## Edge cases

- Timezones are mixed. Normalize everything to UTC at ingest; a
  timeline with mixed zones lies about sequence.
- Timestamps were altered (timestomping). Cross-check with logs and
  journal entries that the attacker may have missed.
- The clock was wrong during the incident. Note the skew if you can
  prove it (NTP logs, correlated external events); otherwise flag the
  uncertainty.
- The timeline is millions of rows. Filter to the window and the
  interesting paths first; full-timeline review is a last resort.

## Escalation

- You need deeper artifact timelines: hand specific questions to
  artifact-parsing (browser history, registry, event logs each have
  their own timeline tools).
- The timeline must be court-ready: document every source, every
  normalization step, and every filter applied.
- Correlation needs the network side: merge firewall and proxy logs
  using the same UTC normalization.

## Detection and defender view

For defenders, timelines are the incident reconstruction tool: they turn
alerts into sequences and sequences into root cause. Building timelines
routinely (not just during incidents) creates the baseline that makes
anomalies visible. The defender's investment is centralized logging with
synchronized clocks; without NTP discipline, every timeline is suspect.

## Key references

- NIST SP 800-86 (Guide to Integrating Forensic Techniques into Incident
  Response).
- The Sleuth Kit documentation: fls, mactime.
- "File System Forensic Analysis" (timestamp interpretation).
