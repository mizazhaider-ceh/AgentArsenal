---
name: iam-enumeration
description: Use when enumerating AWS IAM with credentials on an
  authorized engagement to map what the keys can do. Covers
  caller-identity checks, privilege enumeration, policy simulation, and
  finding escalation paths. Use when you have AWS keys, when assessing
  what a compromised key grants, when the cloud-iam-review needs the
  attacker's view, or when planning cloud post-exploitation.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
parent: aws-enumeration
requires: [aws-enumeration]
extends: []
relates: [cloud-security-basics]
tools:
  - name: AWS CLI
    version: 2.15
  - name: Python
    version: 3.12
---

IAM enumeration from the attacker's side answers: what do these
credentials actually allow. This skill covers mapping key privileges on
authorized engagements: identifying the identity, enumerating its
policies, simulating actions, and finding escalation paths. It is the
offensive complement to cloud-iam-review; where that skill audits the
configuration, this one tests what the keys unlock.

## Quick Workflow

1. Identify the identity behind the keys.
2. Enumerate its attached and inline policies.
3. Simulate key actions to confirm effective permissions.
4. List assumable roles and their permissions.
5. Map privilege escalation paths from the permission set.
6. Document the effective access with the evidence.

## 1. Identity and policy mapping

```bash
# Who are these keys?
aws sts get-caller-identity --output text

# Policies on the identity (user example; adapt for role)
USER=$(aws sts get-caller-identity --query 'Arn' --output text | cut -d/ -f2)
aws iam list-attached-user-policies --user-name $USER --output text
aws iam list-user-policies --user-name $USER --output text

# Read each policy document for the effective permission set
aws iam get-policy --policy-arn <arn> --query 'Policy.DefaultVersionId' --output text
```

Keys often belong to roles assumed via STS, not IAM users: check the ARN
shape. Role credentials expire, which bounds your session; note the
expiry and plan the enumeration inside it.

## 2. Simulation and role assumption

```bash
# Policy simulator: can I do X on Y? (no guessing, ask the API)
aws iam simulate-principal-policy \
  --policy-source-arn <user-or-role-arn> \
  --action-names s3:GetObject ec2:DescribeInstances iam:PassRole \
  --output text

# List roles I can assume
aws iam list-roles --query 'Roles[].[RoleName,Arn]' --output text | head -20

# Assume a role and enumerate from inside it
aws sts assume-role --role-arn <role-arn> --role-session-name test \
  --output text --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]'
```

The simulator is authoritative: it evaluates the real policy set
including conditions and boundaries. When simulation and your reading
disagree, trust the simulator and update your reading.

## 3. Escalation path mapping

```bash
# Classic escalation primitives to check (with the simulator or careful reads):
# - iam:PassRole + ec2:RunInstances -> new instance with an admin role
# - iam:CreatePolicyVersion -> escalate your own policies
# - iam:AttachUserPolicy -> attach admin to yourself
# - lambda:CreateFunction + iam:PassRole -> code as the role

# Check for the specific dangerous combos your permission set allows
aws iam simulate-principal-policy --policy-source-arn <arn> \
  --action-names iam:PassRole iam:CreatePolicyVersion iam:AttachUserPolicy \
  --output text
```

Document each escalation path as a chain: starting permission, action,
resulting access. Only execute the escalation with explicit approval;
enumeration proves the path exists, execution proves it works, and the
engagement decides which it needs.

## Edge cases

- The keys are heavily restricted. Enumerate what is allowed; limited
  keys still map the account's shape through allowed read APIs.
- Simulation is denied. Fall back to careful policy reading; note the
  simulator gap.
- The session expires mid-enumeration. Re-assume the role and continue;
  keep the enumeration scripted so reruns are cheap.
- Multiple key sets exist. Enumerate each separately; different keys
  often have different privilege levels.

## Escalation

- A privilege escalation path is confirmed: get approval before
  executing; the finding stands on the enumeration alone if approval
  is denied.
- The keys grant admin: the assessment pivots to data and persistence
  review; re-scope with the test lead.
- You need persistence for the scenario: persistence in cloud needs
  separate explicit approval; enumerate it, do not create it.

## Detection and defender view

Defenders see IAM enumeration as unusual API call patterns: policy
reads, simulator calls, and role assumption attempts from a key that
normally does something narrow. CloudTrail logs all of it. Defenses are
alerting on enumeration patterns, least-privilege keys (so enumeration
finds little), and short-lived credentials that bound the session.
The attacker's enumeration is the defender's detection opportunity.

## Key references

- MITRE ATT&CK T1580 (Cloud Infrastructure Discovery).
- CWE-250 (Execution with Unnecessary Privileges).
- AWS IAM policy simulator documentation.
