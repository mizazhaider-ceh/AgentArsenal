---
name: ctf-competition-playbook
description: Use when preparing for, competing in, or reviewing a CTF
  competition as an individual or team. Covers pre-competition setup
  (tooling, notes, environment), team roles and communication, challenge
  triage and point strategy, time management across the event, solver
  scripting discipline, flag submission hygiene, and post-event review.
  Use when a CTF starts soon, when your team needs operating procedures,
  when deciding which challenges to attempt, or when building a reusable
  competition workflow.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ctf-web-challenges, ctf-osint-challenges]
tools:
  - name: Python
    version: 3.12
  - name: tmux
    version: 3.4
  - name: git
    version: 2.45
  - name: CyberChef
    version: latest
---

Winning CTFs is mostly logistics: the team that triages well, shares
notes cleanly, and spends time on solvable challenges beats the team
with slightly better skills and no process. This skill is the operating
playbook for authorized competitions: setup before the event, roles and
communication during it, triage and time strategy, and review after it.
It applies to jeopardy-style CTFs, the format this playbook assumes.

## Quick Workflow

1. Before the event: set up the shared environment (notes doc, chat
   channels, solver repo, tooling checklist) and assign roles.
2. At start: triage all challenges in the first 30 minutes; every
   challenge gets a category, a difficulty guess, and an owner.
3. Work in parallel: each player owns challenges, updates status in
   the shared notes, and asks for help early rather than silently
   stalling.
4. Script everything: solvers go in the shared repo immediately, with
   the flag format assertion built in.
5. Submit flags carefully: copy exactly, verify the format, confirm
   the points land.
6. Re-triage hourly: drop stuck challenges, reassign fresh eyes,
   chase the point categories you are strongest in.
7. In the final hour: stop starting new challenges; finish partials
   and double-check unsubmitted flags.
8. After the event: write up solves, archive solvers, and review what
   the triage got wrong.

## 1. Pre-competition setup

```bash
# Shared solver repo layout (one per event)
/ctf-event/
  web/  pwn/  rev/  crypto/  forensics/  osint/  misc/
  notes.md          # live status: challenge, owner, status, notes
  flags.txt         # submitted flags log (who, what, when, points)

# Tooling checklist (verify before start, not during)
python3 -c "import pwn; print(pwn.__version__)"   # pwntools
which gdb ropper RsaCtfTool zsteg steghide binwalk tshark exiftool
hashcat --version 2>/dev/null | head -1
# VPN / challenge network access tested; credentials saved in the vault
```

Notes template per challenge: name, category, points, owner, status
(untouched / looking / stuck / solving / done), key findings, and the
solver path. One shared doc beats five private ones.

## 2. Challenge triage in the first 30 minutes

Everyone opens every challenge in their categories and spends at most
5 minutes each answering:

- What category and what does it give me (binary? URL? file? text?)?
- Is there source code? (Source means solvable; no source means
  harder.)
- What is the point value relative to effort? (Low points plus source
  usually means quick win.)
- Has anyone on the team seen this pattern before?

Mark each: `quick-win`, `medium`, `hard`, or `skip-for-now`. Assign
owners to quick wins first; points early build momentum and unlock
harder challenges (some events gate categories). Never let two people
unknowingly work the same challenge; the notes doc prevents it.

## 3. Time management during the event

- Timebox stuck challenges: 45 minutes with no progress means asking
  for help or swapping owners, not grinding alone for 3 hours.
- Fresh eyes rule: a teammate reading your notes for 10 minutes
  solves more "stuck" challenges than another hour solo.
- Protect the final hour: no new challenges after T-60 minutes;
  finish partials, verify submissions, and check for unsubmitted
  flags in notes.
- Sleep in 24h+ events: schedule it; a rested player at hour 20
  outperforms an exhausted one. Keep one person on triage while
  others rest.
- Track bloods (first solves): they are worth bonus points in many
  events and signal which challenges are tractable.

## 4. Solver scripting discipline

```python
#!/usr/bin/env python3
"""Template: every solver follows this shape."""
import sys

def solve():
    # ... exploit / decode / analysis ...
    return "flag{...}"

if __name__ == "__main__":
    flag = solve()
    assert flag.startswith("flag{"), f"bad format: {flag}"
    print(flag)
    # optional: auto-submit via the platform API when allowed
```

Rules: solvers live in the repo from the first working version (not
"when clean"), they assert the flag format, and they take the target
host as an argument (local vs remote). A solver that only works on one
person's laptop is a liability at 3am.

## 5. Flag submission hygiene

- Copy the flag exactly: no trailing whitespace, no missing braces;
  paste into the platform, do not retype.
- Verify the points increased after submitting; platforms glitch.
- Log every submission in flags.txt with timestamp and owner.
- If a flag is rejected, check the format against the event's
  pattern before assuming the solve is wrong; many rejections are
  whitespace or case issues.
- Never share flags outside the team during the event; most events
  treat it as cheating.

## 6. Communication patterns

- One channel per category plus one for announcements; keep solve
  discussions in the category channel so others can follow.
- Status updates are short: "web/login-bypass: stuck on WAF, trying
  tamper scripts, 20 min" beats silence.
- Ask for help with context: link the notes entry and paste what you
  tried; "this is broken, help" wastes the helper's time.
- Celebrate solves briefly and move on; momentum matters more than
  any single flag.

## Edge cases

- Solo competing: triage even harder; you cannot parallelize, so
  quick wins first is mandatory, and skip anything that smells like
  a time sink.
- The platform is unstable: keep local copies of everything,
  screenshot submitted flags, and have the organizers' contact ready.
- Challenge files disappear or change: hash downloads on receipt
  (`sha256sum`) so you can prove what you worked with.
- Teammate goes quiet: check in once, then reassign their
  challenges; do not let work stall on an absent owner.
- Scoreboard watching becomes obsessive: check it at the captain's time
  calls only; constant refreshing fragments focus and rarely changes
  decisions.
- A challenge you solved gets patched mid-event: keep the original files
  and solver; organizers usually re-award or clarify, and your notes
  prove the solve.

## Escalation

- The whole team is stuck across categories: re-triage from zero;
  the initial difficulty guesses were wrong, and a fresh 30-minute
  pass finds the misjudged quick win.
- One category yields nothing after hours: it may be genuinely hard
  (or broken); cap the investment and redistribute to categories
  with momentum.
- Suspected broken challenge: document the evidence, contact
  organizers once with specifics, and move on; do not burn the event
  on it.
- Key platform credentials leak or a teammate's machine is compromised:
  rotate credentials immediately, notify organizers, and continue from
  clean checkouts; do not investigate on the compromised box.

## Detection and defender view

From the organizer side, this playbook is what fair play looks like:
teams solving with their own tooling and notes. Organizers detect
rule-breaking through flag sharing patterns (same flag submitted from
unrelated teams in sequence), automated solving at inhuman speed
without corresponding traffic, and attacks on the platform itself
rather than the challenges. Durable event design: unique flags per
team, rate-limited submissions, and challenge infrastructure isolated
from the scoring platform.

## Key references

- MITRE ATT&CK: the competition playbook maps to defensive
  understanding of T1595 (Active Scanning) and T1190 (Exploit
  Public-Facing Application) as practiced in authorized events.
- CTFtime (event calendar and team rankings): https://ctftime.org/
- Trail of Bits CTF guide: https://github.com/trailofbits/ctf-wiki
- LiveOverflow CTF methodology videos (triage and workflow).
- DEF CON CTF and picoCTF retrospective writeups (past-event strategy
  and tooling patterns).
