---
name: linux-log-intrusion-analysis
description: Use when investigating a Linux host for signs of intrusion using
  its logs, in a defensive incident response or threat hunting role. Covers
  the triage workflow (scope, timeline, indicators), auth log analysis for
  brute force and account abuse, journalctl forensics across boots and
  units, detecting lateral movement in SSH and audit trails, log integrity
  checks, and mapping findings to MITRE ATT&CK. Defensive only, covering analysis of
  systems you are authorized to investigate.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening, linux-hardening-baseline, linux-systemd-security, linux-log-intrusion-analysis]
tools:
  - name: systemd
    version: 255
  - name: auditd
    version: 3.1
  - name: Python
    version: 3.12
---

When something is wrong on a Linux host, the logs are the witness: authentication logs show who knocked and who got in, the journal shows what the system did, and audit trails show what processes touched. This parent skill covers the defensive workflow for log-based intrusion analysis: how to scope an investigation, build a timeline, triage auth logs, do journal forensics, spot lateral movement, and verify the logs themselves have not been tampered with. Everything here is defensive analysis of systems you are authorized to investigate, typically during incident response or threat hunting. The sub-skills go deep on auth log triage, journalctl forensics, and lateral movement detection; this file is the investigation strategy.

## Quick Workflow

1. Scope the investigation: which hosts, what time window, what triggered it (alert, user report, anomaly).
2. Preserve evidence first: snapshot logs and journal files before analysis alters access times or triggers rotation.
3. Check log integrity: journal seals, collector comparison, unexpected gaps or rotations.
4. Build a timeline: authentication events, new processes, privilege changes, network connections, ordered by time.
5. Triage auth logs for brute force, valid-account abuse, and impossible patterns (see auth-log-triage sub-skill).
6. Do journal forensics across boots and units for persistence and execution traces (see journalctl-forensics sub-skill).
7. Hunt lateral movement: SSH chains, new keys, credential use across hosts (see detecting-lateral-movement sub-skill).
8. Write findings with timestamps, log excerpts, ATT&CK mappings, and confidence levels.

## 1. Scoping and evidence preservation

An investigation without a scope becomes a fishing expedition; analysis without preservation destroys the evidence it needs. Define the window from the first indicator, then copy (not move) the relevant logs to an analysis location.

```bash
ls -lat /var/log/auth.log* /var/log/secure* 2>/dev/null | head -10
journalctl --list-boots | head -10
mkdir -p /root/ir-evidence && cp -a /var/log/auth.log* /root/ir-evidence/ 2>/dev/null
```

Example output shape: log rotation dates bounding your available history, boot list showing whether the suspect window is covered, and a preserved copy with original timestamps (`cp -a`). Note the earliest available log timestamp immediately: if the incident window predates your logs, say so up front rather than discovering it mid-investigation. Work from copies where possible; every read of a live log is fine, but avoid actions that rotate or truncate.

## 2. Log integrity: trust but verify

Attackers clean logs (MITRE T1070), so the first analytical step is asking whether the witness is reliable. Check journal seals, compare against the central collector, and look for gaps.

```bash
journalctl --verify 2>&1 | tail -5
journalctl --list-boots --no-pager | wc -l
last -x 2>/dev/null | head -10
```

Red flags: seal verification failures, boots missing from the expected sequence, `wtmp`/`btmp` entries inconsistent with auth logs, and log files smaller than rotation policy predicts. If the local logs disagree with the central collector, trust the collector and treat the local gap as a finding in itself. Document the integrity verdict for every log source you rely on; a timeline built on tampered logs is worse than no timeline.

## 3. Building the incident timeline

A timeline turns scattered events into a story: initial access, execution, persistence, lateral movement. Pull the key event types into one chronological view.

```bash
journalctl --since "2026-10-20" --until "2026-10-23" -p info --no-pager -o short-precise 2>/dev/null | grep -iE "sshd|sudo|useradd|cron|systemd.*(start|enable)" | head -30
```

Correlate across sources: auth logs (who authenticated), journal (what services started), auditd (what processes executed what), and file timestamps (what changed). A typical intrusion timeline reads: brute force or valid-account login, then a new user or key added, then a persistence mechanism (cron, timer, unit), then outbound connections or lateral SSH. Write each timeline entry with timestamp, source, event, and confidence; mark inferred entries as inferred.

## 4. Auth log triage at a glance

Authentication logs answer the highest-value questions fastest: was there brute force, did any of it succeed, and were legitimate accounts abused? The full method is in the auth-log-triage sub-skill; the parent-level pass is:

```bash
grep -c "Failed password" /var/log/auth.log 2>/dev/null
grep "Accepted" /var/log/auth.log 2>/dev/null | awk '{print $1, $2, $3, $9, $11}' | sort | uniq -c | sort -rn | head -15
grep -iE "invalid user|authentication failure" /var/log/auth.log 2>/dev/null | wc -l
```

Example output shape: failure counts (reconnaissance volume), accepted logins by time/user/source (the sessions that matter), and invalid-user attempts (username enumeration). Any `Accepted` outside expected users, hours, or source networks becomes a timeline anchor to investigate. One successful login from an unusual source outweighs ten thousand failed guesses.

## 5. Journal forensics at a glance

The journal shows system behavior around the suspect window: service starts, timer firings, kernel messages, and unit changes. The full method is in the journalctl-forensics sub-skill; the parent-level pass is:

```bash
journalctl -b -p warning --no-pager 2>/dev/null | head -20
journalctl --since "2026-10-22 00:00" --no-pager -o short 2>/dev/null | grep -iE "started|enabled|failed.*service|new session" | head -20
```

Look for: services starting that should not exist, timers firing unknown units, new user sessions at odd hours, and kernel warnings (OOM kills hiding activity, module loads). Cross-reference every suspicious service start with the unit audit from the systemd security skills: an unknown unit that started at 03:00 is persistence until proven otherwise.

## 6. Lateral movement at a glance

Intruders rarely stop at one host. Look for the signs of movement: SSH from this host to others, new authorized keys, credential material accessed, and connections to internal hosts outside normal patterns. Full method in the detecting-lateral-movement sub-skill.

```bash
grep -E "Accepted.*sshd" /var/log/auth.log 2>/dev/null | awk '{print $(NF-2)}' | sort | uniq -c | sort -rn | head -10
ls -lat ~/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null
ss -tnp 2>/dev/null | grep ESTAB | head -15
```

Example output shape: accepted-login source IPs (unexpected internal sources suggest pivoting), recently modified authorized_keys files (new keys are persistence), and current established connections (unexpected internal peers). Treat every internal connection the host's role does not explain as a lead, not as noise.

## Edge cases

- Log volume on busy hosts makes naive grepping slow and misleading; use time-bounded queries (`--since`/`--until`) and aggregate (counts by hour, by source) before reading individual lines, or you will miss patterns in the noise.
- Timezone and clock issues corrupt timelines: verify NTP health and note the timezone of every source, because correlating logs with skewed clocks produces false sequences that look like attacks.
- Attackers may log nothing if they used existing valid credentials quietly; absence of brute force does not mean absence of intrusion, so also hunt for behavioral anomalies (new keys, new persistence, odd hours) rather than only failed logins.
- Log rotation can delete the evidence mid-investigation; the preservation step exists for this reason, and on long-running incidents, arrange log shipping to hold the window open.
- Containers and orchestrated workloads log differently (stdout to the runtime, not the host journal); know where each workload's logs actually land before concluding a host is clean.
- Encrypted or obfuscated payloads in logs (base64 blobs in cron commands, encoded PowerShell-style invocations) need decoding before judging; do not dismiss what you have not decoded.
- Multiple analysts touching live logs can contaminate access times and trigger rotations; coordinate a single evidence collection, then analyze from copies.

## Escalation

- If integrity checks fail (seal failures, collector gaps, missing boots), escalate to full incident response immediately: you are likely looking at an active adversary doing Indicator Removal, not a logging bug.
- If the timeline shows successful authentication from unknown sources, escalate for credential containment: rotate the affected credentials and hunt the same indicators across the fleet before the trail cools.
- If lateral movement indicators appear, widen the scope to the connected hosts now, not after finishing this host; intruders move faster than sequential investigations.
- If the available log window does not cover the suspected intrusion start, escalate the visibility gap itself as a finding: the investigation is bounded by evidence, and the business needs to know what cannot be answered.

## Detection and defender view

Log intrusion analysis is where the defensive skills converge: hardening (baselines) reduces noise, systemd security (unit audits, journal integrity) protects the evidence, and this skill consumes it all. MITRE ATT&CK mappings run through the whole intrusion chain: T1110/T1078 for initial access, T1053/T1543 for persistence, T1070 for defense evasion, T1021/T1080-adjacent movement for lateral spread. The defender's posture is continuous rather than incident-only: the same queries run as scheduled hunts, baselined against normal, so that an incident investigation starts from "what changed" instead of from zero. Centralized, tamper-evident logging is the foundation; everything in this skill assumes it and degrades without it.

## Key references

- MITRE ATT&CK enterprise matrix: https://attack.mitre.org/
- MITRE ATT&CK T1070 Indicator Removal: https://attack.mitre.org/techniques/T1070/
- MITRE ATT&CK T1021 Remote Services: https://attack.mitre.org/techniques/T1021/
- journalctl manual: https://www.freedesktop.org/software/systemd/man/journalctl.html
- Linux auditd documentation: https://github.com/linux-audit/audit-documentation
- NIST SP 800-92 Guide to Computer Security Log Management: https://csrc.nist.gov/publications/detail/sp/800-92/final
