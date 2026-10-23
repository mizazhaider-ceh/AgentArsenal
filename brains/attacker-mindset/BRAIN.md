---
name: attacker-mindset
kind: brain
description: Use when an agent needs to reason like an attacker: planning a penetration test, prioritizing recon targets, choosing which vulnerability to exploit first, reviewing a design for how it could be broken, or deciding where a real adversary would strike next. Provides attacker mental models: think in attack graphs not feature lists, always take the cheapest path, hunt defender blind spots, abuse trust instead of breaking crypto, and chain small weaknesses into full compromise. Load this brain before offensive security work so the agent attacks like an adversary, not like a checklist.
version: 1.0.0
provides:
  - Attack graph thinking instead of feature lists
  - Cheapest-path targeting and effort prioritization
  - Defender blind spot hunting
  - Trust abuse over crypto breaking
  - Chaining small weaknesses into full compromise
  - Target value assessment from the attacker's view
used_by: []
---

An attacker does not see your system the way you built it. You see services, features, and layers. They see a graph of doors, and every door has a price. The attacker-mindset brain teaches an agent to read that graph: find the cheapest door, walk through it, and repeat until the objective falls. It matters because defenders who never think this way defend the wrong things. They harden the vault door while the attacker walks in through the loading dock with a stolen badge.

## Core mental models

**Think in graphs, not lists.** A target is not a list of hosts or a list of CVEs. It is a graph where nodes are assets, identities, and trust relationships, and edges are ways to move from one to another. The question is never "is this host vulnerable" but "does this host lead somewhere more valuable." A forgotten dev server with no patches can be the shortest path to the domain controller if it holds a service account credential. Always draw the graph first, then pick paths.

**The cheapest path wins.** Attackers are lazy in the smart sense: they spend the least effort that reaches the goal. Nobody writes a zero-day when password spraying works. Nobody builds a custom exploit when the vendor left default credentials on the admin panel. When you plan an attack or predict one, rank candidate paths by attacker cost (time, skill, money, risk of detection), not by how impressive they sound. The boring path is the real path.

**Hunt the defender's blind spots.** Every defense has places it does not look: legacy systems nobody owns, the gap between two teams' responsibilities, encrypted traffic nobody decrypts, the contractor VPN nobody monitors. Attackers live in these gaps. When reasoning about a target, ask where the defenders are not watching, who owns the neglected asset, and which logs nobody reads. The blind spot is worth more than the vulnerability.

**Abuse trust, do not break crypto.** Real attackers rarely defeat strong cryptography. They go around it: steal the session cookie instead of cracking TLS, phish the admin instead of brute-forcing the password, abuse a trusted integration instead of attacking the hardened core. Every trust relationship (SSO, API keys, vendor access, "internal" network) is a shortcut past the crypto. Map who trusts whom, and the attack path writes itself.

## Operating checklist

1. State the objective in one sentence. What does the attacker actually want (data, access, disruption)?
2. List the assets that matter to the objective, ranked by attacker value, not defender value.
3. Draw the attack graph: nodes (hosts, users, services, trust links), edges (possible moves).
4. For each edge, estimate attacker cost: time, skill, money, and chance of getting caught.
5. Pick the cheapest complete path from entry to objective. Start there.
6. Identify what the defenders monitor, then ask what they are not monitoring on that path.
7. Look for trust to abuse: shared credentials, SSO, vendor access, flat internal networks.
8. Plan two fallback paths. The first path fails more often than you expect.
9. Before each step, ask: does this step get me closer to the objective, or is it just interesting?
10. After each success, re-draw the graph. New access changes every path cost.

## Heuristics

- If it has default credentials, try them before anything clever.
- One valid credential beats ten exploits.
- The forgotten asset is the open door: old, unowned, unpatched, unmonitored.
- Attackers chain: three low findings together equal one critical path.
- Phishing is a path, not a joke. Treat the human as a node in the graph.
- If you are doing something hard, you missed something easy. Stop and re-scan the graph.
- Detection risk is a cost. Noisy on a neglected box is fine; noisy on the crown jewels is not.
- Ask "what would a tired sysadmin have skipped" and start there.

## Anti-patterns

- **Checklist attacking.** Running every scan and exploit in order without asking which path is cheapest. Produces noise, not access.
- **Falling in love with the hard path.** Spending days on a fancy exploit while password spray would have worked in an hour.
- **Ignoring trust relationships.** Attacking the hardened web app directly while the trusted third-party integration sits wide open.
- **No objective.** Wandering through a network collecting shells with no goal. Gets you caught and gets you nothing.
- **Forgetting the graph updates.** Treating the plan as fixed after the first foothold instead of re-ranking paths with new access.

## Worked example

Target: a mid-size company's customer portal. Objective: customer data. The agent draws the graph: public portal, API, admin panel, support VPN, and the helpdesk. The portal itself is well patched. The cheap path check: the helpdesk uses the same SSO as the admin panel, and the company posts staff names on LinkedIn. Cost of a password spray against the helpdesk login is low. One spray lands a valid helpdesk credential. The blind spot: helpdesk logins are not monitored by the SOC, which watches only the portal. Trust abuse: the helpdesk account can impersonate customers in the support tool, which shares a database with the portal. The agent never touches the hardened portal. It logs in as helpdesk, impersonates customers, and reads their data through a trusted feature. Three small facts (public staff list, unmonitored helpdesk login, shared database) chained into full objective. That is the attacker mindset in action.
