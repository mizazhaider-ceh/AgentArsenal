---
name: forensics-fundamentals
description: Use when you must investigate a disk image, memory dump, or compromised host under proper legal authority, on an authorized incident response engagement, lab, or CTF. Covers chain of custody and write-blocked acquisition with dc3dd, hashing and verification with sha256sum, file system analysis with Sleuth Kit tools (fls, icat, istat), file carving with scalpel and foremost, timeline analysis with Plaso log2timeline, memory forensics basics with Volatility 3 (process lists, network connections, injected code), and spotting anti-forensics such as timestomping, log wiping, and hidden files. Emphasizes working on copies, documenting every step, and writing findings that hold up in a report.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response]
tools:
  - name: sleuthkit
    version: 4.12.1
  - name: autopsy
    version: 4.21.0
  - name: volatility3
    version: 2.11.0
  - name: plaso
    version: 2024.x
---

Digital forensics is the disciplined recovery and interpretation of digital evidence. The method matters more than the tools: preserve first, analyze copies, hash everything, document every step, and never work on original media. This skill covers the core workflow used on authorized investigations, incident response engagements, and CTFs: chain of custody, disk imaging, file system analysis, file carving, timeline analysis, and memory forensics basics. It pairs with incident-response, which owns the containment and recovery decisions while forensics owns the evidence.

## Quick Workflow

1. Confirm scope and legal authority: what you may collect, from which systems, under whose authorization.
2. Preserve the evidence: write-block the media and create a forensic image before anything else.
3. Hash the image (SHA-256) and record hashes, serials, dates, and handlers in the chain of custody log.
4. Analyze the copy: partition layout, file system walk, deleted file recovery.
5. Carve unallocated space for deleted files of interest.
6. Build a timeline and correlate events across sources.
7. Analyze memory if a capture exists: processes, connections, injected code.
8. Write findings with timestamps, tool versions, and exact commands so the work is reproducible.

## Phase 1: Chain of custody and preparation

Chain of custody is the written record of who handled evidence, when, and what they did. Start it before you touch anything. For each item record: description, serial or identifier, source system and location, date and time of collection, collector name, storage location, and every transfer with signatures.

```bash
mkdir -p /evidence/case-001/{images,notes,exports}
cat > /evidence/case-001/notes/custody.log <<'EOF'
CASE: case-001
ITEM: suspect workstation SSD, serial WD-XXXXXXX
COLLECTED: 2026-10-23 09:15 CEST by <analyst> at <location>
METHOD: write-blocked imaging via Tableau bridge
STORAGE: /evidence/case-001/images/
EOF
```

Rules that keep evidence defensible: never boot the suspect drive, never mount it read-write, work only on the image or a copy of the image, and photograph or record the physical state before disconnecting anything. If the machine is running and volatile data matters, capture memory before pulling power (see Phase 6), because a shutdown destroys it.

## Phase 2: Disk imaging and hashing

Image with a tool that hashes during acquisition and logs errors. dc3dd is the forensic build of dd with hashing and logging built in.

```bash
dc3dd if=/dev/sdb of=/evidence/case-001/images/disk.dd hash=sha256 log=/evidence/case-001/notes/acquire.log
```

Verify the copy independently after acquisition:

```bash
sha256sum /dev/sdb > /evidence/case-001/notes/source.sha256
sha256sum /evidence/case-001/images/disk.dd > /evidence/case-001/notes/image.sha256
diff /evidence/case-001/notes/source.sha256 <(cut -d' ' -f1 /evidence/case-001/notes/image.sha256)
```

The hashes must match. If the source is failing, use `dc3dd` with error recovery options or `ddrescue` and document every bad sector; a partial image with a documented gap beats a failed acquisition with no notes.

For remote or live acquisition where pulling the disk is impossible, image over the network with netcat or ssh and hash both ends. Always note in the custody log that this was a live acquisition and why.

## Phase 3: File system analysis with Sleuth Kit

Work on the image, never the original. Start with partition layout, then walk the file system.

```bash
mmls /evidence/case-001/images/disk.dd
```

`mmls` shows the partition table with start sectors and lengths. Note the offset of the partition you need (the Start column). Then list files recursively:

```bash
fls -r -o 2048 -p /evidence/case-001/images/disk.dd | head -50
```

The `-o 2048` is the partition offset in sectors; replace it with the value `mmls` reported. Deleted files appear with an asterisk. For a specific file, inspect its metadata:

```bash
istat -o 2048 /evidence/case-001/images/disk.dd 12345
```

`istat` shows timestamps (accessed, modified, changed, and on some systems created), size, and the block addresses holding the data. Recover the file content by inode:

```bash
icat -o 2048 /evidence/case-001/images/disk.dd 12345 > /evidence/case-001/exports/recovered-12345.bin
```

This recovers deleted files too, as long as their blocks have not been overwritten. Check the file type of what you recovered (`file recovered-12345.bin`) because extensions lie and inodes do not.

For NTFS specifics, `ntfscat` and `fls -m` variants help; for ext4, `istat` shows the extra timestamps. Autopsy provides a GUI over all of this when you prefer point and click, but the commands above are what you script and what you cite.

## Phase 4: File carving

Carving recovers files from unallocated space by header and footer signatures, independent of the file system. Use it when files were deleted and their metadata is gone, or when you suspect data hidden outside the file system.

```bash
scalpel -o /evidence/case-001/exports/carved /evidence/case-001/images/disk.dd
```

Configure `/etc/scalpel/scalpel.conf` first: uncomment only the file types you care about (jpg, png, pdf, docx, zip), because carving everything wastes hours. foremost is the simpler alternative:

```bash
foremost -t jpg,pdf,docx -i /evidence/case-001/images/disk.dd -o /evidence/case-001/exports/foremost
```

Carved files lose names and timestamps, so triage by content: run `file` on the output, view images, and strings-search documents for keywords from the case.

```bash
strings -n 8 /evidence/case-001/exports/carved/jpg/* | grep -iE "password|confidential|invoice" | head
```

Photorec (companion to TestDisk) is the interactive option for badly damaged media. Document which tool, which version, and which config you used; carving results are only as defensible as the method note behind them.

## Phase 5: Timeline analysis

Timelines correlate file timestamps, logs, and registry artifacts into one chronological view. Build one with Plaso (log2timeline):

```bash
log2timeline.py --storage-file /evidence/case-001/notes/timeline.plaso /evidence/case-001/images/disk.dd
pinfo.py /evidence/case-001/notes/timeline.plaso | head -30
psort.py -o l2tcsv -w /evidence/case-001/notes/timeline.csv /evidence/case-001/notes/timeline.plaso
```

Then filter for the incident window:

```bash
grep "2026-10-2" /evidence/case-001/notes/timeline.csv | grep -iE "prefetch|mft|evtx|chrome|bash" | head -40
```

What to look for in the timeline: first execution of unknown binaries (Prefetch on Windows, or new files with recent MAC times on Linux), log gaps (evidence of wiping), mass file access (staging for exfiltration), and persistence creation (Run keys, cron, systemd units) shortly before or after the intrusion window.

On Linux images, also pull the key logs directly:

```bash
fls -o 2048 -p /evidence/case-001/images/disk.dd | grep -iE "auth.log|syslog|messages"
icat -o 2048 /evidence/case-001/images/disk.dd <inode-of-auth.log> > /evidence/case-001/exports/auth.log
grep -iE "accepted|failed|sudo" /evidence/case-001/exports/auth.log | tail -30
```

On Windows, export the Event Logs and registry hives by inode and parse them with evtx tools and RegRipper-style parsers on your analysis box.

## Phase 6: Memory forensics basics

Memory holds what disk does not: running processes, network connections, injected code, and encryption keys. If you captured memory from a live host (with winpmem, LiME, or AVML), analyze it with Volatility 3.

Identify the right profile automatically and list processes:

```bash
vol -f /evidence/case-001/images/mem.raw windows.pslist
vol -f /evidence/case-001/images/mem.raw windows.pstree
```

Look for: processes with no parent or with a suspicious parent (a Word document spawning PowerShell), multiple processes with the same name, and processes running from temp directories. Then check network state and injected code:

```bash
vol -f /evidence/case-001/images/mem.raw windows.netscan
vol -f /evidence/case-001/images/mem.raw windows.malfind
vol -f /evidence/case-001/images/mem.raw windows.dlllist --pid <pid>
```

`malfind` flags memory regions with execute permissions that are not backed by a file on disk, the classic sign of injected code. Dump anything suspicious for further analysis:

```bash
vol -f /evidence/case-001/images/mem.raw windows.malfind --dump --pid <pid>
vol -f /evidence/case-001/images/mem.raw windows.dumpfiles --pid <pid>
```

For Linux memory, use the linux.pslist, linux.bash, and linux.procmaps plugins. Capture memory before disk imaging on live systems, because rebooting or imaging first can overwrite the very regions you need.

## Phase 7: Browser and artifact triage

User activity artifacts answer what the user did, not just what the system did. Priorities per OS:

- Windows: browser history and downloads (Chrome, Edge, Firefox profiles under AppData), RecentDocs, ShellBags, Jump Lists, Prefetch (execution evidence with run counts and last run times), Amcache (executed programs inventory).
- Linux: shell histories (`.bash_history`, `.zsh_history`), browser profiles under `~/.config` and `~/.mozilla`, systemd journal, auth logs, cron files.
- Both: USB connection history (Windows registry USBSTOR, Linux syslog), cloud sync client databases, and email client stores.

Extract by inode with `icat` as in Phase 3, then parse with dedicated tools (browser history SQLite queries, Prefetch parsers) on your analysis machine. Correlate every artifact back into the timeline from Phase 5; an artifact without a timestamp is a hint, not evidence.

## Edge cases

- The image will not mount or parse: verify the partition offset from `mmls` again; a wrong `-o` value produces garbage. Check whether the disk uses GPT, BitLocker, or LUKS, which need the recovery key or passphrase before any analysis.
- Encryption blocks you: look for recovery keys in the case paperwork, Active Directory (BitLocker recovery passwords are often escrowed), or memory captures (keys live in RAM). Document the attempt; do not brute force without authority and a realistic chance.
- Timestamps look wrong: check the timezone. File systems store UTC; the suspect may have changed the clock. Correlate with log timestamps and note the discrepancy instead of silently correcting it.
- Carving returns thousands of false positives: narrow the config to the file types the case needs, and triage with `file` plus keyword searches rather than opening everything.
- Memory plugins fail: Volatility 3 needs the right symbols. Let it download them (it does this automatically with network access) or supply a matching symbol table for custom kernels.
- The suspect used anti-forensics (timestomping, log wiping): pivot to sources the attacker cannot easily alter, like network logs, firewall records, and external telemetry, and treat gaps in the timeline as findings themselves.

## Escalation

- Disk analysis stalls on encryption or damage: escalate to memory analysis and network evidence while the disk problem is worked in parallel. Cases are rarely single-source.
- Timeline is inconclusive: widen the window by 48 hours on each side and add sources (DHCP logs, VPN logs, proxy logs, EDR telemetry). Attackers prepare before and clean up after the visible window.
- Findings suggest an active intruder still present: stop pure forensics and invoke incident-response for containment. Evidence preservation and containment can conflict; the incident commander decides the order.
- Legal or HR sensitivity appears (personal data, employee privacy): pause collection beyond the authorized scope and get written guidance before proceeding. Over-collection creates liability.

## Detection and defender view

- Anti-forensics is itself detectable: timestomping leaves MFT anomalies (sequence numbers out of order, timestamps newer than the parent directory), log wiping leaves gaps and service restart events, and file deletion leaves unallocated clusters with intact signatures.
- Defenders make forensics possible by ensuring it in advance: centralized logging that attackers cannot reach, EDR with process and network telemetry, memory capture tooling pre-deployed, and documented imaging procedures so first responders do not trample evidence.
- Central log forwarding (syslog, Windows Event Forwarding) defeats local log wiping. Immutable storage (WORM buckets, append-only log servers) defeats tampering.
- For the offensive side, every privesc and persistence technique in privesc-linux and privesc-windows leaves the artifacts this skill recovers; assume the defender will find them.

## Key references

- MITRE ATT&CK: T1070 (Indicator Removal), T1070.001 (Clear Windows Event Logs), T1070.002 (Clear Linux or Mac System Logs), T1070.004 (File Deletion), T1070.006 (Timestomp), T1027 (Obfuscated Files or Information), T1564.001 (Hidden Files and Directories).
- CWE: CWE-778 (Insufficient Logging), CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- Tool docs: Sleuth Kit and Autopsy (sleuthkit.org), Volatility 3 (volatilityfoundation.org), Plaso (plaso.readthedocs.io), NIST SP 800-86 (Guide to Integrating Forensic Techniques into Incident Response).
