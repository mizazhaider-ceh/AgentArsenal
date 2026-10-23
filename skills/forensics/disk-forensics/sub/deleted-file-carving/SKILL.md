---
name: deleted-file-carving
description: Use when recovering deleted files from unallocated space on a
  forensic image. Covers file carving by headers and footers, carving
  tool workflows, and validating carved output. Use when the filesystem
  metadata is gone, when hunting deleted malware or documents, when the
  suspect emptied the recycle bin, or when unallocated space is the only
  remaining source.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
parent: disk-forensics
requires: [disk-forensics]
extends: []
relates: [forensics-fundamentals, partition-recovery]
tools:
  - name: The Sleuth Kit
    version: 4.12.1
  - name: Python
    version: 3.12
---

Deleted files leave their content in unallocated space until overwritten:
carving recovers them by recognizing file headers and footers without any
filesystem metadata. This skill covers carving on forensic images: choosing
targets, running carvers, and validating the output. Carving is noisy and
partial by nature; it answers "what was here" with probabilities, not
certainties.

## Quick Workflow

1. Define what file types matter to the investigation.
2. Extract unallocated space from the image (or carve the whole image).
3. Run the carver with the relevant file types enabled.
4. Review carved files: validate headers, check sizes, open samples.
5. Correlate carved files with the timeline and the case questions.
6. Report carved files with their validation status and caveats.

## 1. Extracting unallocated space

```bash
# TSK: list unallocated blocks, then extract them
blkls /analysis/case01_work.img > /tmp/unallocated.dd 2>/dev/null
ls -la /tmp/unallocated.dd

# Or carve the full image when the filesystem layout is uncertain
# (slower, but catches files in slack and odd regions)
```

Carving unallocated only is faster and cleaner; carving the whole image
catches allocated files too (duplicates) but finds things in slack space.
Choose based on the case: unallocated first, whole image if the question
demands it.

## 2. Running the carver

```bash
# scalpel-style carving with a focused config (edit to the case's file types)
# /etc/scalpel/scalpel.conf: enable only what you need
# jpg, png, pdf, docx, zip are the usual suspects

# Example: carve JPEGs and PDFs from unallocated space
# scalpel -c /tmp/case.conf -o /tmp/carved/ /tmp/unallocated.dd

# Validate every carved file: headers, footers, and openability
file /tmp/carved/jpg/* 2>/dev/null | head -10
ls -la /tmp/carved/pdf/ 2>/dev/null | head -10

# Quick triage: sizes and counts per type
du -sh /tmp/carved/* 2>/dev/null
```

A focused config beats the default: enabling every file type multiplies
false positives and review time. Carve for the case's questions, not for
completeness.

## 3. Validation and correlation

```bash
# Headers lie: verify the content matches the claimed type
# - Images: try to render thumbnails; broken renders mean partial files
# - Documents: check they open; carve-adjacent fragments often do not
# - Archives: test integrity (unzip -t)

# Correlate with the timeline: carved file timestamps are gone,
# but the unallocated region's neighbors and the case timeline bound it
python3 - <<'EOF'
print("For each carved file of interest, record:")
print("- carver, config, and source region")
print("- validation result (opens cleanly / partial / corrupt)")
print("- correlation: which case question it answers")
print("- caveat: no original name, path, or timestamps survive carving")
EOF
```

Report carved files honestly: "a JPEG recovered from unallocated space,
partial, shows X" is a solid finding; "the suspect's deleted photo" is
a claim carving cannot support alone.

## Edge cases

- The carver finds thousands of files. Triage by type and size first;
  thumbnails and icons are noise in most cases.
- Files are fragmented. Carvers recover the first fragment well and the
  rest poorly; fragmented files carve as corrupt partials.
- The data was securely wiped. Carving finds nothing, which is itself
  an answer: document the wipe evidence (tool artifacts, patterns).
- Encrypted files carve as opaque blobs. Without the key they are
  unvalidatable; note their presence and size.

## Escalation

- You need one specific deleted file: target its type and the
  unallocated region near its last known location instead of
  whole-image carving.
- Carving must be court-ready: document the tool, version, config, and
  validation for every file you rely on.
- The volume is huge: carve in parallel per region and merge the
  validated results.

## Detection and defender view

For defenders, carving is the recovery tool when deletion was the
anti-forensics: attackers who delete logs and tools leave carveable
traces. The defender's preparation is the imaging discipline that
preserves unallocated space (never "clean" a drive under investigation)
and the knowledge that deletion is not destruction. Secure wipe tools
on a suspect host are themselves suspicious.

## Key references

- NIST SP 800-86 (data recovery techniques).
- File signature databases (Gary Kessler's file signatures table).
- The Sleuth Kit documentation: blkls, carving concepts.
