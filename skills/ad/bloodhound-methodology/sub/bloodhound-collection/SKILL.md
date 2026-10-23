---
name: bloodhound-collection
description: Use when you need to collect Active Directory data for
  BloodHound analysis on an authorized engagement. Covers SharpHound and
  BloodHound.py collection, collection method choices, session and local
  admin data gathering, and opsec tradeoffs. Use when starting AD attack
  path analysis, when you have domain credentials, or when you need the
  full object graph for offline review.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: bloodhound-methodology
requires: [bloodhound-methodology]
extends: []
relates: [ad-enumeration, ldap-enumeration]
tools:
  - name: BloodHound
    version: 4.3
  - name: Python
    version: 3.12
  - name: Impacket
    version: 0.11.0
---

BloodHound turns Active Directory into a graph and finds the shortest path
from your user to Domain Admin. Collection is the step that feeds it:
gathering users, groups, sessions, local admins, and ACLs into the JSON
files BloodHound ingests. This skill covers running collectors on
authorized engagements with the right method for the situation and an
honest view of the noise each method makes.

## Quick Workflow

1. Confirm credentials and the collection account's context.
2. Choose the collector: SharpHound on Windows, BloodHound.py from
   Linux.
3. Choose the collection method: default first, all only with reason.
4. Run collection and verify the output files are complete.
5. Ingest into BloodHound and sanity-check node counts.
6. Re-collect after any privilege change; the graph is a snapshot.

## 1. Running the collectors

```powershell
# SharpHound on a domain-joined Windows host (most complete, needs .NET)
SharpHound.exe -c All --outputdirectory C:\temp\ --prettyjson
# Quieter default: -c Default collects the core object types
SharpHound.exe -c Default --outputdirectory C:\temp\
```

```bash
# BloodHound.py from Linux with domain credentials
bloodhound-python -u testuser -p 'TestPass123!' -d corp.example \
  -dc 10.0.5.10 -c All -o /tmp/bh
ls -la /tmp/bh/*.json

# With NTLM hash instead of password (pass-the-hash collection)
bloodhound-python -u testuser --hashes :<nthash> -d corp.example \
  -dc 10.0.5.10 -c All -o /tmp/bh
```

`-c All` includes session enumeration and local admin collection, which
are the noisiest and most valuable parts. Default to `All` unless the
engagement demands quiet; the extra data usually decides the attack
path.

## 2. Collection methods and their cost

```bash
# Method guide:
# Default: users, groups, computers, OUs, GPOs, trusts. Quiet, fast.
# All: Default plus sessions, local admins, ACLs, RDP. Noisy, complete.
# SessionOnly: just user sessions. For when you only need sessions.
# LoggedOn: sessions via NetWkstaUserEnum, needs admin on targets.

# Verify completeness: compare counts against LDAP reality
python3 - <<'EOF'
import json, glob
for f in glob.glob("/tmp/bh/*.json"):
    data = json.load(open(f))
    print(f.split("/")[-1], len(data.get("data", [])))
EOF
```

Session collection touches every computer (it asks each who is logged
on), which is why it is noisy and why it finds the admin sessions that
win engagements. If `All` is too loud, run `Default` first and add
sessions later against high-value targets only.

## 3. Ingestion and sanity checks

```bash
# Ingest: drag the JSON files into the BloodHound UI, or use the API
# Sanity checks in the UI:
# - Total users roughly matches the LDAP count
# - Domain Admins group is populated
# - Your starting user node exists with its groups

# Timestamp the collection; label it in your notes
date -u > /tmp/bh/collection_time.txt
```

A collection with zero sessions when admins definitely log on somewhere
means the session method failed (permissions, firewall); fix the method,
do not assume no sessions exist.

## Edge cases

- The collector crashes on huge domains. Split by OU or use `Default`
  first, then targeted `All` on the OUs that matter.
- Session enumeration needs privileges you lack. Collect what you can;
  sessions appear after the first privilege escalation, so re-collect
  then.
- BloodHound.py and SharpHound disagree. They query differently;
  SharpHound on a domain host is usually more complete for Windows
  artifacts.
- The data is stale within hours. Sessions change constantly; timestamp
  every collection and re-collect before acting on session-based paths.

## Escalation

- You need stealth collection: use `Default`, avoid session sweeping,
  and accept the thinner graph.
- Collection is blocked by EDR: coordinate with the test lead; collectors
  are dual-use tools that defenses correctly flag.
- The graph is too big to read: move to bloodhound-path-analysis for
  the query-driven approach.

## Detection and defender view

Defenders see collection as LDAP query storms from one host, session
enumeration touching every workstation (event logs on each), and the
collector binary itself (SharpHound is signatured). Good detection is
alerting on enumeration patterns from non-admin hosts. Defenses are
monitoring for the patterns, limiting who can read sensitive attributes,
and remembering that collection is read-only: the damage comes from what
the attacker does with the paths it reveals.

## Key references

- MITRE ATT&CK T1087 (Account Discovery).
- MITRE ATT&CK T1069 (Permission Groups Discovery).
- BloodHound 4.3 documentation: collectors and ingestion.
