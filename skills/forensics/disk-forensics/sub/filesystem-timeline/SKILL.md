---
name: filesystem-timeline
description: Use when building a detailed filesystem timeline from a disk
  image for forensic analysis. Covers super-timeline generation, filtering
  to incident windows, and interpreting filesystem events. Use when the
  basic timeline needs filesystem depth, when correlating file activity
  with the incident, or when the investigation centers on what changed on
  disk and when.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
parent: disk-forensics
requires: [disk-forensics]
extends: []
relates: [timeline-basics, artifact-parsing]
tools:
  - name: The Sleuth Kit
    version: 4.12.1
  - name: Python
    version: 3.12
---

A filesystem timeline lists every timestamped filesystem event in order:
the disk's own story of what happened. This skill covers building deep
filesystem timelines from images: full extraction, smart filtering, and
reading the patterns that indicate attacker activity. It is the disk
complement to timeline-basics; where that skill merges sources, this one
goes deep on the filesystem itself.

## Quick Workflow

1. Work from the verified image with the recovered layout.
2. Extract the full filesystem timeline (body file to timeline).
3. Filter to the incident window and interesting paths.
4. Hunt the classic patterns: staging, persistence, cleanup.
5. Correlate hits with logs and memory findings.
6. Annotate and freeze the timeline for the report.

## 1. Full extraction

```bash
# Body file for the whole filesystem (or per partition with -o offset)
fls -r -m / -o <sector_offset> /analysis/case01_work.img > /tmp/body_full.txt
wc -l /tmp/body_full.txt

# Timeline in CSV for analysis
mactime -b /tmp/body_full.txt -d > /tmp/fs_timeline.csv

# Sanity: time range of the timeline
head -2 /tmp/fs_timeline.csv
cut -d',' -f1 /tmp/fs_timeline.csv | sort -u | head -3
cut -d',' -f1 /tmp/fs_timeline.csv | sort -u | tail -3
```

Full timelines are big; that is normal. The extraction is the cheap
part. The analysis discipline below is what makes it useful.

## 2. Filtering to the incident

```bash
# Window filter: the incident plus margin on both sides
awk -F',' '$1 >= "2026-10-20" && $1 <= "2026-10-23"' /tmp/fs_timeline.csv \
  > /tmp/fs_window.csv

# Path filters for the usual attacker locations
grep -E '/tmp/|/var/tmp/|/dev/shm/|/etc/cron|/etc/systemd|/root/|/home/' \
  /tmp/fs_window.csv > /tmp/fs_hot.csv

# Event focus: creations and modifications (reads are noise at scale)
grep -E ',(m| c|\.a\.)' /tmp/fs_window.csv | head -20
# (mactime codes: m modified, a accessed, c changed, b birth)
```

Filter aggressively and iteratively: window, then hot paths, then event
types. Each filter should shrink the set by an order of magnitude while
keeping the incident's shape.

## 3. Pattern hunting

```bash
# Burst analysis: what happened in the busiest minutes
cut -d',' -f1,2 /tmp/fs_window.csv | sort | uniq -c | sort -rn | head -15

# New executables in the window
grep -E '\.(sh|py|pl|elf|bin|exe)$' /tmp/fs_window.csv | head -20

# Persistence writes: startup locations touched in the window
grep -i -E 'cron|systemd|/etc/rc|Startup|Run\\' /tmp/fs_window.csv | head -20

# Cleanup signals: many deletions or timestamp clusters in one minute
grep -c 'deleted' /tmp/fs_window.csv
```

Read bursts as stories: a burst of creates in /tmp at 03:12, followed by
a cron write at 03:13, followed by deletions at 03:14, is the intrusion,
persistence, and cleanup in four lines. The timeline's job is to make
that sequence obvious.

## Edge cases

- The window is unknown. Start with the busiest anomalous periods from
  the full timeline, then widen as the story develops.
- Timestamps are unreliable (timestomping). Lean on sequence and
  correlation with logs rather than absolute times.
- The filesystem is huge. Sample the hot paths first; full review of
  millions of rows is rarely the best use of time.
- Multiple partitions and images. Build per-filesystem timelines, then
  merge with source labels; do not mix them silently.

## Escalation

- You need the super-timeline: merge this filesystem timeline with
  logs, registry, and browser artifacts into one sortable master.
- The timeline must be presented: export the annotated window as the
  report's visual centerpiece, with the key events highlighted.
- Deep dives needed per hit: hand file paths to artifact-parsing and
  PIDs to memory-forensics.

## Detection and defender view

For defenders, filesystem timelines are the post-incident microscope
and the hunting telescope: the same techniques find past intrusions and
baseline normal change patterns. FIM tools produce a live version of
this timeline for critical paths. The defender's investment is knowing
which paths matter (the hot list above) and having the timeline ready
before the incident, not after.

## Key references

- The Sleuth Kit documentation: fls, mactime.
- "File System Forensic Analysis" (timeline interpretation).
- NIST SP 800-86 (timeline analysis).
