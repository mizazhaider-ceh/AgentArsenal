---
name: incident-containment-playbooks
description: Use when a security incident is confirmed on systems you
  are authorized to defend and you must stop the bleeding without
  destroying evidence. Covers the containment decision framework, host
  isolation with iptables and Windows Firewall, network segmentation
  and quarantine VLANs, account disablement and credential rotation,
  perimeter blocking of indicators, evidence preservation order, and
  ransomware-specific containment. Use when the incident-response
  workflow reaches the containment phase, when an active attacker
  needs cutting off, or when preparing containment runbooks before an
  incident. Authorized systems only, verified with osquery checks and
  Velociraptor fleet actions.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, incident-timeline-analysis, incident-breach-scoping]
tools:
  - name: iptables
    version: 1.8
  - name: osquery
    version: 5.12.1
  - name: Velociraptor
    version: 0.72
  - name: Python
    version: 3.12
---

Containment stops the attacker from doing more damage while
preserving the evidence needed to understand what happened. It is a
set of reversible, documented actions: isolate hosts, segment
networks, disable accounts, block indicators. This skill covers the
playbooks for each, the order to run them in, and the tradeoffs the
incident commander must weigh. It assumes you are operating on systems
you are authorized to defend, under an incident command structure.
Containment without scoping is guesswork; scoping without
containment is negligence.

## Quick Workflow

1. Confirm the incident is real and open the incident record with an
   incident commander assigned.
2. Preserve volatile evidence first: memory and critical logs before
   any disruptive action.
3. Isolate affected hosts at the network layer, keeping them powered
   on for forensics.
4. Disable compromised accounts and begin credential rotation in the
   blast radius.
5. Segment the network: quarantine VLANs, firewall rules, DNS
   sinkholes for attacker infrastructure.
6. Block indicators at the perimeter: IPs, domains, hashes.
7. Communicate: notify stakeholders, log every action with a
   timestamp.
8. Validate: confirm the attacker lost access before declaring
   containment effective.

## 1. The containment decision framework

Not every incident gets the same containment. Decide based on:

- Attacker activity: active intrusion gets immediate isolation;
  dormant malware gets scheduled containment.
- Evidence value: if forensics needs live memory, isolate at the
  network layer rather than powering off.
- Business impact: isolating the payment database at noon needs the
  incident commander's explicit call.
- Scope certainty: contain what you know, monitor what you suspect,
  and do not tip off the attacker before scoping if stealth matters.

```bash
# Incident record header: every containment action references this
cat > incident-2026-1042.md <<'EOF'
# INC-2026-1042
Commander: <name>
Opened: 2026-10-23 09:00 UTC
Severity: high (suspected ransomware staging)
Scope: web-03, db-01 (expanding)
Containment actions: (logged below with timestamps)
EOF
```

Short-term containment (isolate now, ask questions later) buys time;
long-term containment (segmented quarantine with monitoring) holds
the line while eradication is planned. Name which one you are doing.

## 2. Host isolation playbook

Keep the host powered on unless the commander orders otherwise;
memory dies with the power.

```bash
# Linux: allow only your security tooling, drop everything else
SIEM=203.0.113.10
EDR=203.0.113.11
iptables -F OUTPUT
iptables -A OUTPUT -d $SIEM -j ACCEPT
iptables -A OUTPUT -d $EDR -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -j DROP
iptables -A INPUT -j DROP
iptables -L -n --line-numbers | head -20
```

```powershell
# Windows: block all outbound except the security stack (run as admin)
New-NetFirewallRule -DisplayName "IR-allow-SIEM" -Direction Outbound `
  -RemoteAddress 203.0.113.10 -Action Allow
New-NetFirewallRule -DisplayName "IR-allow-EDR" -Direction Outbound `
  -RemoteAddress 203.0.113.11 -Action Allow
New-NetFirewallRule -DisplayName "IR-deny-all-out" -Direction Outbound `
  -Action Block
```

The host-isolation sub-skill covers EDR network containment,
nftables variants, and keeping forensic access working through the
isolation. Validate isolation by attempting a connection from the
host to an external address and confirming it fails, while the EDR
still checks in.

## 3. Network segmentation playbook

Move affected hosts into a quarantine VLAN where they can talk to
forensics tooling and nothing else.

```bash
# Switch-level: shut the access port or move it to the quarantine VLAN
# (example for a managed switch CLI; adapt to your platform)
# configure terminal
# interface GigabitEthernet1/0/12
# switchport access vlan 400
# description QUARANTINE-INC-2026-1042

# Firewall: quarantine VLAN may only reach the forensics network
# iptables on the quarantine gateway
iptables -A FORWARD -s 192.168.400.0/24 -d 203.0.113.0/24 -j ACCEPT
iptables -A FORWARD -s 192.168.400.0/24 -j DROP
```

DNS sinkholing for attacker domains:

```bash
# On the internal resolver: sinkhole attacker domains to a logging IP
# (dnsmasq example)
echo "address=/evil.example.com/203.0.113.99" >> /etc/dnsmasq.d/sinkhole.conf
systemctl reload dnsmasq
# 203.0.113.99 runs a listener that logs which hosts still query the domain
```

The network-segmentation sub-skill details VLAN design, ACLs, and
NAC-driven quarantine.

## 4. Account and credential containment

```bash
# Linux: lock the account but keep it for forensics (do not delete)
passwd -l compromised-user
usermod -s /usr/sbin/nologin compromised-user
# Preserve the authorized_keys for evidence before reviewing
cp /home/compromised-user/.ssh/authorized_keys /evidence/INC-2026-1042/

# Check for recently created accounts (possible attacker additions)
awk -F: '$3 >= 1000 && $3 < 60000 {print $1, $3}' /etc/passwd
```

```powershell
# Windows: disable, do not delete
Disable-LocalUser -Name "compromised-user"
# Domain: disable in AD and revoke sessions
Disable-ADAccount -Identity "compromised-user"
```

Rotate credentials for every account in the blast radius: the
compromised accounts, service accounts on affected hosts, API keys
the accounts could read, and VPN credentials. Assume the attacker
read everything the account could read; "probably fine" is not a
rotation criterion.

## 5. Perimeter indicator blocking

```bash
# Firewall block for attacker IPs (record the rule with the incident id)
iptables -A INPUT -s 198.51.100.23 -j DROP -m comment --comment "INC-2026-1042"
iptables -A OUTPUT -d 198.51.100.23 -j DROP -m comment --comment "INC-2026-1042"

# EDR/AV: push the hash block fleet-wide via Velociraptor or your EDR console
```

Block at every layer you control: border firewall, WAF, DNS, email
gateway, and EDR. One layer is a speed bump; all layers is
containment. Time-box the blocks with a review date so emergency
rules do not become permanent cruft.

## 6. Evidence preservation order

Follow the order of volatility; the evidence-preservation sub-skill
has the full procedures:

1. Memory capture (most volatile, dies at power-off).
2. Network state: connections, ARP, routing tables.
3. Running processes and open files.
4. Disk image or at minimum targeted file copies with hashes.
5. Logs: local copies before rotation, plus central copies.

```bash
# Minimal volatile capture before isolation changes state
mkdir -p /evidence/INC-2026-1042
ss -tulpn > /evidence/INC-2026-1042/ss.txt
ps auxf > /evidence/INC-2026-1042/ps.txt
lsof -i -P -n > /evidence/INC-2026-1042/lsof.txt
date -u > /evidence/INC-2026-1042/captured-at.txt
```

## 7. Ransomware-specific containment

Ransomware spreads fast; containment must be faster and broader:

- Isolate affected hosts immediately, including ones that only
  show early indicators.
- Disable SMB and RDP at the network layer between segments to
  cut lateral movement paths.
- Snapshot virtualization hosts before the encryption reaches
  them; snapshots are your recovery option.
- Assume data theft: containment includes revoking external
  sharing and published access, not just stopping encryption.
- Do not pay or negotiate without the legal and executive chain;
  that decision is above the response team.

```bash
# Blunt but effective: drop SMB and RDP between internal segments at the core
iptables -A FORWARD -p tcp --dport 445 -j DROP -m comment --comment "INC-2026-1042 ransomware"
iptables -A FORWARD -p tcp --dport 3389 -j DROP -m comment --comment "INC-2026-1042 ransomware"
```

## Edge cases

- The attacker is active during containment. Coordinate the
  isolation wave so all affected hosts go dark simultaneously;
  sequential isolation lets the attacker hop ahead of you.
- A host cannot be isolated without stopping a life-safety or
  revenue-critical process. The commander weighs the tradeoff in
  writing; compensate with narrowed firewall rules and continuous
  monitoring instead of full isolation.
- Cloud workloads: security groups replace VLANs, and
  snapshotting replaces disk imaging. Snapshot before
  terminating; terminated instances take their ephemeral disks
  with them.
- The EDR console itself may be compromised or unreachable. Fall
  back to host firewall rules and switch-level actions that do
  not depend on the agent.
- Containment breaks the backup path. Verify backups still run
  from the quarantine network or accept the gap explicitly with a
  recovery plan.
- The scope keeps growing mid-containment. Freeze the current
  wave, re-scope from network telemetry, then run the next wave;
  do not chase individual hosts.

## Escalation

- Containment fails and the attacker re-enters. Assume missed
  persistence or a second entry vector; re-scope from the network
  side rather than repeating host isolation.
- The incident involves ransomware with data theft and an
  extortion deadline. Escalate to executive leadership and legal
  immediately; the response team does not negotiate.
- Evidence preservation conflicts with business recovery
  pressure. The commander decides in writing, with legal aware;
  never let recovery destroy evidence silently.
- Containment actions affect customer-facing systems. Involve
  communications early; customers notice outages before they
  read status pages.

## Detection and defender view

Containment playbooks are the defender's muscle memory: the faster
the isolation wave, the smaller the incident. Build the muscle
before the incident with quarterly tabletop exercises that actually
run the iptables commands and VLAN moves, not just talk about them.
Measure containment time as a metric: detection to isolation in
minutes is the goal, and every exercise should try to beat the last
one. The strategic defenses that make containment easier are
network segmentation done in peacetime, EDR on every host, and
credential hygiene that shrinks the blast radius before anything
burns.

## Key references

- NIST SP 800-61 Rev. 2 (containment, eradication, recovery):
  https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final
- SANS incident handling cheat sheets:
  https://www.sans.org/white-papers/
- MITRE ATT&CK (map each containment to the technique it stops):
  https://attack.mitre.org/
- Companion skills: incident-timeline-analysis, incident-breach-scoping
  (this repo)
- Velociraptor documentation: https://docs.velociraptor.app/
- osquery schema: https://osquery.io/schema/
