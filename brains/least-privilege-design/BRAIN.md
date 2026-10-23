---
name: least-privilege-design
kind: brain
description: Use when an agent must design or review access control: assigning permissions to users, services, or automation; reviewing IAM policies and API keys; designing CI/CD pipelines; or auditing who can do what. Provides least-privilege reasoning: default deny, scope access to the task not the role, treat privilege as liability, make access time-bound, and build review into the design. Load this brain whenever the question is "what should this be allowed to do" rather than "how do we stop the attacker."
version: 1.0.0
provides:
  - Default-deny access design
  - Task-scoped permission modeling
  - Privilege-as-liability framing
  - Time-bound and just-in-time access patterns
  - Standing privilege elimination
  - Access review as design component
used_by: []
---

Every permission is a loaded gun you hand out and hope is never misused or stolen. Least privilege is the discipline of handing out the smallest gun for the shortest time: each identity gets exactly the access its task needs, nothing more, and the access expires. It matters because over-privileged accounts are how small breaches become big ones. The attacker who steals a scoped token gets a scoped win. The attacker who steals an admin token gets the company.

## Core mental models

**Default deny, then justify.** Start every access design from zero: nobody and nothing can do anything. Then add permissions one by one, each with a written reason tied to a task. This feels slow, and it is the only direction that works. Starting from "allow everything" and trimming never converges; nobody ever finishes removing permissions, but everyone finishes adding the ones they can justify.

**Privilege is a liability, not a perk.** Each permission you grant is future blast radius. Admin rights feel like trust and convenience; in security terms they are stored risk. When someone asks for broad access, translate it: "you are asking to increase the damage if your account is compromised." Scope by task, not by role or seniority. The CEO's laptop does not need production database write.

**Scope to the task, bound by time.** The best permission is one that does not exist most of the time. Just-in-time access (elevate for the deploy, expire after an hour), short-lived tokens, scoped API keys per service: these shrink the window in which a stolen credential is useful. A standing admin account is a 24/7 opportunity. A 30-minute elevated session is a 30-minute opportunity.

**Review is part of the design.** Permissions rot: people change teams, services get new jobs, temporary access becomes permanent. A least-privilege design includes its own maintenance: periodic reviews, automatic expiry, alerts on privilege use. Without review, every system drifts back to over-privilege within a year. Design the review on day one, not as an afterthought.

## Operating checklist

1. List the identities: users, services, automation, vendors. Every one gets scoped.
2. For each identity, list the tasks it must perform. Not the role, the tasks.
3. Map tasks to the minimal permissions that accomplish them. Write the justification.
4. Start from deny-all and add only justified permissions. No inherited broad roles.
5. Separate duties: no single identity should be able to both create and approve the critical action.
6. Make privileged access time-bound: just-in-time elevation, short-lived tokens, expiring grants.
7. Remove standing privilege: no always-on admin for daily work. Admin is a separate, audited hat.
8. Log every use of privilege. Privilege without audit is just trust.
9. Schedule the review: who re-checks these permissions, how often, and what triggers an early review.
10. Test it: can the identity still do its job? Can it do anything else? Prove both.

## Heuristics

- If you cannot explain why a permission exists in one sentence, remove it.
- Wildcards in IAM policies are a confession. Replace them with the exact actions.
- Service accounts deserve the same scoping as humans. They are juicier targets.
- Break-glass accounts exist for emergencies, are heavily monitored, and are never used for daily work.
- Temporary access that never expires is permanent access with a misleading name.
- The deploy pipeline needs deploy rights, not admin rights. Scope the robot.
- Read is also privilege. Scope data access, not just write access.
- When in doubt, grant less and widen on evidence of need, not on request.

## Anti-patterns

- **Admin for everyone.** Developers with production admin "to move fast." Fast toward what, exactly?
- **Standing privilege.** Accounts that are always powerful, waiting to be stolen at 3 AM.
- **Role-based bloat.** Roles that accumulate permissions over years until "developer" means "god."
- **Vendor god-mode.** Third-party integrations with full access because scoping was "too much work."
- **Review never.** Permissions granted in 2021 still active for people who left in 2023.

## Worked example

A CI/CD pipeline deploys a web app to cloud storage and a database. The old setup: one cloud key with full account admin, stored in the pipeline, never rotated. Least-privilege redesign: the pipeline gets a short-lived token (1 hour) issued per run, scoped to write-only on the app's storage bucket and deploy-only on the app's database migration role. It cannot read other buckets, cannot touch other databases, cannot create users. The token is issued by the cloud identity service at run start and dies at run end. When an attacker later compromises a build script, the stolen token is already expired, and even a live one could only touch the app's own resources. The deploy still works. The blast radius shrank from "the whole cloud account" to "one app's bucket for one hour." That is least privilege doing its job.
