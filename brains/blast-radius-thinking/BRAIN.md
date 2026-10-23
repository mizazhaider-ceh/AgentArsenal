---
name: blast-radius-thinking
kind: brain
description: Use when an agent must limit how far a failure can spread: designing deployments, choosing credential scope, planning rollouts, reviewing single points of failure, or preparing for the inevitable bad day. Provides blast-radius reasoning: define failure domains, contain with bulkheads, test the radius before the attacker does, keep rollback ready, and never let one key, one deploy, or one mistake take down everything. Load this brain when designing anything that can fail, which is everything.
version: 1.0.0
provides:
  - Failure domain definition and mapping
  - Bulkhead and compartment design
  - Blast radius testing before incidents
  - Rollback and recovery readiness
  - Single-point-of-failure elimination
  - Progressive rollout discipline
used_by: []
---

Everything fails: code, credentials, people, vendors. The question is never whether, it is how far the failure travels. Blast-radius thinking is the habit of drawing a circle around every component and asking: if this dies, is compromised, or misbehaves, what else goes with it? Then shrinking that circle until the worst day is survivable. It matters because most outages and breaches are not caused by exotic failures. They are caused by ordinary failures with unlimited blast radius: one key for all environments, one deploy to all servers at once, one shared database for everything.

## Core mental models

**Define the failure domains.** A failure domain is the set of things that fail together: an availability zone, a service, a credential's scope, a deploy batch. If you cannot draw the domains, you have one domain: everything. Explicit domains let you reason about worst cases honestly. "If this API key leaks, these three services are exposed, and nothing else" is a design achievement.

**Bulkheads contain the flood.** Ships survive hull breaches because bulkheads divide the hull into compartments. Systems survive failures the same way: separate credentials per environment, separate data stores per service, separate deploy pipelines per region. Each bulkhead is a decision that one failure may not become another. They cost a little convenience and pay out enormously on the worst day.

**Test the radius before the attacker does.** Do not wait for a real incident to discover your blast radius. Game it out: if this key leaks right now, walk the graph and list what falls. Run the drill: revoke the key on purpose and see what breaks (in staging first). The radius you measure in peacetime is the radius you will live with in wartime. Surprises are for birthdays, not incidents.

**Rollback is a control.** The ability to undo a change quickly is as much a security control as any firewall. A bad deploy with a one-minute rollback is a blip. A bad deploy with no rollback is an outage. Design every change to be reversible: versioned deploys, feature flags, database migrations that roll back, credential rotation that does not require downtime. If you cannot undo it, you cannot safely do it.

## Operating checklist

1. For each critical component, credential, and deploy, draw its failure domain: what fails with it?
2. List the single points of failure: one key, one person, one server, one vendor that everything depends on.
3. Insert bulkheads: separate credentials per environment, per service; separate data stores; separate deploy scopes.
4. Size the domains so the worst single failure is survivable. If it is not, split further.
5. Make every change reversible: versioned, flagged, or staged, with a tested rollback path.
6. Roll out progressively: canary, then a slice, then the rest. Never all at once.
7. Walk the compromise graph: if this credential leaks today, exactly what does the attacker get?
8. Document the radius for each secret and each deploy. Review when the architecture changes.
9. Drill it: simulate the failure in staging and confirm the blast stays inside the domain.
10. After any real incident, check whether the radius was as designed. If not, the design was fiction.

## Heuristics

- One credential per environment, per service. Sharing a key across prod and dev is sharing the blast radius.
- If a deploy cannot be rolled back in minutes, it is not ready to ship.
- Canary first, always. The canary exists to die so the fleet does not have to.
- The blast radius of a secret equals the union of everything it can touch. Read the policy, not the intention.
- People are failure domains too. No process may depend on one specific human being awake.
- A vendor is a failure domain. Know what happens when they are down or breached.
- Smaller domains, smaller incidents. Splitting is almost always worth it.
- If the drill is scary, the design is wrong. Fix the design, not the drill.

## Anti-patterns

- **One key to rule them all.** A single API key or admin credential valid across every environment and service.
- **Big-bang deploys.** Pushing to all servers at once, discovering the bug everywhere simultaneously.
- **No rollback plan.** "We will fix forward" as the entire recovery strategy.
- **Shared everything.** One database, one bucket, one account for all services, so one compromise is total.
- **Untested assumptions.** Believing the blast radius is small without ever walking it or drilling it.

## Worked example

A SaaS company uses one cloud API key for all environments, embedded in every service. Blast-radius walk: leak that key and the attacker gets production data, staging data, billing, and DNS. Everything. Redesign: separate keys per environment (prod, staging, dev), each scoped to the services in that environment; production data key separate from production infra key; each key rotatable independently. Deploys go canary first in one region with automatic rollback on error budget burn. Six months later a dev laptop is stolen with a staging key on it. Old radius: total compromise. New radius: staging only, key revoked in minutes, production untouched, customers never notice. The failure still happened. The blast radius made it boring. Boring is the goal.
