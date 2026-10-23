---
name: linux-log-intrusion-analysis-detecting-lateral-movement
description: Use when hunting for lateral movement across Linux hosts during
  incident response or threat hunting you are authorized to conduct. Covers
  tracing SSH chains between hosts, spotting pivoting via agent forwarding
  and ProxyJump abuse, detecting new credentials and keys used for spread,
  correlating logins across hosts by time, auditing trust relationships
  (known_hosts, authorized_keys), and containing movement. Defensive analysis
  mapped to MITRE ATT&CK T1021 Remote Services and T1078 Valid Accounts.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-log-intrusion-analysis]
extends: []
parent: linux-log-intrusion-analysis
relates: [linux-log-intrusion-analysis, linux-log-intrusion-analysis-auth-log-triage, linux-hardening-baseline]
tools:
  - name: OpenSSH
    version: 9.6
  - name: auditd
    version: 3.1
  - name: Python
    version: 3.12
---

Attackers rarely stop at the first host: they pivot, harvesting credentials and hopping to the next system. Lateral movement is the phase where a single-host incident becomes a fleet incident, so detecting it quickly bounds the damage. This sub-skill covers the defensive analyst's method for finding movement between Linux hosts: tracing SSH chains, spotting forwarding and proxy abuse, finding the credentials used to spread, correlating logins across hosts, and auditing the trust relationships that make movement possible. For investigations you are authorized to conduct; defensive only. The parent skill sets the strategy; this file is the lateral movement field manual.

## Quick Workflow

1. From the compromised host, list outbound SSH sessions and connections: who went where, when, as whom.
2. Pull the accepted-login history on neighboring hosts for the same window and look for the chain.
3. Audit trust material on the source host: private keys, agent sockets, known_hosts, and authorized_keys changes.
4. Correlate by time: a login to host B minutes after a login to host A from the same user is a chain until proven otherwise.
5. Check for forwarding and proxy abuse: agent forwarding, ProxyJump chains, and tunnel listeners.
6. Identify the credential used for each hop (key, password, agent) and scope the rotation accordingly.
7. Contain: revoke the credentials, break the trust paths, and widen the hunt to every host in the chain before cleanup.

## 1. Tracing outbound SSH from the source host

Start where you have the foothold: what did this host reach out to? Auth logs show outbound only indirectly, so combine process, connection, and log evidence.

```bash
grep -E "Accepted" /var/log/auth.log | awk '{print $1, $2, $3, $9, $11}' | head -20
ss -tnp 2>/dev/null | grep -E ":22" | head -20
ps aux | grep -E "ssh |scp " | grep -v grep | head -10
```

Example output shape: accepted logins into this host (the inbound side of the chain), current TCP connections to port 22 elsewhere (the outbound side), and running ssh/scp processes with their full command lines (which reveal the target host and user). For historical outbound SSH, check shell history files and `~/.ssh/known_hosts` additions: a new known_hosts entry timestamps first contact with a host. Every outbound hop becomes a new host to investigate.

## 2. Correlating logins across hosts

A lateral chain looks like this in logs: host A shows an accepted login from the attacker at 02:10, host B shows an accepted login from host A's IP at 02:13 as the same user. Correlate aggressively.

```bash
grep "Accepted" /var/log/auth.log | awk '{print $1" "$2" "$3" "$9" "$11}' > /root/ir-evidence/accepted-hostA.log
awk '{print $4, $5}' /root/ir-evidence/accepted-hostA.log | sort | uniq -c | sort -rn | head -10
```

Do this on every host in the suspected chain, then align the timelines: same username appearing on multiple hosts within minutes, especially service or admin accounts, is the signature. Watch for the attacker's discipline breaking down: inconsistent usernames per host, logins at times the legitimate user never works, and key-based logins from hosts where that user normally uses a bastion. Build one merged timeline across hosts; the chain usually reads clearly once ordered.

## 3. Auditing trust material: keys, agents, known_hosts

Lateral movement runs on trust: private keys on disk, loaded ssh agents, and authorized_keys entries. Audit all of it on the source host.

```bash
find /home /root -name "id_*" -not -name "*.pub" 2>/dev/null | head -10
ls -la /tmp/ssh-*/agent.* /run/user/*/openssh_agent 2>/dev/null
cat /root/.ssh/known_hosts 2>/dev/null | awk '{print $1}' | head -20
find /home /root -name "authorized_keys" -newermt "2026-10-01" 2>/dev/null
```

Example output shape: private keys present (each one is a credential the attacker could have taken), agent sockets (a loaded agent lets an attacker hop without the key file), known_hosts entries (the map of where this host connects), and recently changed authorized_keys (new keys are both persistence and movement enablers). An `ssh-add -l` on a live agent lists loaded keys; treat every loaded key as compromised if the host is. Rotation scope follows the trust: every key found here, everywhere it is trusted.

## 4. Forwarding, ProxyJump, and tunnel abuse

SSH's legitimate features are the attacker's pivot toolkit: agent forwarding exposes the agent to the remote host, ProxyJump chains hops opaquely, and `-R`/`-L` tunnels punch through network boundaries.

```bash
grep -iE "forwarding|proxyjump|proxycommand" /etc/ssh/sshd_config /etc/ssh/ssh_config 2>/dev/null | head -10
ps aux | grep -E "ssh.*-[LRD]" | grep -v grep | head -10
ss -tlnp 2>/dev/null | grep -i ssh | head -10
```

Example output shape: forwarding settings (enabled agent forwarding is the risk), ssh processes with `-L`/`-R`/`-D` flags (active tunnels, with endpoints in the command line), and listening sockets owned by ssh (reverse tunnels waiting for use). Check `AllowAgentForwarding`, `AllowTcpForwarding`, and `PermitTunnel` in sshd_config as part of containment hardening. A reverse tunnel from a compromised host to an internal service is both movement and exfiltration path; note its endpoints before killing it.

## 5. Detecting credential harvesting for spread

Before moving, attackers collect the credentials that enable it: reading key files, dumping memory, querying the agent, or reusing passwords. Look for the harvesting.

```bash
grep -iE "id_rsa|id_ed25519|authorized_keys|\.ssh" /var/log/auth.log 2>/dev/null | head -10
ausearch -k ssh_keys 2>/dev/null | tail -10
ls -lat /home/*/.ssh/ /root/.ssh/ 2>/dev/null | head -20
```

Indicators: access times on private key files outside the owner's normal pattern, auditd records of processes reading `.ssh` directories that are not ssh itself, new files in `.ssh` (planted keys), and password-change or key-generation activity in the window. If harvesting is confirmed, the rotation scope expands from "the compromised account" to "every credential present on the host", which is usually the painful but correct answer.

## Edge cases

- Legitimate automation (Ansible, backup systems, monitoring) creates constant host-to-host SSH that looks exactly like lateral movement; maintain an inventory of expected automation sources and service accounts so hunts start from anomalies, not from cron jobs.
- Bastion and jump-host architectures concentrate logins through one host by design; on bastions, correlate session start/end with downstream host logins rather than treating every hop as suspicious.
- Attackers may use non-SSH movement (exploited services, database links, container escapes, management APIs); if the SSH trail goes cold but the timeline continues, widen to service logs and network flows instead of concluding movement stopped.
- Clock skew between hosts breaks time correlation; verify NTP on every host in the chain before ordering events, and allow skew tolerance in the correlation window.
- Deleted logs on intermediate hosts are common when the attacker cleans as they go; a host with a suspicious gap sitting between two confirmed hops is itself evidence of movement through it.
- IPv6 and nonstandard SSH ports evade naive `:22` greps; check listening and established connections broadly (`ss -tnp`) and know your environment's actual SSH ports.
- Cloud and ephemeral hosts may no longer exist; pivot to cloud audit trails (which recorded the instance's network flows and API calls) when the host itself is gone.

## Escalation

- If the chain reaches a high-value host (domain controller equivalent, backup server, identity provider, production database), escalate immediately regardless of what was done there: presence on crown-jewel hosts changes the incident's severity class.
- If credential harvesting is confirmed, escalate for fleet-wide credential rotation planning: the movement phase may be over, but the harvested credentials make re-entry trivial until rotated.
- If movement crossed a trust boundary (prod to dev, corporate to OT, one client to another in MSP contexts), escalate the scope expansion explicitly: each boundary crossed is a separate notification and containment problem.
- If you cannot determine the full chain (logs missing, hosts gone), escalate the uncertainty itself: recommend broader containment (rotate more, isolate more) proportional to what cannot be ruled out, and say so plainly.

## Detection and defender view

Lateral movement detection is continuous correlation, not a one-time hunt. Defenders baseline normal host-to-host SSH (which accounts, which paths, which hours) and alert on deviations: first-time host pairs, unusual service accounts moving, off-hours chains, and forwarding/tunnel creation. MITRE T1021 (Remote Services) is the technique; T1078 (Valid Accounts) is usually the enabler, which is why credential hygiene and rotation scope matter as much as the network detection. Network flow data and EDR process telemetry complement log correlation, catching movement that never touches auth logs. The architectural defenses are structural: bastion hosts with session recording, no direct host-to-host SSH for users, agent forwarding disabled by default, and network segmentation that makes each hop a policy decision rather than a default route.

## Key references

- MITRE ATT&CK T1021 Remote Services: https://attack.mitre.org/techniques/T1021/
- MITRE ATT&CK T1078 Valid Accounts: https://attack.mitre.org/techniques/T1078/
- MITRE ATT&CK T1550 Use Alternate Authentication Material: https://attack.mitre.org/techniques/T1550/
- OpenSSH forwarding and tunneling docs: https://man7.org/linux/man-pages/man1/ssh.1.html
- NIST SP 800-92 Guide to Computer Security Log Management: https://csrc.nist.gov/publications/detail/sp/800-92/final
- CIS distribution benchmarks (SSH and account sections): https://www.cisecurity.org/cis-benchmarks/
