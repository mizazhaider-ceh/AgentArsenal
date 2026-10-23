---
name: binary-patching-techniques-binary-diffing
description: Use when you need to find exactly what changed between two
  binary versions, covering a vendor's security patch, a malware author's update,
  or your own patch verification. Covers byte-level diffing, function-
  level diffing with Diaphora and Ghidra Version Tracking, interpreting
  similarity scores, locating vulnerability fixes in patched binaries,
  and tracking malware evolution across variants. Use when a patch
  Tuesday binary needs analysis, when comparing malware variants, or
  when verifying your own patches changed only what was intended.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: [binary-patching-techniques]
extends: []
parent: binary-patching-techniques
relates: [binary-patching, binary-anti-analysis-bypass]
tools:
  - name: Diaphora
    version: 2.0
  - name: Ghidra
    version: 11.3
  - name: Python
    version: 3.12
---

Binary diffing answers "what changed" without source code: which
functions were added, removed, or modified between two builds. For
defenders, the killer application is patch analysis: diffing a
vulnerable binary against its patched version locates the exact fix,
which reveals the vulnerability and tells you what to hunt for in your
environment. This sub-skill covers the diffing workflow from quick
byte checks to function-level analysis. Scope: diff only binaries you
are authorized to analyze, in an isolated lab, during authorized
security research, DFIR, or patch assessment.

## Quick Workflow

1. Confirm the two binaries are comparable: same architecture, same
   product, adjacent versions.
2. Byte-level first pass: sizes, hashes, and a quick cmp sample.
3. Function-level diff with Diaphora or Ghidra Version Tracking.
4. Review modified functions sorted by lowest similarity (most
   changed first).
5. For patch analysis, read each changed function for the security
   fix pattern.
6. For variant tracking, note added/removed functions and changed
   constants (C2, keys, intervals).
7. Write the diff report: what changed, where, and what it means.

## 1. Byte-level first pass

```bash
ls -l v1.exe v2.exe
sha256sum v1.exe v2.exe

# How different are they, roughly?
cmp -l v1.exe v2.exe | wc -l
# 12 differing bytes  -> tiny patch, likely a hotfix
# 48000 differing bytes -> major rebuild or different toolchain
```

A tiny diff on a security update is the ideal patch-analysis target:
the fix is in those few bytes. A huge diff means the vendor rebuilt
everything; function-level diffing still works but takes longer.

## 2. Function-level diffing with Diaphora

```bash
# Export both binaries (Ghidra or IDA), then diff
python3 diaphora.py v1.sqlite v2.sqlite -o diff_results.sqlite
```

Diaphora matches functions by heuristics (name, CFG hash, constants)
and scores similarity 1.0 (identical) to 0.0 (unrelated). Review order:

1. **Modified, low similarity** (0.3-0.8): the real changes; read each.
2. **Added functions**: new features or new mitigations.
3. **Removed functions**: dead code removal or deleted vulnerable code.
4. **Modified, high similarity** (0.95+): usually compiler noise;
   skim only.

Example output shape:

```text
Modified (similarity < 0.9):
  sub_401200  0.62  validate_input      <- read first
  sub_405500  0.81  parse_header
Added:     sub_40a000  check_bounds     <- new mitigation?
Removed:   sub_403300  old_parser
```

## 3. Ghidra Version Tracking

Ghidra's built-in alternative: create two programs, then use Version
Tracking to correlate functions. It is interactive and visual: matched
functions link, unmatched ones stand out. Best for small binaries or
when you want to read the decompiler side by side. For large binaries
or batch work, Diaphora's scripted output scales better.

## 4. Patch analysis: finding the fix

When v2 is the patched version of vulnerable v1:

```text
Reading a fix in the diff:
  v1:  memcpy(dst, src, len);            // no bounds check
  v2:  if (len > sizeof(dst)) return -1;
       memcpy(dst, src, len);
  -> the vulnerability was a stack buffer overflow in validate_input;
     the fix is a bounds check; the trigger is len > sizeof(dst).
```

From the fix, derive: the vulnerable function's inputs (what attacker
data reaches it), the trigger condition (for detection and hunting),
and whether the fix is complete (does another path reach the same
memcpy?). Write a detection for the trigger: the patch tells you
exactly what malicious input looks like.

## 5. Malware variant tracking

Diffing two samples of the "same" family shows the author's changelog:

```text
Typical variant diff findings:
  Changed constants: C2 domain, XOR key, beacon interval, mutex
  Modified functions: string decoder (new key schedule), C2 routine
  Added functions:   new persistence method, new evasion check
  Removed functions: dead C2 protocol, old packer stub
```

Changed constants are immediate IOC updates. A new evasion check in
the diff warns that your sandbox needs a new bypass. An unchanged
core with rotated strings means your structural YARA rules still
work; rotated imports mean they may not.

## 6. Verifying your own patches

After patching (parent skill), diff original vs patched:

```bash
cmp -l original.exe patched.exe
```

Expect exactly your patch bytes and nothing else. Any extra
differences mean the patching tool modified more than intended;
rebuild the patched copy from a clean original.

## Edge cases

- Different compilers or optimization levels between versions create
  noise diffs; focus on low-similarity functions and changed constants.
- Stripped vs unstripped: function names missing in one binary hurt
  matching; Diaphora's heuristic matching still works but review more.
- Packed binaries: diff the unpacked payloads, not the stubs; stub
  diffs are meaningless.
- .NET assemblies: diff at the IL/metadata level (dnDiff-style)
  rather than native bytes.

- Binaries built with profile-guided optimization reorder functions aggressively; rely on CFG matching, not addresses.

## Escalation

- If the diff suggests a vulnerability being actively exploited and
  your environment is unpatched, escalate to incident response with
  the trigger condition; do not wait for the full writeup.
- If variant diffing reveals a fundamentally new capability (not just
  rotated constants), escalate the family assessment: it may need new
  detections, not just IOC updates.

- If the diff is entirely noise (different toolchain), obtain a same-toolchain build or escalate for manual review of candidate functions.
- If patch analysis reveals an unpatched variant still in your environment, escalate to incident response immediately.

## Detection and defender view

Patch diffing is proactive defense: the day a vendor ships a security
update, diffing tells you what was fixed, which tells you what to hunt
for in logs from before the patch. Build this into the patch cycle for
critical software: diff on release day, hunt for exploitation
indicators the same day. For malware, variant diffs keep detections
current with minimal analyst time; automate the diff and flag only the
interesting changes for human review.

## Key references

- Diaphora:
  https://github.com/joxeankoret/diaphora
- Ghidra Version Tracking documentation:
  https://ghidra-sre.org/
- MITRE ATT&CK: T1587 (Develop Capabilities), for the attacker-side
  context of variant development
- "Patch diffing" methodology references in vendor security research
  blogs (search per vendor for their patch analysis writeups)

- BinDiff (function-level binary diffing):
  https://github.com/google/bindiff
