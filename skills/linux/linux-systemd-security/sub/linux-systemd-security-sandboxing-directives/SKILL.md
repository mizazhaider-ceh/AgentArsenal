---
name: linux-systemd-security-sandboxing-directives
description: Use when sandboxing Linux services with systemd directives on
  systems you administer. Covers filesystem isolation (ProtectSystem,
  ProtectHome, PrivateTmp, ReadWritePaths), capability bounding
  (CapabilityBoundingSet, AmbientCapabilities, NoNewPrivileges), syscall
  filtering (SystemCallFilter, SystemCallArchitectures), network and device
  restrictions (RestrictAddressFamilies, PrivateDevices, ProtectKernelTunables),
  DynamicUser, and measuring results with systemd-analyze security. Defensive
  hardening that contains MITRE ATT&CK execution and persistence techniques.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-systemd-security]
extends: []
parent: linux-systemd-security
relates: [linux-systemd-security, linux-hardening-baseline, linux-hardening]
tools:
  - name: systemd
    version: 255
  - name: Python
    version: 3.12
---

Systemd can sandbox a service with a few unit file lines, constraining what a compromised process can touch: the filesystem, its own privileges, the syscalls it may invoke, and the network. This is defense in depth at its most practical: even if an attacker exploits the service, the sandbox decides what the exploit can reach. This sub-skill is the directive-level reference for defenders: what each sandboxing family does, safe starting templates, how to test without breaking services, and how to measure improvement. For systems you own or administer; purely defensive.

## Quick Workflow

1. Pick a target service, starting with network-exposed ones; record its baseline `systemd-analyze security` score.
2. Apply filesystem directives first (lowest breakage risk): ProtectSystem, ProtectHome, PrivateTmp.
3. Add privilege directives: NoNewPrivileges, User/Group, CapabilityBoundingSet.
4. Add syscall and namespace restrictions: SystemCallFilter, ProtectKernelTunables, PrivateDevices, RestrictAddressFamilies.
5. Restart the service and run its full functional test; check the journal for denials.
6. Re-run `systemd-analyze security` and record the improvement.
7. Roll the working set out via drop-ins in `/etc/systemd/system/<unit>.d/` so package upgrades preserve them.

## 1. Filesystem isolation directives

These control which parts of the filesystem the service can see and write. They are the safest starting point because most services declare their data paths clearly.

```ini
[Service]
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/myapp /var/log/myapp
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
```

`ProtectSystem=strict` mounts the entire OS tree read-only except paths listed in `ReadWritePaths`; `ProtectHome=true` hides home directories (`read-only` variant exposes them read-only); `PrivateTmp=true` gives the service its own `/tmp` invisible to others. Verify with `systemd-analyze security <unit> | grep -iE "protectsystem|privatetmp"` and by testing the service's actual file operations. If the service fails, the journal usually shows exactly which path was denied; add it to `ReadWritePaths` or `BindPaths` rather than loosening the directive.

## 2. Privilege and capability directives

These decide what privileges the service process can ever hold. Apply them after the filesystem layer, because they interact with how the service drops privileges itself.

```ini
[Service]
User=appsvc
Group=appsvc
NoNewPrivileges=true
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
SecureBits=keep-caps
```

`NoNewPrivileges=true` blocks all future privilege gains and is the highest-value single line. `CapabilityBoundingSet` limits the capability set; an empty value (`CapabilityBoundingSet=`) drops all capabilities. Check the service's actual needs first: `grep -r cap /proc/<pid>/status` shows `CapEff` for the running process, and `capsh --decode` translates it. A web server typically needs only `CAP_NET_BIND_SERVICE` (or none, if behind a proxy on a high port); anything more gets justified in writing.

## 3. System call filtering

`SystemCallFilter` restricts which syscalls the service may invoke, enforced by seccomp. This blunts entire exploit classes: a filter that denies `mount`, `ptrace`, and module syscalls removes common privilege escalation primitives even if the attacker gets code execution.

```ini
[Service]
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources
SystemCallArchitectures=native
SystemCallErrorNumber=EPERM
```

Start from the predefined sets (`@system-service` is a sane baseline for daemons) and subtract dangerous groups with `~`. `SystemCallArchitectures=native` blocks 32-bit compat syscalls often used to dodge filters. Test thoroughly: an over-tight filter kills the service with cryptic `EPERM` failures, so develop the filter in staging while watching the journal, and use `SystemCallLog=` during tuning to see what would be denied before enforcing.

## 4. Network, device, and namespace restrictions

These directives cut the service off from kernel interfaces and networks it does not need.

```ini
[Service]
PrivateDevices=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictNamespaces=yes
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictRealtime=true
```

`PrivateDevices=true` gives a minimal `/dev` (no physical device nodes); `RestrictAddressFamilies` limits socket types (a local-only service gets just `AF_UNIX`); `MemoryDenyWriteExecute=true` blocks writable-executable memory mappings (breaks JITs, which is the point for non-JIT services). Verify each family against the service's real behavior: a service that only talks to localhost PostgreSQL needs `AF_UNIX` (socket) or `AF_INET` (TCP), not both, and the journal will show denials if you cut too deep.

## 5. DynamicUser and stateless services

`DynamicUser=yes` allocates a throwaway UID at service start and wipes it at stop: the service cannot persist state as a user, cannot be given file ownership out of band, and gets a private `/tmp` automatically.

```ini
[Service]
DynamicUser=yes
StateDirectory=myapp
CacheDirectory=myapp
LogsDirectory=myapp
```

Pair it with `StateDirectory=`/`CacheDirectory=`/`LogsDirectory=`, which systemd creates owned by the dynamic user. This is ideal for stateless network services and wrong for anything needing stable UIDs, shared group access, or supplementary groups. Verify the dynamic UID with `ps -o user= -C myapp` showing a high-numbered dynamic user, and confirm state survives restarts via the declared directories.

## 6. Measuring with systemd-analyze security

The analyzer scores a unit's exposure from 0 (safe) to 10 across its sandboxing settings. Use it as a before/after metric and a checklist, not as a verdict.

```bash
systemd-analyze security myapp.service | tail -20
systemd-analyze security --offline=true /etc/systemd/system/myapp.service 2>/dev/null | grep -E "Overall|EXPOSURE"
```

Example output shape: per-directive pass/fail lines plus an overall exposure rating. Work through the failures top to bottom, applying the directive families from sections 1-4 in order, re-running the analyzer after each change. A database needing raw devices will never score perfectly; document the justified residual exposure instead of chasing zero.

## Edge cases

- Directives combine in subtle ways: `ProtectSystem=strict` plus `ReadWritePaths` requires every write path enumerated, and `PrivateUsers=true` (user namespaces) changes how file ownership appears inside the service, so add one family at a time and test.
- `MemoryDenyWriteExecute=true` breaks language runtimes with JIT (Java, Node.js, Python with certain extensions); exempt JIT services explicitly and note the exception rather than silently dropping the directive fleet-wide.
- `SystemCallFilter` with `~` subtraction is order-sensitive and set-based: verify the effective filter with `systemd-analyze` or by observing denials, because the mental model of "default minus these" is easy to get wrong.
- `RestrictAddressFamilies` with only `AF_UNIX` breaks services doing DNS resolution over UDP; if the service needs outbound DNS, keep `AF_INET`/`AF_INET6` and restrict at the firewall instead.
- `DynamicUser=yes` is incompatible with `User=`/`Group=` and with services that must own files outside their declared directories; migrating an existing stateful service to DynamicUser requires a data migration plan.
- Sandboxing applies to the service's children too, which breaks services that spawn helpers needing broader access (backup agents, plugin systems); use `ExecStartPre` sparingly and test the full process tree.
- The analyzer's heuristics lag behind new directives and kernel features; a directive it does not recognize is not necessarily useless, and a green score is not proof of containment, so pair measurement with functional and adversarial testing.

## Escalation

- If sandboxing breaks a production service and the cause is not obvious from the journal, revert to the last working directive set immediately, then reproduce in staging with `SystemCallLog=` and strace-style debugging; never iterate on production.
- If a vendor service cannot run under meaningful sandboxing (needs full host access by design), escalate the risk acceptance: document why, isolate the host's role, and add compensating monitoring.
- If different services on one host need conflicting sandboxing (one needs JIT, another needs strict memory policy), that is fine: directives are per-unit, so there is no conflict to resolve, only per-service documentation.
- If the analyzer shows high residual exposure after all applicable directives, escalate the service itself for review: some services are inherently hard to sandbox and may need architectural changes (splitting privileges, moving to a container) rather than more unit lines.

## Detection and defender view

Sandboxing directives are preventive, but they also generate detection signal: denied syscalls and filesystem accesses appear in the journal (and in auditd when seccomp logging is enabled), so a sudden burst of denials from a previously quiet service is an anomaly worth investigating (it may be an exploit attempt hitting the sandbox). MITRE mitigations map across techniques: sandboxing blunts execution (T1059), persistence helpers (T1543/T1053 need fewer privileges to matter less), and privilege escalation (T1068 loses its primitives when dangerous syscalls are filtered). Track the analyzer exposure score per critical service over time as a hardening metric, and alert on unit changes that remove sandboxing directives, which is both a misconfiguration and a possible attacker action to weaken containment before exploiting.

## Key references

- MITRE ATT&CK mitigations catalog: https://attack.mitre.org/mitigations/
- systemd.exec manual (all sandboxing directives): https://www.freedesktop.org/software/systemd/man/systemd.exec.html
- systemd-analyze manual: https://www.freedesktop.org/software/systemd/man/systemd-analyze.html
- systemd.resource-control manual: https://www.freedesktop.org/software/systemd/man/systemd.resource-control.html
- CIS distribution benchmarks (service hardening sections): https://www.cisecurity.org/cis-benchmarks/
- Linux seccomp and SystemCallFilter concepts: https://man7.org/linux/man-pages/man2/seccomp.2.html
