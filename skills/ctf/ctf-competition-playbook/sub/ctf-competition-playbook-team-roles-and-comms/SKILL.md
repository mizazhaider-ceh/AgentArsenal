---
name: ctf-competition-playbook-team-roles-and-comms
description: Use when organizing a CTF team for an upcoming or live
  competition. Covers defining team roles (captain, category leads,
  floater, scribe), setting up communication channels and conventions,
  running effective help requests, managing handoffs when players rest or
  get stuck, and keeping shared notes useful under time pressure. Use when
  forming a team, when communication is breaking down mid-event, or when
  you need operating procedures that keep parallel work from colliding.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-competition-playbook
requires: [ctf-competition-playbook]
extends: []
relates: [ctf-competition-playbook, ctf-osint-challenges]
tools:
  - name: Python
    version: 3.12
  - name: git
    version: 2.45
---

A CTF team without roles duplicates work, loses findings, and stalls
when someone sleeps. This sub-skill defines the lightweight role
structure and communication conventions that keep a team fast for the
whole event. It is process, not theory: who does what, what gets said
where, and how handoffs work. Scope is authorized competitions only.

## Quick Workflow

1. Before the event, assign the captain, category leads, and a scribe;
   small teams double up roles explicitly.
2. Create one channel per category plus an announcements channel;
   agree on naming before the start.
3. Set the notes convention: every challenge has an owner and a
   status, updated in the shared doc, not in chat.
4. During the event, leads triage their categories and reassign
   stuck challenges; the captain watches overall points and time.
5. Use structured help requests (what, tried, stuck-at, notes link)
   instead of vague calls for help.
6. Hand off cleanly when resting or swapping: status, findings, and
   next step in the notes.
7. In the last hour, the captain calls the stop on new work and runs
   the submission sweep.
8. After the event, the scribe's notes become the writeup skeleton.

## 1. Role definitions

- Captain: owns the clock and the points. Runs triage, reassigns
  stuck work, calls sleep rotations, and makes the final-hour stop
  decision. Does not own challenges unless the team is tiny.
- Category leads (web, pwn, rev, crypto, forensics, osint): own
  triage and assignment inside their category; the person others ask
  first for that category.
- Floater: no fixed category; picks up quick wins anywhere, verifies
  others' partial solves with fresh eyes, and covers gaps.
- Scribe: keeps the notes doc and flags log current; in small teams
  this is a 10-percent duty shared by everyone, not a full role.
- Everyone: updates their own challenge status; asks for help early;
  commits solvers to the repo.

For a 2-3 person team: captain doubles as a lead, everyone scribes
their own work, and the floater role disappears. Write the assignments
down; verbal agreements evaporate at hour 10.

## 2. Channel and notes conventions

```text
#announcements  -> solves, bloods, organizer messages, time calls (read-only-ish)
#web  #pwn  #rev  #crypto  #forensics  #osint  -> working discussion per category
#general        -> logistics, food, sleep rotation
```

Notes doc format (one shared file, updated live):

```text
## web/jwt-admin (200 pts) -- owner: izaz -- status: solving
Findings: alg none rejected; secret brute force running (rockyou, 40%).
Next: try kid header injection; source shows key lookup by kid.
Solver: ctf-event/web/jwt_admin.py (partial)
```

Status vocabulary (keep it fixed): `untouched`, `looking`,
`solving`, `stuck`, `verifying`, `done`. Fixed words let the captain
scan the doc in seconds.

## 3. Effective help requests

Bad: "web is broken, help". Good:

```text
#web @here stuck: sqli-login (150 pts)
What: login bypass, source shows concatenated query, WAF blocks UNION.
Tried: comment bypasses, tamper space2comment, boolean blind (slow).
Stuck at: need faster exfil; blind gives 1 char/40s.
Notes: notes.md#web/sqli-login -- owner: izaz, 50 min in.
```

The template: challenge, what it is, what you tried, where you are
stuck, time invested, notes link. Anyone reading it can help in under
5 minutes. Set the norm early: asking with context is encouraged,
silent grinding past 45 minutes is not.

## 4. Handoffs: rest, swaps, and fresh eyes

```text
Handoff: pwn/heap-note (300 pts) -- izaz -> mariam
Status: solving. Findings: UAF confirmed, leak works, tcache poison
  fails on remote (libc differs?). Next: identify remote libc from
  the two leaks in solver output. Solver: ctf-event/pwn/heap_note.py
  runs to the poison step locally. Time in: 90 min.
```

A handoff needs: status, findings so far, concrete next step, solver
state, and time invested. The receiver reads the notes, runs the
solver, and continues; no verbal-only handoffs. For sleep rotations in
long events: the captain keeps a simple roster (who sleeps when), and
sleeping players hand off all owned challenges first.

## 5. Captain's time calls

Fixed announcements keep everyone synchronized without meetings:

- T+30min: "Triage done? Post your category's quick-win list."
- Hourly: "Status check: post one line per owned challenge."
- T-3h: "Last call for starting hard challenges."
- T-1h: "Stop new work. Finish partials, verify submissions."
- T-15min: "Submission sweep: check notes for unverified flags."

Short, predictable, in #announcements. No discussion threads there;
discussion goes to category channels.

## Edge cases

- Two people want the same challenge: the lead assigns one owner;
  the other becomes reviewer (fresh eyes later) or takes the next
  challenge.
- A player disappears mid-event: captain reassigns after one
  check-in attempt; the notes doc makes reassignment painless.
- Personality friction under stress: keep feedback about the work
  ("this approach is slow, try X"), not the person; the captain
  de-escalates by reassigning, not by debating.
- Remote vs in-person mix: default to written updates; voice calls
  only for active pairing on one challenge.
- Chat scrolls too fast during a blood race: move coordination to the
  notes doc and keep chat for the single active decision.

## Escalation

- Communication collapses (everyone silent, work duplicated): the
  captain calls a 5-minute reset: everyone posts status, leads
  re-triage, duplicates get merged.
- The notes doc is stale: the scribe (or captain) does a 10-minute
  audit each hour in long events; stale notes are worse than no
  notes because they misdirect helpers.
- Help requests go unanswered: the floater's explicit duty is
  answering them; if there is no floater, the captain assigns
  reviewers round-robin.
- A disagreement about strategy turns personal: the captain separates
  the people (different challenges) and revisits the decision with data
  after 30 minutes.

## Detection and defender view

For organizers, healthy team communication is invisible; unhealthy
patterns are detectable: multiple teams submitting identical flags in
sequence (flag sharing), or one account solving across impossible
category breadth at machine speed (shared accounts or automation
against the rules). Event rules typically require named team members
and prohibit cross-team collaboration; the playbook here stays firmly
inside those lines.

## Key references

- CTFtime team guidelines and fair play norms: https://ctftime.org/
- Trail of Bits CTF wiki (team organization):
  https://github.com/trailofbits/ctf-wiki
- picoCTF team play guides (role splits for small teams):
  https://picoctf.org/
- DEF CON CTF retrospective writeups (communication under pressure).
- HackTheBox CTF team guides (role splits for small teams).
