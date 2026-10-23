---
name: cloud-review
kind: playbook
description: Use when you need a security review of AWS, Azure, or GCP environments, covering identity, storage, network exposure, and container platforms, ending with an architecture hardening plan. Combines offensive enumeration and privilege escalation path analysis with defensive architecture review. Load this playbook when the client provides read-only cloud access and you need ordered phases, owners, skills, brains, and decision gates for a complete cloud security review.
version: 1.0.0
---

# Cloud Security Review Playbook

Authorized work only. Use the read-only credentials the client provides. Never create resources, modify IAM policies, or run destructive commands in a client account. All write actions happen in an isolated lab account unless the client gives explicit written approval.

## Objective

Review the client's cloud environments for misconfiguration and identity weaknesses, map privilege escalation paths, validate the high-impact ones safely, and deliver an architecture hardening plan. Success is full coverage of the in-scope accounts and subscriptions, validated escalation paths, and a remediation plan the cloud team can implement.

## Phase table

| phase | owner agent | skills used | brains used | decision gates | exit criteria |
|-------|-------------|-------------|-------------|----------------|---------------|
| 1. Scope and access | pentest-reporter-agent | technical-writing, cloud-security-basics | least-privilege-design, incident-command-mindset | GO_NO_GO_GATES | Read-only access confirmed, in-scope accounts listed, windows agreed |
| 2. Identity and access review | cloud-attack-agent | aws-enumeration, azure-enumeration, gcp-enumeration, iam-privesc | least-privilege-design, zero-trust-reasoning | ESCALATION_POLICY | Full IAM inventory, privilege escalation paths mapped |
| 3. Data and storage exposure | cloud-attack-agent | s3-misconfigurations, cloud-security-basics, tls-analysis | blast-radius-thinking, assume-breach | RISK_MATRIX | Public or over-shared storage found and validated |
| 4. Network and compute exposure | cloud-attack-agent | cloud-security-basics, container-escape, kubernetes-rbac, kubernetes-basics | blast-radius-thinking, threat-modeling | RISK_MATRIX | Internet-facing services inventoried, container escape paths checked |
| 5. Architecture review | secure-architect-agent | secure-coding, terraform-basics, cloud-security-basics | threat-modeling, secure-defaults, zero-trust-reasoning | COST_BENEFIT | Design gaps documented with secure reference patterns |
| 6. Reporting and hardening plan | pentest-reporter-agent | technical-writing, testing-strategies | evidence-chain, root-cause-analysis | COST_BENEFIT | Findings report with severity, prioritized hardening plan |

## Detailed phases

### Phase 1. Scope and access

Steps:
1. List every in-scope account, subscription, project, region, and management group from the engagement letter.
2. Confirm the read-only role works in each scope and record exactly which APIs it can call.
3. Agree on how findings that need write validation will be handled: lab account reproduction or client-approved write windows.
4. Set the review window and the escalation contact for the cloud team.

Evidence to collect: scope list, role capability matrix, credential receipt log, window agreement, escalation contact.

### Phase 2. Identity and access review

Steps:
1. Enumerate users, roles, service principals, policies, and trust relationships in each in-scope account.
2. Flag overly broad permissions: wildcard actions, admin policies on human users, long-lived keys, unused access.
3. Map privilege escalation paths: which role can assume what, which policy allows passing roles or editing trust.
4. Validate one hop of each high-value path with a read-only API call where possible, without performing the escalation.

Commands (where relevant):
```bash
aws iam get-account-authorization-details --output json > iam/aws-authz.json
az role assignment list --all --output json > iam/azure-assignments.json
```

Evidence to collect: IAM inventories per account, over-permission findings, escalation path map, validation call logs.

### Phase 3. Data and storage exposure

Steps:
1. Enumerate storage buckets, containers, and file shares. Check public access blocks, ACLs, and policy statements.
2. Validate public readability with anonymous requests to one sample object only. Never download client data.
3. Check for exposed snapshots, database backups, and logging buckets with weak permissions.
4. Verify encryption at rest and in transit settings and note gaps.

Evidence to collect: storage inventory with exposure flags, anonymous validation results, encryption gap list.

### Phase 4. Network and compute exposure

Steps:
1. Inventory security groups, firewall rules, load balancers, and public IPs. Flag management ports open to the internet.
2. Review Kubernetes RBAC: cluster-admin bindings, overly broad service accounts, exposed dashboards.
3. Check container configurations for privileged mode, host mounts, and known escape paths, using read-only inspection.
4. Confirm TLS configuration on public endpoints and note weak protocols or certificates.

Evidence to collect: network exposure inventory, RBAC findings, container misconfiguration notes, TLS scan results.

### Phase 5. Architecture review

Steps:
1. Review the account and landing zone design: separation of workloads, logging coverage, and guardrails.
2. Compare identity, network, and data patterns against secure defaults: private endpoints, centralized logging, MFA enforcement.
3. Assess infrastructure as code for hardcoded secrets, permissive defaults, and drift from the reviewed templates.
4. Identify the structural fixes that close whole classes of findings, not just single instances.

Evidence to collect: architecture gap register, IaC findings with file references, secure reference patterns per gap.

### Phase 6. Reporting and hardening plan

Steps:
1. Write findings with severity, affected resources, proof of exposure or escalation path, and the exact remediation step.
2. Build the hardening plan in phases: immediate containment, identity cleanup, structural architecture changes.
3. Include detection recommendations so the client's monitoring catches recurrence.
4. Deliver the draft, run the cloud team walkthrough, finalize, and schedule the retest.

Evidence to collect: draft and final report, hardening plan with owners and timelines, walkthrough notes, retest schedule.

## Decision gates

- **GO_NO_GO_GATES** (decisions/GO_NO_GO_GATES.md): must pass before Phase 1 and Phase 2. Checks: written authorization, read-only access verified in every scope, account and region list complete, review window agreed.
- **ESCALATION_POLICY** (decisions/ESCALATION_POLICY.md): used in Phase 2. Unexpected account, cross-account trust to an out-of-scope account, or production identity store: stop, notify, wait for written approval.
- **RISK_MATRIX** (decisions/RISK_MATRIX.md): used in Phases 3 and 4. Anonymous access validation and any call that could change state are scored first. Write actions run only in the lab account or with explicit approval.
- **COST_BENEFIT** (decisions/COST_BENEFIT.md): used in Phases 5 and 6. Hardening items are ordered by implementation cost versus risk reduction, with structural fixes ranked by how many findings they close.

## Deliverables

1. Scope document with accounts, regions, and access matrix.
2. IAM inventory with over-permission findings and escalation path map.
3. Storage exposure inventory with validation results.
4. Network, Kubernetes, and TLS exposure findings.
5. Architecture gap register with secure reference patterns.
6. Findings report with severity and phased hardening plan.
7. Retest schedule.
