---
name: cloud-iam-review
description: Use when reviewing cloud identity and access management for
  over-privilege on an authorized engagement. Covers user and role
  enumeration, policy analysis for wildcard permissions, unused access
  detection, and MFA coverage. Use when assessing cloud account security,
  when the asset inventory is done, when hunting privilege escalation
  paths, or when the scope asks who can do what in the cloud.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
parent: cloud-security-basics
requires: [cloud-security-basics]
extends: []
relates: [aws-enumeration]
tools:
  - name: AWS CLI
    version: 2.15
  - name: Python
    version: 3.12
---

Cloud IAM is where cloud breaches start: over-privileged users, wildcard
policies, and keys that never rotate. This skill covers the IAM review on
authorized engagements: enumerating identities, analyzing policies for
excessive permission, finding unused access, and checking MFA coverage.
It is read-only; the findings feed remediation, not exploitation.

## Quick Workflow

1. Enumerate users, roles, groups, and their attached policies.
2. Flag wildcard permissions (`*` actions, `*` resources) immediately.
3. Check MFA coverage on console users and privileged roles.
4. Find unused access: keys and permissions idle for 90+ days.
5. Map privilege escalation paths in the policy set.
6. Write findings with the identity, the permission, and the fix.

## 1. Identity and policy enumeration

```bash
# Users, roles, and their policies (AWS example)
aws iam list-users --query 'Users[].[UserName,CreateDate]' --output text | head -20
aws iam list-roles --query 'Roles[].[RoleName,CreateDate]' --output text | head -20

# Attached managed policies per user
for u in $(aws iam list-users --query 'Users[].UserName' --output text); do
  echo "== $u"
  aws iam list-attached-user-policies --user-name $u \
    --query 'AttachedPolicies[].PolicyName' --output text
done

# Inline policies (often where the surprises live)
aws iam list-user-policies --user-name <name> --output text
```

Inline policies deserve extra attention: they are written by hand, rarely
reviewed, and frequently over-broad. Managed policies at least went
through someone's review once.

## 2. Wildcard and privilege analysis

```bash
# Pull a policy document and look for the dangerous patterns
aws iam get-policy-version --policy-arn <arn> --version-id v1 \
  --query 'PolicyVersion.Document' --output json | python3 -m json.tool | head -40

# Patterns to flag:
# - "Action": "*" or "iam:*" or "*:*"           -> full admin, justify it
# - "Resource": "*" with sensitive actions      -> over-broad scope
# - "Effect": "Allow" without conditions        -> check each one
# - sts:AssumeRole to *                        -> role chaining risk

# Users with the managed AdministratorAccess policy
aws iam list-entities-for-policy \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess \
  --output text | head -10
```

Every `*` needs a justification in the report: who holds it, why they
need it, and when it was last reviewed. Unjustified wildcards are the
finding; the fix is scoped policies with conditions.

## 3. Hygiene: MFA and unused access

```bash
# MFA coverage on users (credential report is the fast path)
aws iam generate-credential-report 2>/dev/null
aws iam get-credential-report --query 'Content' --output text | base64 -d > /tmp/cred.csv
head -3 /tmp/cred.csv
# Check: password_enabled + mfa_active=false -> finding

# Old unused keys: created long ago, never used recently
python3 - <<'EOF'
import csv
with open('/tmp/cred.csv') as f:
    for row in csv.DictReader(f):
        if row['access_key_1_active'] == 'true' and 'N/A' in row.get('access_key_1_last_used_date', ''):
            print("UNUSED KEY:", row['user'])
EOF
```

Unused keys and missing MFA are the quick wins of every IAM review:
easy to find, easy to fix, and real risk reduction. Report them as a
batch with the remediation (enforce MFA, delete unused keys).

## Edge cases

- The review is read-only but policies are huge. Summarize by
  effective permission per identity; the full documents go in the
  appendix.
- Cross-account roles complicate the picture. Map the trust: who can
  assume what, and what the assumed role can do.
- The organization uses SSO/federation. Review the IdP side too: the
  cloud role is only as strong as the federated identity.
- Break-glass accounts exist. Verify they exist, are monitored, and
  their credentials are sealed; unmonitored break-glass is a backdoor.

## Escalation

- You find active misuse of over-privilege: treat it as an incident
  input alongside the review finding.
- Privilege escalation paths exist in the policy set: document the
  chain concretely (identity A can do X, reaching permission Y).
- The IAM is too tangled to review manually: recommend the CSPM tool
  that fits, with the manual findings as the seed backlog.

## Detection and defender view

For defenders, IAM review is continuous hygiene: the credential report,
access advisor (last-used data), and policy simulator are the tools.
Alert on policy changes, new wildcard grants, and MFA removal. The
defender's discipline is least privilege as a process (regular access
reviews with owners who actually review) rather than a one-time
project.

## Key references

- CIS AWS Benchmark: IAM sections.
- CWE-250 (Execution with Unnecessary Privileges).
- CWE-269 (Improper Privilege Management).
- Cloud provider IAM best practice documentation.
