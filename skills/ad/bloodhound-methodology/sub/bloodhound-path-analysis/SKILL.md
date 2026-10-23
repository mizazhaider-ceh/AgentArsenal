---
name: bloodhound-path-analysis
description: Use when BloodHound data is collected and you need to find
  attack paths from your user to high-value targets on an authorized AD
  engagement. Covers shortest-path queries, pre-built attack path
  queries, reading path edges correctly, and prioritizing paths by
  reliability. Use when planning domain escalation, when choosing between
  several possible paths, or when explaining the attack chain for the
  report.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: bloodhound-methodology
requires: [bloodhound-methodology]
extends: []
relates: [ad-enumeration, kerberoasting]
tools:
  - name: BloodHound
    version: 4.3
  - name: Python
    version: 3.12
---

Path analysis is why BloodHound exists: given the graph, find how your
compromised user reaches Domain Admins through sessions, group
memberships, ACLs, and misconfigurations. This skill covers querying
paths on authorized engagements: the built-in queries, custom shortest
paths, and the judgment to pick paths that work in practice, not just in
the graph.

## Quick Workflow

1. Mark your owned principals (right-click, mark owned) as you gain
   access.
2. Run the shortest-path query to the high-value target.
3. Read each edge: understand what the edge means before trusting it.
4. Prioritize paths by reliability: sessions and group membership first,
   exotic ACL abuse later.
5. Validate each hop manually before executing the chain.
6. Update owned marks and re-query as the engagement progresses.

## 1. Core queries

```cypher
// Shortest path from your user to Domain Admins (BloodHound UI query bar)
MATCH p=shortestPath((u:User {name:'TESTUSER@CORP.EXAMPLE'})-[:MemberOf|AdminTo|HasSession|CanRDP|ExecuteDCOM|AddMember|WriteDacl|Owns*1..]->(g:Group {name:'DOMAIN ADMINS@CORP.EXAMPLE'})) RETURN p

// Built-in queries to run first (UI: Analysis tab):
// - "Shortest Paths to Domain Admins"
// - "Find all Domain Admins"
// - "Users with ForeignSecurityPrincipals"
// - "Kerberoastable users"
```

Start with the pre-built queries; they encode community knowledge about
which paths matter. Custom Cypher comes after, for the specific questions
the built-ins do not answer.

## 2. Reading edges honestly

```cypher
// What each common edge really requires:
// HasSession: the user is logged on; you need code execution on that box
// AdminTo: local admin on the computer; full control of the box
// MemberOf (Domain Admins): you ARE a DA; the path is done
// GenericAll / WriteDacl: ACL abuse; powerful but fiddly, verify by hand
// CanRDP / ExecuteDCOM: remote execution vectors; need network + creds

// Find unconstrained delegation systems (high value)
MATCH (c:Computer {unconstraineddelegation:true}) RETURN c.name

// Find computers your user can RDP to
MATCH (u:User {name:'TESTUSER@CORP.EXAMPLE'})-[:CanRDP]->(c:Computer) RETURN c.name
```

An edge in the graph is a hypothesis, not a fact. `HasSession` from a
stale collection, `GenericAll` on a hardened target, and paths through
decommissioned machines all fail in practice. Validate each hop with a
real action before chaining the next.

## 3. Path prioritization

```cypher
// Rank candidate paths: prefer few hops, reliable edges, fresh sessions
// 1. HasSession on a DA workstation (2 hops: you -> box -> DA session)
// 2. Nested group membership into Domain Admins (check each nesting)
// 3. ACL edges you can validate quickly (AddMember, WriteOwner)
// 4. Kerberoastable service account with DA rights (offline crack)

// List kerberoastable users with their privilege context
MATCH (u:User {hasspn:true}) RETURN u.name, u.admincount
```

Work the list top to bottom. The shortest path is not always the best
path: a 2-hop path through a stale session loses to a 4-hop path through
live, validated hops every time.

## Edge cases

- The graph shows paths through machines that are offline. Ping and port
  check each hop; dead machines break chains silently.
- Sessions are stale. Re-collect sessions before trusting a HasSession
  edge that decides the whole plan.
- The path needs a technique you have not validated. Time-box the
  validation per hop; a path with three unvalidated exotic hops is a
  research project, not a plan.
- Multiple domains confuse the queries. Scope queries per domain and use
  trust-mapping knowledge for the cross-domain hops.

## Escalation

- No path to Domain Admins exists in the graph: enumerate harder
  (re-collect with All), or pivot the objective to the valuable data
  reachable without DA.
- The path works in the lab but not in production: differences in
  patching, EDR, or permissions explain most gaps; diagnose one hop at
  a time.
- You need the path for the report: export the path visualization and
  annotate each hop with the validation evidence.

## Detection and defender view

Defenders use the same tool: running BloodHound defensively finds the
same paths before attackers do, which is the entire point of the
defensive use case. Each edge type maps to a hardening action: remove
stale sessions (reboot workstations), clean nested groups, fix ACLs,
rotate service account passwords. The attacker's path analysis is the
defender's remediation backlog.

## Key references

- MITRE ATT&CK T1087 (Account Discovery).
- MITRE ATT&CK T1069 (Permission Groups Discovery).
- BloodHound 4.3 documentation: Cypher queries and attack paths.
