---
name: cicd-security
description: Use when securing a CI/CD pipeline on an authorized
  engineering task. Covers the pipeline attack surface (poisoned
  pipeline execution, secret exfiltration, compromised actions),
  least-privilege tokens and OIDC, pinning actions by SHA, secret
  scanning with gitleaks 8.24, dependency and image scanning with Trivy
  0.58, artifact signing with cosign 2.4, and branch protection rules.
  Use when hardening GitHub Actions or similar pipelines, auditing a
  pipeline for supply-chain risk, or responding to a suspected pipeline
  compromise.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [devsecops-pipeline, github-actions, git-workflows]
tools:
  - name: Trivy
    version: 0.58
  - name: gitleaks
    version: 8.24
  - name: cosign
    version: 2.4
---

The CI/CD pipeline builds, tests, and deploys your software, which
makes it one of the most valuable targets in the supply chain: a
compromised pipeline ships backdoors to every customer at once. This
skill covers the pipeline attack surface, the controls that shrink
it, and the scanning and signing tooling that proves what you
shipped. It pairs with devsecops-pipeline (designing the pipeline)
and github-actions (authoring workflows).

## Quick Workflow

1. Inventory every workflow, runner, secret, and third-party action
   in the pipeline.
2. Map the attack surface: script injection via PR titles, secret
   exfiltration paths, and actions that run with write tokens.
3. Set minimal `permissions` on every workflow and job, and require
   OIDC instead of long-lived cloud keys.
4. Pin all third-party actions to commit SHAs and enable Dependabot
   for updates.
5. Add secret scanning (gitleaks) so credentials never land in git.
6. Add dependency and container scanning (Trivy) as blocking gates.
7. Sign release artifacts with cosign and verify signatures on
   deploy.
8. Enforce branch protection, required reviews, and CODEOWNERS on
   workflow files.

## 1. Mapping the attack surface

The pipeline attack surface is everything an attacker can reach: the
workflow YAML, the runner environment, secrets, artifacts, and every
third-party action in the chain.

```bash
# Inventory workflows and third-party action usage
find .github/workflows -name '*.yaml' | sort
grep -rh 'uses:' .github/workflows | sort | uniq -c | sort -rn

# Find dangerous patterns: unpinned actions, write-all permissions
grep -rn 'uses:.*@v[0-9]' .github/workflows        # floating tags, pin these
grep -rn 'pull_request_target' .github/workflows   # high-risk trigger
grep -rn 'permissions.*write-all\|write-all' .github/workflows

# Classic script injection: PR-controlled data interpolated into run:
grep -rn 'github.event' .github/workflows | grep -i 'run:'
```

The highest-risk pattern is interpolating attacker-controlled data
(`github.event.pull_request.title`, issue bodies) into a `run:`
script block. That is remote code execution on your runner, triggered
by opening a pull request.

## 2. Least-privilege tokens and OIDC

```bash
cat > .github/workflows/hardened.yaml <<'EOF'
name: Hardened example

on:
  pull_request:

permissions: {}  # deny all at the top

jobs:
  build:
    runs-on: ubuntu-24.04
    permissions:
      contents: read   # only what this job needs
    steps:
      - uses: actions/checkout@v4  # pin to SHA in production
      - run: make build

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-24.04
    environment: production
    permissions:
      contents: read
      id-token: write  # OIDC only, no stored cloud keys
    steps:
      - uses: actions/checkout@v4  # pin to SHA in production
      - name: Assume deploy role via OIDC
        uses: aws-actions/configure-aws-credentials@v4  # pin to SHA
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-deploy
          aws-region: eu-west-1
EOF
```

Rules: top-level `permissions: {}` everywhere; per-job grants only;
`environment: production` with required reviewers for deploys; OIDC
instead of static `AWS_SECRET_ACCESS_KEY` in secrets; fork PRs never
get secrets.

## 3. Secret scanning with gitleaks

```bash
# Install gitleaks 8.24 (single static binary)
# https://github.com/gitleaks/gitleaks/releases

# Scan the working tree for leaked secrets
gitleaks detect --source . --verbose

# Scan full git history (finds secrets committed long ago)
gitleaks detect --source . --log-opts="--all" --verbose

# Baseline: record existing findings so only NEW leaks fail CI
gitleaks detect --source . --baseline-path .gitleaks-baseline.json --redact
```

```bash
# CI gate: fail the build on any new secret
cat > .github/workflows/secrets.yaml <<'EOF'
name: Secret scan
on: [pull_request]
permissions: {}
jobs:
  gitleaks:
    runs-on: ubuntu-24.04
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v4  # pin to SHA in production
        with:
          fetch-depth: 0
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2  # pin to SHA in production
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
EOF
```

When gitleaks finds a secret, rotate it immediately: removing it
from git does not unexpose it, because history keeps it forever.
Use `git filter-repo` to purge it from history after rotation.

## 4. Dependency and image scanning with Trivy

```bash
# Scan container images for OS and language CVEs
trivy image --severity HIGH,CRITICAL myapp:1.2.3

# Scan a repository: dependencies, IaC misconfigurations, secrets
trivy fs --severity HIGH,CRITICAL --scanners vuln,misconfig,secret .

# Scan a Kubernetes manifest before applying
trivy config --severity HIGH,CRITICAL k8s/

# Output SARIF for the GitHub code scanning UI
trivy image --format sarif --output trivy.sarif myapp:1.2.3
```

```bash
# CI gate: block on CRITICAL, warn on HIGH
cat > .github/workflows/scan.yaml <<'EOF'
name: Vulnerability scan
on: [pull_request]
permissions:
  contents: read
  security-events: write
jobs:
  trivy:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4  # pin to SHA in production
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Scan image
        uses: aquasecurity/trivy-action@master  # pin to SHA in production
        with:
          image-ref: myapp:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL
          exit-code: "1"
EOF
```

Fail the build on CRITICAL findings and triage HIGH within a fixed
window. Suppress a finding only with a documented reason and an
expiry date, never silently.

## 5. Signing artifacts with cosign

```bash
# Install cosign 2.4
# https://github.com/sigstore/cosign/releases

# Generate a key pair (or use keyless OIDC signing in CI)
cosign generate-key-pair

# Sign a container image
cosign sign --key cosign.key myapp:1.2.3

# Keyless signing in CI via OIDC (no keys to manage)
cosign sign myapp:1.2.3

# Verify before deploying: refuse unsigned images
cosign verify --key cosign.pub myapp:1.2.3

# Sign and verify a release tarball with a blob signature
cosign sign-blob --key cosign.key --output-signature app.sig app.tar.gz
cosign verify-blob --key cosign.pub --signature app.sig app.tar.gz
```

Enforce verification at deploy time (admission controllers in
Kubernetes, policy checks in the deploy job). An unsigned artifact
must not reach production, no matter how urgent the release.

## 6. Branch protection and workflow governance

```bash
# Require PR reviews, status checks, and signed commits on main
gh api repos/{owner}/{repo}/branches/main/protection -X PUT \
  -f required_status_checks[strict]=true \
  -f required_status_checks[contexts][]='CI' \
  -f enforce_admins=true \
  -f required_pull_request_reviews[required_approving_review_count]=1 \
  -f required_pull_request_reviews[dismiss_stale_reviews]=true \
  -f required_linear_history=true \
  --silent

# Require review for workflow file changes specifically
cat > .github/CODEOWNERS <<'EOF'
.github/workflows/ @security-team
Dockerfile @security-team
EOF
```

CODEOWNERS on `.github/workflows/` means pipeline changes need a
security review, which blocks the quiet insertion of an exfiltration
step into a build job.

## 7. Responding to a suspected pipeline compromise

```bash
# 1. Freeze: disable the workflow and rotate exposed secrets
gh workflow disable suspicious.yaml

# 2. Find what ran: list recent runs and their logs
gh run list --workflow=suspicious.yaml --limit 20

# 3. Check what changed: diff workflow files against the last known good
git log --oneline -10 -- .github/workflows/
git diff <good-commit> HEAD -- .github/workflows/

# 4. Check artifacts produced by suspicious runs for tampering
gh run download <run-id>

# 5. Rebuild and re-sign artifacts from a clean commit after remediation
```

Treat a compromised pipeline like any incident: contain, preserve
logs, find the entry point (often a malicious action update or a
stolen token), rotate every secret the pipeline could read, and
rebuild artifacts from a verified commit.

## Edge cases

- Legitimate workflow needs `pull_request_target` (for labeling
  fork PRs). Never check out the PR's code in that workflow; use it
  only for metadata operations with read-only tokens.
- Trivy flags a CVE in a base image with no fixed version. Options:
  switch to a slimmer base, wait for the upstream fix with a
  documented exception, or confirm the vulnerable code path is
  unreachable in your image.
- gitleaks false-positives on test fixtures. Add precise
  `allowlist` rules in `.gitleaks.toml` for the fixture paths,
  never a blanket exclusion of whole directories.
- cosign keyless verification fails in air-gapped deploys. Use
  key-based signing with the public key distributed to the deploy
  environment, and pin the Rekor/Fulcio bundle when available.
- Dependabot PRs pile up and get ignored. Auto-merge patch and
  minor updates after green CI; require human review only for
  major bumps and for actions.
- OIDC trust misconfigured: the cloud role trusts the wrong repo.
  Scope the trust policy to the exact repository and environment;
  a wildcard subject lets any repo in the org assume the role.
- Secret scanning passes but a key leaks via build logs. Masked
  secrets can still leak transformed (base64, URL-encoded); audit
  logs for suspicious echoes and rotate on suspicion.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration of the pipeline itself. Defenders monitor for
workflow files changed without a linked review, new `uses:` entries
pointing at unfamiliar actions, jobs requesting `id-token: write`
outside deploy workflows, and runs that access secrets they never
used before. Pipeline compromise indicators: a familiar action
suddenly exfiltrating (watch for new DNS or HTTPS connections from
build jobs to unknown hosts), artifacts whose cosign signatures no
longer verify, and deploys triggered outside the normal schedule.
Ship workflow audit logs and runner logs to a SIEM; alert on
`pull_request_target` workflows modified by non-security-team
authors, and on OIDC role assumptions from unexpected repositories.

## Key references

- GitHub Actions security hardening:
  https://docs.github.com/actions/security-guides/security-hardening-for-github-actions
- OWASP Top 10 CI/CD Security Risks:
  https://owasp.org/www-project-top-10-ci-cd-security-risks/
- SLSA framework (supply-chain levels): https://slsa.dev/
- Sigstore/cosign 2.4 docs: https://docs.sigstore.dev/cosign/
- Trivy 0.58 docs: https://aquasecurity.github.io/trivy/
- gitleaks 8.24: https://github.com/gitleaks/gitleaks
- CWE-829 (Inclusion of Functionality from Untrusted Control
  Sphere): unpinned third-party actions.
- CWE-798 (Use of Hard-coded Credentials): secrets in pipelines.
- MITRE ATT&CK T1195.002 (Supply Chain Compromise: Compromise
  Software Supply Chain): pipeline compromise pattern.
