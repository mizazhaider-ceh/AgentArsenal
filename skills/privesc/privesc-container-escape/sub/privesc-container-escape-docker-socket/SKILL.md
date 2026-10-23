---
name: privesc-container-escape-docker-socket
description: Use when assessing container deployments for exposed Docker
  sockets during an authorized engagement. Covers detecting mounted
  /var/run/docker.sock inside containers, auditing compose files and pod
  specs for socket mounts, understanding what the finding means for impact
  rating, how defenders detect socket abuse in audit logs and daemon events,
  and remediation guidance including least privilege and rootless Docker.
  Assessment and detection level throughout, this skill describes the risk and the check,
  aligned with MITRE ATT&CK T1611, not an exploitation procedure.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-container-escape]
extends: []
parent: privesc-container-escape
relates: [privesc-container-escape, privesc-container-escape-privileged-containers, linux-container-hardening]
tools:
  - name: Docker
    version: 25.0
  - name: auditd
    version: 3.1
  - name: Python
    version: 3.12
---

The Docker socket (`/var/run/docker.sock`) is the control plane of the Docker daemon, and mounting it into a container hands that container the keys to the host. This is one of the most commonly found high-severity container misconfigurations in assessments, usually introduced so a container can "manage its siblings" (CI agents, monitoring sidecars, portainer-style dashboards). This sub-skill is deliberately written at the assessment and detection level: it teaches you to find the misconfiguration, rate its impact accurately, recognize its abuse in defender telemetry, and recommend fixes. It does not provide an exploitation procedure. The finding maps to MITRE ATT&CK T1611 (Escape to Host), and in almost every rating scheme it lands at critical because daemon access is equivalent to host root.

## Quick Workflow

1. From inside each in-scope container, check for the socket's presence: `ls -la /var/run/docker.sock` and socket entries in `/proc/self/mountinfo`.
2. From the orchestrator side (where authorized), audit workload definitions for socket mounts: compose files, `docker inspect` output, pod specs, and Helm charts.
3. Classify the exposure: socket mounted read-write versus read-only, and which container user can reach it.
4. Rate the impact: a reachable daemon socket is host-level compromise by design, so document it as critical with the reasoning spelled out.
5. Check defender telemetry for signs of prior abuse: daemon logs, auditd socket activity, and unexpected container lifecycle events.
6. Write the remediation: remove the mount, replace the use case with a least-privilege pattern, and consider rootless Docker.
7. Verify the fix: re-run the detection checks and confirm the socket is no longer reachable from any workload container.

## 1. Detecting a mounted socket from inside the container

The check is simple and safe: look for the socket file and confirm how it is mounted. This is read-only inspection, appropriate even in production-adjacent assessments.

```bash
ls -la /var/run/docker.sock 2>/dev/null
cat /proc/self/mountinfo | grep -i "docker.sock"
stat -c "%a %U %G" /var/run/docker.sock 2>/dev/null
```

Example output shape: `srw-rw---- 1 root docker /var/run/docker.sock` plus a mountinfo line binding the host's `/var/run/docker.sock` into the container confirms the exposure. Note the permissions: if the container user is in the `docker` group (or runs as root), the socket is usable to that user. Record the mount mode (rw versus ro) and the container UID, because both feed the impact rating.

## 2. Auditing workload definitions for socket mounts

Finding one exposed container is a finding; finding the pattern across a fleet is a systemic issue. Audit the definitions that create containers.

```bash
grep -rn "docker.sock" /opt/stacks /srv/docker ~/docker 2>/dev/null | head -20
docker inspect $(docker ps -q) 2>/dev/null | grep -B3 -A3 "docker.sock" | head -30
```

Example output shape: compose files with `- /var/run/docker.sock:/var/run/docker.sock` under `volumes`, or `docker inspect` output showing a bind mount with source `/var/run/docker.sock`. In Kubernetes the equivalent is a `hostPath` volume pointing at the socket (rare, but check pod specs the same way). Common legitimate-seeming reasons you will see in comments: CI runners building images, log shippers, and management UIs. Each one needs a safer replacement pattern, which is covered in remediation.

## 3. What the finding means for impact rating

Rate this finding on what the socket permits, not on what you demonstrated. The Docker daemon API allows starting containers with arbitrary host mounts and privileged flags, which means anyone who can talk to the daemon can obtain host root. That makes a reachable socket a critical, host-level finding in virtually every assessment, equivalent in impact to a privileged container. Adjust the rating only on reachability facts: a socket mounted read-only into a container still permits most daemon operations (the read-only flag does not restrict the API the way people assume), while a socket reachable only by a non-root container user without group access is a lower but still high finding. State the rating rationale explicitly: "daemon API access equals host root, therefore critical", so the report reader does not have to infer it.

## 4. How defenders detect socket abuse

You assess the misconfiguration, but you should also know what its abuse looks like in telemetry, both to check for prior compromise and to advise the blue team.

```bash
journalctl -u docker.service --since "7 days ago" | grep -iE "create|start|exec" | tail -20
ausearch -k docker_socket 2>/dev/null | tail -10
docker events --since 24h 2>/dev/null | head -20
```

Indicators of abuse include: containers created with host path mounts or `--privileged` that do not match any known deployment pipeline, `docker exec` sessions at unusual hours, images pulled from untrusted registries just before a suspicious container start, and auditd records of processes inside containers connecting to the socket. A standing detection is an auditd watch on the socket path plus alerting on daemon API calls that create privileged containers or mount host paths. Recommend the client add both if they are missing.

## 5. Remediation patterns

Every remediation here follows the same principle: the workload almost never needs the full daemon API, so replace the socket with the narrowest mechanism that serves the real use case.

- Remove the mount entirely where it was added for convenience rather than need; most "management" containers work fine against a remote, authenticated daemon API instead.
- For CI image builds, use rootless builders (Kaniko, Buildah in rootless mode, buildkit with user namespaces) instead of Docker-in-Docker with the host socket.
- For monitoring, use the daemon's metrics endpoint or a read-only socket proxy that whitelists safe API paths rather than exposing the raw socket.
- For management UIs, run them outside the container fleet or behind mutual TLS to a dedicated daemon, never with the host socket mounted.
- Adopt rootless Docker where the workload allows it: a compromised rootless daemon is contained to an unprivileged user, which collapses the impact of a socket exposure from host root to user-level.
- Enforce the rule in policy: admission control or CI linting that fails any workload definition mounting `/var/run/docker.sock` (or any `hostPath` to daemon sockets) before it deploys.

## 6. Verifying the fix

Remediation is not done when the config changes; it is done when the detection checks come back clean. Re-run the inside-container socket check on every affected workload after redeploy, re-grep the workload definitions, and confirm in `docker inspect` output that no bind mount references the socket. Where a socket proxy was introduced, verify from inside the container that privileged operations are rejected while the intended read operations succeed. Record the before and after state in the report so the fix is auditable.

## Edge cases

- The socket may be mounted at a nonstandard path inside the container (for example `/tmp/docker.sock` with `DOCKER_HOST` set); check the `DOCKER_HOST` environment variable and any custom mount paths, not just the default location.
- Docker contexts and TCP listeners (`tcp://0.0.0.0:2375` without TLS) are the network equivalent of a mounted socket; audit daemon flags and `daemon.json` for exposed TCP ports as part of the same finding family.
- Podman and containerd expose their own sockets (`/run/podman/podman.sock`, containerd's API socket); the same assessment logic applies, so do not stop at Docker's path on mixed runtimes.
- A socket mounted read-only still exposes the full daemon API in practice; do not downgrade the finding on the read-only flag alone, because the API does not honor mount-level read-only the way file access does.
- In Docker Desktop, the socket inside containers reaches a Linux VM's daemon, not the physical host; the impact is still critical for that VM and everything in it, so describe the actual boundary reached.
- Some agents legitimately need limited daemon access (backup tools listing containers); route these through a filtering proxy and document the allowlist rather than granting the raw socket.
- Socket presence in a build container that is ephemeral and destroyed after each CI run is still a finding, but its exploitability window is short; note the lifetime in the rating rationale.

## Escalation

- If assessment telemetry shows signs of prior socket abuse (unknown privileged containers, off-hours daemon activity), escalate immediately: the engagement shifts from misconfiguration assessment to suspected compromise, and the client needs incident response, not just a report finding.
- If the socket is reachable from an internet-facing workload, raise the severity narrative: the attack path no longer requires an initial container foothold, and the client should treat it as an emergency fix.
- If the same socket mount pattern appears across many workloads, escalate from single finding to systemic control failure and recommend policy-level enforcement rather than per-workload fixes.
- If scope does not include the host or orchestrator, document the finding from the container-side evidence alone and mark orchestrator-level verification as a recommended follow-up rather than exceeding scope.

## Detection and defender view

The defender's view of this misconfiguration has three layers. At deploy time, CI linting and admission controllers (OPA Gatekeeper, Kyverno) should reject any workload mounting the Docker socket or equivalent daemon sockets. At runtime, Falco rules can alert on unexpected processes connecting to the socket or on containers started with host mounts and privileged flags outside the deployment pipeline. At the host level, auditd watches on `/var/run/docker.sock` plus daemon audit logging give a forensic trail of who talked to the daemon and what they asked it to do. The single most effective control is the deploy-time deny rule: no workload definition containing a daemon socket mount should ever reach a cluster.

## Key references

- MITRE ATT&CK T1611 Escape to Host: https://attack.mitre.org/techniques/T1611/
- Docker daemon security documentation: https://docs.docker.com/engine/security/
- Docker daemon socket and API security: https://docs.docker.com/engine/api/
- Rootless Docker documentation: https://docs.docker.com/engine/security/rootless/
- CIS Docker Benchmark (socket and daemon checks): https://www.cisecurity.org/cis-benchmarks/
- Falco container runtime threat detection: https://falco.org/docs/
