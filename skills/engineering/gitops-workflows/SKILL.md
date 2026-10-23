---
name: gitops-workflows
description: Use when implementing or reviewing GitOps for Kubernetes
  deployments. Covers repo structure, Argo CD or Flux setup, promotion
  between environments, secret handling, and drift detection. Also use
  when deployments are done by hand and need a reliable pipeline.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [git-workflows, github-actions, kubernetes-basics, devsecops-pipeline]
tools:
  - name: Git
    version: 2.47
  - name: Python
    version: 3.12
---

GitOps makes Git the source of truth for what runs in the cluster:
an agent syncs the desired state, so the cluster matches the repo.
This skill covers the practice: repo layout, tool setup, promotion
flows, and the security of the pipeline. It is engineering with
security built in, since every change is reviewed and auditable.

## Quick Workflow

1. Structure the repo: one folder per environment, shared bases,
   and clear ownership.
2. Choose the sync tool and install it with least privilege.
3. Define the promotion flow: how a change moves dev to staging to
   production.
4. Handle secrets: never in Git; use sealed secrets or external
   secret operators.
5. Enable drift detection and alerting: manual cluster edits must
   surface.
6. Require reviews on the Git side: the PR is the change control.
7. Test the sync in a non production cluster first.
8. Document rollback: revert the commit, the agent does the rest.

## 1. Repo structure and sync

```bash
# Layout: environments as folders, apps as subfolders
mkdir -p /tmp/gitops/{base,overlays/{dev,staging,prod}}/webapp
cat > /tmp/gitops/overlays/prod/kustomization.yaml << 'YAML'
resources:
  - ../../base/webapp
images:
  - name: webapp
    newTag: "1.4.2"   # promotion = bump the tag in a PR
YAML
```

```bash
# Argo CD app pointing at the environment folder (least privilege
# service account, sync only its namespace)
# argocd app create webapp-prod \
#   --repo https://git.example/gitops.git \
#   --path overlays/prod --dest-server https://kubernetes.default.svc \
#   --dest-namespace prod --sync-policy automated
echo "check: sync status, drift alerts, and who can approve prod PRs"
```

## 2. Secrets and drift

```bash
# Secrets via external operator (example: External Secrets)
# The Git repo holds an ExternalSecret manifest; the operator fetches
# the value from the vault at sync time. No secret bytes in Git, ever.
grep -rn "password\|token" /tmp/gitops/ --include="*.yaml" | head -5
# Any hit is a finding; move it to the secret operator
```

```bash
# Drift detection: the agent reports OutOfSync when someone edits the
# cluster by hand. Alert on it; manual edits bypass review.
# argocd app get webapp-prod -o json | jq .status.sync.status
echo "policy: drift auto heals or pages, never silently persists"
```

## Edge cases

- Emergency fix needed faster than the pipeline. Allow a
  documented break glass with automatic revert to Git state after.
- Multiple clusters and regions. One repo with per cluster
  overlays, or one repo per cluster; pick and stay consistent.
- The sync tool itself needs admin. Scope its service account to
  the namespaces it manages, not cluster admin.

## Escalation

- Sync stuck or failing: check the agent logs and the repo
  permissions before touching the cluster.
- Secret sprawl already in Git: rotate every exposed secret, purge
  history per policy, then move to the operator.

## Detection and defender view

GitOps is defensive by design: every change is a reviewed commit,
and drift detection catches manual tampering. Misuse looks like
direct cluster edits bypassing Git, or secrets committed to the
repo. Monitor the sync status, alert on drift, and audit who can
merge to the production path. The security win is auditability:
the cluster's history is the Git log.

## Key references

- Argo CD and Flux documentation.
- Related skills: git-workflows, devsecops-pipeline.
