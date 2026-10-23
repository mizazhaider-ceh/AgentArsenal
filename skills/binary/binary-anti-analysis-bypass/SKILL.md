---
name: binary-anti-analysis-bypass
description: Use when a binary under authorized lab analysis resists
  analysis resists debugging or sandboxing, covering debugger detection,
  timing checks, VM and
  sandbox fingerprinting, or stalling tricks. Covers identifying each
  check statically and dynamically, bypassing them with debugger settings,
  patches, hooks, or environment hardening, and validating that the
  bypass worked by comparing behavior before and after. Use when a sample
  exits immediately in the sandbox, when a debugger will not attach, or
  when dynamic analysis shows suspiciously little activity.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [malware-sandbox-analysis, binary-patching-techniques]
tools:
  - name: x64dbg
    version: 2025.06
  - name: ScyllaHide
    version: 1.4
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.2
  - name: Ghidra
    version: 11.3
---

Defensive binaries and malware both use anti-analysis: checks that detect
debuggers, virtual machines, and sandboxes, then hide behavior or exit.
For the analyst this is a gate, not a verdict; a sample that quits in the
sandbox is usually evading, not benign. This skill covers recognizing the
common checks, defeating each class with the right technique, and proving
the bypass worked. Scope: bypass anti-analysis only on binaries you are
authorized to analyze, inside an isolated lab, during authorized DFIR,
malware research, or defensive testing. These techniques exist so analysts
can observe hostile code safely; never use them to evade detection on
systems you do not own.

## Quick Workflow

1. Establish the baseline: run the sample in the sandbox and in the
   debugger, record exactly how it misbehaves (instant exit, no network,
   error message).
2. Identify the check statically: search for debugger, VM, and timing
   APIs and strings (see technique sections).
3. Pick the bypass class: hide the debugger (ScyllaHide, PEB patch),
   patch the check, hook the API, or harden the environment.
4. Apply one bypass at a time and re-run; behavior change proves which
   check was gating.
5. Iterate until the sample shows its real behavior (network, dropped
   files, injection).
6. Document every bypass applied: the next analyst must reproduce your
   environment to reproduce your results.
7. Re-run the full analysis pipeline (sandbox, memory capture) with the
   bypasses in place.

## 1. Debugger evasion: the API checks

The classic checks and their signatures:

```text
IsDebuggerPresent()            -> PEB.BeingDebugged flag
CheckRemoteDebuggerPresent()   -> kernel query
NtQueryInformationProcess(ProcessDebugPort) -> debug port set
FindWindow("x64dbg", ...) / FindWindow("OLLYDBG") -> window title scan
OutputDebugString + GetLastError trick -> debugger consumes the string
int 3 / int 2D exceptions      -> debugger swallows them
```

Static hunt:

```bash
# Strings and imports that name the check
floss sample.exe | grep -iE "debug|DbgUi|NtQueryInformationProcess" | sort -u
```

Bypass ladder, easiest first:

1. **ScyllaHide**: enable the profile matching your debugger (x64dbg),
   tick PEB flags, NtQueryInformationProcess, and window hooks. This
   defeats most API checks with zero patching.
2. **Manual PEB patch**: in x64dbg, dump the PEB and zero BeingDebugged
   (offset 0x2), NtGlobalFlag, and heap flags. Script it so every run
   starts clean.
3. **Patch the check**: NOP the call or force its return to false
   (see binary-patching-techniques). Best when only one check gates.
4. **Hook the API**: intercept IsDebuggerPresent to always return FALSE.
   Cleanest when several checks call the same API.

Verify: the sample now proceeds past the point where it exited. If it
exits later at a new point, there is a second check; repeat.

## 2. Timing checks: sleep, stalls, and tick counts

```text
Sleep(600000)                  -> outlasts short sandbox runs
GetTickCount deltas             -> detects breakpoints (time froze)
rdtsc deltas                    -> detects single-stepping / emulation
NtDelayExecution                -> kernel-level sleep
```

Static hunt: imports of Sleep, GetTickCount, QueryPerformanceCounter, or
inline `rdtsc` bytes (`0F 31`).

Bypasses:

- **Longer timeout**: submit to the sandbox with 10+ minutes instead of
  2. Defeats pure sleeps with no patching.
- **Patch the sleep**: in the debugger, NOP the Sleep call or patch its
  argument to 0. One patch, immediate behavior.
- **Accelerate time**: hook GetTickCount to return inflated values so
  delta checks pass.
- **rdtsc handling**: x64dbg can trap rdtsc; alternatively patch the
  comparison after the second rdtsc to always succeed.

```text
Example patch shape:
  Before:  FF 15 .. .. .. ..   call Sleep        ; Sleep(600000)
  After:   90 90 90 90 90 90   nop x6
```

Confirm by timestamp: the sample's first network beacon should now appear
seconds after start instead of minutes.

## 3. VM and sandbox fingerprinting

What they check, grouped:

```text
Registry:  HKLM\HARDWARE\...\SystemBiosVersion containing VBOX, QEMU, VMWARE
Files:     C:\windows\system32\drivers\vmmouse.sys, vmhgfs.sys, VBoxGuest
Processes: vmtoolsd.exe, vboxservice.exe, qemu-ga.exe
MAC:       08:00:27 (VirtualBox), 00:05:69 / 00:0C:29 / 00:50:56 (VMware)
WMI:       Win32_ComputerSystem Manufacturer = "innotek GmbH", "VMware, Inc."
CPUID:     hypervisor bit (bit 31 of ECX, leaf 1)
```

Bypass strategy is environmental, not per-sample:

1. Rename or remove guest-tool artifacts from the analysis VM image.
2. Change the virtual MAC to a real vendor OUI.
3. Scrub registry strings the sample checks (snapshot a hardened image
   once, reuse it).
4. For CPUID hypervisor bit: some hypervisors can mask it; otherwise
   patch the check in the sample.

Static hunt to learn exactly which artifact a sample checks:

```bash
floss sample.exe | grep -iE "vbox|vmware|qemu|virtual|xen" | sort -u
```

Example output shape:

```text
VBoxGuest
SELECT * FROM Win32_ComputerSystem
08:00:27
```

That output tells you the exact three things to scrub or spoof. Always
let the sample tell you what it checks before you harden blindly.

## 4. Stalling and logic bombs

Beyond sleeps: samples that require user interaction (mouse movement,
document scroll), require a reboot to continue (RunOnce staging), or wait
for a date. Handle each:

- Interaction checks: enable simulated user activity in the sandbox
  profile; in manual analysis, move the mouse and click while stepping.
- Reboot staging: let the VM reboot with the snapshot chain intact, or
  manually run the staged payload from its persistence location.
- Date checks: set the VM clock forward in a snapshot (never on the
  host), or patch the GetSystemTime comparison.

## 5. Validating the bypass

A bypass is proven, not assumed. Validation protocol:

1. Baseline run (no bypass): record behavior (exit code, API count,
   network events).
2. Bypass run: record the same metrics.
3. The delta must show new malicious behavior (beacons, drops, injection),
   not just a longer run doing nothing.
4. Revert the bypass and confirm the sample goes quiet again
   (proves the bypass caused the change, not luck).

```bash
# Compare sandbox API call volume as a rough signal
jq '[.behavior.processes[].calls | length] | add' baseline.json
jq '[.behavior.processes[].calls | length] | add' bypassed.json
```

If the bypassed run shows 10x the API calls and new network traffic, the
gate is open. Document the exact bypass set with the report; "sample
analyzed with ScyllaHide default profile plus Sleep patched at file
offset 0x1234" is reproducible, "we got it working" is not.

## Edge cases

- Layered checks: debugger check, then timing check, then VM check in
  sequence. Defeat one at a time; patching all at once hides which one
  mattered and can break the sample.
- Checks in TLS callbacks or entry-point obfuscation: the check runs
  before main(). Set breakpoints on module load, not on main.
- Samples that behave differently under any debugger even with hiding:
  fall back to sandbox-only analysis with a hardened image, or to
  bare-metal detonation.
- Anti-bypass: some samples detect ScyllaHide's hooks. Then patch the
  check directly instead of hiding the debugger.
- Legitimate protectors: commercial software uses the same techniques
  (Themida, VMProtect). The bypass methods are identical; the
  authorization boundary is what differs.
- Over-patching: NOPing too aggressively can remove initialization the
  payload needs. Patch minimally and smoke-test.
- 64-bit PEB offsets differ from 32-bit; use the right offsets for the
  target bitness or your manual PEB patch hits the wrong field.

## Escalation

- If the sample detects every hiding technique and patching breaks it,
  escalate to bare-metal analysis or to tracing via Intel PT / hypervisor
  introspection; some samples only yield to invisible observation.
- If bypass reveals worm-like spreading or destructive behavior,
  escalate to the incident lead before continuing; the analysis
  environment gets tighter, not looser.
- If the anti-analysis is custom and undocumented after serious effort,
  escalate to a reverse engineer for a dedicated unpacking/dev obfuscation
  pass.
- If you cannot determine whether a check is anti-analysis or legitimate
  tamper protection on software you are assessing, stop and clarify scope
  before bypassing further.

## Detection and defender view

Every evasion technique you bypass is a detection idea. IsDebuggerPresent
before network activity is itself suspicious; WMI queries for VM vendor
strings in a process that then exits is a sandbox-evasion signal worth a
Sigma rule. Feed the specific artifacts (registry keys queried, MAC OUIs
checked, window titles scanned) to threat intel: they fingerprint the
malware family as surely as a C2 domain. For defenders hardening their own
detection lab, this skill runs in reverse: build the hardened image once
(scrubbed artifacts, realistic MAC, guest tools removed) and every future
detonation benefits. Track evasion trends across samples; a sudden rise in
a new check (a novel timing trick) is intel about the tooling your
adversaries are adopting.

## Key references

- x64dbg documentation:
  https://x64dbg.com/
- ScyllaHide (anti-anti-debug plugin):
  https://github.com/x64dbg/ScyllaHide
- MITRE ATT&CK: T1622 (Debugger Evasion), T1497 (Virtualization/Sandbox
  Evasion), T1497.001 (System Checks), T1497.003 (Time Based Evasion)
- Practical Malware Analysis (Sikorski and Honig), Chapter 16
  (anti-disassembly) and Chapter 17 (anti-debugging concepts)
- MITRE ATT&CK T1497 sub-techniques:
  https://attack.mitre.org/techniques/T1497/
- Al-Khaser (open-source anti-analysis test tool, for validating your
  hardened lab):
  https://github.com/LordNoteworthy/al-khaser
