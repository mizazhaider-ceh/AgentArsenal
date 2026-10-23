---
name: devsecops-pipeline
description: Use when designing or improving a DevSecOps delivery
  pipeline on an authorized engineering task. Covers pipeline stage
  design (build, test, scan, sign, deploy), placing SAST DAST and SCA
  gates, environment promotion with approvals, artifact promotion
  instead of rebuilds, SBOM generation, deployment strategies, and
  pipeline observability. Use when building a secure delivery pipeline
  from scratch, adding security gates to an existing one, or reviewing
  a pipeline design for gaps.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [cicd-security, github-actions, git-workflows]
tools:
  - name: Trivy
    version: 0.58
  - name: OWASP Dependency-Check
    version: 11.1.0
  - name: cosign
    version: 2.4
---

DevSecOps moves security into the delivery pipeline as automated
gates instead of a review at the end. This skill covers designing
that pipeline: which stages run in which order, where each security
check belongs, how artifacts move between environments without being
rebuilt, and how to prove what shipped. It is the design companion
to cicd-security (hardening the pipeline itself) and github-actions
(authoring the workflows).

## Quick Workflow

1. Sketch the stages: commit, build, unit test, SAST, SCA, image
   build, image scan, sign, deploy to staging, DAST, promote to
   production.
2. Make every stage produce versioned, immutable artifacts; never
   rebuild between staging and production.
3. Put fast checks early (lint, unit tests, SAST) and slow checks
   later (DAST, full image scan) so developers get feedback in
   minutes.
4. Gate promotion on scan results: fail on critical, triage high,
   record decisions.
5. Generate an SBOM at build time and attach it to the release.
6. Deploy with a strategy that allows rollback (blue-green or
   canary), behind required approvals.
7. Sign artifacts and verify signatures at deploy time.
8. Observe the pipeline itself: duration, failure rate, and time
   from commit to production per stage.

## 1. Reference pipeline design

A solid pipeline has the same shape regardless of tooling. Each box
is a stage with a clear pass/fail gate:

```
commit -> build -> unit test -> SAST -> SCA -> image build
  -> image scan -> sign + SBOM -> deploy staging -> DAST
  -> approval -> promote to production (no rebuild)
```

- Build once: compile, run unit tests, produce the artifact.
- SAST (static analysis) on every pull request: finds injection,
  hardcoded secrets, and unsafe patterns in your own code.
- SCA (software composition analysis) on every pull request:
  finds known CVEs in dependencies.
- Image scan after the image is built: OS packages plus app
  dependencies.
- Sign plus SBOM: the artifact becomes tamper-evident and its
  contents are inventoried.
- DAST (dynamic scan) against staging: finds runtime issues SAST
  cannot see.
- Promote the exact tested artifact to production; rebuilding
  invalidates every test you just ran.

## 2. SAST gate placement and tuning

Run a static analysis scanner over the codebase on every pull
request. The gate position matters more than the tool: SAST belongs
early, on the PR, where the developer who wrote the code sees the
finding within minutes.

```bash
# Example scan command shape (semgrep shown; swap in your org scanner)
pip install semgrep
semgrep --config auto --error --strict src/

# Scan only changed files for speed on large repos
git diff --name-only origin/main...HEAD | grep '\.py$' | xargs -r semgrep --config auto --error
```

Tune rules before enforcing: run in warn mode for two weeks, fix or
suppress the noise with documented reasons, then flip to blocking.
A SAST gate with a 40 percent false-positive rate trains developers
to ignore security gates entirely.

## 3. SCA gate with OWASP Dependency-Check

```bash
# OWASP Dependency-Check 11.1.0 scans project dependencies for known CVEs
# Release page: https://github.com/dependency-check/DependencyCheck/releases

dependency-check.sh \
  --project myapp \
  --scan . \
  --format HTML \
  --out reports/ \
  --failOnCVSS 9

# Keep the vulnerability database cache warm between runs
dependency-check.sh --updateonly
```

`--failOnCVSS 9` blocks only critical findings; tune the threshold
to your policy and record exceptions with expiry dates. For
container images and lockfiles, Trivy covers the same ground faster
(see cicd-security); use Dependency-Check where Trivy lacks a
language ecosystem.

## 4. SBOM generation and artifact promotion

```bash
# Generate an SBOM for the built image (SPDX format)
trivy image --format spdx-json --output sbom.spdx.json myapp:1.2.3

# Sign the image so tampering is detectable
cosign sign myapp:1.2.3

# Promote the SAME image digest from staging to production: no rebuild
STAGING_DIGEST=$(docker inspect myapp:1.2.3 --format '{{index .RepoDigests 0}}')
echo "promoting $STAGING_DIGEST"
docker tag "$STAGING_DIGEST" registry.example/myapp:prod-1.2.3
docker push registry.example/myapp:prod-1.2.3

# Verify signature before the deploy job touches the cluster
cosign verify --key cosign.pub "$STAGING_DIGEST"
```

Promotion by digest guarantees production runs the exact bytes that
passed staging. The SBOM answers "which library version is running
where" in minutes during the next big CVE.

## 5. Deployment strategies

```bash
# Blue-green with kubectl: two deployments, switch the service selector
kubectl apply -f k8s/app-green.yaml
kubectl rollout status deployment/app-green
# smoke tests against green go here
kubectl patch service app -p '{"spec":{"selector":{"version":"green"}}}'
# keep blue for instant rollback: patch the selector back if needed

# Canary with a second deployment at low replica count
kubectl apply -f k8s/app-canary.yaml
kubectl scale deployment/app-canary --replicas=3
# on failure: kubectl delete deployment/app-canary

# Record every production deploy as an annotation for forensics
kubectl annotate deployment/app \
  kubernetes.io/change-cause="release 1.2.3 promoted from staging" --overwrite
```

Choose blue-green when you need instant full rollback, canary when
you want to measure the new version on real traffic first. Both beat
recreate deployments, which cause downtime on every release.

## 6. DAST against staging

```bash
# Baseline OWASP ZAP scan against the staging deployment
zap-baseline.py -t https://staging.example.com \
  -r zap-report.html \
  -I

# Targeted scan of the API surface changed in this release
zap-api-scan.py -t https://staging.example.com/openapi.json \
  -f openapi -r zap-api-report.html
```

The `-I` flag fails only on HIGH findings so informational noise
does not block releases. DAST runs against a staging environment
that mirrors production topology (same ingress, same auth) with
synthetic data, never real customer data.

## 7. Pipeline observability

Track four delivery metrics per pipeline: lead time (commit to
production), deploy frequency, change failure rate (deploys causing
incidents), and mean time to restore.

```bash
# Example: list recent runs with timing from the GitHub CLI
gh run list --limit 20 --json databaseId,conclusion,createdAt,updatedAt
```

Alert when the pipeline itself degrades: p95 build time doubling
week over week means cache or runner trouble; a spiking scan-gate
failure rate means a vulnerable dependency merged widely; dropping
deploy frequency means approvals or flaky tests are blocking flow.
A pipeline nobody measures rots quietly until an incident exposes
it.

## Edge cases

- SAST blocks a release on a false positive the night before a
  deadline. Have a documented break-glass: a security approver can
  waive with a ticket and expiry, and the waiver is audited.
- DAST finds nothing because staging does not match production.
  Keep staging's topology identical (same ingress, same auth);
  data can be synthetic but shapes must match.
- SBOM generation slows every build. Generate once per artifact
  and attach it; cache the vulnerability database on runners.
- Teams bypass the pipeline with manual kubectl applies. Make the
  pipeline the only path with credentials to production; detect
  drift with scheduled diff jobs that alert on out-of-band changes.
- Signing keys are lost or compromised. With keyless (OIDC) signing
  there is no key to lose; with key-based signing, keep the private
  key in a KMS or HSM and have a rotation runbook ready.
- Promotion copies tags instead of digests. Tags are mutable; a
  re-pushed tag can change what "prod-1.2.3" means. Always promote
  by digest and keep the tag as a human label.
- Security gates run but nobody reads the reports. Route findings
  to the team's tracker automatically, assign owners, and review
  the aging backlog weekly; a gate without follow-through is
  theater.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration of the delivery pipeline design. A weak pipeline
design shows rebuilt artifacts between staging and production,
unsigned releases reaching production, DAST running against mocks
instead of a real staging, and security gates that warn but never
block. Detect drift by comparing deployed digests against the
signed release manifest; any digest in production without a
matching signature is an incident. Monitor for deploys that skip
stages (direct pushes to production branches), SBOMs missing from
releases, and approval steps rubber-stamped in seconds. During an
active CVE, the SBOM inventory tells you exactly which services are
exposed; a pipeline without SBOMs turns that into a week of manual
hunting.

## Key references

- SLSA framework (supply-chain levels): https://slsa.dev/
- OWASP DevSecOps Guideline:
  https://owasp.org/www-project-devsecops-guideline/
- OWASP Top 10 CI/CD Security Risks:
  https://owasp.org/www-project-top-10-ci-cd-security-risks/
- NIST SSDF (Secure Software Development Framework):
  https://csrc.nist.gov/projects/ssdf
- OWASP ZAP documentation: https://www.zaproxy.org/docs/
- OWASP Dependency-Check releases:
  https://github.com/dependency-check/DependencyCheck/releases
- CWE-494 (Download of Code Without Integrity Check): unsigned
  artifacts in the pipeline.
- CWE-829 (Inclusion of Functionality from Untrusted Control
  Sphere): unvetted dependencies passing SCA silently.
