---
name: opa-decision-loop
kind: brain
description: Use when an agent must act under time pressure with incomplete information: live incident response, active defense decisions, prioritizing containment vs investigation, or any operation where waiting for perfect data costs more than deciding fast. Provides OODA loop reasoning (observe, orient, decide, act): keep the tempo faster than the adversary, let orientation shape decisions, make reversible decisions quickly and irreversible ones carefully, and close the loop with fresh observation. Load this brain when the situation is moving and the agent must move with it.
version: 1.0.0
provides:
  - OODA loop tempo management
  - Orientation as the decisive phase
  - Reversible vs irreversible decision sorting
  - Decision thresholds under uncertainty
  - Loop-closing feedback discipline
  - Tempo advantage over the adversary
used_by: []
---

OODA stands for Observe, Orient, Decide, Act, and it is a loop, not a line. Fighter pilots use it; incident responders live it. The side that cycles the loop faster, with better orientation, wins the engagement. In security operations the adversary is already looping: they observe your defenses, orient on the gaps, decide, and act. If your loop is slower, you are always responding to their last move. This brain teaches an agent to keep its own loop tight: observe constantly, orient honestly, decide at the right threshold, act, and immediately observe the result.

## Core mental models

**Tempo beats perfection.** A good-enough decision now beats the perfect decision in an hour, when the adversary acts in minutes. Ransomware does not wait for your full forensic picture. The loop rewards speed of cycling, not speed of any single phase. Observe briefly, orient well, decide, act, and let the next loop correct you. Waiting for certainty is a decision too, and usually the wrong one.

**Orientation decides everything.** Observe gives you raw facts; orient turns facts into understanding: what does this mean, what is the adversary doing, what matters most? Two teams with the same observations make different decisions because their orientation differs. Orientation is where your mental models, prior incidents, and biases live. Name your orientation explicitly ("I believe this is automated ransomware, not targeted espionage, because...") so it can be challenged and updated.

**Sort decisions by reversibility.** Reversible decisions (isolate a host, block an IP, revoke a session) should be made fast and undone if wrong. Irreversible decisions (wipe a server, notify customers, shut down production) deserve a slower loop and a second opinion. Most incident paralysis comes from treating reversible decisions as irreversible. When in doubt, ask: can I undo this in five minutes? If yes, decide now.

**Close the loop.** Act is not the end. Every action must be followed by observation: did the isolation stop the spread? Did the block break legitimate traffic? An open loop is how you isolate the wrong host and never notice. The loop only works if act feeds back into observe, every single cycle.

## Operating checklist

1. Observe: what are the raw facts right now? Separate facts from interpretations.
2. Orient: what do the facts mean? State your working theory and your confidence.
3. Name the adversary's likely loop: what are they doing while you decide?
4. Sort pending decisions into reversible (decide now) and irreversible (slow down).
5. Set a decision threshold in advance: "If X is confirmed, we isolate immediately."
6. Decide: pick the action that best fits the orientation, at the current tempo.
7. Act: execute cleanly, note the exact time, tell the team what changed.
8. Observe the result: did the action have the intended effect? Any side effects?
9. Update orientation with the new facts. Kill the old theory if the facts killed it.
10. Repeat. Keep a written log of each loop so the timeline survives the chaos.

## Heuristics

- If you have been observing for 20 minutes without deciding, your threshold is too high.
- State your theory out loud (or in the log). Silent theories cannot be corrected.
- Default to the reversible action. You can always escalate; you cannot always undo.
- The adversary's tempo sets your minimum tempo. Match it, then beat it.
- One person decides. A committee does not loop.
- Log as you go. Memory is the first casualty of an incident.
- When orientation is split, pick the theory that explains the most facts with the fewest assumptions.
- A wrong fast decision you correct beats a right slow decision that arrives too late.

## Anti-patterns

- **Analysis paralysis.** Observing forever while the adversary completes their objective. The most common failure.
- **Acting without orienting.** Jumping from observation to action: blocking IPs at random, rebooting servers blindly. Motion without understanding.
- **Open loops.** Acting and never checking the result, so mistakes compound silently.
- **Treating every decision as irreversible.** Slow-walking a host isolation that could be undone in seconds.
- **Frozen orientation.** Clinging to the first theory after the facts changed. The loop must update or it is just a line.

## Worked example

02:14: alerts show mass file renames on three workstations. Observe: facts are encrypted-looking extensions, ransom notes, SMB connections from workstation A to the file server. Orient: working theory is ransomware spreading via SMB, confidence medium-high; adversary's loop is measured in minutes. Reversible decisions: isolate the three workstations and block SMB from them at the firewall (undoable in minutes). Irreversible: wiping anything (deferred). Threshold set: if the file server shows renames, isolate it too. Decide and act at 02:19: hosts isolated, SMB blocked. Observe result: no new renames after 02:21, but the file server already has 400 renamed files, so the threshold triggers and it is isolated as well. Orientation updated: patient zero was workstation A, entry via phishing two hours earlier. Next loop: hunt for other patient-zero candidates. Total time from first alert to containment: under ten minutes, because reversible decisions were never allowed to wait.
