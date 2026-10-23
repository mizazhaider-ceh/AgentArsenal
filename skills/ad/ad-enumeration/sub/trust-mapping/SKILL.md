---
name: trust-mapping
description: Use when mapping Active Directory trust relationships on an
  authorized engagement to find cross-domain attack paths. Covers trust
  enumeration, trust direction and transitivity, SID filtering status, and
  identifying the weakest domain in the trust chain. Use when the target
  has multiple domains or forests, when planning lateral movement across
  trusts, or when assessing whether a compromise of one domain reaches
  another.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: ad-enumeration
requires: [ad-enumeration]
extends: []
relates: [ldap-enumeration, bloodhound-methodology]
tools:
  - name: PowerShell
    version: 7.4
  - name: Impacket
    version: 0.11.0
  - name: Python
    version: 3.12
---

Trusts let users of one domain access resources in another, which means
the security of every domain in a trust chain is only as strong as the
weakest one. This skill covers trust mapping on authorized engagements:
enumerating trusts, understanding direction and transitivity, checking
SID filtering, and finding the practical attack paths across them.

## Quick Workflow

1. Enumerate all trusts visible from the starting domain.
2. Record direction (inbound, outbound, bidirectional) and type (forest,
   external, shortcut).
3. Check transitivity and SID filtering on each trust.
4. Identify the weakest domain: oldest, least monitored, most user
   controlled.
5. Map the concrete path: what access in domain A yields what in domain
   B.
6. Test the path only within the approved scope for each domain.

## 1. Trust enumeration

```powershell
# From a domain-joined host
Get-ADTrust -Filter * | Select-Object Name, Direction, TrustType,
  TrustAttributes, SelectiveAuthentication

# Direction meanings:
# Outbound: your domain trusts the other (their users access your resources)
# Inbound: the other domain trusts yours (your users access theirs)
# Bidirectional: both ways

# nltest alternative on any domain member
nltest /domain_trusts
```

Draw the trust map before doing anything else. An outbound trust from a
well-defended domain to a neglected one is the classic pivot: compromise
the weak domain, ride the trust into the strong one.

## 2. SID filtering and transitivity

```powershell
# Trust attributes: check for SID filtering quarantine
Get-ADTrust -Filter * | Select-Object Name, TrustAttributes
# QUARANTINED_DOMAIN (SID filtering on) blocks SID history abuse
# FOREST_TRANSITIVE means the trust extends through the forest

# Check selective authentication: limits which users can cross
# SelectiveAuthentication = 1 means only explicitly allowed users cross
```

SID filtering off on an external trust enables SID history injection:
add the target domain's Enterprise Admins SID to your token's history
and cross as an admin. Verify the attribute before planning around it;
assuming it is off is a common wasted effort.

## 3. Cross-domain path testing

```bash
# Enumerate the trusting domain's users from your side
python3 /opt/impacket/examples/ldapsearch.py other.corp/testuser:'TestPass123!' \
  -dc-ip 10.0.6.10 -request "(objectClass=user)" \
  -attributes sAMAccountName 2>&1 | head -20

# Kerberos across the trust: request a service ticket in the other domain
# using your domain credential (works when the trust allows it)
python3 /opt/impacket/examples/GetUserSPNs.py other.corp/testuser:'TestPass123!' \
  -dc-ip 10.0.6.10 -request 2>&1 | head -10
```

Test with read-only queries first. Each successful cross-domain query
confirms the trust direction in practice, not just on paper.

## Edge cases

- Selective authentication blocks your user specifically. The trust
  exists but your account is not on the allowed list; note the
  configuration and test with an allowed account if the engagement
  provides one.
- Trusts to decommissioned domains linger. A trust to a dead domain is
  a finding (stale trust), and if the domain still resolves, it may be
  resurrectable by an attacker.
- Forest trusts behave differently from external trusts. Transitivity
  rules differ; map each trust on its own terms.
- The scope covers only one domain. Map the trusts anyway (it is
  read-only), but do not cross into out-of-scope domains; report the
  paths as theoretical.

## Escalation

- A cross-domain path is confirmed in scope: follow it with the same
  enumeration discipline as the first domain, and keep the trust map
  updated.
- SID history abuse is possible and in scope: it requires explicit
  approval as a high-impact technique; prove the missing filter first.
- The trust map is complex: feed it to bloodhound-path-analysis, which
  models cross-domain paths automatically.

## Detection and defender view

Defenders see trust abuse as cross-domain authentication spikes,
impossible combinations of domain memberships in tokens, and SID
history anomalies. Defenses are SID filtering on all external trusts,
selective authentication where full trust is not needed, removing stale
trusts, monitoring cross-domain ticket requests, and treating the whole
forest as one security boundary (because it is).

## Key references

- MITRE ATT&CK T1482 (Domain Trust Discovery).
- MITRE ATT&CK T1558.001 (Steal or Forge Kerberos Tickets: Golden
  Ticket, cross-domain use).
- Microsoft documentation on Active Directory trusts and SID filtering.
