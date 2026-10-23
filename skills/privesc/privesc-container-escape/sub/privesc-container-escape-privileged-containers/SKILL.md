---
name: privesc-container-escape-privileged-containers
description: Use when authorized container escape testing reveals a privileged
  container and you need to confirm host-level impact safely and document it.
  Covers detecting privileged mode from inside the container, verifying with
  capsh and device node inspection, mounting the host filesystem as evidence,
  auditing cgroup and device exposure, and mapping findings to MITRE ATT&CK
  T1611. Built for authorized engagements, labs, and CTFs only. Privileged
  containers erase the container/host boundary, so authorization must be at
  host level and Docker must be used with care.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-container-escape]
extends: []
parent: privesc-container-escape
relates: [privesc-container-escape, privesc-container-escape-capabilities-abuse, privesc-linux-vectors, linux-container-hardening]
tools:
  - name: capsh
    version: 2.44
  - name: Docker
    version: 25.0
  - name: Python
    version: 3.12
---

A privileged container is a container with the safety off: the runtime grants all capabilities, lifts device cgroup restrictions, and relaxes several namespace protections. From an authorized tester's view it is the fastest container escape primitive because the boundary is nearly gone. From a defender's view it is one of the highest severity misconfigurations a deployment can carry. This sub-skill covers how to confirm privileged mode from inside a container during an authorized engagement, how to demonstrate host impact with the minimum necessary action, and how to document the finding. Scope is authorized penetration tests, labs, and CTFs only. Because a privileged container implies host compromise, treat every test here as host-level exploitation and get host-level authorization first.

## Quick Workflow

1. Confirm you are in a container and note the runtime (Docker, containerd, CRI-O, Kubernetes) before touching anything.
2. Check the effective capability set with `capsh --print` and look for the full `0x000001ffffffffff` mask.
3. Check device exposure: list `/dev` for host devices (e.g. `/dev/sda`, `/dev/kvm`, `/dev/mem`) that a normal container never sees.
4. Check mounts and cgroups for host paths (`/proc/mounts`, `/proc/self/mountinfo`) and relaxed device rules.
5. Verify privileged mode indirectly if possible (capability mask is the strongest single signal) and record every check.
6. Demonstrate host impact with the quietest primitive available: mount a host block device read-only, or create a marker file through an exposed host path, never destructive writes.
7. Capture evidence (command, output, timestamp), revert any changes, and write the finding up as MITRE ATT&CK T1611 with host impact stated explicitly.

## 1. Detecting privileged mode from inside

No single file says "privileged", so you triangulate. The strongest signal is the capability mask: a normal Docker container gets a reduced set, while `--privileged` grants all 41 capabilities.

```bash
capsh --print | grep -i "current"
cat /proc/self/status | grep -i cap
grep Cap /proc/1/status
```

Example output shape: `Current: = cap_chown,cap_dac_override,...,cap_checkpoint_restore+ep` listing every capability, or a `CapEff:` value of `000001ffffffffff`. A full mask plus host device nodes in `/dev` is conclusive in practice. Also check `cat /proc/1/cgroup` for the runtime and `ls /sys/fs/cgroup/devices/` permissions: in a privileged container the devices cgroup controller often allows everything.

## 2. Auditing device and mount exposure

Privileged containers see host devices that standard containers cannot. Enumerate them and the mounts before deciding what to prove.

```bash
ls -la /dev/ | grep -E "sd[a-z]|vd[a-z]|nvme|mem|kvm|dm-"
mount | grep -v "^cgroup\|^tmpfs" | head -20
cat /proc/self/mountinfo | awk '{print $5, $10}' | sort -u | head -30
```

Example output shape: entries like `/dev/sda`, `/dev/sda1`, `/dev/mem` in `/dev`, and mountinfo rows showing host block devices mounted into the container. Also run `fdisk -l 2>/dev/null | head -20` to list host disks visible from inside. If `/dev/sda` exists and is readable, the host root filesystem is one mount command away, which is the core of the finding.

## 3. Demonstrating host impact safely

The goal is proof, not damage. Mount the host disk read-only, list a host-only path, and unmount. If even a read-only mount is out of scope, fall back to the evidence already gathered (capability mask plus device nodes) and describe the impact as confirmed-by-configuration.

```bash
mkdir -p /tmp/hostproof
mount -o ro /dev/sda1 /tmp/hostproof 2>&1 | head -3
ls /tmp/hostproof/etc/hostname 2>/dev/null && cat /tmp/hostproof/etc/hostname
umount /tmp/hostproof
```

Example output shape: `cat` printing the host's hostname, which differs from the container's hostname, proving host filesystem access. Always mount read-only (`-o ro`), always unmount afterwards, and never write to host paths. Document the exact device node, mount options, and the host-identifying value you read.

## 4. Host process and namespace visibility

Privileged mode also relaxes other boundaries. Check what else leaked through: host processes, host network, and kernel message access.

```bash
ps aux | head -10
ls /proc/ | grep -E "^[0-9]+$" | wc -l
ip addr show | head -20
dmesg 2>&1 | tail -5
```

Example output shape: a `ps` listing that includes host PIDs outside the container's init tree, or `ip addr` showing the host's physical interfaces, indicates further namespace leakage. In many deployments only some of these leak, so record exactly which boundaries held and which did not; that detail is what makes the report credible.

## 5. Kubernetes-flavored privileged pods

In Kubernetes, privileged mode comes from `securityContext.privileged: true` in the pod spec. From inside the pod, confirm with the same capability and device checks, and also look for the service account token, which decides whether a cluster-level escape is also in play.

```bash
ls /var/run/secrets/kubernetes.io/serviceaccount/ 2>/dev/null
cat /var/run/secrets/kubernetes.io/serviceaccount/namespace 2>/dev/null
capsh --print 2>/dev/null | head -3
```

Example output shape: a `namespace` file containing e.g. `default` plus a full capability mask means a privileged pod with a service account, which is a host escape plus potential cluster lateral movement. Treat the token as sensitive evidence: describe its permissions, do not exfiltrate it, and note that reading it is only for scope-confirmed engagements.

## Edge cases

- The capability mask can look full in some rootless or user-namespace setups where the capabilities are namespaced and far less powerful; cross-check with device node access, because real host devices do not lie about the boundary.
- `capsh` may not be installed in minimal images; fall back to decoding `CapEff` from `/proc/self/status` with a small Python snippet, or use `grep Cap /proc/1/status` and compare against the known full mask `000001ffffffffff`.
- Device nodes can be present but the mount syscall can still fail if the container has a restricted seccomp profile or AppArmor policy layered on top of privileged mode; a failed mount is a finding about layered defenses, not a failed test.
- On systems using cgroup v2 the devices controller path differs (`/sys/fs/cgroup` unified hierarchy); check `stat -fc %T /sys/fs/cgroup` for `cgroup2fs` and adjust paths instead of assuming the v1 layout.
- Some managed platforms (Fargate, Cloud Run, GKE Autopilot) never allow privileged mode at all; finding it there is impossible by design, so do not burn time re-verifying, note the platform constraint instead.
- Mounting `/dev/sda1` may fail with "wrong fs type" if the host uses LVM, LUKS, or a partition scheme you did not enumerate; run `lsblk` or `blkid` first to pick the right device, and never attempt to unlock encrypted volumes.
- In Docker Desktop or kind clusters the "host" you reach may be a VM, not the physical host; state exactly which layer you reached so the impact rating matches reality.

## Escalation

- If privileged mode is confirmed, treat the finding as confirmed host compromise and stop expanding: notify the engagement lead and confirm whether host-level actions stay in scope before going further.
- If the socket or orchestrator API is also reachable from the privileged container, document it as a combined finding (privileged plus control-plane access) because the remediation differs from either issue alone.
- If you can read host credentials (cloud metadata, kubelet credentials, `/etc/shadow` from a mounted host disk), report their existence and location without exfiltrating the values, and rotate or flag them per the engagement rules.
- If the engagement scope excludes the host, downgrade your proof to configuration-level evidence (capability mask, device list) and explicitly mark host impact as assessed but not demonstrated, with the reason recorded.

## Detection and defender view

Defenders detect privileged container abuse through runtime security tooling and audit trails. Falco rules flag `k8s.pod.privileged` and container starts with the privileged flag; auditd on the host can log mount syscalls originating from container PIDs. In Kubernetes, admission controllers (OPA Gatekeeper, Kyverno) can deny privileged pods at deploy time, and `kubectl` audit logs show who created the privileged workload and when. Docker daemon logs and `docker events` record privileged container creation with the image and user. The strongest preventive control is policy: never allow `privileged: true` in production, enforce it with admission control, and alert on any privileged container start as a severity-1 event because it is functionally equivalent to host root.

## Key references

- MITRE ATT&CK T1611 Escape to Host: https://attack.mitre.org/techniques/T1611/
- MITRE ATT&CK T1068 Exploitation for Privilege Escalation: https://attack.mitre.org/techniques/T1068/
- Docker runtime privilege and security docs: https://docs.docker.com/engine/security/
- Kubernetes pod securityContext reference: https://kubernetes.io/docs/tasks/configure-pod-container/security-context/
- Linux capabilities manual page: https://man7.org/linux/man-pages/man7/capabilities.7.html
- Falco privileged container detection rules: https://falco.org/docs/rules/
