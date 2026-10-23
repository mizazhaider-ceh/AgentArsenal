---
name: ctf-competition-playbook-challenge-triage
description: Use when triaging CTF challenges at the start of an event,
  re-triaging mid-event, or deciding what to work on next. Covers the
  first-30-minutes triage pass, classifying challenges by category and
  effort, reading point values and solve counts as difficulty signals,
  spotting quick wins (source provided, low points, known patterns),
  assigning owners, and running hourly re-triage. Use when the event
  starts, when new challenges release, when the team is misallocated, or
  when choosing between candidate challenges.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-competition-playbook
requires: [ctf-competition-playbook]
extends: []
relates: [ctf-competition-playbook, ctf-crypto-challenges]
tools:
  - name: Python
    version: 3.12
---

Triage is the highest-leverage 30 minutes of a CTF: correctly sorting
challenges into quick wins, mediums, and hard-skips determines where
every hour goes. This sub-skill covers the authorized triage method:
the opening pass, the signals that predict solvability, owner
assignment, and the re-triage habit that keeps the team on the best
challenges as information arrives. Scope is authorized competitions.

## Quick Workflow

1. In the first 30 minutes, open every challenge; spend max 5
   minutes each on the triage questions.
2. For each challenge record: category, points, artifacts given,
   source or no source, solve count, and a difficulty guess.
3. Flag quick wins: low points plus source, or a pattern the team
   recognizes instantly.
4. Flag likely time sinks: high points, no source, novel
   construction, zero solves after hours.
5. Assign owners to quick wins first, then mediums; hard challenges
   get one scout, not the whole team.
6. Post the triage board in the shared notes where everyone sees it.
7. Re-triage hourly and on every new challenge release; update
   guesses with solve-count data.
8. Protect the board: one owner per challenge, no unassigned work on
   quick wins.

## 1. The 5-minute triage questions

For each challenge, answer fast:

1. What do I get? (binary, URL, file bundle, text blob, nothing yet)
2. Is there source code? (Yes: difficulty drops a full tier.)
3. What category and subcategory? (web/sqli vs web/crypto-hybrid
   need different owners.)
4. Points vs the event's scale? (150/500 is different from 150/3000.)
5. How many solves? (Many solves: tractable. Zero solves after 6
   hours: hard or broken.)
6. Do I recognize the pattern? (Seen it: quick win. Novel: budget
   carefully.)
7. What is the first concrete step? (If you cannot name one in 30
   seconds, it is not a quick win.)

If question 7 has no answer, mark it `needs-scouting` and move on;
do not start solving during triage.

## 2. Reading the signals

```text
Strong quick-win signals:
  + source code provided, under ~200 lines
  + low points relative to the event max
  + high solve count early (the crowd has validated it)
  + category matches a team strength
  + challenge name hints the bug ("jwt-none", "ssti-bakery")

Strong time-sink signals:
  - no source, large binary, custom protocol
  - very high points with few solves
  - "misc" category with vague description (often long)
  - requires chaining 3+ techniques
  - zero solves and no organizer response to questions
```

Solve counts are the best mid-event signal: a challenge with 40
solves is proven tractable regardless of your first impression.
Re-check counts hourly; a sudden spike means someone published a
hint or the intended path clicked for the crowd.

## 3. The triage board

```text
## Triage board (updated 14:30)
QUICK WINS (do first)
  web/jwt-admin      150  src   owner: izaz    status: solving
  crypto/caesar-salad 100  no-src owner: mariam status: done
MEDIUM (owners assigned)
  pwn/heap-note      300  src   owner: izaz    status: stuck (swap at 15:00)
  rev/vm-me          250  src   owner: chen    status: looking
HARD / SCOUT ONLY
  crypto/lattice-4   500  src   one scout: mariam, 60 min cap
SKIP FOR NOW
  misc/quantum-dreams 400  vague, 0 solves
```

Keep it in the shared notes, top of the file. The captain scans it,
not the chat history. Statuses use the fixed vocabulary from the
team-roles sub-skill.

## 4. Owner assignment rules

- Quick wins: assign immediately, strongest matching player first.
- Mediums: assign by category lead's judgment; one owner each.
- Hards: one scout with a time cap (60-90 min); the scout's job is
  a better difficulty estimate, not a solve.
- Nobody owns two quick wins at once; finish or hand off before
  claiming another.
- Unassigned quick wins are a bug: the captain assigns them within
  the hour.

## 5. Re-triage: hourly and on release

Every hour (captain's time call), spend 10 minutes:

1. Update solve counts on the board.
2. Move challenges whose status changed (stuck mediums become
   hard, scouted hards become mediums with a plan).
3. Reassign freed owners to the best available work.
4. Kill anything over budget with no path (mark honestly).

On new challenge releases: batch-triage them in 10 minutes, do not
let each release interrupt deep work. New releases late in the event
are often quick wins designed to keep the scoreboard moving; check
them before assuming they are hard.

## 6. Category-specific triage heuristics

- Web: source provided means read the routes first; the bug is
  usually in the least-reviewed route. No source: check JS and
  headers before deep fuzzing.
- Pwn: `checksec` in the first minute; no-NX plus win function is
  the fastest pwn solve that exists.
- Rev: `strings` and `file` first; packed or VM means budget up.
- Crypto: parameters tell all; n/e/c with e=3 is a 10-minute
  challenge, custom ciphers need source reading.
- Forensics: `file` plus `binwalk` plus `strings` triages most
  artifacts in 5 minutes; huge pcaps need a plan, not diving in.
- OSINT: the challenge text is the triage; every noun is a search
  seed, and metadata checks take 2 minutes.

## Edge cases

- The event has dynamic scoring: point values drop as solves rise;
  prioritize high-current-value challenges, not original values.
- Gated challenges (unlock by solving others): factor the unlock
  chain into triage; a medium guarding three quick wins outranks a
  lone hard.
- The team is solo: triage twice as ruthlessly; skip anything
  without a clear first step until quick wins are exhausted.
- The scoreboard hides solve counts: fall back to point values and team
  chatter; ask in the event chat which challenges are tractable.
- A challenge's category label is misleading (crypto labeled misc):
  triage by artifacts, not labels; the first 5 minutes reveal the true
  category.

## Escalation

- Triage says everything is hard: the event may be genuinely hard
  (or your triage is calibrated wrong); pick the least-hard medium
  and timebox a scout, then recalibrate from what you learn.
- A challenge looks broken (contradictory files, impossible
  setup): document evidence, ask organizers once, mark skip, move
  on; do not let one broken challenge consume triage cycles.
- The board keeps diverging from reality: shorten the re-triage
  interval to 30 minutes until it stabilizes.
- Two scouts disagree on difficulty: trust the one who named a concrete
  first step; vague optimism loses to specific plans.

## Detection and defender view

Organizers design triage signals deliberately: point values, solve
counts, and challenge ordering are the intended difficulty
communication. They detect unhealthy triage exploitation (like
targeting only low-hanging challenges with shared accounts) through
account and submission patterns. For defenders, the triage mindset
transfers to incident response: triage alerts by severity and
tractability first, then allocate analysts, then re-triage as
evidence arrives.

## Key references

- CTFtime (solve counts and dynamic scoring): https://ctftime.org/
- Trail of Bits CTF wiki: https://github.com/trailofbits/ctf-wiki
- picoCTF practice challenges (triage drills on real difficulty curves):
  https://picoctf.org/
- CTFtime event writeups (how top teams describe their triage):
  https://ctftime.org/
- LiveOverflow CTF methodology videos (triage and workflow).
