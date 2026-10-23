---
name: root-cause-analysis
kind: brain
description: Use when an agent must find why something really failed: post-incident review after a breach or outage, a recurring bug that keeps coming back, a security control that failed silently, or any problem where the first explanation feels too easy. Provides root cause reasoning models: the five whys, separating proximate triggers from root causes, mapping contributing factors, fixing the system instead of blaming the person, and verifying the fix removes the cause. Load this brain whenever a fix must last instead of just quieting the symptom.
version: 1.0.0
provides:
  - Five whys causal drilling
  - Proximate cause vs root cause separation
  - Contributing factor mapping
  - System fix over blame framing
  - Fix verification against the true cause
  - Repeat-incident pattern recognition
used_by: []
---

Every incident has a story that is too simple. "The server went down because the disk filled up." That is a trigger, not a cause. The disk filled up because logs were never rotated. Logs were never rotated because the base image ships without rotation. The base image ships without rotation because nobody owns the image pipeline. Root cause analysis is the discipline of refusing to stop at the first satisfying answer and drilling until you find the thing that, if fixed, prevents the whole class of failure. It matters because symptom fixes feel productive and change nothing. The disk will fill again.

## Core mental models

**Ask why five times, then once more.** The five whys is a drill, not a ritual. Each answer must be verified, not guessed: check the log, read the config, ask the owner. The chain stops being useful when answers become vague ("because of human error"), which is a signal you took a wrong turn, not that you arrived. A good chain ends at a concrete, fixable system property: a missing check, an unowned process, a default nobody changed.

**Separate the trigger from the cause.** The proximate cause is what set the incident off (the phishing click, the bad deploy). The root cause is what made the trigger possible and uncaught (no MFA, no deploy canary). Fixing only the trigger is mowing the lawn: it grows back. Fixing the root cause changes the soil. When you write up an incident, label each fact as trigger, contributing factor, or root cause, and make sure the fixes map to the root causes.

**Contributing factors are not root causes.** Most incidents have several contributing factors: the alert fired but nobody was on call, the runbook was outdated, the dashboard was down. These matter and deserve fixes, but they are not the root cause. The root cause is the deepest fixable system condition that allowed the failure chain. List all contributors honestly, then keep drilling past them to the one or two conditions that made the chain possible.

**Fix the system, not the person.** "Human error" is where analysis goes to die. People make mistakes at a predictable rate; the system decides whether a mistake becomes an incident. If an engineer can delete the production database with one command, the root cause is not the engineer, it is the missing guardrail. Every "human error" finding should be rewritten as a system question: what allowed it, what failed to catch it, what made it easy?

## Operating checklist

1. Write the timeline first: what happened, in order, with timestamps and sources.
2. State the impact plainly: what broke, for whom, for how long.
3. List candidate causes. Separate triggers, contributing factors, and suspected root causes.
4. Drill each candidate with why, verifying every answer against evidence, not memory.
5. Stop drilling when the answer is a concrete fixable system property, not a vague blame.
6. Check for pattern: has this class of failure happened before? If yes, the last fix missed the root cause.
7. Write fixes for the root cause AND the contributing factors. Both matter.
8. For each fix, state how you will verify it worked (test, metric, drill).
9. Assign every fix an owner and a date. An unowned fix is a wish.
10. Publish the writeup blamelessly. The goal is learning, and blame kills reporting.

## Heuristics

- If the root cause names a person, you have not found the root cause.
- The second occurrence of an incident is a process failure, not bad luck.
- Verify each why with evidence. A guessed why is a story, not analysis.
- The fix must make the failure class impossible or caught, not just this instance unlikely.
- Ask "what made this easy" and "what failed to catch it." Both are root cause territory.
- Simple chains beat complex ones. Prefer the shortest verified causal chain.
- If two teams each think the other owns it, ownership is the root cause.
- A root cause you cannot fix is just a sad fact. Find the nearest fixable link.

## Anti-patterns

- **Stopping at the trigger.** "Disk full" gets a cleanup cron, the unowned image pipeline ships the same bug next quarter.
- **Blaming human error.** Ends the analysis, teaches nothing, guarantees recurrence.
- **Fix theater.** A fix that sounds good but does not touch the causal chain (more training, after the third identical incident).
- **Skipping verification.** Declaring the root cause fixed without a test that proves it.
- **Blameful writeups.** Naming and shaming, which teaches everyone to hide the next incident.

## Worked example

Incident: customer data was exfiltrated through a vendor's compromised account. First story: "the vendor got phished." Drill: why did a phished vendor account reach customer data? Because vendor accounts had the same access as employees. Why? Because the access request form had no vendor tier. Why? Because nobody defined what vendors should be allowed to do. Root cause: no vendor access model and no owner for third-party access. Contributing factors: no MFA on vendor accounts, no alert on bulk export. Fixes: define vendor access tiers with an owner (root cause), enforce MFA and alert on bulk export (contributors), verify with a quarterly access review and a test alert. The phishing was the trigger. The missing access model was the cause. Fix the model and the next phished vendor account reaches nothing.
