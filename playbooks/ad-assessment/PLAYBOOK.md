---
name: ad-assessment
kind: playbook
description: Use when you need an Active Directory security assessment, from anonymous enumeration to domain compromise paths, mapped attack chains, and a hardening roadmap. Covers network discovery, SMB and AD enumeration, BloodHound path analysis, Kerberos attacks, credential recovery, and privilege escalation to domain admin. Load this playbook when the engagement covers an internal AD forest and you need ordered phases, owners, skills, brains, and decision gates for safe, documented domain testing.
version: 1.0.0
---

# Active Directory Assessment Playbook

Authorized work only. Test only the domains, OUs, and accounts named in the rules of engagement. Kerberos attacks and credential extraction run only against approved targets, and never during production hours without written approval.

## Objective

Map the Active Directory attack surface, find the shortest and most realistic paths to domain compromise, demonstrate them safely, and deliver a hardening roadmap ordered by risk reduction. Success is a complete attack path map from the assumed starting position, validated privilege escalation chains, and fixes the defenders can implement in priority order.

## Phase table

| phase | owner agent | skills used | brains used | decision gates | exit criteria |
|-------|-------------|-------------|-------------|----------------|---------------|
| 1. Scope and start position | pentest-reporter-agent | technical-writing, testing-strategies | assume-breach, incident-command-mindset | GO_NO_GO_GATES | In-scope domains, start position (unauthenticated or standard user), test windows |
| 2. Network and host discovery | recon-agent | recon-active, nmap-methodology, smb-enumeration, dns-enumeration | attacker-mindset, opa-decision-loop | GO_NO_GO_GATES | Live hosts, DCs identified, SMB shares listed |
| 3. AD enumeration | ad-attack-agent | ad-enumeration, bloodhound-methodology, llmnr-poisoning | attacker-mindset, evidence-chain | ESCALATION_POLICY | Users, groups, GPOs, trusts, and attack paths collected |
| 4. Credential attacks | ad-attack-agent | kerberoasting, asreproasting, password-attacks, hash-cracking | cost-of-attack, opa-decision-loop | RISK_MATRIX | Cracked or recovered credentials documented with source |
| 5. Privilege escalation and domain compromise | ad-attack-agent | dcsync, golden-ticket, privesc-windows, network-pivoting | blast-radius-thinking, assume-breach | ESCALATION_POLICY, RISK_MATRIX | Validated path to domain admin, impact demonstrated safely |
| 6. Reporting and hardening roadmap | pentest-reporter-agent | technical-writing, testing-strategies | root-cause-analysis, evidence-chain | COST_BENEFIT | Attack path map, findings, prioritized hardening plan |

## Detailed phases

### Phase 1. Scope and start position

Steps:
1. Confirm the forest, domains, and any excluded OUs, service accounts, or systems in the rules of engagement.
2. Agree the starting position: unauthenticated network access, standard domain user, or both. Get the test accounts provisioned.
3. Set test windows that avoid backups, patching, and business hours for noisy actions.
4. Record the approval chain for escalation decisions during the test.

Evidence to collect: signed ROE, domain and OU scope list, test account details, window schedule, approval chain.

### Phase 2. Network and host discovery

Steps:
1. Sweep the in-scope subnets for live hosts and identify domain controllers by service fingerprint.
2. Enumerate SMB shares, null sessions where permitted, and exposed services on each host.
3. Enumerate DNS for the AD zones to find DCs, trusts, and service records.
4. Reconcile findings with the client's asset list and confirm any unexpected DC before touching it.

Commands (where relevant):
```bash
nmap -sS -T4 -p 53,88,135,139,389,445,636,3268 --open -oA scans/ad-ports <in-scope-subnet>
nxc smb <dc-ip> -u '' -p '' --shares
```

Evidence to collect: raw scan output, DC identification notes, share listings, reconciliation log.

### Phase 3. AD enumeration

Steps:
1. Run standard AD enumeration: users, groups, computers, OUs, GPOs, trusts, and delegation settings.
2. Collect BloodHound data with the approved collector and analyze shortest paths to high-value targets.
3. Test for LLMNR, NBT-NS, and WPAD poisoning opportunities on the local segment within the test window.
4. Document every attack path with the starting principal, the technique, and the target.

Commands (where relevant):
```bash
bloodhound-python -u <user> -p <pass> -d <domain> -dc <dc-ip> -c all -o out/
# import out/*.json into BloodHound, export shortest path queries
```

Evidence to collect: enumeration output, BloodHound dataset and path exports, poisoning test results, attack path register.

### Phase 4. Credential attacks

Steps:
1. Request Kerberoastable service account tickets and crack them offline. Record which accounts fall and how fast.
2. Test for AS-REP roastable accounts and attempt offline cracking.
3. Run approved password spraying with a small, agreed wordlist against a limited account set, watching for lockout.
4. Crack recovered hashes offline and document the source of each credential.

Commands (where relevant):
```bash
GetUserSPNs.py <domain>/<user>:<pass> -dc-ip <dc-ip> -request -outputfile roast.txt
hashcat -m 13100 roast.txt wordlists/approved.txt
```

Evidence to collect: roastable account list, cracking results with times, spray logs, credential source register.

### Phase 5. Privilege escalation and domain compromise

Steps:
1. Walk the shortest validated attack path toward domain admin, confirming each hop before taking the next.
2. Demonstrate domain compromise safely: read a proof object or show DCSync capability on a test account, never dumping the full NTDS without explicit written approval.
3. Test persistence mechanisms only if persistence testing is in scope, and remove every artifact afterward.
4. Stop at the first sign of touching production safety systems, backup infrastructure, or out-of-scope trusts. Escalate immediately.

Evidence to collect: hop-by-hop path log, domain compromise proof, persistence artifact inventory with removal confirmation, escalation records.

### Phase 6. Reporting and hardening roadmap

Steps:
1. Draw the attack path map: every path from the start position to domain admin, with the technique at each hop.
2. Write findings with severity, affected objects, reproduction steps, and the exact hardening change that closes the path.
3. Build the hardening roadmap in priority order: quick wins first (for example, strong service account passwords, LLMNR disabled), structural fixes next (tiering, delegation cleanup).
4. Deliver the draft, run the defender walkthrough, finalize, and schedule the retest.

Evidence to collect: attack path map, findings with reproduction steps, prioritized hardening roadmap, walkthrough notes, final report.

## Decision gates

- **GO_NO_GO_GATES** (decisions/GO_NO_GO_GATES.md): must pass before Phase 1 and Phase 2. Checks: signed authorization, domain and OU scope confirmed, test accounts provisioned, test windows agreed, backup and patching blackout times recorded.
- **ESCALATION_POLICY** (decisions/ESCALATION_POLICY.md): used in Phases 3 and 5. Unexpected DC, out-of-scope trust, or production safety system encountered: stop, notify, wait for written approval.
- **RISK_MATRIX** (decisions/RISK_MATRIX.md): used in Phases 4 and 5. Password spraying, ticket requests, DCSync, and golden ticket creation are scored for lockout and replication risk before running.
- **COST_BENEFIT** (decisions/COST_BENEFIT.md): used in Phase 6. Hardening items are ordered by implementation cost versus path closure value so defenders fix the highest-value items first.

## Deliverables

1. Scope document with domains, OUs, start position, and windows.
2. Network and SMB discovery output.
3. AD enumeration dataset and attack path register.
4. Credential attack results with sources and cracking times.
5. Validated domain compromise path log with safe proof.
6. Attack path map, findings report, and prioritized hardening roadmap.
7. Retest schedule.
