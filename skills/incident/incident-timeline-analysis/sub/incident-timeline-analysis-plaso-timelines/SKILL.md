---
name: incident-timeline-analysis-plaso-timelines
description: Use when you need to build forensic timelines from disk
  images or log collections during an authorized investigation. Covers
  running log2timeline.py from Plaso 20241006 with the right parsers,
  managing storage files, inspecting output with pinfo.py, filtering
  with psort.py, exporting to CSV and other formats, and handling
  large timelines without running out of memory or patience. Use when
  the parent incident-timeline-analysis workflow needs a concrete
  timeline built, when triaging a disk image for file activity, or
  when extracting browser, registry, or log artifacts at scale, with
  Python helpers for batch exports.
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
---

Plaso (log2timeline) parses forensic artifacts into a single
timestamped event store: file system metadata, logs, browser
history, registry hives, and dozens more. This sub-skill is the
operator's guide: installation notes, parser selection, storage
handling, psort filtering, and the performance practices that keep
large cases moving. Authorized investigations on your own evidence
only.

## Quick Workflow

1. Confirm Plaso is installed and note the version for the case.
2. Choose the input: disk image, mounted image, or log directory.
3. Select parsers: start broad, then narrow for the second pass.
4. Run log2timeline.py into a named storage file per host.
5. Inspect with pinfo.py: event counts, time range, parser stats.
6. Filter with psort.py to the incident window and export CSV.
7. Iterate: add parsers or narrow filters based on what you find.
8. Archive the storage file with the case; it is re-queryable.

## 1. Running log2timeline

```bash
# From a disk image (read-only handling is your responsibility)
log2timeline.py --storage-file web-03.plaso /evidence/INC-2026-1042/disk-sda.img

# From a directory of collected logs and artifacts
log2timeline.py --storage-file logs.plaso /evidence/INC-2026-1042/logs/

# With a specific parser set for a focused second pass
log2timeline.py --parsers syslog,apache_access,chrome_history \
  --storage-file web-03-focused.plaso /evidence/INC-2026-1042/disk-sda.img

# Workers: scale to the machine, but watch memory
log2timeline.py --workers 4 --storage-file web-03.plaso /evidence/INC-2026-1042/disk-sda.img
```

Example console output shape:

```
[INFO] log2timeline version 20241006
[INFO] Source: /evidence/INC-2026-1042/disk-sda.img
[INFO] Processing completed: 184,203 events in 00:14:32
[INFO] Storage file: web-03.plaso (412 MB)
```

One storage file per host keeps cases manageable; merging happens
at psort time. Name files `hostname.plaso` so a year from now the
archive still makes sense.

## 2. Inspecting with pinfo

```bash
pinfo.py web-03.plaso
```

Example output shape:

```
Plaso storage file: web-03.plaso
Events: 184,203
First event: 2026-10-18 06:12:44.000000 UTC
Last event: 2026-10-23 09:41:02.000000 UTC
Parsers:
  filestat: 142,010
  syslog: 28,442
  apache_access: 8,911
  chrome_history: 3,102
  ...
```

Sanity checks: the time range should cover your incident window;
if the first event is after the suspected intrusion, you are
missing history (image too new, logs rotated). Parser counts tell
you what you have to work with; zero syslog events on a Linux web
server means the logs did not survive.

## 3. Filtering and exporting with psort

```bash
# Incident window to CSV, UTC
psort.py -o csv --slice "2026-10-20 00:00:00" "2026-10-23 12:00:00" \
  -w incident-window.csv web-03.plaso

# Filter language: parser, message content, timestamps
psort.py -o csv -w ssh-events.csv \
  --filter "parser is 'syslog' and message contains 'sshd'" web-03.plaso

# File writes in /tmp during the window (staging detection)
psort.py -o csv -w tmp-writes.csv \
  --filter "parser is 'filestat' and filename contains '/tmp' and timestamp_desc contains 'Content Modification'" \
  web-03.plaso

# Deduplicated, sorted output for the super-timeline
psort.py -o csv -w web-03-clean.csv --dedup web-03.plaso
```

psort filter examples worth keeping in the runbook:

```
# Authentication events across common parsers
parser is 'syslog' and (message contains 'Accepted' or message contains 'Failed')

# Browser downloads
parser is 'chrome_history' and message contains 'Download'

# USB device connections (Linux)
parser is 'syslog' and message contains 'USB'
```

## 4. Merging hosts and feeding Timesketch

```bash
# One CSV per host, then concatenate for the super-timeline
psort.py -o csv -w web-03-clean.csv --dedup web-03.plaso
psort.py -o csv -w ws-11-clean.csv --dedup ws-11.plaso
head -1 web-03-clean.csv > super.csv
tail -n +2 -q web-03-clean.csv ws-11-clean.csv >> super.csv

# Import into Timesketch for collaborative analysis
# (Timesketch web UI: create sketch > upload super.csv)
```

Timesketch turns the flat CSV into a searchable, annotatable
timeline the whole team can work. Upload per-host CSVs as separate
timelines in one sketch to keep the source straight.

## 5. Performance practices

- Run log2timeline on the evidence copy, never the original.
- Start with default parsers on the full image, then run focused
  parser passes into separate storage files; re-parsing everything
  for one new parser wastes hours.
- `--workers` helps up to the disk's throughput; beyond that it
  just burns memory. Watch `htop` on the first run and tune.
- Storage files grow large (hundreds of MB per host). Keep them;
  re-running log2timeline costs more than disk space.
- For very large cases, slice by time at psort and archive the
  window CSVs alongside the full storage file.

## Edge cases

- log2timeline fails on a corrupt image region. Use
  `--partition` to target specific partitions, or image the
  readable regions and note the gap.
- Zero events from a parser you expected. The artifact may be
  absent (logs wiped), the parser name may be wrong (check
  `log2timeline.py --info`), or the file may be a format variant
  the parser does not handle.
- Timestamps far in the future or past (year 2080, year 1970).
  Filesystem timestamp corruption is common on failing disks;
  filter the absurd range out and note it.
- The storage file is corrupt after an interrupted run. Delete
  and re-run; partial storage files are not repairable.
- Memory exhaustion on huge images. Reduce workers, process
  partitions separately, or move to a bigger analysis host;
  do not `--workers 32` a laptop and hope.
- Encrypted volumes. Decrypt with the recovered key first (see
  evidence preservation); Plaso cannot parse ciphertext.

## Escalation

- The timeline shows the intrusion predates all available
  history. Escalate the retention gap as a finding and check
  backups or archives for older copies.
- Parser output suggests anti-forensics (timestomping: clusters
  of identical unlikely timestamps). Escalate to the forensics
  lead; timestomping analysis is a specialty.
- The case needs timelines from dozens of hosts. Script the
  log2timeline runs, parallelize across analysis hosts, and
  track completion in the case file; do not run them by hand.
- Results will go to legal. Freeze the Plaso version, the exact
  commands, and the storage files; reproducibility is the
  requirement.

## Detection and defender view

Plaso timelines are how defenders see what the attacker did after
the fact, which is why attackers target the underlying artifacts:
log deletion, timestomping, and wiping shell history. The defense
is layered: centralize logs beyond the attacker's reach, protect
filesystem metadata with integrity monitoring, and keep retention
longer than your detection time. Every timeline gap you hit in an
investigation becomes a detection engineering task for peacetime.

## Key references

- Plaso documentation: https://plaso.readthedocs.io/
- Parser list and filter language:
  https://plaso.readthedocs.io/en/latest/sources/user/Parsers-and-plugins.html
- Timesketch: https://timesketch.org/
- Parent workflow: incident-timeline-analysis (this repo)
- NIST SP 800-86: https://csrc.nist.gov/publications/detail/sp/800-86/final
