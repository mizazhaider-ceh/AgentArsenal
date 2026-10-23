---
name: rule-based-mangling
description: Use when dictionary attacks stall and each wordlist entry
  needs systematic mutations (case changes, leetspeak, appendages) on an
  authorized engagement. Covers Hashcat and John rule syntax, choosing
  rule sets by hash speed, writing custom rules, and combining rules with
  targeted wordlists. Use when rockyou alone cracks nothing, when the
  password policy forces complexity patterns, or when you need to multiply
  a small targeted list into millions of candidates.
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
  - name: John the Ripper
    version: 1.9.0
  - name: Python
    version: 3.12
---

Rule-based mangling multiplies a wordlist: one base word becomes hundreds
of variants through case toggles, leetspeak, appended digits and symbols,
and policy-shaped mutations. This skill covers writing and choosing rules
on authorized engagements, for Hashcat and John, matched to the hash speed
so the key space fits the time budget. Rules are where most real-world
cracks happen after the plain dictionary fails.

## Quick Workflow

1. Finish the plain dictionary pass first; rules build on its misses.
2. Estimate the key space: wordlist size times rule count, divided by the
   benchmarked hash rate.
3. Start with a proven rule set (best64), then larger sets as budget
   allows.
4. Write custom rules for the target's password policy shape.
5. Combine rules with the targeted wordlist from dictionary-attacks.
6. Record which rule set cracked what, for the report.

## 1. Running rule sets

```bash
# Hashcat best64: 64 well-chosen rules, the standard first step
hashcat -m 1000 /tmp/ntlm.txt /tmp/targeted.txt -r /usr/share/hashcat/rules/best64.rule \
  -o /tmp/cracked_rules.txt

# Larger sets when time allows: d3ad0ne (thousands of rules)
hashcat -m 1000 /tmp/ntlm.txt rockyou.txt -r /usr/share/hashcat/rules/d3ad0ne.rule \
  --status -o /tmp/cracked_big.txt

# John wordlist rules: enable in the run
john --wordlist=/tmp/targeted.txt --rules /tmp/hashes.txt
john --wordlist=rockyou.txt --rules=Jumbo /tmp/hashes.txt

# Estimate before a big run: keyspace times rules over rate
hashcat -m 1000 /tmp/ntlm.txt rockyou.txt -r d3ad0ne.rule --keyspace
```

Rule count times wordlist size is the real workload. best64 on a 10k
targeted list is 640k candidates (seconds on NTLM); d3ad0ne on rockyou is
billions (hours to days). Do the arithmetic before launching.

## 2. Writing custom rules

```bash
# Hashcat rule syntax examples, one per line in /tmp/custom.rule:
# c        capitalize first letter
# u        uppercase all
# $1 $2 $3 append 123
# ^!       prepend !
# sa@      replace a with @
# se3      replace e with 3
cat > /tmp/custom.rule <<'EOF'
c $1 $2 $3
c $2 $0 $2 $6
u $!
sa@ se3 sO0 $1 $2 $3 !
EOF
hashcat -m 1000 /tmp/ntlm.txt /tmp/targeted.txt -r /tmp/custom.rule -o /tmp/cracked_custom.txt

# Match the rule to the password policy you observed:
# policy "8 chars, 1 digit, 1 symbol" -> rules that append digit+symbol
# policy "passphrase words" -> rules that join and capitalize words
```

Write rules from the policy, not from imagination. If the policy forces a
digit and a symbol, every rule should add a digit and a symbol; rules that
do not match the policy waste the key space.

## 3. Combining techniques

```bash
# Combinator attack: join two wordlists (company + year patterns)
hashcat -m 1000 /tmp/ntlm.txt -a 1 /tmp/words_left.txt /tmp/words_right.txt

# Hybrid: dictionary plus mask appendage (Spring + 4 digits)
hashcat -m 1000 /tmp/ntlm.txt /tmp/targeted.txt -a 6 ?d?d?d?d

# Hybrid: mask prefix plus dictionary (?d?d + word)
hashcat -m 1000 /tmp/ntlm.txt /tmp/targeted.txt -a 7 ?d?d
```

Order the campaign by expected yield per hour: plain dictionary, best64,
custom policy rules, combinator, hybrid masks, then full mask attacks (see
mask-attacks). Stop when the budget ends, and report the coverage honestly.

## Edge cases

- Rules explode the key space beyond the budget. Cut the wordlist or the
  rule set, never both blindly; keep the targeted list and trim rules to
  the policy shape.
- The rule file has syntax errors. Hashcat reports them at startup; test
  new rules against a tiny list first.
- Cracks appear but look like false positives. Verify with
  `--show` and a manual login or hash comparison before reporting.
- Slow hashes (bcrypt) make big rule sets infeasible. On slow hashes,
  rules are a luxury; keep to best64 and the targeted list.

## Escalation

- You need a bigger rule set: generate candidates offline with the rules,
  deduplicate, and crack the unique list, which is often faster than
  applying rules at crack time on slow hashes.
- The policy is unknown: infer it from the application's error messages
  and from any cracked samples, then write rules to the inferred shape.
- Time is short: run best64 plus custom policy rules only, and document
  the limited coverage as a scoping note.

## Detection and defender view

Like all offline cracking, rule-based mangling is invisible to the target;
the defense is entirely preventive. Password policies that require length
over complexity, breached-password blocklists, and slow hashes (argon2,
bcrypt) with proper cost parameters blunt mangling. The defender's real
leverage is making the base words themselves rare: password managers and
passphrases beat every rule set.

## Key references

- MITRE ATT&CK T1110.001 (Brute Force: Password Guessing).
- CWE-521 (Weak Password Requirements).
- Hashcat 6.2.6 rule engine documentation.
- John the Ripper wordlist rules documentation.
