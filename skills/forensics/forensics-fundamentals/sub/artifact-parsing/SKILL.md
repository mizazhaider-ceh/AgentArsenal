---
name: artifact-parsing
description: "Use when extracting meaning from specific forensic artifacts: browser history, registry hives, event logs, and application data. Covers locating artifacts on disk images, parsing them with standard tools, and correlating artifact contents. Use when the timeline needs detail, when investigating user activity, when hunting persistence mechanisms, or when an artifact holds the answer a log does not."
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
parent: forensics-fundamentals
requires: [forensics-fundamentals]
extends: []
relates: [disk-forensics, memory-forensics]
tools:
  - name: Python
    version: 3.12
  - name: The Sleuth Kit
    version: 4.12.1
---
Artifacts are the structured traces applications leave: browser history
databases, registry hives, event logs, jump lists. This skill covers
finding and parsing the high-value artifacts on disk images: where they
live, which tools read them, and what questions each answers. Artifacts
give you user intent where timelines give you sequence; together they
reconstruct the incident.

## Quick Workflow

1. Identify the OS and the artifacts it produces.
2. Extract the artifact files from the image to your analysis copy.
3. Parse each with the right tool; never hand-read binary formats.
4. Correlate artifact contents with the timeline.
5. Answer the investigation's specific questions from the artifacts.
6. Document the artifact path, tool, and interpretation.

## 1. Windows artifacts

```bash
# Extract hives and event logs from the image (TSK icat by inode,
# or mount read-only and copy)
# Key paths on the image:
# C:\Windows\System32\config\SYSTEM, SOFTWARE, SECURITY, SAM
# C:\Windows\System32\winevt\Logs\Security.evtx, System.evtx
# C:\Users\<u>\NTUSER.DAT, UsrClass.dat

# Registry: recent docs, run keys, USB history (parse with a registry tool)
# Python registry parsing (or use an established parser on the copies)
python3 - <<'EOF'
print("Parse NTUSER.DAT RecentDocs, Run keys, and TypedURLs")
print("Parse SYSTEM hive: USBSTOR (USB history), Services (persistence)")
print("Parse SOFTWARE hive: installed programs, uninstall entries")
EOF

# Event logs: filter Security.evtx for logons (4624) and process creation (4688)
# Use evtx parsing tools; filter to the incident window first
```

Registry Run keys and Services are the persistence checklist; USBSTOR
answers "was data walked out on a thumb drive"; Security.evtx logons
answer "who was here and when."

## 2. Browser and application artifacts

```bash
# Browser history locations on the image:
# Chrome: C:\Users\<u>\AppData\Local\Google\Chrome\User Data\Default\History (sqlite)
# Firefox: ...\Profiles\<p>\places.sqlite

# Query Chrome history directly with sqlite3 on the extracted copy
sqlite3 /tmp/History "SELECT url, datetime(last_visit_time/1000000-11644473600,'unixepoch') FROM urls ORDER BY last_visit_time DESC LIMIT 20;"

# Downloads, cookies, and login data are sibling sqlite files;
# parse each for the investigation's questions

# Email and chat artifacts per the applications installed;
# check the usual data directories under AppData and Documents
```

Browser history is often the investigation's best witness: it shows
intent (searches), access (URLs with timestamps), and downloads. Treat
timestamps carefully (WebKit epoch differs from unix epoch).

## 3. Linux artifacts

```bash
# Key paths on a Linux image:
# /var/log/auth.log, syslog: authentication and sudo
# /home/*/.bash_history: typed commands (often the whole attack)
# /var/log/cron: scheduled task execution
# /etc/crontab, /etc/cron.*: persistence
# ~/.ssh/authorized_keys: planted keys

# Bash history is frequently the entire intrusion in one file
grep -E 'wget|curl|chmod|nc |ncat|/dev/tcp' /mnt/image/home/user/.bash_history | head -20

# Auth log: logons, sudo use, in the incident window
grep -E 'sshd.*Accepted|sudo.*COMMAND' /mnt/image/var/log/auth.log | head -20
```

On Linux, `.bash_history` plus `auth.log` plus the timeline usually
reconstructs the intrusion end to end. Check for history deletion too:
a truncated history file is itself evidence.

## Edge cases

- The artifact is corrupted or partially overwritten. Parse what
  survives; carve the rest (see deleted-file-carving) and note the
  gaps.
- The user cleared history or logs. The clearing is evidence; look for
  the tools used to clear and the artifacts they missed.
- Timestamps conflict between artifacts. Different applications, different
  epochs and zones; normalize before correlating.
- The artifact format is proprietary. Find the vendor's documentation or
  a community parser; do not guess at binary layouts.

## Escalation

- You need registry or evtx at scale: use dedicated forensic frameworks
  that batch-parse hives and logs into the timeline.
- Artifacts point to memory-resident activity: hand the question to
  memory-forensics with the artifact evidence attached.
- The artifact answers are needed for legal proceedings: document the
  tool, version, and exact commands for reproducibility.

## Detection and defender view

For defenders, artifacts are the detection surface that survives log
deletion: registry persistence, browser history, and file artifacts
persist where logs were cleared. Building artifact baselines (normal
Run keys, normal services) makes anomalies visible during hunts. The
defender's lesson is that attackers who clean logs often forget
artifacts.

## Key references

- NIST SP 800-86 (Guide to Integrating Forensic Techniques into Incident
  Response).
- SANS forensic artifact references (persistence locations).
- SQLite database format documentation (browser artifacts).
