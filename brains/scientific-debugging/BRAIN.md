---
name: scientific-debugging
kind: brain
description: Use when an agent must find the cause of a malfunction: a bug that will not reproduce reliably, a system behaving differently than expected, a failing test with an unclear cause, or any technical problem where guessing has replaced understanding. Provides scientific debugging reasoning: reproduce first, change one variable at a time, binary-search the cause, distrust your assumptions before your tools, and instrument before guessing. Load this brain when the fix must address the real cause, not the symptom that was easiest to blame.
version: 1.0.0
provides:
  - Reproduce-first discipline
  - One-variable experiment design
  - Binary search cause narrowing
  - Assumption auditing
  - Instrumentation-before-guessing habit
  - Minimal test case construction
used_by: []
---

Debugging fails when it becomes guessing: change something, hope, repeat. Sometimes you get lucky. Usually you "fix" the symptom, break something else, and meet the bug again next month. Scientific debugging treats the bug as a hypothesis to be tested: reproduce it reliably, narrow the cause systematically, and only then fix it. It matters because the cost of a wrong fix compounds: each guess adds complexity that the next debugger must untangle. The disciplined path is slower per step and faster overall.

## Core mental models

**Reproduce first, fix never before.** If you cannot make the bug happen on demand, you cannot prove you fixed it. The reproduction is the foundation of everything: it turns "sometimes it fails" into a controlled experiment. Invest whatever it takes to get a reliable repro, a script, a sequence, a minimal case. Debugging without a repro is arguing with a ghost.

**The bug is in your assumptions.** When the code "cannot" be wrong, check what you assumed: that the config loaded, that the versions match, that the cache was cleared, that the test hits the code you think it does. Most long debugging sessions end with "oh, it was reading the old config." Audit assumptions explicitly before blaming the logic. The environment lies more often than the code.

**Binary search the cause.** When the failure is somewhere in a large space (a thousand commits, a long pipeline, a big config), do not walk it linearly. Bisect: test the middle, keep the half that fails, repeat. Each test eliminates half the space. This turns a hundred possibilities into seven tests. The same logic applies to code paths, config options, and input ranges. Halve, test, repeat.

**Instrument before guessing.** Add logging, tracing, or a probe that shows what actually happens, then read it. A guess is a theory with no data; an instrumented run is data looking for a theory. The five minutes spent adding the log line saves the fifty minutes spent guessing. When you catch yourself theorizing for more than a few minutes, stop and measure instead.

## Operating checklist

1. Write down the symptom precisely: what happens, when, with what input, in what environment.
2. Build a reliable reproduction: a script or sequence that triggers the bug every time (or with known probability).
3. Check the assumptions first: versions, configs, caches, which code actually runs, which data it reads.
4. Form a hypothesis about the cause, then design the smallest test that could kill it.
5. Change one variable per test. Record each result.
6. If the space is large, bisect it: commits, config halves, input ranges, code paths.
7. Instrument the suspect area: log the actual values, trace the actual path. Read the output.
8. Once found, build the minimal test case: the smallest input that still triggers it.
9. Fix the cause, not the symptom. Then re-run the repro to prove the fix.
10. Add a regression test so the bug cannot return silently. The repro becomes the test.

## Heuristics

- If you have been guessing for 30 minutes, stop and build the repro. You are behind, not ahead.
- "It works on my machine" means the environments differ. Diff the environments, not the code.
- The last change is guilty until proven innocent. Check the recent diff first.
- Intermittent bugs are timing or state bugs. Make timing and state your first suspects.
- Read the error message literally before interpreting it creatively. It usually means what it says.
- Rubber-duck it: explain the system out loud. The flaw often surfaces mid-sentence.
- When the fix feels like a hack, you found the symptom. Keep digging for the cause.
- A bug you cannot explain will return. Understanding is part of the fix.

## Anti-patterns

- **Guess-and-patch.** Changing code on hunches without a repro or a test. Fixes nothing reliably, breaks things randomly.
- **Symptom suppression.** Catching the exception, retrying blindly, or restarting on a schedule instead of finding the cause.
- **Blaming the tools.** "The compiler is broken" before checking your own assumptions. It is never the compiler. (Almost never.)
- **Skipping the repro.** "I know what it is" followed by a fix that does not fix it, twice.
- **No regression test.** Fixing the bug and leaving the door open for its return.

## Worked example

Users report intermittent login failures, roughly one in twenty attempts, no pattern by user. Guessing would start with the auth code. Scientific debugging starts with the repro: a script hammering logins shows the same one-in-twenty rate in staging. Assumptions audit: same code, same config, but staging and prod share nothing else... except the auth service calls a time API. Instrumentation: log the token timestamps on failures. Pattern found: failures cluster when the app server's clock drifts more than 30 seconds from the token issuer. Root cause: no NTP sync on two app servers; tokens generated on one are "from the future" on the other. Binary search was unnecessary; the assumption audit found it. Fix: enable NTP everywhere and add clock-skew monitoring. Regression test: a login with a skewed clock now alerts instead of failing silently. The auth code was innocent all along. The environment was the bug.
