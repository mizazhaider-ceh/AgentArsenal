---
name: container-image-security
description: Use when assessing container image security on an
  authorized engagement or in your own pipeline. Covers image
  scanning, base image choice, secret leakage in layers, and signing
  with Cosign. Also use when a deployment's images need hardening
  before production.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [docker-deep, cicd-security, devsecops-pipeline]
tools:
  - name: Python
    version: 3.12
---

Container images ship the whole userspace: vulnerable libraries,
leaked secrets in layers, and malware in base images. This skill
covers the assessment and hardening: scanning, minimal bases,
layer forensics, and signing. Work on images you own or are
authorized to assess.

## Quick Workflow

1. Inventory the images: where they come from, how they are built,
   and where they are stored.
2. Scan for vulnerabilities with a scanner and triage by
   exploitability, not just CVE count.
3. Inspect layers for secrets: history, env, and files in every
   layer.
4. Check the base image: minimal, pinned, and from a trusted
   source.
5. Verify the build: reproducible, no network at build surprises,
   and SBOM generated.
6. Check signing: Cosign signatures verified at deploy time.
7. Review runtime config: non root, read only filesystem, dropped
   capabilities.
8. Gate the pipeline: block on criticals with a documented
   exception process.

## 1. Scanning and layer forensics

```bash
# Scan with trivy (as assessment tooling)
trivy image --severity HIGH,CRITICAL myregistry/app:1.2.3 2>/dev/null | head -40
# Triage: focus on reachable, network exposed packages first
```

```bash
# Secrets in layers: history shows build time values, layers keep deleted files
docker history --no-trunc myregistry/app:1.2.3 | head -20
# Extract every layer and grep for secrets
mkdir -p /tmp/img && cd /tmp/img
docker save myregistry/app:1.2.3 -o app.tar && tar xf app.tar
grep -rhoE "AKIA[0-9A-Z]{16}|xox[bap]-[A-Za-z0-9-]{10,}" . 2>/dev/null | sort -u | head
# Any hit = secret baked into the image; rotate it and fix the build
```

```bash
# Base image check: distroless or minimal, pinned by digest
docker inspect myregistry/app:1.2.3 --format '{{.Config.Image}}' | head -2
# Pinned by digest (sha256:...) not by floating tag (latest)
```

## 2. Signing with Cosign

```bash
# Sign at build time (pipeline)
cosign sign --key cosign.key myregistry/app:1.2.3
# Verify at deploy time (admission controller or manual check)
cosign verify --key cosign.pub myregistry/app:1.2.3
# Unsigned or badly signed images must not deploy
```

## Edge cases

- The scanner flags hundreds of CVEs in a language runtime. Triage
  by the app's actual exposure; a CVE in an unused binary is noise.
- The image is from a vendor and cannot be rebuilt. Scan it, sign
  your approval, and isolate it at runtime.
- Secrets found in a public image. Rotate immediately; the secret
  is already compromised.

## Escalation

- Critical RCE in an internet facing image: patch and redeploy on
  an emergency timeline, then fix the pipeline gate that missed it.
- Signing missing everywhere: propose the rollout in stages (warn,
  then enforce) to avoid breaking deploys.

## Detection and defender view

Defenders detect image attacks with registry scanning on push,
admission controllers that block unsigned or vulnerable images, and
runtime monitoring for unexpected processes. They defend with
minimal bases, automated rebuilds, and signed pipelines. The
durable practice is treating images as build artifacts with full
provenance: source, SBOM, scan results, and signature, all the way
to the cluster.

## Key references

- CWE-798 (Use of Hard-coded Credentials): layer secrets.
- CWE-1104 (Use of Unmaintained Third Party Components).
- Sigstore/Cosign documentation.
