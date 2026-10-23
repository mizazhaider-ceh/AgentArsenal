---
name: github-actions
description: Use when writing or debugging GitHub Actions workflows on an
  authorized engineering task. Covers workflow triggers, jobs and steps,
  matrix builds, caching dependencies, artifacts, reusable workflows,
  pinning third-party actions by SHA, OIDC authentication to clouds, and
  local testing with act 0.2.71. Use when adding CI to a repo, fixing a
  failing workflow, speeding up slow pipelines, or reviewing a workflow
  for correctness and safety.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [git-workflows, devsecops-pipeline, cicd-security]
tools:
  - name: git
    version: 2.48
  - name: GitHub CLI
    version: 2.68
  - name: act
    version: 0.2.71
---

GitHub Actions runs your CI/CD inside the repository: workflows
trigger on pushes, pull requests, and schedules, and execute jobs on
runners. This skill covers authoring correct workflows, the caching
and matrix patterns that keep them fast, and the pinning and
permissions practices that keep them safe. Debug locally with `act`
before burning runner minutes.

## Quick Workflow

1. Put workflows in `.github/workflows/` with one file per pipeline
   (ci.yaml, release.yaml).
2. Trigger narrowly: `pull_request` and `push` to protected branches,
   not every branch.
3. Set top-level `permissions: {}` and grant each job only what it
   needs.
4. Pin every third-party action to a full commit SHA, with a comment
   naming the version.
5. Cache dependencies and split jobs so failures are fast and
   obvious.
6. Test locally with `act` before pushing.
7. Watch runs with `gh run watch` and read logs with `gh run view`.
8. Store secrets in repository or environment secrets, never in the
   workflow file.

## 1. First workflow

```bash
mkdir -p .github/workflows
cat > .github/workflows/ci.yaml <<'EOF'
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions: {}  # deny everything by default, grant per job

jobs:
  test:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    steps:
      - name: Check out code
        uses: actions/checkout@v4  # pin to the release SHA, see section 1 note
      - name: Set up Python
        uses: actions/setup-python@v5  # pin to the release SHA, see section 1 note
        with:
          python-version: "3.12"
          cache: pip
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest -q
EOF

git add .github/workflows/ci.yaml
git commit -m "Add CI workflow"
git push
gh run list --limit 5
gh run watch
```

`permissions: {}` at the top denies all token scopes; each job then
declares exactly what it needs (`contents: read` to check out code).
Pin every third-party action to the full commit SHA published on the
action's release page (Dependabot opens PRs that keep pins current).
The examples below use version tags for readability; replace each tag
with the pinned SHA before merging to a protected branch.

## 2. Matrix builds and caching

```bash
cat > .github/workflows/matrix.yaml <<'EOF'
name: Matrix CI

on:
  pull_request:

permissions: {}

jobs:
  test:
    runs-on: ${{ matrix.os }}
    permissions:
      contents: read
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-24.04, macos-15]
        python: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4  # pin to the release SHA, see section 1 note
      - uses: actions/setup-python@v5  # pin to the release SHA, see section 1 note
        with:
          python-version: ${{ matrix.python }}
          cache: pip
      - run: pip install -r requirements.txt
      - run: pytest -q
EOF
```

`fail-fast: false` shows all matrix failures instead of cancelling
the rest after the first red cell. The built-in `cache:` option on
setup actions handles dependency caching without manual cache keys;
for custom caches use `actions/cache` with a key derived from lock
files.

```bash
# Manual cache example for a Go build
cat > .github/workflows/go-cache.yaml <<'EOF'
name: Go CI
on: [pull_request]
permissions: {}
jobs:
  build:
    runs-on: ubuntu-24.04
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v4  # pin to the release SHA, see section 1 note
      - uses: actions/setup-go@v5  # pin to the release SHA, see section 1 note
        with:
          go-version: "1.23"
          cache: true
      - run: go build ./...
      - run: go test ./...
EOF
```

## 3. Artifacts and job dependencies

```bash
cat > .github/workflows/artifacts.yaml <<'EOF'
name: Build and release

on:
  push:
    tags: ["v*"]

permissions: {}

jobs:
  build:
    runs-on: ubuntu-24.04
    permissions: { contents: read }
    steps:
      - uses: actions/checkout@v4  # pin to the release SHA, see section 1 note
      - run: go build -o app .
      - name: Upload binary
        uses: actions/upload-artifact@v4  # pin to the release SHA, see section 1 note
        with:
          name: app-linux-amd64
          path: app
          retention-days: 7

  release:
    needs: build
    runs-on: ubuntu-24.04
    permissions:
      contents: write  # needed to create the release
    steps:
      - name: Download binary
        uses: actions/download-artifact@v4  # pin to the release SHA, see section 1 note
        with:
          name: app-linux-amd64
      - name: Create release with the GitHub CLI (no third-party action needed)
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          chmod +x app
          gh release create "${{ github.ref_name }}" app \
            --title "${{ github.ref_name }}" --generate-notes
EOF
```

`needs:` orders jobs and passes artifacts between them. Short
retention on artifacts keeps storage costs down; release assets live
on the release, not in artifact storage.

## 4. OIDC: no long-lived cloud keys

```bash
cat > .github/workflows/deploy.yaml <<'EOF'
name: Deploy

on:
  push:
    branches: [main]

permissions:
  contents: read
  id-token: write  # required for OIDC token issuance

jobs:
  deploy:
    runs-on: ubuntu-24.04
    environment: production  # approvals and secrets scoped here
    steps:
      - uses: actions/checkout@v4  # pin to the release SHA, see section 1 note
      - name: Configure AWS credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4  # pin to the release SHA, see section 1 note
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-deploy
          aws-region: eu-west-1
      - name: Deploy
        run: ./scripts/deploy.sh
EOF
```

OIDC exchanges a short-lived GitHub token for cloud credentials, so
no static access keys live in secrets. The cloud side trusts the
specific repo and environment; `environment: production` adds
required reviewers before deploy jobs run.

## 5. Local testing with act

```bash
# Install act (runs workflows locally with Docker)
# https://github.com/nektos/act releases, or via package manager
act --version

# List jobs in a workflow file
act -W .github/workflows/ci.yaml -l

# Run the test job locally
act -W .github/workflows/ci.yaml -j test

# Dry run: print what would execute without running it
act -W .github/workflows/ci.yaml -j test -n
```

`act` catches YAML errors, bad action references, and broken shell
steps before you push. It is not a perfect replica of GitHub-hosted
runners (different images, no OIDC), so a green `act` run still gets
one real CI run before merge.

## 6. Debugging failed runs

```bash
# List recent runs and watch the latest
gh run list --limit 10
gh run view --log-failed | tail -60

# Re-run only failed jobs
gh run rerun --failed <run-id>

# Download logs for offline reading
gh run download <run-id> -n logs 2>/dev/null || gh run view <run-id> --log > run.log

# Debug with tmux-style live session on failure (add to workflow)
# uses: mxschmitt/action-tmate@...  # only on self-hosted or with approval
```

Enable debug logging per run by setting the `ACTIONS_STEP_DEBUG`
secret to `true`; it prints far more about what each step did.
For flaky tests, `gh run rerun --failed` retries without rerunning
green jobs.

## Edge cases

- Workflow does not trigger on pull requests from forks. Fork PRs
  run with read-only tokens and no secrets by default; workflows
  needing secrets must use `pull_request_target` with extreme care
  (it runs your base-branch code, review what it checks out).
- `GITHUB_TOKEN` permission denied on push or release. The job
  needs explicit `contents: write`; the default token is read-only
  when top-level permissions are locked down.
- Pinned SHA comment drifts from the real version. Re-pin with a
  tool like Dependabot, which opens PRs updating both the SHA and
  the comment together.
- Cache never hits. The key includes a lock-file hash; any
  dependency change invalidates it by design. For partial reuse,
  add `restore-keys` with a prefix fallback.
- `act` fails where GitHub succeeds. Usually a missing secret
  (`act -s NAME=value`), a different runner image, or a service
  container networking difference; treat `act` as a smoke test.
- Matrix explodes runner minutes. Cap the matrix (2 OS x 2
  versions is usually enough), use `fail-fast: false` only when
  you need the full failure picture.
- Secrets printed in logs. GitHub masks known secrets, but
  transformed values (base64, substrings) leak; never echo
  credentials, and rotate any secret that appears in a log.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. A misconfigured workflow shows unpinned actions
(floating `@v4` tags that can move), `pull_request_target` checking
out untrusted PR code, `permissions: write-all`, and secrets passed
as plain inputs to third-party actions. Detect misuse by auditing
workflow files for these patterns in CI, requiring CODEOWNERS
review on `.github/workflows/`, and alerting on workflow runs that
exfiltrate data (unexpected outbound network from build jobs, or
artifacts containing `.git` or secret files). A compromised action
pin is caught by verifying SHAs against the upstream release and by
Dependabot update PRs; cryptominers in CI reveal themselves through
sudden spikes in runner minutes and CPU-heavy steps with no
legitimate build output.

## Key references

- GitHub Actions documentation: https://docs.github.com/actions
- Workflow syntax: https://docs.github.com/actions/reference/workflows/workflow-syntax-for-github-actions
- Security hardening guide:
  https://docs.github.com/actions/security-guides/security-hardening-for-github-actions
- act (local runner): https://github.com/nektos/act
- GitHub CLI manual: https://cli.github.com/manual/
- CWE-798 (Use of Hard-coded Credentials): secrets in workflow
  files.
- CWE-250 (Execution with Unnecessary Privileges): write-all
  tokens and unscoped permissions.
