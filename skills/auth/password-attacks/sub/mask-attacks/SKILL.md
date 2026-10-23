---
name: mask-attacks
description: Use when you know the password structure (length and
  character sets per position) and need brute-force over that key space on
  an authorized engagement. Covers mask syntax, key-space math and time
  estimates, incremental modes, and splitting masks across sessions. Use
  when OSINT reveals the pattern (SeasonYear! format), when the policy
  shape is known, when dictionaries and rules are exhausted, or when
  estimating crack time for the report.
version: 1.0.0
domain: auth
lifecycle: stable
last_verified: 2026-10-23
parent: password-attacks
requires: [password-attacks]
extends: []
relates: [auth-attacks]
tools:
  - name: Hashcat
    version: 6.2.6
  - name: Python
    version: 3.12
---

Mask attacks brute-force a known password shape: `?u?l?l?l?d?d?s` instead of
every possible string. This skill covers building masks from observed
patterns on authorized engagements, doing the key-space math honestly, and
running incremental attacks that fit the time budget. Masks are the last
resort in the cracking order because their key spaces explode fast; the
math section below is what keeps them honest.

## Quick Workflow

1. Derive the mask from evidence: cracked samples, policy text, OSINT
   patterns.
2. Compute the key space and divide by your benchmarked hash rate.
3. If the time fits the budget, run the mask; if not, narrow it.
4. Run incrementally (short masks first) so partial coverage finishes.
5. Split long runs into resumable sessions.
6. Report the coverage: what key space was tested, what was not.

## 1. Mask syntax and key-space math

```bash
# Hashcat charsets: ?l lower, ?u upper, ?d digit, ?s symbol, ?a all
# Pattern "Capitalized word + 4 digits + !" observed in cracked samples:
hashcat -m 1000 /tmp/ntlm.txt -a 3 ?u?l?l?l?l?l?l?d?d?d?d?s

# Key-space math first (Python, before burning GPU hours):
python3 - <<'EOF'
import math
# ?u?l x6 ?d x4 ?s : 26 * 26^6 * 10^4 * 33
space = 26 * (26**6) * (10**4) * 33
rate = 50_000_000_000  # 50 GH/s example NTLM benchmark; use YOUR benchmark
secs = space / rate
print(f"keyspace: {space:.2e}")
print(f"at 50 GH/s: {secs/3600:.1f} hours")
EOF

# Incremental: --increment covers shorter masks first, so an
# interrupted run still completed something
hashcat -m 1000 /tmp/ntlm.txt -a 3 --increment --increment-min 4 \
  --increment-max 8 ?a?a?a?a?a?a?a?a
```

If the math says centuries, the mask is wrong or the hash is too slow:
narrow the mask with better evidence instead of launching anyway.

## 2. Evidence-driven masks

```bash
# From OSINT: passwords look like SeasonYYYY! -> build exactly that
# Spring2026! Summer2025! -> mask per season word is wasteful;
# use hybrid attack instead: dictionary of seasons + mask ?d?d?d?d?s
hashcat -m 1000 /tmp/ntlm.txt /tmp/seasons.txt -a 6 ?d?d?d?d?s

# From policy: "exactly 8 chars, 1 upper, 1 digit" ->
# try ?u?l?l?l?l?l?d?s permutations (several masks, each cheap)

# Custom charsets shrink the space: only observed symbols
hashcat -m 1000 /tmp/ntlm.txt -a 3 -1 ?l?u -2 '!@#$' \
  ?1?1?1?1?1?1?2?d
```

Every position you fix from evidence divides the key space. A mask built
from three cracked samples beats a generic `?a?a?a?a?a?a?a?a` by orders of
magnitude.

## 3. Session management for long runs

```bash
# Named session with restore file: interrupt and resume cleanly
hashcat -m 1000 /tmp/ntlm.txt -a 3 ?u?l?l?l?l?l?l?d?d?d?d \
  --session maskrun1 --status --status-timer 60

# Resume after interruption
hashcat --session maskrun1 --restore

# Show progress without stopping the run (status display does this)
```

Long mask runs belong on hardware you control for the duration. Do not
start a 40-hour mask on a laptop you will close; use the restore workflow
or a dedicated rig.

## Edge cases

- The benchmark was optimistic. Real rates drop with rules, masks, and
  heat; re-benchmark on the actual rig and pad estimates by 50 percent.
- The mask covers the shape but cracks nothing. The evidence was wrong
  about one position; vary one position at a time to find which.
- Slow hashes make even small masks infeasible. On bcrypt, a 6-char
  lowercase mask can take years; report the math instead of running it.
- The key space needs splitting across machines. Divide by mask prefix
  (`?u` fixed per node) and keep the bookkeeping exact.

## Escalation

- The math never fits: recommend against mask attacks in the report and
  explain why, with the numbers; that analysis is itself valuable.
- You need cloud GPUs: get written approval with a cost cap, use the
  cheapest region that meets the need, and stop the instances when done.
- A partial crack reveals the pattern was right: narrow the remaining
  masks around the cracked samples and continue.

## Detection and defender view

Mask attacks are offline and invisible; defense is preventive. Long
minimum lengths destroy mask feasibility (each added character multiplies
the space), slow hashes multiply the time, and MFA makes the cracked
password insufficient alone. The defender's math is the same as the
attacker's: publish the policy, enforce the length, hash slowly.

## Key references

- MITRE ATT&CK T1110.001 (Brute Force: Password Guessing).
- CWE-521 (Weak Password Requirements).
- Hashcat 6.2.6 mask attack documentation.
