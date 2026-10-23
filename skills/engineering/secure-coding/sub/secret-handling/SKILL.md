---
name: secret-handling
description: Use when code needs API keys, passwords, tokens, or
  certificates and you need them handled safely. Covers secret storage,
  injection at deploy time, rotation, and keeping secrets out of code and
  logs. Use when adding a new integration, when removing hardcoded
  credentials, when reviewing configuration, or when responding to a
  leaked secret.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
parent: secure-coding
requires: [secure-coding]
extends: []
relates: [code-reviewer]
tools:
  - name: Python
    version: 3.12
  - name: Git
    version: 2.43
---

Secrets in code become secrets in git history, in logs, in error
messages, and eventually in someone else's hands. This skill covers
handling secrets correctly: never in code, injected at deploy time,
rotatable, and absent from logs. It applies to every API key, database
password, token, and private key the application touches.

## Quick Workflow

1. Inventory every secret the application uses.
2. Remove each from code, config files, and history.
3. Store in the secret manager or environment, injected at deploy.
4. Reference secrets by name in code, never by value.
5. Set rotation: schedule and procedure, tested.
6. Scan for leaks in code, logs, and history continuously.
7. Have the leak response runbook ready before you need it.

## 1. Storage and injection

```python
#!/usr/bin/env python3
"""Secrets by reference, never by value."""
import os

def get_db_password() -> str:
    # From the environment (injected by the deploy system)
    pwd = os.environ.get("DB_PASSWORD")
    if not pwd:
        raise RuntimeError("DB_PASSWORD not set")
    return pwd

# What NOT to do (all real patterns found in breaches):
# DB_PASSWORD = "s3cret123"          # hardcoded
# config = {"key": "AKIA..."}        # config file in git
# print(f"connecting with {pwd}")    # secret in logs
```

```bash
# Deployment injects the secret; the repo never sees it
# docker-compose, k8s secrets, or the cloud secret manager

# Verify no secret is in the repo (run in CI)
git log -p --all | grep -i -E 'password|secret|api[_-]?key' | head -5
# Better: a real secret scanner in CI (gitleaks, trufflehog patterns)
```

The test is simple: a new engineer cloning the repo gets zero working
credentials. If they get any, the secret handling failed.

## 2. Rotation

```bash
# Rotation plan per secret (write it down, test it):
# - Database passwords: rotate quarterly; app reads at startup AND
#   reloads on signal, so rotation needs no deploy
# - API keys: rotate on a schedule; keep two active during the change
# - Certificates: automate renewal (short lifetimes force this)
# - OAuth client secrets: rotate with the provider's process

# Rotation drill: do it once in staging before you need it in prod
# If rotation requires a deploy and downtime, fix that first
```

A secret you cannot rotate is a secret you do not control. The rotation
drill is the proof: if the drill is scary, the real rotation during an
incident will be worse.

## 3. Leak response

```bash
# When a secret leaks (committed, logged, exposed):
# 1. REVOKE it immediately: the leak is public the moment it happens
# 2. Generate a new secret through the normal issuance process
# 3. Deploy the new secret everywhere the old one was used
# 4. Verify the old secret is dead (test it: must fail)
# 5. Remove it from history (git filter, log redaction) AND assume
#    copies exist: history rewriting is hygiene, not containment
# 6. Review what the secret accessed during the exposure window

# Do NOT: just delete the commit and keep using the secret
```

Speed beats thoroughness in the first hour: revoke first, then clean.
Every minute the leaked secret stays valid is a minute someone else can
use it.

## Edge cases

- Local development needs secrets. Use a local secret store or
  dev-only credentials with no production access; never the real ones.
- Secrets in error messages and logs. Redact by pattern (key formats,
  token prefixes) at the logging layer, and test the redaction.
- Third-party SDKs log secrets. Review SDK logging defaults; disable
  debug logging in production.
- Secret sprawl across services. Centralize in one manager; the
  inventory is the control.

## Escalation

- A production secret leaked publicly: revoke in minutes, then do the
  full response; treat the exposure window as compromised until the
  logs prove otherwise.
- The codebase is full of hardcoded secrets: prioritize by access
  level, rotate as you remove, and track the cleanup like the incident
  it is.
- Compliance requires secret management proof: the inventory, the
  rotation logs, and the scan results are the evidence.

## Detection and defender view

Leaked secrets are detected by scanning: repos, logs, and artifacts in
CI, plus public leak monitoring for the organization's key patterns.
The defender's view is that every secret should be revocable in
minutes and every leak should page someone. The engineering investment
is the secret manager plus the CI scanner; everything else is
discipline.

## Key references

- CWE-798 (Use of Hard-coded Credentials).
- CWE-259 (Use of Hard-coded Password).
- CWE-532 (Insertion of Sensitive Information into Log File).
- OWASP Secrets Management Cheat Sheet.
