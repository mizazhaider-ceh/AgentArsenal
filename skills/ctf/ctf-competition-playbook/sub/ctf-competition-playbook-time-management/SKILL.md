---
name: ctf-competition-playbook-time-management
description: Use when managing time during a CTF competition as a player
  or captain. Covers timeboxing stuck challenges, the fresh-eyes rule,
  scheduling sleep in long events, protecting the final hour for
  submissions, deciding when to abandon versus persist, pacing across
  categories, and keeping personal energy up. Use when the clock is
  running, when you have been stuck too long, when planning a 24 or 48
  hour event, or when the team needs rules for stopping work.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-competition-playbook
requires: [ctf-competition-playbook]
extends: []
relates: [ctf-competition-playbook, ctf-web-challenges]
tools:
  - name: Python
    version: 3.12
---

Time is the only resource you cannot get back in a CTF. Skilled players
lose events by spending 4 hours on a 100-point challenge while three
200-point quick wins sit untouched. This sub-skill sets the time rules:
how long to try, when to ask for help, when to quit, and how to pace a
team across the event. Scope is authorized competitions only.

## Quick Workflow

1. Start every challenge with a time budget based on its points and
   your triage guess (quick win: 30 min, medium: 90 min, hard: 3h).
2. Set a visible timer or checkpoint; when it rings, assess honestly.
3. At 45 minutes with no meaningful progress: ask for help or swap
   owners (the fresh-eyes rule).
4. At the budget limit with only partial progress: decide persist or
   abandon using the expected-value check (section 4).
5. Log time spent in the notes; hidden time debt is how events are
   lost.
6. Protect breaks and sleep in long events; schedule them like
   challenges.
7. In the final 60 minutes: no new challenges, only finishing and
   verifying.
8. After the event, compare budgets to actuals and calibrate for next
   time.

## 1. Time budgets by challenge type

| Triage guess | Budget | Checkpoint |
|---|---|---|
| Quick win (low pts, source given) | 30 min | 15 min: do I see the bug? |
| Medium (standard category work) | 90 min | 45 min: help-or-swap rule |
| Hard (high pts, novel) | 3 h | 90 min: persist-or-abandon |
| Unknown | 45 min | 20 min: re-triage, do not drift |

Budgets are per owner, not per challenge; a swap resets the helper's
clock but the challenge keeps its total. Write the budget in the notes
entry when you claim a challenge.

## 2. The 45-minute help-or-swap rule

No meaningful progress in 45 minutes means one of three things: the
triage guess was wrong, you are missing a tool or technique, or you
need fresh eyes. The rule:

1. Post a structured help request (see the team-roles sub-skill).
2. If help unblocks you within 15 minutes, continue with a new
   45-minute budget.
3. If not, swap owners: you take one of their stuck challenges, they
   take yours. Both get fresh eyes, nobody "fails".
4. Log the swap in the notes with the reason; patterns in swaps
   reveal triage weaknesses.

Enforce this socially before the event: agree that swapping is normal
and smart, not a defeat. The rule only works if nobody feels judged.

## 3. Sleep and energy in 24h+ events

- Plan sleep before the event: two 3-hour blocks beat one 6-hour
  block for coverage, and beat zero sleep for performance.
- Schedule explicitly: "izaz sleeps 02:00-05:00, mariam 05:00-08:00".
  Unscheduled sleep happens at the worst moment.
- Keep one person on triage during sleep blocks: they watch for new
  challenge releases and bloods, and keep notes current.
- Handoff before sleeping: every owned challenge gets status,
  findings, and next step in the notes.
- Food and movement: eat real meals, stand up hourly; the
  performance drop from skipping meals is measurable by hour 16.

Solo players in long events: sleep is mandatory, not optional. A
4-hour block at the natural low point (02:00-06:00) preserves more
points than grinding through it.

## 4. Persist or abandon: the expected-value check

At the budget limit, answer honestly:

1. Points remaining divided by estimated time to finish: is the rate
   better than the average untouched challenge?
2. Is the blocker knowledge (I need to learn X) or luck (I need to
   guess Y)? Knowledge blockers sometimes clear with one hint;
   luck blockers rarely do.
3. Has anyone else on the team solved something similar this event?
   If yes, persist with their help. If no, the challenge may be
   genuinely hard.
4. Are there untouched quick wins? If yes, abandon and take them;
   points per hour almost always favors the quick win.

Abandoned is not deleted: mark it `stuck`, keep the notes, and revisit
only if everything else is done.

## 5. Pacing across categories

- Front-load your strongest categories: points early fund morale
  and unlock gated challenges.
- Do not let one category consume the whole team: cap any single
  challenge at its budget even if "it feels close".
- Watch the scoreboard: categories where many teams score are
  tractable; categories where nobody scores are either hard or
  broken, so discount them.
- Bloods (first solves) are worth chasing in your best category
  early; they are worth ignoring elsewhere.

## 6. The final hour protocol

- T-60: captain announces the stop. No new challenges, no new
  techniques on stuck ones.
- T-60 to T-30: finish partials. A 90-percent solve submitted beats
  a 100-percent solve in your head.
- T-30 to T-10: verification sweep. Re-read every notes entry
  marked solving or verifying; submit anything unsubmitted.
- T-10 to end: no changes. Watch the scoreboard, confirm points
  landed, save everything.

The most common final-hour mistake is starting "one quick thing"
at T-45. The rule is absolute because willpower is depleted.

## Edge cases

- A challenge is "almost done" past its budget: grant one 20-minute
  extension, once. If it is still not done, it was not almost done.
- The event releases new challenges mid-way: triage them in a
  10-minute batch; do not let each release interrupt deep work.
- You are solo and everything is stuck: take a 15-minute walk;
  the break resets fixation more reliably than another hour of
  staring.
- A dependency blocks you (waiting for a teammate's output): timebox the
  wait to 20 minutes, then work the next best challenge; idle waiting is
  the worst use of event time.
- You feel guilty resting while others work: rest is scheduled team
  strategy, not slacking; the roster exists so nobody has to feel guilty.

## Escalation

- The whole team is over budget everywhere: call a re-triage;
  the initial difficulty map was wrong, and a fresh pass finds the
  misjudged challenges.
- Morale collapses: the captain names small wins explicitly
  ("three solves in the last hour, we are climbing"); progress
  visibility restores energy faster than pep talks.
- A key player burns out: enforce their rest immediately; a rested
  player tomorrow is worth more than a broken one tonight.
- The event extends or shortens unexpectedly: the captain re-issues time
  calls immediately against the new end time; the final-hour protocol
  always anchors to the real clock.

## Detection and defender view

Organizers watch for time anomalies as integrity signals: solves at
inhuman speed, or flag submissions in patterns suggesting automation
beyond the rules. Legitimate teams show human pacing: bursts of
activity, sleep gaps, and gradual progress. Keeping honest time logs
in your notes doubles as evidence of fair play if questions arise.

## Key references

- CTFtime (event formats and durations): https://ctftime.org/
- Trail of Bits CTF wiki: https://github.com/trailofbits/ctf-wiki
- Deep Work (Cal Newport): timeboxing and attention management
  principles that transfer directly to competition pacing.
- picoCTF time management tips (beginner event pacing):
  https://picoctf.org/
- "Make Time" (Knapp and Zeratsky): prioritization tactics that map to
  challenge selection under a clock.
