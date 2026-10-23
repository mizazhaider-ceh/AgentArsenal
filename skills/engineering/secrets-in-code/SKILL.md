---
name: secrets-in-code
description: Use when finding and removing secrets from source code on
  an authorized codebase. Covers scanner setup, historical cleanup,
  rotation after exposure, and preventing recurrence with pre commit
  hooks. Also use when a leak is suspected and the blast radius needs
  measuring.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [git-workflows, ci-secrets-management, secure-coding]
tools:
  - name: Python
    version: 3.12
  - name: Git
    version: 2.47
---

Secrets end up in code constantly: API keys in commits, tokens in
config files, passwords in scripts. This skill covers the full
response on codebases you are authorized to work on: finding them,
measuring exposure, rotating, cleaning history, and stopping the
next one. Assume any secret found in code is compromised until
rotated.

## Quick Workflow

1. Scan the current tree with a secret scanner; triage every hit.
2. Scan the full history: secrets live in old commits too.
3. For each real secret: identify what it accesses and rotate it
   immediately.
4. Check for abuse: audit logs at the provider for the exposure
   window.
5. Remove from history where feasible (filter-repo), knowing
   rotation matters more than purging.
6. Move the secret to a proper store: vault, env, or secret
   manager.
7. Add pre commit hooks and CI scanning to prevent recurrence.
8. Document the incident: what leaked, for how long, what was done.

## 1. Scanning

```bash
# Scan the working tree (gitleaks as tooling)
gitleaks detect --source /tmp/repo --verbose 2>/dev/null | head -30
# Scan the full history
gitleaks detect --source /tmp/repo --verbose --log-opts="--all" 2>/dev/null | head -30
```

```bash
# Quick manual patterns for triage
grep -rn -E "AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|xox[bap]-|sk-live-" \
  --include="*.py" --include="*.js" --include="*.yaml" --include="*.env*" src/ | head -20
# Verify each: is it a real secret or a test placeholder
```

## 2. Rotation and cleanup

```bash
# Rotation order: 1. create the new secret 2. deploy it 3. revoke the old
# Check abuse during the window (example: AWS key last used)
# aws iam get-access-key-last-used --access-key-id AKIA...
echo "assume compromise; the audit log decides the incident severity"
```

```bash
# History cleanup (only after rotation; coordinate with the team)
# git filter-repo --replace-text replacements.txt  (removes the secret)
# Then force push and have everyone re clone; stale clones still have it
echo "purging without rotation is theater; rotation without purging is fine"
```

```bash
# Prevention: pre commit hook running the scanner
cat > /tmp/repo/.git/hooks/pre-commit << 'HOOK'
#!/bin/sh
gitleaks protect --staged --verbose
HOOK
chmod +x /tmp/repo/.git/hooks/pre-commit
```

## Edge cases

- The secret is in a public repo. It is compromised, period; rotate
  now, investigate in parallel.
- Hundreds of historical hits. Prioritize live secrets (still
  valid) over dead ones; rotate the live, purge what is practical.
- Test keys and placeholders trigger the scanner. Maintain an
  allowlist so real hits stay visible.

## Escalation

- Active abuse found in the audit log: engage incident response;
  this is now a breach, not just hygiene.
- Secret belongs to a vendor or customer: notify them per contract
  after rotating your side.

## Detection and defender view

Secret scanning is detection for a hygiene problem: it finds what
developers committed. Attackers find the same secrets with the same
tools, which is why rotation speed matters more than perfect
purging. The durable defense is making the right path easy: secret
managers, short lived credentials, and scanners that block the
commit before the secret ever lands.

## Key references

- CWE-798 (Use of Hard-coded Credentials).
- CWE-312 (Cleartext Storage of Sensitive Information).
- Gitleaks documentation: rules and configuration.
