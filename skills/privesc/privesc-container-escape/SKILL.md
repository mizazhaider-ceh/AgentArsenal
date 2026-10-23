---
name: privesc-container-escape
description: Use when authorized testing lands you inside a container and
  you need to determine whether escape to the host is possible. Covers
  detecting containerization and the runtime, auditing privileged mode and
  dangerous mounts, abusing an exposed Docker socket, exploiting granted
  Linux capabilities (CAP_SYS_ADMIN, CAP_SYS_PTRACE, CAP_DAC_READ_SEARCH),
  host filesystem access through mounted paths, cgroup release_agent
  techniques in lab contexts, and Kubernetes pod escape primitives. Built
  for authorized engagements, labs, and CTFs only: escaping a container
  affects the host, so the authorization bar is host-level.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [privesc-linux, privesc-linux-vectors, linux-container-hardening]
tools:
  - name: docker
    version: 25.0
  - name: kubectl
    version: 1.29
  - name: Python
    version: 3.12
---
A container is not a security boundary by itself: it is kernel namespaces plus cgroups, and misconfigurations punch holes straight through to the host. This skill maps container escape vectors for authorized penetration tests, labs, and CTFs only. Escaping a container compromises the host and every workload on it, so treat escape testing as host-level exploitation: it needs explicit authorization, and in production it is usually out of scope. The workflow is detect, audit the container's privileges and mounts, verify each escape primitive by hand, exploit the quietest path, and document host impact carefully. Deep dives live in the sub-skills.

## Quick Workflow

1. Detect containerization: `/.dockerenv`, `/proc/1/cgroup`, hostname patterns, and limited `/proc` visibility.
2. Identify the runtime and orchestrator: Docker, containerd, CRI-O, Kubernetes service account tokens.
3. Audit the container's power: privileged flag, capabilities (`capsh --print`), mounts (`mount`, `/proc/mounts`), and exposed sockets.
4. Check for the classic escape primitives: docker socket mounted, host filesystem mounted, privileged mode, dangerous capabilities.
5. Verify each primitive by hand before exploiting: confirm the socket responds, confirm the mount is writable, confirm the capability is effective.
6. Exploit the quietest reliable primitive, confirm host access with a marker, and capture evidence.
7. Document host impact precisely: what host paths were reachable and what host-level actions were taken.

## 1. Detecting the container and runtime

Establish what you are inside before planning the escape.

```bash
ls -la /.dockerenv 2>/dev/null
cat /proc/1/cgroup 2>/dev/null | head -5
cat /proc/self/mountinfo | grep -i docker | head -5
ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>/dev/null
```

Example output shape: `/.dockerenv` existing plus cgroup paths containing `docker` confirms Docker; a serviceaccount token directory confirms a Kubernetes pod. Also check `hostname` (Docker sets random hex hostnames) and whether `docker`, `crictl`, or `kubectl` binaries exist inside the container.

## 2. Privileged mode and dangerous mounts

A privileged container has almost no boundary left; dangerous mounts are the next best thing.

```bash
capsh --print | head -5
mount | grep -v cgroup | head -20
```

Example output shape: `capsh` showing a full bounding set including `cap_sys_admin` suggests privileged mode; `mount` showing `/host` or `/` mounted from the host device, or `/var/run/docker.sock` in the list, is the escape primitive. Writable host mounts mean direct host file access: read `/etc/shadow` through the mount or write to host cron. The `privesc-container-escape-privileged-containers` sub-skill covers the full privileged audit.

## 3. Docker socket abuse

A mounted Docker socket is remote root on the host's container runtime: anyone who can talk to it can start a privileged container with the host filesystem mounted.

```bash
ls -la /var/run/docker.sock
curl -s --unix-socket /var/run/docker.sock http://localhost/version
```

Example output shape: the version endpoint returning JSON with `Version: 25.0` confirms the socket is live. The escape is launching a container with host mounts and chrooting into the host filesystem. Full technique, including socket API calls without the docker CLI, is in `privesc-container-escape-docker-socket`.

## 4. Capability abuse

Granted capabilities are granular root powers; several are escape-equivalent on their own.

```bash
capsh --print | grep -i bounding
grep Cap /proc/self/status
```

`CAP_SYS_ADMIN` enables mount and namespace manipulation escapes; `CAP_SYS_PTRACE` allows injecting into host processes when the PID namespace is shared or via host proc mounts; `CAP_DAC_READ_SEARCH` reads any host file through a mounted proc or sys; `CAP_SYS_MODULE` loads kernel modules on the shared host kernel. The `privesc-container-escape-capabilities-abuse` sub-skill maps each dangerous capability to its escape chain.

## 5. Kubernetes pod escapes

Pods add orchestrator-layer primitives on top of container escapes.

```bash
cat /var/run/secrets/kubernetes.io/serviceaccount/token 2>/dev/null | cut -c1-40
env | grep -i -E "kuber|service_host|service_port"
```

A mounted service account token plus network access to the API server means querying the API for your pod's permissions; overly broad RBAC (cluster-admin bindings, pod exec rights, secrets read) converts to cluster compromise. Also check for hostPath volumes, projected tokens, and node-level access. Escape within the authorized scope only; cluster-wide actions need explicit approval.

## Edge cases

- Some containers mount the docker socket read-only or with SELinux labels that block access; verify with an actual API call, not just `ls`.
- `capsh` output inside user namespaces can be misleading; cross-check with `/proc/self/status` capability masks decoded against capability names.
- Distroless and minimal containers lack `curl`, `capsh`, and even a shell; use available binaries or exfiltrate `/proc` files for local analysis.
- Read-only root filesystems block payload drops inside the container but do not block escapes through mounts and sockets.
- Seccomp and AppArmor profiles can neuter capability-based escapes even when the capability is granted; test the primitive rather than assuming.
- Kubernetes network policies may block pod-to-API-server traffic; verify connectivity before assuming the service account token is useful.

## Escalation

- If no escape primitive exists, treat the container as a beachhead: enumerate internal networks, reachable services, and mounted secrets for lateral movement within scope.
- When the socket is absent but the container is privileged, the cgroup release_agent path (lab contexts) or host device access may still apply.
- If capabilities are minimal and mounts are clean, check for writable hostPath volumes and overly permissive service account RBAC in Kubernetes.
- Combine primitives: a read-only host mount plus `CAP_DAC_READ_SEARCH` still yields full host file disclosure.

## Detection and defender view

Defenders prevent escapes by never mounting the docker socket, never running privileged containers, dropping all capabilities and adding back only what is needed, using read-only root filesystems, and enforcing seccomp and AppArmor profiles. Runtime security monitoring (Falco rules for socket access, unexpected mounts, and privilege use) detects escape attempts. From the authorized tester side, escape testing is host-impacting by definition: keep payloads minimal, avoid host modifications beyond proof markers, and document every host-level action with timestamps for the report.

## Key references

- MITRE ATT&CK T1611 (Escape to Host), T1609 (Container Administration Command)
- Docker security docs: https://docs.docker.com/engine/security/
- Kubernetes RBAC docs: https://kubernetes.io/docs/reference/access-authn-authz/rbac/
- HackTricks container escapes: https://book.hacktricks.xyz/linux-hardening/privilege-escalation/docker-breakout
- Center for Internet Security Docker Benchmark: https://www.cisecurity.org/benchmark/docker
- Falco container runtime rules: https://falco.org/docs/rules/
