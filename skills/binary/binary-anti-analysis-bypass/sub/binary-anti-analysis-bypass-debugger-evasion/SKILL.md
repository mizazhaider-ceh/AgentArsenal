---
name: binary-anti-analysis-bypass-debugger-evasion
description: Use when a binary detects debuggers during authorized lab
  analysis and you need to identify and defeat each detection method.
  Covers the Windows debugger detection APIs (IsDebuggerPresent,
  CheckRemoteDebuggerPresent, NtQueryInformationProcess), PEB flag
  patching, ScyllaHide profiles, exception-based tricks (INT3, INT2D),
  timing-assisted debugger detection, and validating the bypass. Use when
  a debugger will not attach, when the sample exits under a debugger but
  runs free, or when hardening your analysis setup.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: [binary-anti-analysis-bypass]
extends: []
parent: binary-anti-analysis-bypass
relates: [malware-sandbox-analysis, binary-patching-techniques]
tools:
  - name: x64dbg
    version: 2025.06
  - name: ScyllaHide
    version: 1.4
  - name: Ghidra
    version: 11.3
  - name: Python
    version: 3.12
---

Debugger detection is the first gate most protected binaries check:
"am I being watched?" The checks range from one API call to layered
tricks with exceptions and timing. This sub-skill catalogs the
detection methods and the matching bypass for each, for the parent
anti-analysis-bypass skill. Scope: bypass debugger detection only on
binaries you are authorized to analyze, in an isolated lab, during
authorized DFIR, malware research, or defensive testing.

## Quick Workflow

1. Reproduce: run free vs under debugger; confirm the behavior gap.
2. Hunt statically: imports and strings naming debugger checks.
3. Classify each check: PEB flag, API query, window/process scan,
   exception trick, timing.
4. Apply the matching bypass, one check at a time.
5. Verify the sample proceeds; look for the next check.
6. Document the bypass set for reproducibility.

## 1. PEB flag checks

```text
IsDebuggerPresent()  -> reads PEB.BeingDebugged (offset 0x02)
PEB.NtGlobalFlag     -> 0x70 when debugged (offset 0x68/0xBC)
Heap flags           -> heap ForceFlags when debugged
```

Manual bypass in x64dbg: open the PEB (dump at FS:[0x30] 32-bit or
GS:[0x60] 64-bit), zero BeingDebugged, clear NtGlobalFlag to 0, and
fix heap flags. Script it so every attach starts clean:

```text
x64dbg script shape:
  mov byte ptr fs:[30h+2], 0     ; BeingDebugged = FALSE
  ; repeat for NtGlobalFlag and heap Flags/ForceFlags
```

This defeats IsDebuggerPresent and direct PEB readers with no code
patches to the sample.

## 2. API query checks

```text
CheckRemoteDebuggerPresent(hProcess, &flag)
NtQueryInformationProcess(hProcess, ProcessDebugPort, ...)  -> nonzero port
NtQueryInformationProcess(hProcess, ProcessDebugObjectHandle, ...)
NtQuerySystemInformation(SystemKernelDebuggerInformation)
```

Bypass options: ScyllaHide hooks these and returns clean values
(easiest); or hook them yourself; or patch each call site to skip the
check. ScyllaHide's NtQueryInformationProcess options cover the
ProcessDebugPort, ProcessDebugObjectHandle, and ProcessDebugFlags
classes that matter.

## 3. ScyllaHide profiles

1. In x64dbg: Plugins, ScyllaHide, Options.
2. Select the profile matching your debugger (x64dbg).
3. Enable: PEB BeingDebugged, PEB NtGlobalFlag, PEB HeapFlags,
   NtQueryInformationProcess, NtSetInformationThread (anti-thread-hide
   defense), GetTickCount (optional), and window hooks.
4. Apply, then restart the target under the debugger.

Verify per check: attach, break at the check, and confirm it returns
"not debugged". If one check still fires, enable the specific option
for it rather than turning everything on blindly; minimal hiding is
more stable.

## 4. Window, process, and driver scans

```text
FindWindowA("x64dbg", NULL) / FindWindowA("OLLYDBG", NULL)
CreateToolhelp32Snapshot + Process32First/Next scanning for
  windbg.exe, ollydbg.exe, x64dbg.exe, ida.exe
DeviceIoControl / driver checks for known analysis drivers
```

Bypasses: ScyllaHide's window hooks hide debugger windows; rename
your debugger executable and window titles for process scans; for
driver checks, patch the comparison or hook the query. Static hunt
tells you which names it scans for:

```bash
floss sample.exe | grep -iE "ollydbg|x64dbg|windbg|ida\.exe|immunity" | sort -u
```

## 5. Exception tricks

```text
INT3 (0xCC):       debugger swallows the breakpoint exception;
                   without a debugger the SEH handler runs.
INT2D:             kernel breakpoint; debugger-specific behavior.
OutputDebugString: with no debugger, sets LastError to a value;
                   with a debugger, does not (GetLastError trick).
```

Bypasses: configure x64dbg's exception handling to pass these to the
program (Options, Exceptions: ignore INT3 outside your own
breakpoints); for OutputDebugString, ScyllaHide handles the
LastError semantics. Test by breaking at the trick and stepping: the
program's handler must run, not the debugger's.

## 6. Timing-assisted debugger detection

Single-stepping and breakpoints distort timing; checks like
GetTickCount deltas or rdtsc around a function detect the slowdown.
Bypass: avoid stepping through the check (run to a breakpoint after
it), use hardware breakpoints (no INT3 overhead), or hook the timing
API to return consistent values. See the timing-checks sub-skill for
the full treatment.

## Edge cases

- Layered checks calling each other: patching one reveals the next;
  budget time for three or more layers.
- Checks in TLS callbacks before main: set the debugger to break on
  module load, not on entry point.
- Anti-attach (DebugActiveProcess blocked): the sample debugs itself
  or its child; analyze the child or patch the self-debug.
- ScyllaHide detected: some samples fingerprint the hooks; fall back
  to manual PEB patching plus call-site patches.

- Debugger checks hidden inside packed layers: unpack first, or the check list is incomplete.

## Escalation

- If every hiding method is detected, escalate to hypervisor-level
  tracing or bare-metal analysis with remote logging.
- If the sample's anti-debug is a commercial protector's, assess
  whether defeating it is in scope before investing days.

- If the binary uses a protector's anti-debug as part of licensing on software you are assessing, confirm the assessment scope covers defeating it before investing further.
- If checks are timed to the debugger attach window, escalate to a scripted attach-and-hide so the window is hit reliably.

## Detection and defender view

Debugger checks are dual-use signals: in malware they indicate
evasion intent (log the specific checks as family fingerprints); in
your own software they are tamper resistance to evaluate during
assessments. For the SOC, a process calling CheckRemoteDebuggerPresent
then exiting is worth a hunt query: legitimate software rarely does
this. Keep your ScyllaHide profiles and PEB scripts versioned with
the lab docs so every analyst hides the same way.

## Key references

- ScyllaHide:
  https://github.com/x64dbg/ScyllaHide
- x64dbg documentation:
  https://x64dbg.com/
- MITRE ATT&CK: T1622 (Debugger Evasion)
- Practical Malware Analysis (Sikorski and Honig), Chapter 17
  (anti-debugging techniques)
- Microsoft PEB documentation:
  https://learn.microsoft.com/en-us/windows/win32/api/winternl/ns-winternl-peb
