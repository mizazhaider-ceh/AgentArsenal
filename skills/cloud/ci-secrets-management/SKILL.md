---
name: ci-secrets-management
description: Use when reviewing how CI/CD pipelines handle secrets on
  an authorized assessment. Covers secret storage in pipeline config,
  log leakage, pull request exposure, and OIDC versus long lived
  tokens. Also use when a leaked secret needs tracing back to the
  pipeline that exposed it.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [cicd-security, github-actions, secrets-in-code, devsecops-pipeline]
tools:
  - name: Python
    version: 3.12
  - name: Git
    version: 2.47
---

CI pipelines are secret sprawl machines: every job gets credentials,
logs echo them, and forks can read them. This skill covers authorized
review: auditing secret storage, testing log masking, checking PR
isolation, and moving to short lived OIDC credentials. Review repos
and pipelines you are authorized to assess.

## Quick Workflow

1. Inventory secrets: where each is stored, who can read it, and
   which jobs use it.
2. Check log masking: do secret values get redacted in build logs.
3. Test PR isolation: can a fork PR access secrets or write to
   protected branches.
4. Review OIDC usage: short lived cloud credentials vs long lived
   tokens.
5. Scan history for leaked secrets in commits and logs.
6. Check secret rotation: age of each secret and the rotation
   process.
7. Verify least privilege: each job gets only the secrets it needs.
8. Report each exposure with the job and the fix.

## 1. Pipeline secret audit

```bash
# GitHub Actions: list secrets and environments (authorized repo)
gh secret list --repo org/repo
gh api repos/org/repo/actions/secrets --jq '.secrets[].name'
# Check which workflows reference them and on which triggers
grep -rn "secrets\." .github/workflows/ | head -20
```

```bash
# PR isolation: does any workflow run secrets on pull_request from forks
grep -rn -B3 "pull_request" .github/workflows/ | grep -A3 "secrets" | head -20
# Danger: pull_request_target with checkout of the PR code executes
# attacker code with access to secrets
```

```bash
# Scan history for leaked secrets (authorized repo)
git log -p --all -S "AKIA" --pickaxe-regex | head -40
# Also scan build logs if retained: secrets echoed by debug flags
```

## 2. OIDC migration check

```bash
# AWS example: is the pipeline using OIDC or a stored access key
grep -rn "aws-access-key-id\|AWS_ACCESS_KEY" .github/workflows/ | head
# OIDC pattern: configure-aws-credentials with role-to-assume, no keys
grep -rn -A5 "role-to-assume" .github/workflows/ | head -20
# Long lived keys in secrets = migrate to OIDC finding
```

```bash
# Log masking test: trigger a build that would echo a canary value
# (use a dummy secret), then check the log shows *** instead
gh run view --log $(gh run list --limit 1 --json databaseId -q '.[0].databaseId') \
  | grep -i "canary" | head -5
```

## Edge cases

- Secrets are in a vault but the CI token can read everything. The
  vault ACL is the real boundary; review it.
- Masking works but secrets appear in error messages and diffs.
  Test the failure paths, not just the happy path.
- Self hosted runners persist state between jobs. One job's secret
  can leak to the next; review runner isolation.

## Escalation

- Active leak found: rotate the secret immediately, purge the logs,
  and check for abuse in the provider's audit trail.
- PR can steal secrets: this is a critical pipeline takeover path;
  fix the trigger and scoping, then retest.
- Need the code side: hand to secrets-in-code for the repo review.

## Detection and defender view

Defenders detect CI secret abuse through cloud audit logs showing
the CI role doing unusual things, secret usage alerts, and
scanning for leaked credentials. They defend with OIDC everywhere,
per job minimal secrets, PR isolation, and log retention policies
that balance forensics with exposure. The durable direction is no
long lived secrets in CI at all.

## Key references

- CWE-798 (Use of Hard-coded Credentials).
- CWE-532 (Insertion of Sensitive Information into Log File).
- GitHub Actions and cloud OIDC documentation.
