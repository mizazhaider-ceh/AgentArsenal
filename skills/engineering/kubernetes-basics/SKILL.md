---
name: kubernetes-basics
description: Use when deploying or troubleshooting workloads on Kubernetes
  on an authorized engineering task. Covers kubectl 1.31 context and
  namespace handling, Pods, Deployments, Services, ConfigMaps and Secrets,
  resource requests and limits, liveness and readiness probes, rolling
  updates and rollbacks, logs and port-forward debugging, and basic RBAC.
  Use when shipping a containerized app to a cluster, debugging a failing
  Pod, or reviewing manifests for correctness.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [docker-deep, linux-hardening]
tools:
  - name: kubectl
    version: 1.31
---

Kubernetes schedules containers across machines, restarts them when
they fail, and rolls out new versions without downtime. This skill
covers the operator basics with kubectl 1.31: the core workload
objects, how they fit together, and how to debug when a Pod refuses
to run. It assumes you can already build a container image (see
docker-deep) and focuses on getting it running correctly in a cluster.

## Quick Workflow

1. Verify cluster access and set the right context and namespace
   before touching anything.
2. Write manifests as versioned YAML files: Deployment, Service,
   ConfigMap, and Secret.
3. Set resource requests and limits, plus liveness and readiness
   probes, on every container.
4. Apply with `kubectl apply`, watch the rollout, and verify
   endpoints.
5. Store config in ConfigMaps and secrets in Secrets (base64, backed
   by etcd encryption at rest).
6. Debug failing Pods with `describe`, `logs`, and `exec`, in that
   order.
7. Roll forward with new images; roll back with `kubectl rollout
   undo` when a release misbehaves.
8. Grant the least RBAC each workload and human actually needs.

## 1. Context, namespaces, and cluster sanity

```bash
# Which cluster am I talking to? Check BEFORE applying anything.
kubectl config current-context
kubectl config get-contexts

# Work in a namespace, not default
kubectl create namespace demo
kubectl config set-context --current --namespace=demo
kubectl get nodes
kubectl get pods -n demo
```

A wrong context applies manifests to the wrong cluster. Make the
current context part of your shell prompt when you manage more than
one cluster.

## 2. Deployment and Service manifests

```bash
mkdir -p k8s && cat > k8s/deployment.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels:
    app: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: web
        image: demo-server:1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
        env:
        - name: PORT
          value: "8080"
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
EOF

cat > k8s/service.yaml <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
EOF

kubectl apply -f k8s/
kubectl rollout status deployment/web
kubectl get pods -l app=web
```

Requests guarantee scheduling capacity; limits cap runaway
consumption. Readiness gates traffic until the app is truly ready;
liveness restarts a stuck container. Without limits, one bad Pod can
starve the node.

## 3. ConfigMaps and Secrets

```bash
cat > k8s/config.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-config
data:
  LOG_LEVEL: "info"
  WORKERS: "4"
---
apiVersion: v1
kind: Secret
metadata:
  name: web-secret
type: Opaque
stringData:
  DB_PASSWORD: "change-me-in-production"
EOF

kubectl apply -f k8s/config.yaml

# Mount config as env vars in the Deployment
kubectl set env deployment/web --from=configmap/web-config
kubectl get secret web-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d; echo

# Secrets are base64, NOT encrypted by default: enable etcd encryption
# at rest on the cluster, and prefer an external secret manager
kubectl get secrets
```

Never commit real secret values to git. Use sealed secrets, external
secret operators, or CI-injected values; the manifest in git should
reference the secret name, not contain the value.

## 4. Debugging failing Pods

```bash
# 1. Describe: events at the bottom explain most failures
kubectl describe pod -l app=web | tail -30

# 2. Logs: current and previous (crashed) container
kubectl logs -l app=web --tail=100
kubectl logs -l app=web --previous --tail=100

# 3. Exec into a running Pod to look around
kubectl exec -it deploy/web -- sh
# inside: check the app listens, env is set, files exist

# Stream logs from all replicas at once
kubectl logs -l app=web -f --max-log-requests=5

# Check why a Pod is not scheduled
kubectl describe pod <pod-name> | grep -A5 Events

# Port-forward to test the Service locally without an Ingress
kubectl port-forward svc/web 8080:80
curl -s localhost:8080/healthz
```

The classic failure table: `ImagePullBackOff` means the image name,
tag, or registry credentials are wrong; `CrashLoopBackOff` means the
app exits, read the previous logs; `Pending` means no node has
capacity or the Pod is unschedulable, check events; `OOMKilled`
means the memory limit is too low, raise it and investigate the leak.

## 5. Rolling updates and rollbacks

```bash
# Roll forward to a new image
kubectl set image deployment/web web=demo-server:1.1.0
kubectl rollout status deployment/web

# Watch the rollout replace Pods one by one
kubectl get pods -l app=web -w

# Something broke: roll back to the previous revision
kubectl rollout undo deployment/web
kubectl rollout status deployment/web

# History of what was deployed when
kubectl rollout history deployment/web

# Pause a rollout to inspect a canary before it completes
kubectl rollout pause deployment/web
kubectl rollout resume deployment/web
```

Deployments keep the previous ReplicaSet, which is what makes instant
rollback possible. Verify new versions with readiness probes so bad
Pods never receive traffic during the rollout.

## 6. Basic RBAC

```bash
cat > k8s/rbac.yaml <<'EOF'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: web-reader
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  verbs: ["get", "list"]
  resources: ["pods", "pods/log"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: web-can-read-pods
subjects:
- kind: ServiceAccount
  name: web-reader
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
EOF

kubectl apply -f k8s/rbac.yaml
kubectl auth can-i --as=system:serviceaccount:demo:web-reader get pods
kubectl auth can-i --as=system:serviceaccount:demo:web-reader delete pods
```

Bind Roles (namespace-scoped) instead of ClusterRoles unless the
access truly is cluster-wide. Test effective permissions with
`kubectl auth can-i` before handing credentials to a workload.

## Edge cases

- `kubectl apply` says "unchanged" but the Pod did not update. The
  Pod template did not change (same image tag counts as unchanged);
  use immutable tags per build (`1.1.0`, never `latest`) so every
  release changes the template.
- Pod stuck in `Pending` with "Insufficient cpu". Requests exceed
  node capacity; lower requests, add nodes, or check for a
  misconfigured LimitRange forcing high defaults.
- Liveness probe kills a healthy app. The probe path or port is
  wrong, or `initialDelaySeconds` is shorter than startup time; the
  Pod restarts in a loop and logs show nothing wrong with the app.
- Secret change does not reach the app. Env-var secrets are only
  read at container start; restart the Pods (rollout restart) or
  mount secrets as volumes for automatic updates.
- `kubectl exec` fails with "unable to upgrade connection". The API
  server proxy or network policy blocks the exec websocket; check
  network policies and try from a node-adjacent network.
- Two Deployments select the same Pods. Overlapping `selector`
  labels make controllers fight over Pods; keep label sets unique
  per Deployment (`app: web` plus `version` or team labels).
- `imagePullPolicy: Always` with `:latest` causes surprise
  restarts. Pin digest or versioned tags and use `IfNotPresent` so
  node-cached images behave deterministically.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. A misconfigured cluster exposes the API server
without authentication, runs Pods as root without seccomp or
read-only filesystems, mounts the service account token into Pods
that never talk to the API, and stores Secrets unencrypted in etcd.
Detect misuse by auditing RBAC for `cluster-admin` bindings and
wildcard verbs, alerting on Pods with `hostNetwork`, `hostPID`, or
privileged security contexts, and watching audit logs for secret
reads outside expected service accounts. Cryptojacking in clusters
shows as DaemonSets or Deployments with no resource limits pinning
CPU; unexpected `kubectl exec` sessions into production Pods deserve
investigation. Enable audit logging and ship it somewhere an
attacker with cluster access cannot delete.

## Key references

- Kubernetes 1.31 documentation: https://kubernetes.io/docs/
- kubectl reference: https://kubernetes.io/docs/reference/kubectl/
- Pods, Deployments, Services concepts:
  https://kubernetes.io/docs/concepts/workloads/
- RBAC authorization: https://kubernetes.io/docs/reference/access-authn-authz/rbac/
- CIS Kubernetes Benchmark: https://www.cisecurity.org/benchmark/kubernetes
- CWE-250 (Execution with Unnecessary Privileges): Pods running as
  root or privileged.
- CWE-798 (Use of Hard-coded Credentials): secrets committed in
  manifests.
