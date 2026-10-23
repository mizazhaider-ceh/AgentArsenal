---
name: bloodhound-custom-queries
description: Use when BloodHound's built-in queries do not answer your
  specific question on an authorized AD engagement. Covers Cypher basics
  for the BloodHound graph, writing custom path and property queries,
  saving reusable queries, and validating results. Use when hunting a
  specific misconfiguration, when scoping queries to one OU or team, when
  correlating attributes the UI does not show, or when building repeatable
  checks for the report.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: bloodhound-methodology
requires: [bloodhound-methodology]
extends: []
relates: [ad-enumeration, gpo-analysis]
tools:
  - name: BloodHound
    version: 4.3
  - name: Python
    version: 3.12
---

Custom Cypher queries turn BloodHound from a path finder into an AD
auditing engine: any question about the graph becomes answerable. This
skill covers writing and validating custom queries on authorized
engagements: the node and edge model, the query patterns that matter, and
keeping a library of reusable checks. Every query result still needs
manual validation; the graph is a map, not the territory.

## Quick Workflow

1. State the question precisely before writing Cypher.
2. Identify the node labels, properties, and edge types involved.
3. Write the query against a small test scope first.
4. Validate the results manually on two or three hits.
5. Save working queries to the custom query library with clear names.
6. Re-run the library after each re-collection.

## 1. Graph model essentials

```cypher
// Node labels: User, Computer, Group, Domain, OU, GPO
// Key properties: name, enabled, pwdlastset, lastlogon, admincount,
//                 hasspn, dontreqpreauth, unconstraineddelegation
// Key edges: MemberOf, AdminTo, HasSession, CanRDP, GenericAll,
//            WriteDacl, AddMember, Owns, Contains, GpLink

// Users who never log on but hold privilege (service-like accounts)
MATCH (u:User) WHERE u.enabled = true AND u.lastlogon < 0
RETURN u.name LIMIT 25

// Computers with unconstrained delegation
MATCH (c:Computer) WHERE c.unconstraineddelegation = true
RETURN c.name
```

Learn the property names from the node details panel, not from memory:
property availability depends on the collector and version. A query on a
nonexistent property returns nothing silently, which looks like a clean
result.

## 2. Useful custom patterns

```cypher
// Stale privileged accounts: DA members with old passwords
MATCH (u:User)-[:MemberOf]->(g:Group)
WHERE g.name CONTAINS 'DOMAIN ADMINS' AND u.pwdlastset < 1600000000
RETURN u.name, u.pwdlastset

// Who can modify the GPO linked to Domain Controllers OU
MATCH (n)-[:Owns|GenericAll|WriteDacl]->(gpo:GPO)-[:GpLink]->(ou:OU)
WHERE ou.name CONTAINS 'DOMAIN CONTROLLERS'
RETURN n.name, gpo.name

// Users with pre-auth disabled (AS-REP roastable)
MATCH (u:User) WHERE u.dontreqpreauth = true AND u.enabled = true
RETURN u.name

// Kerberoastable users outside the usual service OUs (often missed)
MATCH (u:User) WHERE u.hasspn = true AND NOT u.name CONTAINS 'SVC'
RETURN u.name LIMIT 25

// Paths from any owned node to a specific server
MATCH p=shortestPath((n)-[*1..5]->(c:Computer {name:'FILESRV@CORP.EXAMPLE'}))
WHERE n.owned = true RETURN p LIMIT 10
```

Parameterize the patterns (domain name, OU name, target server) so the
same library works across engagements with minimal edits.

## 3. Query library discipline

```bash
# Keep queries in versioned files, not just the UI
mkdir -p /tmp/bh-queries
cat > /tmp/bh-queries/stale_da.cypher <<'EOF'
MATCH (u:User)-[:MemberOf]->(g:Group)
WHERE g.name CONTAINS 'DOMAIN ADMINS' AND u.pwdlastset < 1600000000
RETURN u.name, u.pwdlastset
EOF

# Document what each query checks and what a hit means
cat > /tmp/bh-queries/README.txt <<'EOF'
stale_da.cypher: DA members with passwords older than ~2020. Hit = rotate urgently.
gpo_dc_writers.cypher: non-DA writers of DC-linked GPOs. Hit = domain compromise path.
EOF
```

Name queries for the finding, not the syntax: `stale_da` beats
`query_7`. The library becomes the repeatable audit pack you run on
every AD engagement.

## Edge cases

- A query returns nothing: verify the property exists on your data
  (check one node manually) before celebrating; silent property misses
  are the top cause of false-clean results.
- Results are huge. Add LIMIT and scoping (OU, enabled only) while
  developing, then run the full version once for the record.
- The graph schema changed between BloodHound versions. Re-validate
  the library after upgrades; edge and property names do move.
- Timestamps are Windows file times. Convert before comparing:
  filetime / 10000000 - 11644473600 = unix epoch.

## Escalation

- You need a question the graph cannot answer: check whether the
  collector gathers that attribute; if not, answer it with LDAP
  queries directly (see ldap-enumeration).
- The library keeps growing: organize by phase (recon, privesc,
  persistence-review) so the next operator can run it blind.
- Results feed the report: export hit lists as CSV from the UI and
  attach the query text for reproducibility.

## Detection and defender view

Custom queries are the defender's best use of BloodHound: the same
library that finds attack paths becomes the continuous audit pack.
Defenders should run these queries on their own collections regularly:
stale privileged accounts, delegation misconfigurations, and GPO edit
rights are all fixable findings that queries surface cheaply. The
attacker's custom query is the defender's detection content.

## Key references

- MITRE ATT&CK T1087 (Account Discovery).
- BloodHound 4.3 documentation: Cypher query reference.
- Neo4j Cypher manual (query language basics).
