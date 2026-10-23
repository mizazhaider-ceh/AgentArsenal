---
name: osint-breach-data-password-pattern-analysis
description: Use when you need to turn leaked password data into
  defensive policy improvements during an authorized review. Covers
  building masks and character-class statistics from your own
  organization's breach hits with Python 3.12, testing policy strength
  with hashcat 6.2.6 rule and mask attacks against your own hashes,
  identifying keyboard walks and predictable constructions, and writing
  the aggregate report that justifies policy change. Use when the
  parent osint-breach-data workflow has collected your scoped
  passwords, when auditing whether the current policy produces
  guessable passwords, or when building an evidence case for
  passphrases or passwordless authentication.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-breach-data
requires: [osint-breach-data]
extends: []
relates: [osint-breach-data]
tools:
  - name: Python
    version: 3.12
  - name: hashcat
    version: 6.2.6
  - name: jq
    version: 1.7
---

Password pattern analysis studies the passwords your users actually
chose, as revealed in breaches, to answer one question: does our
policy produce passwords attackers can guess. The analysis is always
aggregate and always defensive: no individual shaming, no cracking of
anyone else's passwords, and the goal is a better policy. Work only
with passwords from your authorized scope, handle them as sensitive
data, and purge them when the analysis is done.

## Quick Workflow

1. Confirm scope and handling rules: your organization's passwords
   from authorized breach queries only.
2. Normalize the set: dedupe, drop non-password fields, count the
   sample size.
3. Compute length distribution and character-class masks.
4. Detect constructions: seasons, keyboard walks, common
   substitutions, company-name variants.
5. Test guessability: run hashcat mask and rule attacks against your
   own hashes in the lab.
6. Aggregate the findings into policy conclusions, never individual
   attributions.
7. Write the recommendation: what changes and why, with numbers.
8. Purge the plaintext working set per the data-handling rule.

## 1. Building the working set

```bash
# Extract your scoped plaintext passwords from the breach triage
jq -r '.results[] | select(.password_plaintext != null) | .password_plaintext' \
  merged.json | sort -u > passwords.txt
wc -l passwords.txt
# Example: 214 unique passwords in scope
```

```python
# masks.py: length and character-class profile
from collections import Counter
import string

def mask(p):
    out = []
    for c in p:
        if c in string.ascii_lowercase: out.append('l')
        elif c in string.ascii_uppercase: out.append('u')
        elif c in string.digits: out.append('d')
        else: out.append('s')
    return ''.join(out)

pwds = [l.rstrip('\n') for l in open('passwords.txt')]
print("n =", len(pwds))
lengths = Counter(len(p) for p in pwds)
print("lengths:", sorted(lengths.items()))
masks = Counter(mask(p) for p in pwds)
for m, c in masks.most_common(8):
    print(f"{m:24s} {c}")
```

Example output shape:

```
n = 214
lengths: [(6, 9), (7, 14), (8, 41), (9, 52), (10, 38), (11, 27), (12, 19), (13, 14)]
uldddddd                 38
ulllllldd                29
ulllllldds               22
```

A dominant `uldddddd` mask (capital, lowercase word, digits) means
the complexity policy is manufacturing one predictable shape. That
single table often ends the debate about the current policy.

## 2. Construction detection

```python
# constructions.py: find the human patterns inside the masks
import re
from collections import Counter

pwds = [l.rstrip('\n') for l in open('passwords.txt')]
hits = Counter()
seasons = ['spring', 'summer', 'autumn', 'fall', 'winter']
kb_walks = ['qwerty', 'asdf', 'zxcv', '123456', 'qazwsx']

for p in pwds:
    low = p.lower()
    if any(s in low for s in seasons) and re.search(r'\d{2,4}', p):
        hits['season+year'] += 1
    if any(k in low for k in kb_walks):
        hits['keyboard walk'] += 1
    if re.fullmatch(r'[A-Z][a-z]+\d{2,4}[!@#$]', p):
        hits['Capitalized+digits+symbol'] += 1
    if 'example' in low or 'company' in low:  # your org name variants
        hits['company name in password'] += 1
    if re.fullmatch(r'(.)\1{3,}', p):
        hits['repeated chars'] += 1

for k, c in hits.most_common():
    print(f"{k:28s} {c:4d}  ({c/len(pwds):.0%})")
```

Example output shape:

```
Capitalized+digits+symbol     96  (45%)
season+year                   41  (19%)
keyboard walk                 12  (6%)
company name in password       7  (3%)
```

Report percentages, not passwords. "45 percent match one guessable
construction" is the executive sentence; the raw list never leaves
the analyst's encrypted working directory.

## 3. Guessability testing with hashcat (your hashes only)

Hash the working set with a fast hash for policy testing, then attack
it the way an attacker would. This tests the policy, not the users.

```bash
# Hash your working set (example: NTLM-style test; use your real hash type)
# In practice: take the hash list from your own directory audit, authorized in writing
while read -r p; do printf '%s' "$p" | iconv -t utf16le | openssl md4; done < passwords.txt > ntlm.txt
wc -l ntlm.txt

# Mask attack shaped by your observed masks: ?u?l?l?l?l?l?l?d?d
hashcat -m 1000 -a 3 ntlm.txt '?u?l?l?l?l?l?l?d?d' --potfile-disable -o cracked-masks.txt

# Rule attack with a standard ruleset over a small dictionary
hashcat -m 1000 -a 0 ntlm.txt dict.txt -r rules/best64.rule --potfile-disable -o cracked-rules.txt

# Score the policy
echo "mask attack cracked: $(wc -l < cracked-masks.txt) / $(wc -l < ntlm.txt)"
echo "rule attack cracked: $(wc -l < cracked-rules.txt) / $(wc -l < ntlm.txt)"
```

Example output shape:

```
mask attack cracked: 121 / 214
rule attack cracked: 68 / 214
```

If a mask attack built from your own observed patterns cracks over
half the set in minutes, the policy is not producing security, only
compliance theater. That number goes in the report; the cracked
passwords do not.

## 4. Keyboard walks and substitution analysis

```python
# Common substitution check: a->@, e->3, i->!, o->0, s->$
subs = str.maketrans({'a': '@', 'e': '3', 'i': '!', 'o': '0', 's': '$'})
base_words = ['password', 'welcome', 'example', 'summer', 'winter']
pwds_set = set(l.rstrip('\n') for l in open('passwords.txt'))
for w in base_words:
    mutated = w.translate(subs)
    if mutated in pwds_set or w in pwds_set:
        print(f"dictionary base with leetspeak in use: {w}")
```

Attackers try these substitutions first; users choose them believing
they add strength. Finding them in your set proves the belief is
false with your own data.

## 5. Writing the aggregate report

Structure:

```
Sample: 214 unique corporate passwords from authorized breach queries
  (breaches: Collection#1, VendorBreach2023), handled per case-scope.md

Findings:
- 45% match a single construction (Capitalized word + digits + symbol)
- 19% are season+year variants
- 57% cracked by a mask attack built from observed patterns (minutes, single GPU)
- Median length 9; only 12% exceed 12 characters

Conclusion: the complexity policy produces predictable passwords.
Recommendation: minimum 14 characters or passphrases, blocklist of
  common constructions, MFA enforced, move toward passwordless.
```

No usernames, no individual passwords, no attribution. The report
argues about the policy using statistics, which is exactly what
leadership needs to approve change.

## Edge cases

- The sample is small (under 50 passwords). Report it as
  indicative, not conclusive, and avoid percentages that imply
  false precision; use counts.
- Passwords are hashed and you lack authorization to crack them.
  The mask and construction analysis still works on any plaintext
  portion; note the cracking limitation explicitly.
- The set mixes corporate and personal passwords (combo lists).
  Analyze only what the scope covers; personal passwords get
  aggregate treatment or exclusion per the case scope.
- Leadership asks "who chose the worst passwords". Decline and
  redirect: the analysis is of the policy, and individual
  attribution destroys trust in future audits.
- The data is old (breaches from years ago). Note the vintage;
  password habits may have improved, which argues for a fresh
  measurement rather than dismissing the finding.

## Escalation

- Analysis shows the current policy is catastrophically weak
  (majority cracked in minutes). Escalate the recommendation to an
  emergency footing: forced resets plus MFA enforcement, not a
  leisurely policy review.
- You find passwords that are clearly shared service credentials in
  the set. Those need rotation as secrets, handled by the owning
  team, separate from the policy discussion.
- The working set is requested for another purpose (discipline,
  surveillance). Refuse the repurposing; the authorization covered
  policy analysis, and scope creep here destroys the program.
- Results must go to regulators or auditors. Provide the aggregate
  report plus methodology; keep raw passwords out of any
  deliverable that leaves the security team.

## Detection and defender view

Pattern analysis is how defenders learn what attackers already
know: users optimize for memorability, and complexity rules channel
that into a few guessable shapes. The defenses that actually work
are well established: length over complexity, blocklists of known
bad passwords, MFA everywhere, and breach-corpus checking at
password set time (reject passwords found in breaches). Run this
analysis yearly; password culture drifts, and the numbers keep the
policy honest.

## Key references

- Parent workflow: osint-breach-data (this repo)
- NIST SP 800-63B: https://pages.nist.gov/800-63-3/sp800-63b.html
- hashcat wiki (mask attacks, rule attacks):
  https://hashcat.net/wiki/
- OWASP Password Storage and authentication cheatsheets:
  https://cheatsheetseries.owasp.org/
- Have I Been Pwned password corpus (defensive checking):
  https://haveibeenpwned.com/Passwords
- MITRE ATT&CK T1110 (Brute Force): https://attack.mitre.org/
