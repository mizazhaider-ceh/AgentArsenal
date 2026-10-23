---
name: dictionary-attacks
description: Use when cracking password hashes or testing logins with
  wordlists on an authorized engagement. Covers wordlist selection and
  building, hash identification, Hashcat and John the Ripper workflows,
  and result handling. Use when you recovered hashes from a dump or
  memory, when testing password strength offline, when choosing between
  CPU and GPU cracking, or when building targeted wordlists from OSINT.
version: 1.0.0
domain: auth
lifecycle: stable
last_verified: 2026-10-23
parent: password-attacks
requires: [password-attacks]
extends: []
relates: [auth-attacks, osint-methodology]
tools:
  - name: Hashcat
    version: 6.2.6
  - name: John the Ripper
    version: 1.9.0
  - name: Python
    version: 3.12
---

Dictionary attacks try every password in a wordlist, and they work because
people reuse a small set of passwords. This skill covers offline hash
cracking on authorized engagements: identifying the hash type, picking the
right wordlists, running Hashcat and John effectively, and building
targeted lists from engagement OSINT. Only crack hashes you are authorized
to hold, and treat cracked passwords as sensitive data from the moment
they appear.

## Quick Workflow

1. Confirm authorization covers the hashes and their source.
2. Identify the hash type precisely before choosing a mode.
3. Pick wordlists: start small and targeted, widen only as needed.
4. Run Hashcat (GPU) or John (CPU) with the right mode and options.
5. Build custom wordlists from target OSINT when generic lists stall.
6. Record cracked credentials securely and report the password policy
   failure they prove.

## 1. Hash identification and setup

```bash
# Identify the hash type by length, alphabet, and prefix
# $2y$... = bcrypt, $6$... = sha512crypt, $NT$ or 32 hex = NTLM,
# $krb5tgs$ = Kerberos TGS (from kerberoasting)
python3 - <<'EOF'
samples = {
    "5f4dcc3b5aa765d61d8327deb882cf99": "MD5 (32 hex)",
    "$2y$12$abcdefghijklmnopqrstuu...": "bcrypt",
}
for h, guess in samples.items():
    print(f"{h[:20]}... -> {guess}")
EOF

# Hashcat example: NTLM (mode 1000) with rockyou
hashcat -m 1000 /tmp/ntlm.txt /usr/share/wordlists/rockyou.txt \
  --status --status-timer 30 -o /tmp/cracked.txt

# John the Ripper example: auto-detect format, wordlist mode
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/hashes.txt
john --show /tmp/hashes.txt
```

Wrong mode wastes the whole run: a bcrypt hash in an MD5 mode cracks
nothing and reports nothing. When unsure, run the hash through a local
identifier and verify with a known test hash first.

## 2. Wordlist strategy

```bash
# Order matters: quick wins first
# 1. Top 10000 passwords (seconds)
hashcat -m 1000 /tmp/ntlm.txt /usr/share/wordlists/seclists/Passwords/Common-Credentials/10-million-password-list-top-10000.txt -o /tmp/c1.txt
# 2. rockyou (minutes to hours)
# 3. Targeted custom list (see below)

# Build a targeted list from engagement OSINT: company name, product
# names, seasons, years, local sports teams
python3 - <<'EOF'
seeds = ["acme", "acmecorp", "spring", "2026", "qwerty"]
out = set()
for s in seeds:
    out.update([s, s.capitalize(), s.upper(), s + "123", s + "2026",
                s + "!", "!" + s, s + "123!"])
with open("/tmp/targeted.txt", "w") as f:
    f.write("\n".join(sorted(out)))
print(f"[*] {len(out)} candidates")
EOF
```

Targeted lists beat big generic lists per hour invested. Ten minutes of
OSINT-driven list building often outperforms ten hours of raw rockyou.

## 3. Managing the crack

```bash
# Benchmark first so time estimates are honest
hashcat -b -m 1000

# Session management: pause and resume long runs
hashcat -m 1000 /tmp/ntlm.txt rockyou.txt --session engagement1
hashcat --session engagement1 --restore  # resume later

# Rule-based mangling belongs to rule-based-mangling; keep pure
# dictionary runs clean and fast here

# Show results without leaking them to the terminal log
hashcat -m 1000 /tmp/ntlm.txt --show -o /tmp/cracked_final.txt
```

Cracked passwords go into the report's credential table and nowhere else:
not chat logs, not screenshots, not ticket comments. Redact them in any
shared artifact.

## Edge cases

- The hash type is misidentified. Symptoms: zero cracks with a good list
  on weak passwords; re-identify with fresh samples and test modes.
- Salts are involved (sha512crypt, bcrypt). Dictionary attacks still
  work but slower; benchmark honestly and set expectations.
- The list cracks nothing. Move to rule-based-mangling before mask
  attacks; mangling multiplies the dictionary, masks start from zero.
- GPU drivers fail on the cracking rig. John on CPU still handles fast
  hashes (NTLM, MD5); slow hashes (bcrypt) need the GPU or a scope
  discussion.

## Escalation

- You need more power: estimate the run honestly (benchmark times key
  space), and only expand hardware or cloud cracking with written
  approval and a clear budget.
- Cracked credentials unlock new access: handle them under the
  engagement's credential rules, rotate or report per the agreed process.
- Nothing cracks: report the negative result with the methods tried;
  strong passwords are a positive finding about the password policy.

## Detection and defender view

Defenders rarely see offline cracking at all: it happens on the
attacker's hardware, leaving no logs on the target. The signals are
upstream: the hash disclosure that made cracking possible (dumps,
kerberoasting, database theft). Defenses are strong hashing (bcrypt,
argon2, scrypt with proper cost), long random passwords via managers,
MFA so a cracked password alone is not enough, and monitoring for the
hash-theft techniques themselves.

## Key references

- MITRE ATT&CK T1110.001 (Brute Force: Password Guessing).
- MITRE ATT&CK T1003 (OS Credential Dumping).
- CWE-521 (Weak Password Requirements).
- CWE-328 (Use of Weak Hash).
- Hashcat 6.2.6 documentation: hash modes and wordlist attacks.
