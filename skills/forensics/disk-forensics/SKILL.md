---
name: disk-forensics
description: Use when examining a disk image or forensic copy of a drive
  during an investigation. Covers The Sleuth Kit and Autopsy workflows:
  partition layout, file carving, deleted file recovery, timeline generation,
  hash analysis, and keyword search. Use when you need to recover deleted
  files, prove what existed on a disk, or build a filesystem timeline for a
  case you are authorized to work.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [forensics-fundamentals, incident-response]
tools:
  - name: The Sleuth Kit
    version: 4.14.0
  - name: Autopsy
    version: 4.22.1
  - name: Python
    version: 3.12
---

Disk forensics reconstructs what was stored on a drive from a bit-for-bit
image of it. Files are rarely truly gone when deleted: the directory entry is
marked free but the content often survives until overwritten, which is why
`fls`, `icat`, and `istat` are the core verbs of this skill. This skill covers
the full command-line workflow with The Sleuth Kit: verifying the image,
mapping partitions, listing files including deleted ones, recovering file
content by inode, carving unallocated space, and building a filesystem
timeline, plus when to switch to Autopsy for keyword search and reporting.
Scope: analyze disk images you are authorized to handle only (your own lab
images, client media under an investigation, or CTF files). Never write to
the original media; work on copies, mount read-only, and record every hash.

## Quick Workflow

1. Hash and copy the image, then verify the partition layout with `mmls`.
2. List the filesystem root with `fls` and note deleted entries (marked `*`).
3. Inspect suspicious files with `istat` (metadata) and `icat` (content),
   working by inode number so deleted files are reachable.
4. Recover deleted files and carve unallocated space for file headers.
5. Build a filesystem timeline with `fls -m` piped through `mactime`.
6. Hash known files against NSRL or your case hash set to filter noise.
7. Run keyword searches for IOCs (IPs, emails, malware strings).
8. Switch to Autopsy when you need ingest modules, image review, or a
   report-ready case file.

## 1. Intake and partition mapping

Hash first, always. Then learn the layout before touching any filesystem.

```bash
# Hash the original, then work on the copy
sha256sum /mnt/evidence/disk01.E01 > disk01.sha256
cp /mnt/evidence/disk01.E01 ./disk01.E01
sha256sum ./disk01.E01

# E01 (EnCase) images: Sleuth Kit reads them natively
# For raw dd images the same commands apply

# Partition table: slots, start sectors, lengths
mmls disk01.E01

# Details of one partition (note its start sector)
mmls -o 2048 disk01.E01 2>/dev/null | head
```

`mmls` output gives you the sector offset of each partition. Every later
command that reads inside a partition needs `-o <offset>`. If `mmls` shows
`DOS Partition Table` with unallocated gaps between partitions, carve those
gaps too, they sometimes hold deleted partition remnants.

```bash
# Filesystem type of the first partition
fsstat -o 2048 disk01.E01 | head -30
```

## 2. Listing files, including deleted ones

`fls` lists directory entries by inode. Deleted entries are flagged and,
critically, still listable because the inode survives.

```bash
# Root of partition starting at sector 2048
fls -o 2048 disk01.E01

# Long format with inode numbers and deleted markers (*)
fls -o 2048 -l disk01.E01 | head -40

# Recursive listing of everything, deleted included
fls -o 2048 -r -p disk01.E01 > full_listing.txt
grep '^\*' full_listing.txt | head -20   # deleted files only

# A specific directory by inode
fls -o 2048 -l disk01.E01 5   # inode 5 is usually root on ext, check first
```

NTFS notes: `$MFT` entries behave the same way, and `fls` on NTFS shows
ADS (alternate data streams) as `file:stream` entries. A lone ADS on an
otherwise boring file is a classic hiding spot.

## 3. Inode metadata and file content recovery

This is the core recovery loop: `istat` tells you where the blocks are,
`icat` pulls the bytes. It works for deleted files too, as long as the
blocks were not overwritten.

```bash
# Metadata for inode 42: size, timestamps, block list
istat -o 2048 disk01.E01 42

# Dump the file content to stdout
icat -o 2048 disk01.E01 42 > recovered_file.bin

# Recover by inode into a named file (same thing, clearer intent)
icat -o 2048 disk01.E01 42 > ./recovered/inode_42.bin

# A deleted file: find its inode in the fls listing first, then icat it
fls -o 2048 -l -d disk01.E01 | grep -i deleted | head
```

When you record an inode in your notes, also record how you found it: which
command revealed it and which line of output named it. "Inode 42, found via
`fls -o 2048 -l` as the deleted entry `secret.docx`" beats a bare number in
court and in your report.

```bash
# Check block allocation: which blocks are unallocated (carving targets)
blkstat -o 2048 disk01.E01 1000 | head

# Dump raw unallocated blocks in a range
blkls -o 2048 disk01.E01 1000-2000 > unalloc.bin
```

## 4. Carving unallocated space

Carving finds files by header signature in space the filesystem considers
free. It recovers content without names or timestamps, so treat results as
leads.

```bash
# Simple header scan for JPEGs in unallocated space
blkls -o 2048 disk01.E01 > unalloc.bin
grep -a -b -o -P '\xff\xd8\xff' unalloc.bin | head -20

# Better: use a dedicated carver for structured recovery
# (scalpel/photorec style tools complement TSK here)
mkdir -p carved && cd carved
# run your carver against unalloc.bin, then inspect each hit by hand
file * | sort | uniq -c | sort -rn | head -20
```

Validate every carved file before reporting it: open images, check document
headers, confirm the content is coherent. Carvers produce false positives
from random byte sequences that happen to match a header.

## 5. Timelining the filesystem

`fls -m` emits one line per file in `mactime` body format. `mactime` turns
that into a sorted timeline, which is where deleted-file timestamps and
mass-modification events jump out.

```bash
# Body file for the whole partition
fls -o 2048 -r -m / disk01.E01 > body.txt

# Sorted timeline
mactime -b body.txt > timeline.txt

# Activity on one suspicious day
grep '2026-10-22' timeline.txt | head -40

# Focus on one directory
grep -i '/home/suspect/' timeline.txt | head -40
```

Look for: bursts of file creation at odd hours, executables with timestamps
newer than the system install, and files whose MAC times cluster around the
incident window. Timestamps can be forged (timestomping), so corroborate
with logs before treating them as fact.

## 6. Hash filtering and keyword search

Hash sets remove the haystack. Keyword search finds the needle.

```bash
# Hash every allocated file and compare against your known-good set
# (build the hash set from NSRL or your gold image first)
hfind known_good.hash MD5_OF_FILE

# Keyword search across raw image for an IOC (case-insensitive, binary-safe)
grep -a -i -o -b 'evil-c2.example' disk01.E01 | head -20

# Search unallocated space only for a leaked email address
grep -a -i -o -b 'leak@[a-z.]*' unalloc.bin | head -20

# Strings plus context around each hit
strings -t d disk01.E01 | grep -i 'mimikatz' | head -20
```

Keep a written list of every keyword you searched and why. A keyword you
never searched is a question the defense can ask.

## 7. Autopsy for ingest and reporting

When the case needs keyword indexing, image triage, or a shareable report,
load the image into Autopsy instead of doing everything by hand.

```bash
# Autopsy is GUI-driven; on a headless box use X forwarding or the
# workstation build. Point a new case at the same hashed image copy.
# Enable ingest modules: Hash Lookup, Keyword Search, EXIF Parser,
# Recent Activity, and (Windows) Registry analysis.
```

Autopsy ingest is slow on large images; run it overnight and check module
completion before trusting "no results". Export reports from the case for
handover, and keep the TSK command history alongside, because Autopsy does
not log the equivalent of your shell history.

## Edge cases

- Image is split (`.E01`, `.E02`, ...): point TSK at the first segment; it
  follows the chain automatically. A missing segment aborts every read, so
  verify all segments hashed and present first.
- Unknown filesystem: `fsstat` fails, try `fsstat -t list` to see supported
  types, and check for encryption (BitLocker, LUKS) before assuming
  corruption. Encrypted volumes need the key, not a carver.
- Damaged partition table: `mmls` shows garbage, scan for filesystem
  superblocks directly with `sigfind` or a hex search for `53ef` (ext) or
  `FILE` (NTFS MFT) signatures.
- `icat` returns zeros for a deleted file: the blocks were reallocated and
  overwritten. Note it as unrecoverable and move to carving or backups.
- ADS on NTFS: list with `fls -l` and read with `icat` using the
  `inode:stream` form. A stream named `:Zone.Identifier` is normal browser
  metadata; anything else deserves a look.

## Escalation

- TSK cannot parse the filesystem at all: try `tsk_recover` for a brute
  directory walk, then fall back to full-image carving, then to a commercial
  or specialist tool for the exotic filesystem.
- Timeline is too big to read: pivot on the incident window first, then on
  file types (executables, archives, documents), then on paths outside normal
  user areas.
- Keyword search is too slow on a multi-TB image: index once with Autopsy or
  bulk_extractor, then query the index instead of re-scanning.
- Suspected timestomping: compare `$STANDARD_INFORMATION` vs `$FILE_NAME`
  timestamps on NTFS with `istat`; mismatches are a red flag, and the
  `$FILE_NAME` times are harder to forge.
- Need file ownership and permissions: `istat` shows UID/GID and mode bits;
  on NTFS check the security descriptor for unexpected ACEs.

## Detection and defender view

Disk forensics is how you prove what happened after the fact: deleted
malware binaries, staged archives, and exfiltration remnants all live here
until overwritten. For defenders, the operational lesson is retention and
integrity: keep forensic images of key systems, hash them at acquisition,
and store hashes separately so tampering is detectable. Watch for
anti-forensic behavior in your own telemetry: mass file deletion, timestamp
modification tools, secure-wipe utilities, and disabled Volume Shadow Copies
(Sysmon/EDR alerts on `vssadmin delete shadows`). The misuse case is reading
someone else's drive without authorization; a disk image contains everything,
so access control and a documented legal basis are non-negotiable.

## Key references

- MITRE ATT&CK T1070.004 (File Deletion): recovering what deletion tried to
  hide.
- MITRE ATT&CK T1564.001 (Hidden Files and Directories) and T1564.004 (NTFS
  File Attributes): ADS and hidden-file analysis.
- MITRE ATT&CK T1070.006 (Timestomping): timestamp forgery detection.
- MITRE ATT&CK T1005 (Data from Local System): what the recovered data
  represents.
- The Sleuth Kit documentation: https://www.sleuthkit.org/sleuthkit/docs.php
- Autopsy documentation: https://www.sleuthkit.org/autopsy/docs.php
