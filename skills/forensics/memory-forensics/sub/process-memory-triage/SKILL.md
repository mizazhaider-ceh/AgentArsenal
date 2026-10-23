---
name: process-memory-triage
description: Use when you need a fast read of processes in a memory dump
  during incident triage. Covers rapid anomaly spotting, parent-child
  analysis, command-line review, and deciding what deserves deep analysis.
  Use when time is short, when prioritizing hosts in an incident, when the
  full Volatility workflow is overkill, or when answering "is this host
  compromised" quickly.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
parent: memory-forensics
requires: [memory-forensics]
extends: []
relates: [incident-response, malware-in-memory]
tools:
  - name: Volatility
    version: 2.5.2
  - name: Python
    version: 3.12
---

Process triage answers one question fast: does this memory image contain
something malicious. This skill covers the rapid pass: listing processes,
spotting the anomalies that matter, and deciding in minutes which hosts
and processes deserve the full workflow. It trades completeness for
speed deliberately; triage finds the fires, the full workflow maps the
building.

## Quick Workflow

1. List processes with parentage and command lines.
2. Flag anomalies: odd parents, odd paths, odd names.
3. Check network connections per suspicious process.
4. Review command lines for encoded or obfuscated content.
5. Decide: clean, suspicious, or compromised, with the evidence.
6. Escalate the suspicious and compromised to full analysis.

## 1. The rapid pass

```bash
V="python3 /opt/volatility3/vol.py -f /evidence/memdump.raw"

# Process tree: parent-child relationships at a glance
$V windows.pstree.PsTree 2>/dev/null | head -50

# Command lines: what each process was actually doing
$V windows.cmdline.CmdLine 2>/dev/null | head -40

# Anomalies to flag immediately:
# - explorer.exe with a non-standard parent
# - svchost.exe outside C:\Windows\System32
# - powershell/cmd with base64 (-enc, -EncodedCommand)
# - processes running from Temp, AppData, ProgramData
# - misspelled system names (svch0st, explorerr)
```

```bash
# Quick scripted anomaly flags
$V windows.pslist.PsList 2>/dev/null | grep -i -E \
  'temp|appdata|programdata|/tmp/|/dev/shm' | head -20
$V windows.cmdline.CmdLine 2>/dev/null | grep -i -E \
  'encod|frombase64|iex|downloadstring|/dev/tcp' | head -20
```

Two minutes of reading the tree with these flags catches most real
intrusions. The patterns above are what attacker tooling looks like in
memory; legitimate software rarely matches them.

## 2. Network correlation

```bash
V="python3 /opt/volatility3/vol.py -f /evidence/memdump.raw"

# Which processes hold external connections
$V windows.netstat.NetStat 2>/dev/null | grep ESTABLISHED | head -20

# Cross-reference: PID from netstat against the process list
# A powershell.exe with an external ESTABLISHED connection is the
# classic triage hit
```

A suspicious process plus an external connection is a compromised
verdict waiting for confirmation. A suspicious process with no network
may be dormant, staged, or a false positive; note the distinction.

## 3. Triage decision

```bash
# Decision template per host:
cat > /tmp/triage_host01.txt <<'EOF'
Host: WS-114, dump 2026-10-23 09:00 UTC
Anomalies:
 - powershell.exe (PID 4820) parent cmd.exe, -EncodedCommand present
 - ESTABLISHED to 203.0.113.45:443 from PID 4820
Verdict: COMPROMISED (evidence: encoded PowerShell + external C2)
Next: full volatility-workflow + malware-in-memory on PID 4820
EOF
```

Write the verdict down with the evidence, even in a fast triage. The
incident team acts on these calls; "looks bad" without the specifics
wastes the speed you gained.

## Edge cases

- Everything looks normal but the host is suspected. Triage is a fast
  pass, not a clean bill of health; say "no anomalies found in triage"
  rather than "clean."
- The dump is from a server with odd but legitimate software. Note the
  oddities as known-good after one verification, so the next triage is
  faster.
- Too many hosts to triage deeply. Triage all broadly, then full
  workflow on the hits; that is exactly what triage is for.
- Encoded command lines are legitimate admin tooling. Check the decoded
  content before verdicting; admins do use -EncodedCommand.

## Escalation

- Verdict is compromised: start containment per the incident plan and
  hand the host to the full workflow.
- Verdict is suspicious: run the full volatility-workflow on that host
  next; triage did its job by prioritizing it.
- You need the decoded payload now: base64-decode the command line and
  read it before deciding.

## Detection and defender view

For defenders, process triage is the incident response skill: the first
hour decides the scope. Building triage runbooks (the exact commands,
the anomaly flags, the verdict template) lets any analyst triage
consistently under pressure. The defender's preparation is memory
capture capability plus practiced triage; the alternative is waiting
for the full analysis while the attacker keeps working.

## Key references

- Volatility 3 2.5.2 documentation: PsList, PsTree, CmdLine, NetStat.
- MITRE ATT&CK T1059 (Command and Scripting Interpreter) for
  command-line patterns.
- NIST SP 800-61 (incident handling).
