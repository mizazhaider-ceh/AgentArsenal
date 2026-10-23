---
name: linux-log-intrusion-analysis-journalctl-forensics
description: Use when doing forensic analysis with journalctl on a Linux
  host you are authorized to investigate. Covers time-bounded queries across
  boots, filtering by unit service and priority, tracing persistence
  (timers, new units, cron), correlating service starts with intrusions,
  extracting evidence with JSON output, verifying journal integrity, and
  working from preserved copies. Defensive forensics mapped to MITRE ATT&CK
  T1543, T1053, and T1070.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-log-intrusion-analysis]
extends: []
parent: linux-log-intrusion-analysis
relates: [linux-log-intrusion-analysis, linux-systemd-security, linux-log-intrusion-analysis-auth-log-triage]
tools:
  - name: systemd
    version: 255
  - name: auditd
    version: 3.1
  - name: Python
    version: 3.12
---

The systemd journal records what the system did: which services started, which timers fired, which sessions opened, and what the kernel saw. In forensics, it answers the questions auth logs cannot: what ran, when, and in what order. This sub-skill covers the defensive analyst's journalctl method: scoping queries by time and boot, filtering by unit and priority, hunting persistence artifacts, extracting evidence cleanly, and verifying the journal has not been tampered with. For hosts you are authorized to investigate; defensive only. The parent skill sets the investigation strategy; this file is the journalctl field manual.

## Quick Workflow

1. Establish journal coverage: list boots, check storage mode, note the earliest entry.
2. Verify integrity before trusting anything: `journalctl --verify` and collector comparison.
3. Scope queries to the incident window with `--since`/`--until` and to the relevant boot with `-b`.
4. Hunt persistence: new units, timer firings, cron activity, and service starts in the window.
5. Correlate execution: session openings, privilege changes, and kernel events around each suspicious start.
6. Extract evidence with stable output options (`-o short-precise`, `--no-pager`, JSON export) into the case directory.
7. Document every query and its result so the analysis is reproducible.

## 1. Establishing coverage and integrity

Before analysis, know what the journal contains and whether it is trustworthy. A volatile journal or a tampered one changes everything about the investigation.

```bash
journalctl --list-boots --no-pager | head -10
journalctl --disk-usage
journalctl --verify 2>&1 | tail -5
```

Example output shape: boot list with IDs and time ranges (gaps in the sequence are significant), disk usage showing whether retention policy held, and verify output reporting seal status. If `--list-boots` misses boots you expect, or `--verify` reports failures, record the integrity verdict before proceeding: findings built on a tampered journal need collector corroboration for every claim.

## 2. Time-bounded and boot-scoped queries

Unbounded journal queries on a busy host return noise. Scope ruthlessly: incident window first, then the specific boot.

```bash
journalctl --since "2026-10-22 18:00" --until "2026-10-23 06:00" --no-pager -o short-precise | head -30
journalctl -b -1 --no-pager -p warning | head -20
journalctl -b 0 -u sshd.service --no-pager | tail -20
```

`-b -1` selects the previous boot (critical when the incident spans a reboot, which intrusions often do to activate persistence). `-o short-precise` gives microsecond timestamps for ordering events that log within the same second. Always record the exact query with each evidence excerpt; "journalctl showed X" is not reproducible, the full command line is.

## 3. Hunting persistence in the journal

Persistence mechanisms announce themselves in the journal when they activate: units starting, timers firing, cron running jobs. Hunt the window for what should not be there.

```bash
journalctl --since "2026-10-22 00:00" --no-pager | grep -iE "started.*\.service|starting.*\.service" | grep -viE "systemd|dbus|network|sshd|cron\.service" | head -20
journalctl -u cron.service --no-pager --since "2026-10-22 00:00" | grep -iE "CMD|RELOAD" | head -20
journalctl --no-pager | grep -iE "\.timer" | tail -20
```

Example output shape: service starts outside the known set, cron job executions with command lines, timer activations. For each unknown service start, pull the unit definition (`systemctl cat`) and check its ExecStart paths for writability and legitimacy. A timer firing an unknown unit at 03:00, or cron executing a base64 blob, goes straight into the timeline as suspected persistence.

## 4. Correlating sessions, privilege, and kernel events

Execution leaves a multi-source trail. Tie session openings to what ran inside them and to kernel-level observations.

```bash
journalctl --since "2026-10-22 18:00" --no-pager | grep -iE "new session|session opened|pam_unix.*session" | head -15
journalctl -k --since "2026-10-22 18:00" --no-pager -p warning | head -15
journalctl --since "2026-10-22 18:00" --no-pager | grep -iE "sudo:.*COMMAND|useradd|passwd.*changed" | head -15
```

Example output shape: session IDs with owning users and times, kernel warnings (module loads, OOM kills, audit denials), and privilege/account events. Correlate by timestamp: a new session at 02:14, a module load at 02:15, and a new unit start at 02:16 is a story, not three facts. Kernel module loads outside maintenance windows deserve special attention as possible rootkit activity.

## 5. Evidence extraction and structured output

Evidence must be stable, complete, and attributable. Use output modes designed for it, and export to the case directory.

```bash
journalctl --since "2026-10-22 18:00" --until "2026-10-23 06:00" -o export > /root/ir-evidence/journal-window.export
journalctl -b -1 -p err -o json-pretty > /root/ir-evidence/journal-prevboot-err.json 2>/dev/null
journalctl --no-pager -o short-precise -u sshd.service --since "2026-10-22 00:00" > /root/ir-evidence/sshd-window.log
```

`-o export` preserves all fields including cursor and monotonic timestamps; JSON output feeds timeline tooling. For each export, record the command, the hostname, the journal's boot ID, and a hash of the file (`sha256sum`), so the evidence chain is intact. Analyze from these exports rather than re-querying the live journal, which keeps the analysis reproducible even if the live logs rotate.

## Edge cases

- The journal may be volatile (`Storage=volatile`) or absent entirely on minimal images; in that case pivot immediately to rsyslog files, the central collector, and auditd logs, and record the journal gap as a visibility finding.
- `--verify` requires the sealing key setup to mean much; without FSS, verification only checks structural integrity, so pair it with collector comparison for real tamper detection.
- Huge journals make full-window greps slow; prefer `-u` unit filters and `-p` priority filters to narrow before grepping, and use `--since`/`--until` aggressively.
- Corrupted journal files (from crashes or tampering) cause journalctl to stop reading at the corruption point; `journalctl --verify` identifies the bad file, and the readable portion is still evidence, so extract what is readable and note the boundary.
- Timezone handling: journalctl displays local time by default; use `--utc` when correlating with UTC sources, and document which you used, because mixed-timezone timelines create false ordering.
- Services that log to their own files instead of the journal (databases, some daemons with `StandardOutput=file`) leave journal gaps that look like inactivity; know each critical service's logging path before concluding nothing happened.
- `journalctl -b -1` fails if the previous boot's journal was not persisted; check `--list-boots` first rather than assuming the boot exists.

## Escalation

- If the journal shows signs of tampering (verify failures, collector mismatches, missing boots), escalate to full incident response: the adversary is actively doing Indicator Removal and the timeline must be rebuilt from off-host sources.
- If persistence artifacts are confirmed (unknown units, timers, cron jobs), escalate for containment before cleanup: understand the full persistence set first, because removing one mechanism while another remains just re-infects.
- If kernel module loads or suspicious driver activity appears, escalate for memory forensics consideration: rootkits hide from disk and log analysis, and the decision to take a memory image is time-sensitive.
- If the journal window does not cover the incident, escalate the visibility gap and pivot the investigation to network logs, EDR telemetry, and the central collector rather than declaring the host clean.

## Detection and defender view

Journal forensics is the deep-dive form of a continuous detection practice. Defenders run the same hunts on a schedule: new unit starts, timer activations outside the known set, session anomalies, and kernel warnings, all baselined against normal. MITRE T1543/T1053 (persistence via system processes and scheduled tasks) are what the persistence hunts detect; T1070 (Indicator Removal) is what the integrity checks counter. The journal's value as evidence depends entirely on the hardening in the journal-security sub-skill: persistent storage, sealing, and central forwarding turn journalctl from a convenience tool into a forensic instrument. Alert on journal gaps and verification failures as detection events in their own right, not just as investigation prerequisites.

## Key references

- MITRE ATT&CK T1543 Create or Modify System Process: https://attack.mitre.org/techniques/T1543/
- MITRE ATT&CK T1053 Scheduled Task/Job: https://attack.mitre.org/techniques/T1053/
- MITRE ATT&CK T1070 Indicator Removal: https://attack.mitre.org/techniques/T1070/
- journalctl manual: https://www.freedesktop.org/software/systemd/man/journalctl.html
- systemd.journal-fields manual: https://www.freedesktop.org/software/systemd/man/systemd.journal-fields.html
- NIST SP 800-92 Guide to Computer Security Log Management: https://csrc.nist.gov/publications/detail/sp/800-92/final
