---
name: evidence-handling
description: Use when acquiring and preserving digital evidence for
  forensic analysis. Covers write blocking, forensic imaging, hashing and
  chain of custody, and storage discipline. Use when starting any forensic
  examination, when the evidence must hold up legally, when imaging disks
  or memory, or when documenting handling for the report.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
parent: forensics-fundamentals
requires: [forensics-fundamentals]
extends: []
relates: [incident-response, disk-forensics]
tools:
  - name: Python
    version: 3.12
  - name: The Sleuth Kit
    version: 4.12.1
---

Evidence handling is the foundation every forensic conclusion stands on:
acquire without altering, prove nothing changed, and document every hand
that touched it. This skill covers the handling workflow: write blocking,
imaging, hashing, and chain of custody. Skip it and the analysis is
worthless in any serious setting; do it right and every later finding is
defensible.

## Quick Workflow

1. Identify the evidence sources and the order of volatility.
2. Photograph and document the scene and system state first.
3. Capture volatile data (memory, network) before powering anything down.
4. Image storage media through a write blocker.
5. Hash the original and the image; the hashes must match.
6. Log every handling step in the chain of custody.
7. Work only on copies; the original stays sealed.

## 1. Order of volatility

```bash
# Collect in this order (most volatile first):
# 1. Memory (RAM)            -> memory-forensics
# 2. Network connections     -> netstat, ss output
# 3. Running processes       -> ps output
# 4. Open files and handles  -> lsof
# 5. Disk (powered on)       -> live imaging considerations
# 6. Disk (powered off)      -> dead-box imaging

# Live capture basics before any shutdown decision
date -u > /tmp/capture_start.txt
ss -tulnp > /tmp/netstat.txt 2>/dev/null
ps aux > /tmp/ps.txt 2>/dev/null
```

Powering down destroys memory and changes disk state (timestamps, caches).
The decision to pull the plug needs a reason; default to live capture of
volatiles first unless the situation demands immediate isolation.

## 2. Imaging with write blocking

```bash
# Hardware write blocker is the standard; software read-only mounting
# is the fallback (mount -o ro), never mount read-write

# Image with dc3dd or dd, logging hashes during the read
dc3dd if=/dev/sdb of=/evidence/case01_disk.img hash=sha256 log=/evidence/case01.log

# Verify: hash the image and compare with the acquisition hash
sha256sum /evidence/case01_disk.img
grep -i 'sha256' /evidence/case01.log

# Split images for storage if needed, keeping the hash manifest
```

Never analyze the original: mount the image read-only or work on a
verified copy. Every examination step happens on the copy; the original
is sealed and its hash is the proof it stayed sealed.

## 3. Chain of custody

```bash
# Custody log: every movement, every access, every copy
cat > /evidence/case01_custody.txt <<'EOF'
Item: case01_disk.img (sha256: <hash>)
2026-10-23 09:00 UTC - Acquired from host WS-114 by <name>, write blocker SN-42
2026-10-23 09:40 UTC - Imaged to /evidence/case01_disk.img, hash verified match
2026-10-23 10:15 UTC - Working copy made to /analysis/case01_work.img, hash verified
2026-10-23 11:00 UTC - Analysis started by <name> on working copy only
EOF

# Hash the custody log itself at each update to show the record is intact
sha256sum /evidence/case01_custody.txt >> /evidence/case01_custody_hashes.txt
```

The custody log answers the only question that matters later: can you
prove this evidence is what you claim and nobody altered it. Gaps in the
log are gaps in the case.

## Edge cases

- The system is encrypted and running. Capture memory first (the keys
  may be in it), image live if the tools allow, and never reboot before
  the memory capture.
- The media is failing. Image the most critical partitions first, use
  tools that retry bad sectors, and document every read error.
- Cloud evidence has no disk to image. Use the provider's snapshot and
  export tools, hash the exports, and document the provider's handling
  alongside yours.
- Legal hold conflicts with analysis speed. The hold wins; document the
  constraint and work within it.

## Escalation

- You need the original powered on for analysis: justify it in writing,
  minimize the interaction, and log every command run on it.
- The hash does not match: stop, investigate (bad sector, tool error,
  handling mistake), and do not proceed until the mismatch is explained.
- Multiple examiners need access: the custody log tracks each one;
  copies are cheap, originals are singular.

## Detection and defender view

For defenders, evidence handling is the incident response discipline:
the same imaging and custody process preserves the option of legal
action and keeps the analysis trustworthy. The defender's view is that
every shortcut in handling becomes the attacker's lawyer's argument.
Write blockers, hashing, and custody logs are cheap; compromised
evidence is expensive.

## Key references

- NIST SP 800-86 (Guide to Integrating Forensic Techniques into Incident
  Response).
- RFC 3227 (Guidelines for Evidence Collection and Archiving).
- ACPO Good Practice Guide for Digital Evidence.
