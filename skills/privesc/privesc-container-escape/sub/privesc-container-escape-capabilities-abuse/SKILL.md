---
name: privesc-container-escape-capabilities-abuse
description: Use when authorized container escape testing shows a container
  running with extra Linux capabilities and you need to assess which ones are
  dangerous. Covers enumerating effective capabilities with capsh, auditing
  CAP_SYS_ADMIN, CAP_SYS_PTRACE, CAP_DAC_READ_SEARCH, CAP_NET_RAW and
  CAP_SYSLOG, understanding what each capability permits against the host,
  and mapping findings to MITRE ATT&CK T1611. For authorized engagements,
  labs, and CTFs only. Capabilities are the fine-grained form of privileged
  mode, and Docker capability audits are a core container skill.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-container-escape]
extends: []
parent: privesc-container-escape
relates: [privesc-container-escape, privesc-container-escape-privileged-containers, privesc-linux-vectors, linux-container-hardening]
tools:
  - name: capsh
    version: 2.44
  - name: Docker
    version: 25.0
  - name: Python
    version: 3.12
---

Capabilities split root's power into pieces, and Docker hands containers a default subset. When a deployment adds capabilities back (often cargo-culted from a Stack Overflow answer), each added piece can be an escape primitive. This sub-skill covers enumerating a container's effective capabilities during an authorized engagement, judging which ones are dangerous, and demonstrating impact with minimal, reversible actions. It is the fine-grained companion to the privileged-containers sub-skill: privileged mode is all capabilities at once, this is the audit of the individual ones. Scope is authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Dump the effective capability set: `capsh --print` and `CapEff` from `/proc/self/status`.
2. Decode the hex mask into named capabilities so the finding names the exact primitive (script it if `capsh` is missing).
3. Compare against the Docker default set; every capability beyond the default is a finding.
4. Rank the extras by danger: CAP_SYS_ADMIN, CAP_SYS_PTRACE, and CAP_DAC_READ_SEARCH are the classic escape trio.
5. Verify each dangerous capability with the smallest possible proof action (mount, read, or trace) and record the result.
6. Check how the capability was granted (compose file, pod securityContext, runtime flags) so the report can point at the configuration line.
7. Write each capability up separately with its ATT&CK mapping, because remediation is per-capability (drop it) rather than one big fix.

## 1. Enumerating effective capabilities

Start with the raw data: what the kernel actually granted this process, not what the config claims.

```bash
capsh --print 2>/dev/null | head -8
grep Cap /proc/self/status
cat /proc/self/status | grep -i capeff
```

Example output shape: `CapEff: 00000000a80425fb` for a standard Docker container versus `000001ffffffffff` for full privileges. If `capsh` is absent, decode the mask in Python against the capability list from `capabilities(7)`. Record both the hex value and the decoded names; reviewers trust findings that show their work.

## 2. CAP_SYS_ADMIN: the near-root capability

CAP_SYS_ADMIN covers mount, namespace manipulation, cgroup configuration, and a long tail of other privileged operations. In a container it is the most common path to escape: mounting the host filesystem or a cgroup with a malicious `release_agent` (in lab contexts), or creating namespaces to reach host resources.

```bash
python3 -c "
import os
caps = int(open('/proc/self/status').read().split('CapEff:')[1].split()[0], 16)
SYS_ADMIN = 21
print('CAP_SYS_ADMIN effective:', bool(caps & (1 << SYS_ADMIN)))
"
mount -t tmpfs none /tmp/captest 2>&1 | head -2; umount /tmp/captest 2>/dev/null
```

Example output shape: `CAP_SYS_ADMIN effective: True` plus a successful tmpfs mount proves the capability is live. For the report, a successful mount syscall is sufficient proof of the primitive; you do not need to complete a full escape to rate the finding as host-impacting. Keep proof actions to harmless mounts on empty directories and clean them up.

## 3. CAP_SYS_PTRACE and process inspection

CAP_SYS_PTRACE lets a process trace and inspect other processes, which in a container can mean reading secrets from sibling processes or, where PID namespace sharing is enabled, host processes.

```bash
ps aux | head -5
cat /proc/1/cmdline 2>/dev/null | tr '\0' ' '; echo
ls /proc/ | grep -E "^[0-9]+$" | wc -l
```

Example output shape: visibility into processes outside the container's own tree, or the ability to read another process's memory maps and environment (where secrets live), confirms the capability matters here. If only the container's own processes are visible, the capability is present but blunted by namespace isolation: record that nuance, because it changes the impact rating from escape to information disclosure.

## 4. CAP_DAC_READ_SEARCH and file access

CAP_DAC_READ_SEARCH bypasses file read permission checks and directory search restrictions. In a container with host paths mounted (even read-only mounts of configuration), it turns limited visibility into broad host file disclosure.

```bash
ls /host 2>/dev/null; ls / 2>/dev/null | head
find / -maxdepth 3 -name "shadow" 2>/dev/null | head -5
```

Example output shape: successfully listing or reading files that the container's UID would normally be denied (host `/etc/shadow` content through a mount, other tenants' files on shared volumes) proves the bypass. Pair this check with the mount audit from the privileged-containers sub-skill: the capability alone is less useful without a host path to point it at, and the report should say which mounts made it dangerous.

## 5. The supporting cast: NET_RAW, SYSLOG, and the rest

Several other capabilities matter in container assessments even though they rarely escape alone.

```bash
capsh --print 2>/dev/null | grep -iE "net_raw|syslog|sys_module|mknod|sys_time|net_admin"
```

CAP_NET_RAW enables packet crafting and sniffing on attached networks (lateral movement aid, MITRE T1040). CAP_SYSLOG permits reading kernel logs that may leak host information. CAP_SYS_MODULE would allow loading kernel modules, which is a direct host compromise if the module interface is reachable. CAP_MKNOD plus device cgroup access can recreate host device nodes. Assess each one found beyond the Docker default set, and remember that combinations (for example NET_ADMIN plus SYS_ADMIN) are worse than the sum of their parts.

## 6. Tracing the grant back to configuration

A finding is only fixable if the report names the line that granted the capability. Check the usual suspects.

```bash
grep -ri "cap_add\|capabilities:" /opt/docker* /srv 2>/dev/null | head -10
grep -ri "add:" /etc/docker/daemon.json 2>/dev/null
```

From outside the container (with orchestrator access in scope), inspect the workload definition: `docker inspect <id> | grep -A15 CapAdd`, `kubectl get pod <p> -o yaml | grep -B2 -A8 capabilities`, or the compose file's `cap_add` block. The remediation for every finding here is the same shape: drop the capability unless a named feature needs it, and prefer `cap_drop: [ALL]` with explicit `cap_add` for the minimum required set.

## Edge cases

- Capabilities can be granted in the bounding set but not the effective set of your shell; always test from the process that will actually use the primitive, because a capability that is not effective is not exploitable from where you stand.
- User namespaces remap capabilities: a full-looking mask inside a user-namespaced container is scoped to that namespace and usually cannot touch the host, so cross-check with an actual device or mount test before rating impact.
- `capsh --print` output differs between libcap versions in how it names newer capabilities (for example `cap_checkpoint_restore`); decode the hex mask yourself when names look unfamiliar rather than guessing.
- Some runtimes add capabilities for their own features (containerd and CRI-O defaults differ slightly from Docker's); compare against the runtime's documented default set, not just Docker's, to avoid false positives.
- Seccomp profiles can block the syscalls a capability would otherwise allow (mount blocked despite CAP_SYS_ADMIN); test the syscall, not just the capability bit, and record layered defenses as risk reducers.
- In Kubernetes, capabilities can come from the pod securityContext, a SecurityContextConstraint, or a mutating admission webhook; check all three layers before concluding where to fix it.
- Dropped capabilities in a parent process are inherited as dropped by children; if your shell lacks the capability but the workload's main process has it, the finding still stands for the workload, so enumerate from the workload process, not just your shell.

## Escalation

- If CAP_SYS_ADMIN is confirmed effective with mount ability, treat the container as host-compromisable and confirm host-level scope with the engagement lead before demonstrating anything beyond a harmless proof mount.
- If capability abuse leads to host credential access (cloud instance metadata, service account tokens), report locations only, do not exfiltrate values, and follow the engagement's credential handling rules.
- If the grant came from a cluster-wide policy (admission webhook, SCC) rather than one workload, escalate the finding to systemic: every workload under that policy is affected, and the fix belongs in the policy, not the pod spec.
- If testing in production-adjacent environments, prefer configuration evidence (decoded mask plus the granting config line) over live proof actions, and get explicit approval for each proof action in writing.

## Detection and defender view

Defenders catch capability abuse through admission-time policy and runtime detection. OPA Gatekeeper and Kyverno can deny pods requesting capabilities outside an allowlist; Pod Security Standards (restricted profile) drop all capabilities by default. At runtime, Falco rules detect unexpected capability use such as mount syscalls from containers or ptrace activity across container boundaries. Auditd with rules on `capset`, `mount`, and `ptrace` syscalls gives host-level visibility, and `docker inspect` output in CI can be scanned for `CapAdd` entries before deployment. The preventive posture is simple and effective: default to dropping all capabilities, add back only named ones with a documented reason, and alert on any workload requesting CAP_SYS_ADMIN as a high-severity policy violation.

## Key references

- MITRE ATT&CK T1611 Escape to Host: https://attack.mitre.org/techniques/T1611/
- MITRE ATT&CK T1068 Exploitation for Privilege Escalation: https://attack.mitre.org/techniques/T1068/
- Linux capabilities manual: https://man7.org/linux/man-pages/man7/capabilities.7.html
- Docker runtime privilege options: https://docs.docker.com/engine/containers/run/
- Kubernetes container securityContext: https://kubernetes.io/docs/tasks/configure-pod-container/security-context/
- Pod Security Standards: https://kubernetes.io/docs/concepts/security/pod-security-standards/
