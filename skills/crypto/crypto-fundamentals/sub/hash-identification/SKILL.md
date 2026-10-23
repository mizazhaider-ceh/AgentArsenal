---
name: hash-identification
description: Use when you encounter an unknown hash and need to identify
  its type before cracking or analysis on an authorized engagement. Covers
  hash format recognition, identifier tools, manual identification by
  structure, and choosing the right crack mode. Use when starting any
  password cracking, when triaging dumped credentials, when the hash type
  is ambiguous, or when teaching hash format literacy.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
parent: crypto-fundamentals
requires: [crypto-fundamentals]
extends: []
relates: [password-attacks]
tools:
  - name: Python
    version: 3.12
  - name: Hashcat
    version: 6.2.6
  - name: John the Ripper
    version: 1.9.0
---

Hash identification is the step before cracking: the right mode for the
right hash, because every wrong guess wastes the run. This skill covers
recognizing hash formats by their structure: prefixes, lengths, and
alphabets, plus the identifier tools that automate it. Learn the common
formats by heart; the uncommon ones get looked up, not guessed.

## Quick Workflow

1. Inspect the hash: length, alphabet, prefix, separators.
2. Match against known formats (table below).
3. Confirm with an identifier tool when ambiguous.
4. Verify with a known test vector before the real run.
5. Select the crack mode for the confirmed type.
6. Record the identification evidence with the hash.

## 1. Format recognition

```bash
# Common formats by sight:
# 32 hex chars                    -> MD5 or NTLM (context decides)
# 40 hex chars                    -> SHA1
# 64 hex chars                    -> SHA256
# $1$...                          -> MD5crypt
# $2y$/$2b$...                    -> bcrypt
# $5$...                          -> SHA256crypt
# $6$...                          -> SHA512crypt
# $NT$<32 hex> or bare 32 hex     -> NTLM (from Windows dumps)
# $krb5tgs$23$...                 -> Kerberos TGS (kerberoasting)
# $krb5asrep$23$...               -> Kerberos AS-REP

python3 - <<'EOF'
def identify(h: str) -> str:
    if h.startswith("$2y$") or h.startswith("$2b$"):
        return "bcrypt"
    if h.startswith("$6$"):
        return "sha512crypt"
    if h.startswith("$krb5tgs$"):
        return "kerberos TGS-REP"
    if h.startswith("$krb5asrep$"):
        return "kerberos AS-REP"
    if len(h) == 32 and all(c in "0123456789abcdef" for c in h.lower()):
        return "MD5 or NTLM (check source)"
    if len(h) == 40 and all(c in "0123456789abcdef" for c in h.lower()):
        return "SHA1"
    return "unknown: use identifier tool"

for sample in ["$2y$12$abcdefghijklmnopqrstuuXXXX",
               "5f4dcc3b5aa765d61d8327deb882cf99",
               "$krb5tgs$23$*user$EXAMPLE.COM*"]:
    print(f"{sample[:30]:32} -> {identify(sample)}")
EOF
```

Context disambiguates the ambiguous: 32 hex from a Windows SAM dump is
NTLM; 32 hex from a web app's users table is probably MD5. Record the
source alongside the hash; the source is part of the identification.

## 2. Identifier tools and verification

```bash
# hashid-style identification (use the installed identifier)
# Paste the hash, read the candidate list, pick by context

# John can auto-detect many formats:
john --list=formats 2>/dev/null | grep -i -E 'ntlm|bcrypt|krb' | head -10

# Verify the mode with a KNOWN password before the real run:
# hash the word "password" in the suspected format, crack it,
# confirm the tool recovers "password". If it does not, the mode is wrong.
echo -n "password" | md5sum
# then: hashcat -m 0 <that hash> with a list containing "password"
```

The known-answer test takes thirty seconds and saves hours: it proves
the mode, the hash format, and the tool setup all at once. Never skip
it on an unfamiliar hash type.

## 3. Choosing the crack mode

```bash
# Hashcat modes for the common types:
# MD5: 0 | NTLM: 1000 | SHA1: 100 | SHA256: 1400
# bcrypt: 3200 | sha512crypt: 1800
# Kerberos TGS: 13100 | Kerberos AS-REP: 18200

# Speed reality check (order of magnitude, benchmark YOUR rig):
# NTLM/MD5: billions/sec on GPU -> dictionaries and rules freely
# bcrypt cost 12: thousands/sec -> targeted lists only
# The mode choice includes the strategy choice: fast hashes get
# big attacks, slow hashes get smart attacks
```

Identification includes the speed assessment: telling the team "bcrypt,
expect targeted-only" at identification time sets the right plan from
the start. See the password-attacks sub-skills for the cracking itself.

## Edge cases

- The hash has a salt you cannot see. Modular formats embed it
  ($6$salt$hash); bare hashes with separate salts need the salt
  recovered from the source.
- Multiple candidate types match. Test each with the known-answer
  method; it is faster than debating.
- The hash is truncated or corrupted. Note it; truncated hashes
  sometimes still crack (NTLM) and sometimes never will.
- Custom hash constructions. Identify the construction from the
  source code, then build the crack approach around it; standard
  modes will not apply.

## Escalation

- Identification is uncertain after all checks: extract more context
  (the code that created the hash is the ground truth).
- The type is exotic: research its cryptanalysis state before
  promising a crack; some exotic hashes are effectively uncrackable.
- You need the crack done: hand the identified hash and mode to
  dictionary-attacks with the speed assessment attached.

## Detection and defender view

For defenders, hash identification is what happens after a dump: the
race between the attacker's crack and your response. The defender's
leverage is entirely preventive: slow hashes (argon2, bcrypt) with
proper cost, unique salts, and pepper for database-stored hashes buy
the time that fast hashes (MD5, NTLM, unsalted SHA) do not. Identify
your own hashes' types today; if they are fast, the migration is
urgent.

## Key references

- CWE-328 (Use of Weak Hash).
- Hashcat 6.2.6 example hashes (mode reference).
- NIST SP 800-63B (memorized secret hashing guidance).
