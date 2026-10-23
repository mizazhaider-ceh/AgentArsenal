---
name: binary-anti-analysis-bypass-timing-checks
description: Use when a binary uses time to detect analysis, covering long
  sleeps to outlast sandboxes, tick-count deltas to detect breakpoints,
  rdtsc to detect single-stepping or emulation. Covers identifying each
  timing primitive statically and dynamically, bypassing via patching,
  hooking, timeout extension, and accelerated clocks, and validating
  that the sample's real behavior emerged. Use when a sample sleeps
  through detonation, when stepping triggers exits, or when beaconing
  appears only after long delays.
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
  - name: Python
    version: 3.12
  - name: CAPE Sandbox
    version: 2.5
---

Time is the cheapest anti-analysis: Sleep(600000) costs the author one
line and costs the analyst ten minutes per run. Timing checks also
detect the analyst directly: breakpoints freeze time, single-stepping
stretches it, and emulation distorts rdtsc. This sub-skill covers
recognizing each timing primitive and defeating it. Scope: bypass
timing checks only on binaries you are authorized to analyze, in an
isolated lab, during authorized DFIR, malware research, or defensive
testing.

## Quick Workflow

1. Note the symptom: instant exit after a delay, no behavior in short
   runs, exits when stepped.
2. Hunt statically: Sleep, GetTickCount, QueryPerformanceCounter,
   rdtsc bytes (0F 31), NtDelayExecution.
3. Classify: stall (sleep out the clock), delta check (detect the
   debugger), or both.
4. Bypass: extend timeout, patch the sleep, hook the clock, or avoid
   stepping through the check.
5. Verify: behavior appears promptly; beacon timestamps confirm.
6. Document the bypass with the report.

## 1. Stall tactics: sleeps and delays

```text
Sleep(600000)              10-minute stall, outlasts default sandboxes
NtDelayExecution(neg 10min) kernel-level equivalent
Loop of Sleep(1000) x 600  same effect, harder to patch in one place
WaitForSingleObject(timeout) stall disguised as synchronization
```

Bypasses, easiest first:

1. **Longer detonation**: submit with a 15-minute timeout. No patching,
   always valid, just slow.
2. **Patch the sleep**: NOP the call or zero its argument in the
   debugger. Immediate.
3. **Hook Sleep**: intercept and return instantly; cleaner than
   patching when sleeps are scattered.

```text
Patch shape:
  Before:  68 00 09 27 00   push 0x270900 (600000 ms)
           FF 15 .. .. ..   call Sleep
  After:   68 00 00 00 00   push 0
           FF 15 .. .. ..   call Sleep
```

For looped sleeps, patch the loop counter or break the loop condition
rather than each Sleep call.

## 2. Tick-count delta checks

```text
t0 = GetTickCount();
<operation that should be fast>
t1 = GetTickCount();
if (t1 - t0 > THRESHOLD) exit();   // a breakpoint froze time
```

Also seen with QueryPerformanceCounter and timeGetTime. The check
detects breakpoints and single-stepping inside the measured region.

Bypasses:

- **Do not step through it**: set a breakpoint after the check and run
  to it; the delta stays small.
- **Hook GetTickCount**: return t0 + epsilon always, so deltas never
  trip. ScyllaHide has a GetTickCount option.
- **Patch the comparison**: flip the conditional jump after the delta
  check so it never exits.

Static hunt: look for two GetTickCount calls with a subtraction and
compare between them; the threshold constant tells you how sensitive
it is (small threshold = aggressive, trips on any debugger pause).

## 3. rdtsc checks

```text
rdtsc                    ; 0F 31, reads timestamp counter
mov [t0], eax
<operation>
rdtsc
sub eax, [t0]
cmp eax, THRESHOLD
ja  debugger_found
```

rdtsc detects single-stepping (each step costs thousands of cycles)
and emulation (emulators distort the counter). Variants use rdtscp or
compare ratios of rdtsc to GetTickCount.

Bypasses:

- x64dbg can intercept rdtsc (set options to handle it); the
  returned values stay consistent.
- Run, do not step, through measured regions.
- Patch the comparison after the delta, same as tick-count checks.
- For ratio checks (rdtsc vs GetTickCount), hook both consistently
  or patch the final verdict.

## 4. Sandbox-timeout evasion patterns

Beyond raw sleeps, samples detect short detonations indirectly:

- **Delayed C2**: first beacon scheduled 20+ minutes out; short runs
  see nothing. Fix: long timeout or patch the schedule.
- **Reboot persistence then wait**: the payload only runs after
  reboot; detonate with a reboot step.
- **Idle detection**: GetLastInputInfo waits for user inactivity
  (ironically) or activity before running. Fix: simulate input in
  the sandbox profile.

```bash
# Confirm delayed beaconing from a long pcap
tshark -r long.pcap -Y "dns" -T fields -e frame.time_epoch -e dns.qry.name \
  | sort -n | head -5
# first C2 DNS at T+1200s -> the sample waited 20 minutes
```

## 5. Validation

1. Baseline: short run shows nothing; note the exact quiet duration.
2. Bypassed: behavior (beacon, drop, injection) appears within seconds
   of start.
3. Timestamp proof: first beacon at T+5s instead of T+600s, from the
   pcap, not from memory.
4. Revert: restore the sleep, confirm quiet again.

Document which primitive was bypassed and how; "patched Sleep at file
offset 0x1234" reproduces, "made it faster" does not.

## Edge cases

- Nested timing: a sleep, then a delta check, then another sleep.
  Defeat outside-in and re-test after each.
- Timing checks on the C2's schedule (beacon only at certain hours):
  set the VM clock or patch the schedule comparison.
- Anti-hook timing: the sample measures its own Sleep to detect
  hooking (hooked Sleep returns too fast). Then patch the argument
  instead of hooking, or extend the real timeout.
- Kernel-mode timing: user-mode hooks do not affect
  NtDelayExecution measured in kernel; patch at the call site.

- Sleep calls with randomized durations: patching one constant is not enough; hook the API or extend the timeout instead.

## Escalation

- If timing is enforced by a remote server (C2 only responds after
  a delay), lab bypasses cannot help; note it and analyze the
  offline-capable parts.
- If the sample combines timing with VM checks such that no lab
  configuration satisfies it, escalate to bare-metal analysis.

- If the sample's schedule depends on a C2 command (the server tells it when to act), lab bypasses cannot trigger it; note the gap and analyze the offline-capable parts.
- If timing checks are enforced in a driver or kernel component, escalate: user-mode techniques do not reach them.

## Detection and defender view

Timing behavior is detection signal: a process that sleeps 10 minutes
before its first network connection is suspicious regardless of what
follows; EDR rules on sleep-then-beacon patterns catch whole classes.
Log the timing profile per family (stall duration, beacon delay);
when a new sample shares the profile, that is a clustering signal.
For sandbox operators, the lesson is operational: default 2-minute
timeouts miss an entire class of malware, so tier timeouts by triage
priority.

## Key references

- MITRE ATT&CK: T1497.003 (Time Based Evasion)
- x64dbg documentation:
  https://x64dbg.com/
- ScyllaHide:
  https://github.com/x64dbg/ScyllaHide
- CAPE Sandbox documentation (timeout configuration):
  https://capev2.readthedocs.io/
- Practical Malware Analysis (Sikorski and Honig), Chapter 17
  (anti-debugging: timing checks)
