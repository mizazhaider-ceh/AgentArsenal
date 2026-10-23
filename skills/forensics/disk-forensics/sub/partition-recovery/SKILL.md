---
name: partition-recovery
description: Use when partition tables are damaged, deleted, or missing on
  a forensic image. Covers partition table analysis, signature-based
  partition discovery, and rebuilding access to filesystems. Use when the
  image shows no partitions, when partitions were deleted, when the
  partition table is corrupt, or when you need the filesystem before any
  file analysis.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
parent: disk-forensics
requires: [disk-forensics]
extends: []
relates: [forensics-fundamentals, deleted-file-carving]
tools:
  - name: The Sleuth Kit
    version: 4.12.1
  - name: Python
    version: 3.12
---

A disk without a readable partition table still holds its filesystems;
the map is gone, not the territory. This skill covers recovering
partition layout from forensic images: reading damaged tables, finding
filesystems by signature, and rebuilding access. It runs on working
copies only, and every step is documented, because partition recovery
changes how the rest of the examination proceeds.

## Quick Workflow

1. Work on the verified working copy, never the original.
2. Try reading the partition table normally first.
3. If it fails, scan for filesystem signatures across the image.
4. Reconstruct the partition layout from found signatures.
5. Access each filesystem read-only and verify it parses.
6. Document the recovered layout for the examination record.

## 1. Reading the damaged table

```bash
# Normal read first: GPT and MBR via TSK
mmls /analysis/case01_work.img 2>&1 | head -20

# If mmls fails, inspect the raw bytes: MBR signature at offset 510
xxd -s 510 -l 2 /analysis/case01_work.img
# expect 55aa; anything else means a damaged or wiped MBR

# GPT header at LBA 1 (offset 512): look for the EFI PART signature
xxd -s 512 -l 8 /analysis/case01_work.img
```

A wiped first sector with intact filesystems later is the classic
anti-forensics or re-partitioning case. The signatures below find what
the table lost.

## 2. Signature scanning

```bash
# Search for filesystem superblocks across the image
# ext4 superblock magic 0x53EF at offset 56 within the superblock
# (superblock starts 1024 bytes into the filesystem)

# NTFS: 'NTFS    ' at the start of the boot sector
# FAT32: 'FAT32   ' at offset 82 of the boot sector

# TSK fls can try likely offsets once you have candidates;
# or scan with a simple Python signature sweep
python3 - <<'EOF'
import sys
Sigs = {b'NTFS    ': 'NTFS boot sector', b'\x53\xef': 'possible ext superblock'}
with open('/analysis/case01_work.img', 'rb') as f:
    data = f.read()
for sig, name in Sigs.items():
    off = 0
    hits = []
    while True:
        off = data.find(sig, off)
        if off == -1:
            break
        hits.append(off)
        off += 1
    print(f"{name}: {len(hits)} hits, first at {hits[:5]}")
EOF
```

Each hit is a candidate filesystem start. Verify by attempting to list
it before declaring the layout recovered.

## 3. Rebuilding access

```bash
# Access a found NTFS at byte offset with TSK
fls -o <sector_offset> /analysis/case01_work.img 2>&1 | head -10
# -o takes the sector offset of the filesystem start

# Verify it parses: list the root and check for sane entries
fls -o <sector_offset> /analysis/case01_work.img | head -20

# For the examination record, write the recovered layout
cat > /tmp/recovered_layout.txt <<'EOF'
Image: case01_work.img
Partition 1: offset <n> sectors, NTFS, parses cleanly, label <x>
Partition 2: offset <n> sectors, ext4, parses cleanly
Method: signature scan after MBR damage at sector 0
EOF
```

Recovered partitions feed the normal workflow: timelines, artifact
parsing, and carving all run per filesystem from here.

## Edge cases

- Signatures are wiped too (full disk wipe). Carving (see
  deleted-file-carving) is the remaining option; partitions are gone.
- The layout uses LVM, RAID, or encryption. Reassemble the logical
  volume first (LVM metadata, RAID parameters); encrypted volumes need
  the key from memory or the investigation.
- False-positive signatures. Verify every candidate by parsing;
  random data contains magic bytes by chance.
- The disk is failing. Image with error recovery first; partition
  recovery on a dying disk without a good image risks everything.

## Escalation

- You need the data urgently and the layout resists recovery: carve
  files directly from the image while continuing the layout work in
  parallel.
- The filesystem parses but is corrupt: use the filesystem's own
  recovery tools on a copy, and document every repair.
- Recovery must be defensible: keep the signature scan logs and the
  verification outputs with the case file.

## Detection and defender view

For defenders, partition damage is either failure or anti-forensics:
both matter. Unexpected partition changes on a server (monitoring
partition tables is cheap) signal tampering or re-imaging. The
defender's preparation is known-good partition baselines for critical
systems and the imaging discipline that makes recovery possible.

## Key references

- The Sleuth Kit documentation: mmls, fls with offsets.
- "File System Forensic Analysis" (partition systems).
- NIST SP 800-86 (media analysis).
