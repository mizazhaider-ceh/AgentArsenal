---
name: ldap-enumeration
description: Use when you need to enumerate Active Directory over LDAP on
  an authorized engagement. Covers anonymous and authenticated binds,
  user and computer enumeration, group membership mapping, and finding
  interesting attributes like descriptions and comments. Use when you have
  domain credentials or network access to a domain controller, when
  building the AD user inventory, or when hunting for misconfigurations in
  directory attributes.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: ad-enumeration
requires: [ad-enumeration]
extends: []
relates: [kerberoasting, bloodhound-methodology]
tools:
  - name: Impacket
    version: 0.11.0
  - name: Python
    version: 3.12
  - name: PowerShell
    version: 7.4
---

LDAP is the directory's front door: users, computers, groups, and their
attributes are all queryable, and misconfigurations leak through it
constantly. This skill covers LDAP enumeration on authorized engagements:
binding, dumping the objects that matter, and reading the attributes where
admins leave passwords and notes. It is the foundation the other AD
sub-skills build on.

## Quick Workflow

1. Locate domain controllers and confirm LDAP is reachable.
2. Test anonymous bind; if it works, note it as a finding and enumerate.
3. Bind with the engagement credentials.
4. Enumerate users, computers, groups, and OUs.
5. Read interesting attributes: descriptions, comments, and any field
   that might hold credentials.
6. Map group memberships, especially privileged groups.
7. Save the dumps for BloodHound and manual review.

## 1. Binding and basic queries

```bash
# Find domain controllers via DNS SRV
dig +short SRV _ldap._tcp.corp.example

# Anonymous bind test (finding if it succeeds)
ldapsearch -x -H ldap://10.0.5.10 -b "dc=corp,dc=example" \
  "(objectClass=user)" dn 2>&1 | head -10

# Authenticated bind and base DN discovery
ldapsearch -x -H ldap://10.0.5.10 -D "testuser@corp.example" -w 'TestPass123!' \
  -b "dc=corp,dc=example" "(objectClass=domain)" dn
```

Anonymous LDAP bind succeeding on a domain controller is worth reporting
on its own: it exposes the directory to anyone on the network.

## 2. User and group enumeration

```bash
# All users with key attributes
ldapsearch -x -H ldap://10.0.5.10 -D "testuser@corp.example" -w 'TestPass123!' \
  -b "dc=corp,dc=example" "(objectClass=user)" \
  sAMAccountName description comment memberOf 2>/dev/null | head -60

# Users with passwords in descriptions (the classic LDAP find)
ldapsearch -x -H ldap://10.0.5.10 -D "testuser@corp.example" -w 'TestPass123!' \
  -b "dc=corp,dc=example" "(objectClass=user)" \
  sAMAccountName description 2>/dev/null | grep -i -B2 -E 'pass|pwd|cred' | head -20

# Privileged group membership
ldapsearch -x -H ldap://10.0.5.10 -D "testuser@corp.example" -w 'TestPass123!' \
  -b "dc=corp,dc=example" "(&(objectClass=group)(cn=Domain Admins))" member | head -20

# Computers and their operating systems
ldapsearch -x -H ldap://10.0.5.10 -D "testuser@corp.example" -w 'TestPass123!' \
  -b "dc=corp,dc=example" "(objectClass=computer)" \
  sAMAccountName operatingSystem 2>/dev/null | head -30
```

Descriptions and comments are where credentials hide. Grep every text
attribute for password-like strings before doing anything cleverer.

## 3. Scripted enumeration with Impacket

```bash
# Impacket ldapsearch: cleaner output for scripting
python3 /opt/impacket/examples/ldapsearch.py \
  corp.example/testuser:'TestPass123!' -dc-ip 10.0.5.10 \
  -request "(objectClass=user)" -attributes sAMAccountName,description | head -40

# Dump all groups and memberships to files for offline review
python3 /opt/impacket/examples/ldapdomaindump.py \
  -u 'corp.example\testuser' -p 'TestPass123!' 10.0.5.10 -o /tmp/lddapdump
ls /tmp/lddapdump/
```

Scripted dumps beat manual ldapsearch for anything over a dozen objects.
Save the raw dumps; you will re-query them throughout the engagement.

## Edge cases

- LDAP signing is enforced and simple binds fail. Use NTLM or Kerberos
  binds through Impacket instead of plaintext ldapsearch.
- The directory is huge. Page the queries and filter by OU; dumping
  100k users in one query times out and annoys the DC.
- LDAPS only (port 636). Switch the URI to ldaps:// and add `-ZZ` or
  the right TLS handling; the queries are identical.
- Permissions hide attributes. A low-privilege bind sees less; note
  what was visible at your privilege level and re-run after any
  escalation.

## Escalation

- You need the full object graph: hand the LDAP dumps to
  bloodhound-collection for automated path analysis.
- Interesting users found (service accounts, admins): pivot to
  kerberoast-execution for crackable service tickets.
- Credentials found in attributes: verify by binding as that user, then
  handle under the engagement's credential rules.

## Detection and defender view

Defenders see LDAP enumeration as high-volume directory queries from a
non-admin host, especially wildcard searches and attribute sweeps, which
good monitoring flags. Anonymous binds log distinctly. Defenses are
disabling anonymous bind, LDAP signing and channel binding, monitoring
for enumeration patterns (impossible for normal users to generate that
query volume), and keeping sensitive data out of directory attributes.

## Key references

- MITRE ATT&CK T1087.002 (Account Discovery: Domain Account).
- MITRE ATT&CK T1069.002 (Permission Groups Discovery: Domain Groups).
- CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- Microsoft AD LDAP documentation.
