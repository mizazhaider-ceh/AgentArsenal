---
name: linux-container-hardening
description: Use when hardening Linux containers you run. Covers
  runtime options, seccomp and AppArmor profiles, capability drops,
  read only filesystems, and user namespaces. Also use when a
  container deployment needs a security baseline.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening, container-escape, docker-deep]
tools:
  - name: Python
    version: 3.12
---

Containers share the host kernel, so hardening is about limiting
what a compromised container can do: drop capabilities, filter
syscalls, and make the filesystem read only. This skill covers the
practical baseline for containers you run: the runtime flags, the
profiles, and the checks. It complements image hardening with
runtime hardening.

## Quick Workflow

1. Run as non root: set the user in the image and at runtime.
2. Drop all capabilities, then add back only what is needed.
3. Apply seccomp: the default profile or a tighter custom one.
4. Apply AppArmor or SELinux confinement where available.
5. Make the filesystem read only with tmpfs for the writable bits.
6. Limit resources: CPU, memory, and PIDs per container.
7. Drop the dangerous flags: no privileged, no host namespaces.
8. Verify the config on a running container.

## 1. Runtime hardening flags

```bash
# Hardened run example (docker as tooling)
docker run -d --name app \
  --user 10001:10001 \
  --cap-drop=ALL --cap-add=NET_BIND_SERVICE \
  --security-opt seccomp=/etc/docker/seccomp-tight.json \
  --security-opt apparmor=docker-tight \
  --read-only --tmpfs /tmp --tmpfs /run \
  --memory=512m --cpus=1 --pids-limit=100 \
  --network appnet \
  myregistry/app:1.2.3
```

```bash
# Verify a running container (your host)
docker inspect app --format '{{.Config.User}} {{.HostConfig.Privileged}}'
# Want: user set, privileged false
docker exec app cat /proc/self/status | grep -i cap
# Want: minimal bounding capabilities
docker exec app touch /test_write 2>&1 | head -2
# Want: read only file system error
```

## 2. Orchestrator enforcement

```bash
# Kubernetes: enforce with Pod Security Standards (restricted)
# namespace labels: pod-security.kubernetes.io/enforce=restricted
# Or policy engines (Kyverno/Gatekeeper) requiring:
# - runAsNonRoot, readOnlyRootFilesystem, seccompProfile RuntimeDefault
# - no privileged, no hostPath, no hostNetwork
kubectl label namespace prod pod-security.kubernetes.io/enforce=restricted
```

## Edge cases

- The app needs a dropped capability. Add it back narrowly and
  document why; "it didn't work" is not documentation.
- Legacy app needs root. Then isolate harder: user namespace
  remapping, tighter seccomp, and a plan to fix the app.
- The platform manages the runtime (Fargate, Cloud Run). Apply
  what the platform exposes and verify the rest is defaulted safe.

## Escalation

- Escape suspected: the runtime flags are the containment; check
  them first, then do incident response.
- Need the image side: hand to container-image-security.

## Detection and defender view

Container hardening is prevention; its detection side is runtime
monitoring for policy violations: privileged launches, capability
use outside the profile, and writes to read only paths. Defenders
enforce with admission control so non compliant pods never start.
The durable practice is secure by default templates every team
uses, not per app heroics.

## Key references

- CIS Docker and Kubernetes benchmarks.
- CWE-250 (Execution with Unnecessary Privileges).
- Related skills: container-escape, linux-hardening.
