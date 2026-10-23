---
name: log-forensics
description: Use when reconstructing an incident from system and application
  logs you are authorized to analyze. Covers Linux journald and syslog, JSON
  log filtering with jq, Windows EVTX triage, authentication log hunting for
  brute force and lateral movement, detecting log tampering and gaps, and
  building a cross-source timeline. Use when you need to prove who did what
  and when, or when a host's own logs disagree with each other.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [forensics-fundamentals, incident-response]
tools:
  - name: systemd
    version: 257
  - name: jq
    version: 1.8.1
  - name: ripgrep
    version: 14.1.1
---

Logs are the narrative layer of an investigation: they say who authenticated,
what ran, and what the system thought was happening. They are also the first
thing a competent attacker tries to silence, so log forensics is equal parts
reading and distrusting. This skill covers Linux journald/syslog triage, JSON
log filtering with jq, Windows EVTX basics, hunting authentication anomalies,
spotting tampering and coverage gaps, and merging sources into one timeline.
Scope: analyze logs from systems you are authorized to investigate, and treat
log contents as sensitive (they hold usernames, IPs, and sometimes secrets).
Never assume a log is complete; always check what is missing.

## Quick Workflow

1. Inventory the log sources available (journald, syslog files, auth logs,
   application logs, EVTX) and their time ranges.
2. Normalize to one timezone (UTC) before comparing anything.
3. Hunt authentication events: failures, successes at odd hours, new users,
   privilege changes.
4. Hunt execution events: new services, cron jobs, scheduled tasks, suspicious
   child processes.
5. Check log integrity: gaps, truncation, cleared logs, and time jumps.
6. Filter structured (JSON) logs with jq for IOCs and error patterns.
7. Corroborate across sources: the same event should appear in two places.
8. Build a merged timeline of the incident window.

## 1. Linux: journald and syslog triage

journald is the first stop on modern Linux. Query it with time bounds and
output formats that survive piping.

```bash
# Everything since yesterday, short format, no pager
journalctl --since "yesterday" --no-pager | head -100

# One service only, with UTC timestamps
journalctl -u sshd --since "2026-10-22" --until "2026-10-23" -o short-utc --no-pager | head -100

# JSON output for jq filtering
journalctl -u sshd -o json --no-pager > sshd.json

# Failed SSH logins grouped by source IP
journalctl -u sshd -o json --no-pager | jq -r 'select(.MESSAGE | test("Failed password")) | ._SOURCE_REALTIME_TIMESTAMP' | wc -l
journalctl -u sshd --no-pager | grep -oE 'Failed password.*from [0-9.]+' | grep -oE '[0-9.]+$' | sort | uniq -c | sort -rn | head -20

# Successful logins: who, from where, when
journalctl -u sshd --no-pager | grep -E 'Accepted (password|publickey)' | head -20

# Classic syslog files when journald is not the source of truth
ls -lt /var/log/auth.log* /var/log/secure* 2>/dev/null
grep -E 'Failed|failure' /var/log/auth.log | tail -40
```

Also check `cron` logs (`/var/log/cron`, or `journalctl -u cron`), because
persistence via cron is quiet and common. A cron entry that appeared the
night of the incident is worth more than a week of SSH noise.

```bash
journalctl -u cron --since "2026-10-22" --no-pager | grep -v -E 'pam_unix|session' | head -30
grep -r . /etc/cron* /var/spool/cron/ 2>/dev/null | grep -v '^Binary'
```

## 2. JSON logs with jq

Modern apps and forwarders emit JSON. jq turns a million-line blob into
answers in seconds. Learn five patterns and you cover most cases.

```bash
# Pretty-print one record to learn the schema
head -c 2000 app.json | jq .

# Filter by field value, print selected fields
jq -r 'select(.level == "error") | "\(.timestamp) \(.msg)"' app.json | head -20

# Count events per source IP, top talkers first
jq -r '.client_ip // .src_ip // empty' app.json | sort | uniq -c | sort -rn | head -20

# Time window filter (ISO 8601 timestamps)
jq -r 'select(.timestamp >= "2026-10-22T02:00:00Z" and .timestamp <= "2026-10-22T04:00:00Z")' app.json | head -20

# Rare values: things that appear once are often the interesting things
jq -r '.user_agent' app.json | sort | uniq -c | sort -n | head -20

# Nested fields and arrays
jq -r 'select(.request.path | test("admin")) | "\(.timestamp) \(.request.method) \(.request.path) \(.response.status)"' app.json | head -30
```

When a field is missing on some records, use `// empty` or `?` so jq does
not abort mid-file. For multi-GB files, prefer `jq -c` streaming patterns or
split the file first; jq loads the whole input for non-streaming filters.

## 3. Windows EVTX triage

Windows logs live in EVTX files under `C:\Windows\System32\winevt\Logs`.
Copy them off the image (see disk-forensics), then parse.

```bash
# List the logs available on the image
ls -lh /mnt/image/Windows/System32/winevt/Logs/ | head -30

# Parse Security.evtx to XML/JSON with an EVTX parser
# (python-evtx or evtx_dump style tools; output to text for grepping)
evtx_dump.py /mnt/image/Windows/System32/winevt/Logs/Security.evtx > security.xml

# Key Security event IDs to hunt
grep -E 'EventID>4625<' security.xml | wc -l   # failed logons
grep -E 'EventID>4624<' security.xml | wc -l   # successful logons
grep -E 'EventID>4672<' security.xml | wc -l   # special privileges (admin logon)
grep -E 'EventID>4720<' security.xml | wc -l   # user account created
grep -E 'EventID>4732<' security.xml | wc -l   # member added to group
grep -E 'EventID>7045<' security.xml | wc -l   # service installed (in System.evtx)

# Extract logon type and source IP from 4624 events
grep -A5 'EventID>4624<' security.xml | grep -E 'LogonType|IpAddress|TargetUserName' | head -30

# PowerShell operational log: script blocks (4104) are the gold
evtx_dump.py /mnt/image/Windows/System32/winevt/Logs/Microsoft-Windows-PowerShell%4Operational.evtx > ps.xml
grep -E 'EventID>4104<' ps.xml | wc -l
```

Cross-check Security.evtx against the System log: a service installed
(System 7045) with no matching 4624/4672 logon nearby suggests the installer
ran as SYSTEM, which points at an existing privileged foothold.

## 4. Detecting log tampering and gaps

An attacker who clears logs leaves a different-shaped hole than rotation
does. Learn to tell them apart.

```bash
# journald: check for gaps and the earliest available entry
journalctl --list-boots
journalctl -o short-utc --no-pager | head -3
journalctl -o short-utc --no-pager | tail -3

# Sudden truncation: file shrank or starts mid-rotation unexpectedly
ls -l /var/log/auth.log* /var/log/syslog*
# Compare against logrotate config: is this rotation schedule or deletion?
grep -A5 'auth.log' /etc/logrotate.d/rsyslog 2>/dev/null

# Windows: event ID 1102 (audit log cleared) and 104 (log cleared)
grep -E 'EventID>(1102|104)<' security.xml system.xml | head

# Time jumps: clock changes that break timeline order
journalctl -o short-utc --no-pager | awk '{print $1, $2}' | uniq -c | awk '$1 > 1000' | head

# Forwarded copies: if logs ship to a SIEM, compare counts
# local count vs SIEM count for the incident window; a local-only deficit
# means local tampering after forwarding
```

Document gaps explicitly: "auth.log covers 2026-10-20 to 2026-10-22 03:14,
then nothing until 2026-10-22 09:02; logrotate shows weekly rotation, so this
gap is unexplained." An unexplained gap is itself evidence.

## 5. Merging sources into one timeline

One timezone, one format, one sorted file. Everything else is decoration.

```bash
# Normalize journald to epoch, then to ISO UTC
journalctl -o json --no-pager | jq -r '"\(._SOURCE_REALTIME_TIMESTAMP | tonumber / 1000000 | strftime("%Y-%m-%dT%H:%M:%SZ")) journald \(.MESSAGE)"' > t_journal.txt

# Syslog lines already carry timestamps; convert and tag
awk '{print $1"T"$2"Z syslog "$0}' /var/log/auth.log > t_syslog.txt 2>/dev/null

# Merge and sort
sort -m t_journal.txt t_syslog.txt > merged_timeline.txt

# Slice the incident window
awk '$1 >= "2026-10-22T02:00:00Z" && $1 <= "2026-10-22T04:00:00Z"' merged_timeline.txt | head -100
```

For serious cases use a proper timeline tool, but this 10-line version is
enough to test a hypothesis before you commit to heavy tooling. Always note
which sources fed the timeline and their clock confidence.

## Edge cases

- Logs are in a non-UTC timezone with no offset recorded: establish the
  offset from a known event (a reboot, a scheduled job) before comparing
  against UTC sources, and document the assumption.
- journald is volatile (Storage=volatile): logs exist only in RAM and are
  gone after reboot. Check `/etc/systemd/journald.conf` and the presence of
  `/var/log/journal/` to know what you should have had.
- Compressed rotated logs (`.gz`): use `zgrep`/`zcat`, and remember rotation
  order when reconstructing a sequence across files.
- EVTX files are corrupt or partially overwritten: parse what you can and
  note the record count vs expected; a parser that stops early is not proof
  the rest is empty.
- Application logs with no timestamps: correlate by sequence against a
  timestamped source, or treat ordering as unreliable.
- Clock skew between hosts: a 5-minute skew turns "A caused B" into "B
  caused A". NTP status (`timedatectl`, `w32tm /query /status`) is part of
  every log case.

## Escalation

- Local logs are destroyed: pivot to forwarded copies (SIEM, syslog server,
  cloud audit trails like CloudTrail or Entra sign-in logs) which the
  attacker could not reach.
- No central logging exists: rebuild activity from non-log sources, such as
  filesystem timelines (disk-forensics), memory artifacts
  (memory-forensics), firewall and proxy logs, and DHCP lease history.
- JSON logs are too large for jq: pre-filter with ripgrep on the raw text
  (`rg -a 'pattern' huge.json`), then jq only the matching lines.
- Need to prove a negative (user X never logged in): document the complete
  log coverage for the window first; absence of evidence is only meaningful
  when the coverage is complete and untampered.
- Encrypted or access-controlled log stores: get the keys through the proper
  case authority, never by attacking the store.

## Detection and defender view

From the defender side, logs are both the detection surface and the target.
Build detections on the events this skill hunts: impossible-travel logons,
first-time admin privilege use (Windows 4672), service installations outside
change windows (7045), and cron or scheduled-task creation on servers that
should be static. Just as important, detect log tampering itself: alert on
Windows event IDs 1102 and 104, on journald or syslog daemons stopping
unexpectedly, and on forwarding pipeline failures, because a blind SIEM is
worse than no SIEM. The misuse case is reading logs beyond your
authorization: logs contain credentials in cleartext more often than anyone
admits, so scope access, mask secrets in reports, and never copy full logs to
personal machines.

## Key references

- MITRE ATT&CK T1070.001 (Clear Windows Event Logs) and T1070.002 (Clear
  Linux or Mac System Logs): the tampering this skill detects.
- MITRE ATT&CK T1110 (Brute Force): the auth-log hunting pattern.
- MITRE ATT&CK T1053 (Scheduled Task/Job): cron, at, and Task Scheduler
  persistence in logs.
- MITRE ATT&CK T1036 (Masquerading): log entries that lie about their
  source.
- CWE-778 (Insufficient Logging): the defensive gap to close.
- CWE-117 (Improper Output Neutralization for Logs): log injection and
  forgery.
- journalctl manual: https://www.freedesktop.org/software/systemd/man/latest/journalctl.html
- jq manual: https://jqlang.github.io/jq/manual/
