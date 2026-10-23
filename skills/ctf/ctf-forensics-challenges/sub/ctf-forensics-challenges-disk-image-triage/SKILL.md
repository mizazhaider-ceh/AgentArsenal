---
name: ctf-forensics-challenges-disk-image-triage
description: Use when a CTF forensics challenge provides a disk image, or
  when triaging storage media you are authorized to examine. Covers
  partition enumeration with mmls and fdisk, file listing with fls
  including deleted entries, file recovery with icat, carving unallocated
  space with blkls, building timelines with mactime, and checking slack
  space, alternate data streams, and shadow copies. Use when handed a .img,
  .dd, .E01, or .vmdk, when the flag is in a deleted file, or when you
  need to reconstruct file activity on the image.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-forensics-challenges
requires: [ctf-forensics-challenges]
extends: []
relates: [forensics-fundamentals, memory-forensics]
tools:
  - name: Python
    version: 3.12
  - name: CyberChef
    version: latest
---

Disk images preserve filesystems, including deleted files, unallocated
space, and metadata that never appears in a live listing. CTF disk
challenges hide flags in deleted files, slack space, hidden partitions,
and alternate streams. This sub-skill covers the authorized Sleuth Kit
workflow for triaging images without altering them: partition mapping,
file enumeration, targeted recovery, carving, and timeline building.
Scope is CTF competitions, lab images, and media you are authorized to
examine. Never write to the original image; work on copies.

## Quick Workflow

1. Copy the image to a working file; compute a hash of the original for
   your notes.
2. Enumerate partitions (`mmls`, `fdisk -l`); note filesystem types and
   offsets.
3. List files per partition with `fls -r -p`; scan for interesting
   names (flag, secret, backup, .zip).
4. List deleted entries with `fls -r -d`; deleted files are the most
   common CTF hiding spot.
5. Recover candidates with `icat` by inode number and inspect them.
6. Carve unallocated space (`blkls | strings`) for fragments of
   deleted content.
7. Build a timeline (`fls -m` plus `mactime`) to answer "what happened
   when" challenges.
8. Check filesystem extras: NTFS alternate data streams, ADS, volume
   shadow copies, ext4 journal remnants.

## 1. Partition enumeration

```bash
# Sleuth Kit media management (works on raw dd images)
mmls disk.img
# DOS Partition Table
# Offset Sector: 0
# Units are in 512-byte sectors
#      Slot      Start        End          Length       Description
#      000:  Meta            0000000000   0000000000   0000000001   Primary Table (#0)
#      001:  -------         0000000000   0000002047   0000002048   Unallocated
#      002:  000:000         0000002048   0002097151   0002095104   Linux (0x83)

fdisk -l disk.img   # cross-check; shows sizes in human units

# For E01 (Expert Witness) images, convert first or use ewf-tools
ewfinfo disk.E01 | head -30
```

The offset matters: Sleuth Kit tools take `-o <sector>` for partitioned
images (`fls -o 2048 disk.img`). Record which partition holds the OS;
CTF flags usually live on the data partition, not the boot partition.

## 2. File listing: live and deleted

```bash
# Recursive listing with full paths, partition at sector 2048
fls -r -p -o 2048 disk.img | head -50
# r/r 1234:  home/user/flag.txt
# r/r * 5678: home/user/deleted_secret.txt   <- * marks deleted entries

# Deleted files only (the money command for CTF disk challenges)
fls -r -d -o 2048 disk.img

# Details: sizes, times, inode numbers
fls -l -r -o 2048 disk.img | head -30

# Search the listing for interesting names
fls -r -p -o 2048 disk.img | grep -i -E "flag|secret|passw|backup|\.zip$|\.png$" | head -20
```

Inode numbers from `fls` feed directly into `icat`. The `*` prefix on
deleted entries is the fastest visual triage: scan the deleted list
before reading the live tree.

## 3. Targeted recovery with icat

```bash
# Extract file by inode number (from fls output)
icat -o 2048 disk.img 5678 > /tmp/recovered.txt
file /tmp/recovered.txt && head -c 500 /tmp/recovered.txt

# Recover all deleted files in one loop
mkdir -p /tmp/deleted
fls -r -d -o 2048 disk.img | grep -o -E "^\S+ \* [0-9]+" | awk '{print $3}' | while read ino; do
  icat -o 2048 disk.img "$ino" > "/tmp/deleted/inode_$ino.bin" 2>/dev/null
done
ls -la /tmp/deleted && file /tmp/deleted/* | head -20
```

Partial overwrites happen: a deleted file's blocks may be reused, so a
recovered file can be truncated or mixed with newer data. When `icat`
output looks half-right, carve the raw blocks around it with `blkcat`.

## 4. Carving unallocated space

```bash
# Dump unallocated blocks, then strings and flag-grep
blkls -o 2048 disk.img | strings -n 8 > /tmp/unalloc_strings.txt
grep -i -E "flag\{[^}]+\}|password|BEGIN.*PRIVATE KEY" /tmp/unalloc_strings.txt | head -20

# File carving for deleted images/archives in unallocated space
blkls -o 2048 disk.img > /tmp/unalloc.bin
binwalk /tmp/unalloc.bin | head -20
foremost -i /tmp/unalloc.bin -o /tmp/carved -q && ls /tmp/carved/* | head

# Slack space: file tails beyond logical EOF in the last block
# (Sleuth Kit exposes this via icat -s on some versions; otherwise blkcat the tail block)
```

Unallocated carving finds content whose metadata is fully gone: chat
fragments, deleted documents, browser artifacts. In CTFs the flag is
sometimes split: half in a deleted file, half in unallocated space.

## 5. Timeline building

```bash
# Bodyfile format: one line per file with MAC times
fls -r -m "/" -o 2048 disk.img > /tmp/body.txt

# Human-readable timeline, sorted
mactime -b /tmp/body.txt -d > /tmp/timeline.csv
head -30 /tmp/timeline.csv

# Focus on a window (e.g. the hour the challenge says the incident happened)
grep "2026-10-2[23]" /tmp/timeline.csv | head -40
```

Timelines answer "what did the attacker touch": files created, modified,
or accessed in a tight window cluster around the interesting activity.
Sort by modified time descending to see the most recently changed files
first.

## 6. Filesystem extras

```bash
# NTFS alternate data streams (flag:hidden.txt style hiding)
fls -r -o 2048 disk.img | grep -i ":.*\$DATA" | head
icat -o 2048 disk.img 1234:secret.txt > /tmp/ads.bin   # stream syntax

# NTFS: check for additional data streams on an interesting file
istat -o 2048 disk.img 1234 | grep -A5 -i "stream\|ads"

# Volume Shadow Copies (Windows): list and diff
# (vssadmin parsing needs the image mounted or libvshadow tooling)

# ext4: check the journal for recently deleted metadata
# debugfs -R "logdump" /dev/loop0  (on a loop-mounted read-only copy)
```

Also check: `$Recycle.Bin` / `.Trash` contents, browser profile
directories, shell history files (`.bash_history` often survives and
contains the flag-handling commands), and scheduled task or cron
artifacts.

## Edge cases

- The image is a full disk with an unfamiliar partition scheme (GPT):
  `mmls` handles GPT; adjust `-o` offsets per partition entry.
- Filesystem is corrupted by design: `fsstat -o 2048 disk.img` shows
  superblock details; Sleuth Kit often reads through minor corruption
  that stops normal mounting.
- The image is compressed (qcow2, vmdk): convert with `qemu-img
  convert` to raw first.
- E01 with compression and hashes: verify with `ewfverify` before
  analysis so a corrupt segment does not waste hours.
- Timestamps are all zeroed (anti-forensics): fall back to content
  carving; ordering comes from block allocation sequence, not times.

## Escalation

- `fls` shows nothing useful and unallocated carving is empty: the
  flag may be in a hidden partition (`mmls` unallocated gaps), in
  firmware-like regions outside partitions, or the image is a
  decoy and the real artifact is elsewhere in the bundle.
- Deleted file recovery yields garbage: blocks were overwritten;
  check the journal (ext4) or USN journal (NTFS) for filenames and
  partial content instead.
- The challenge expects registry analysis (Windows): export hives
  with `icat` (SAM, SYSTEM, SOFTWARE, NTUSER.DAT) and parse offline
  with registry tools.
- Timeline is too noisy: filter to one directory subtree or one file
  type; CTF timelines usually have one obvious burst of activity.

## Detection and defender view

Defenders perform this same triage during incident response: deleted
file recovery reveals attacker tooling, timelines reconstruct the
intrusion, and carving finds wiped logs. Anti-forensics (timestomping,
secure deletion, journal wiping) is itself an indicator. Detections
focus on the behaviors: mass deletion, shadow copy deletion
(`vssadmin delete shadows`), and clearing event logs. Durable defenses:
immutable backups, centralized logging (so local deletion does not
blind you), and file integrity monitoring on critical paths.

## Key references

- MITRE ATT&CK T1070 (Indicator Removal), T1005 (Data from Local
  System).
- Sleuth Kit wiki and tool docs: https://wiki.sleuthkit.org/
- NIST SP 800-86 (Guide to Integrating Forensic Techniques into
  Incident Response).
- Carrier, "File System Forensic Analysis": the reference for
  filesystem internals.
- SANS FOR508 course materials (disk forensics process and tool
  workflows).
