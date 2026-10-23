---
name: incident-containment-playbooks-network-segmentation
description: Use when an incident requires cutting off attacker
  movement between network segments on infrastructure you are
  authorized to defend. Covers designing quarantine VLANs, moving
  hosts with switch commands, writing segment firewall rules with
  iptables 1.8, DNS sinkholing of attacker domains, NAC-driven
  quarantine, and validating that lateral paths are dead. Use when
  the parent incident-containment-playbooks workflow calls for
  network-level containment, when lateral movement is suspected
  across segments, or when building pre-approved segmentation
  runbooks for the incident plan. Validate every cut with Wireshark
  captures on the quarantine gateway.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-containment-playbooks
requires: [incident-containment-playbooks]
extends: []
relates: [incident-containment-playbooks]
tools:
  - name: iptables
    version: 1.8
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.2
---

Network segmentation as a containment action means redrawing the
network's trust boundaries mid-incident: affected hosts go into a
quarantine segment, attacker paths between segments get cut, and
malicious domains get sinkholed. Done in peacetime it is
architecture; done mid-incident it is surgery. This sub-skill covers
the quarantine VLAN pattern, the firewall rules that enforce it, and
the validation that proves lateral movement is actually dead.
Authorized infrastructure only.

## Quick Workflow

1. Map the current segments and the paths the attacker could be
   using (from scoping and network telemetry).
2. Define the quarantine segment: VLAN id, subnet, and exactly what
   it may reach.
3. Move affected hosts into quarantine at the switch or via NAC.
4. Cut inter-segment attacker paths: SMB, RDP, WinRM, SSH between
   segments at the firewalls.
5. Sinkhole attacker domains on the internal resolver.
6. Validate: no flows between quarantine and production except the
   allowed forensics paths.
7. Monitor the quarantine for reconnection attempts and new
   infections.
8. Log every change with the incident id for rollback.

## 1. Quarantine VLAN design

```bash
# Quarantine segment plan (example addressing)
# VLAN 400: 192.168.400.0/24, gateway 192.168.400.1
# Allowed destinations:
#   - Forensics network 203.0.113.0/24 (evidence, SIEM, EDR)
#   - Nothing else, including no internet and no production VLANs
cat > quarantine-plan.md <<'EOF'
## Quarantine VLAN 400 (INC-2026-1042)
Subnet: 192.168.400.0/24
Members: web-03 (moved 10:15), db-01 (moved 10:18)
Allowed: 203.0.113.0/24 (forensics)
Denied: everything else
DHCP: disabled in quarantine (static assignments only)
Review: after eradication, before re-admission
EOF
```

Disable DHCP in quarantine: a host that renews and gets a production
address has escaped. Static assignments, documented per host.

## 2. Moving hosts into quarantine

```bash
# Managed switch CLI pattern (adapt to your platform)
# configure terminal
# vlan 400
#  name QUARANTINE-INC-2026-1042
# interface GigabitEthernet1/0/12
#  description web-03 QUARANTINED INC-2026-1042
#  switchport mode access
#  switchport access vlan 400
#  spanning-tree portfast
# end
# show vlan id 400
```

For wireless or NAC-managed ports, push the quarantine
authorization instead of touching the switch:

```bash
# NAC quarantine pattern (platform-specific; concept shown)
# Set the endpoint's authorization profile to QUARANTINE, which assigns
# VLAN 400 and a restrictive ACL at the next re-authentication.
# Force re-auth: bounce the port or send a CoA (change of authorization).
```

Virtual machines move at the hypervisor: change the port group to
the quarantine port group, which is instant and cannot be reverted
by guest malware. Prefer hypervisor moves for VMs over in-guest
firewall rules.

## 3. Inter-segment firewall rules

On the firewall or router between segments, cut the lateral movement
protocols. Be surgical: killing all inter-segment traffic may break
the business worse than the attacker does.

```bash
# Example: core firewall between server segments
# Drop the classic lateral movement ports from quarantine to anywhere
iptables -A FORWARD -s 192.168.400.0/24 -p tcp --dport 445 -j DROP \
  -m comment --comment "INC-2026-1042 no SMB out of quarantine"
iptables -A FORWARD -s 192.168.400.0/24 -p tcp --dport 3389 -j DROP \
  -m comment --comment "INC-2026-1042 no RDP out of quarantine"
iptables -A FORWARD -s 192.168.400.0/24 -p tcp --dport 5985:5986 -j DROP \
  -m comment --comment "INC-2026-1042 no WinRM out of quarantine"
iptables -A FORWARD -s 192.168.400.0/24 -p tcp --dport 22 -j DROP \
  -m comment --comment "INC-2026-1042 no SSH out of quarantine"

# Allow only the forensics network
iptables -A FORWARD -s 192.168.400.0/24 -d 203.0.113.0/24 -j ACCEPT \
  -m comment --comment "INC-2026-1042 forensics access"
iptables -A FORWARD -s 192.168.400.0/24 -j DROP \
  -m comment --comment "INC-2026-1042 quarantine default deny"
```

Order matters: the forensics allow must precede the default deny.
Save the ruleset before and after (`iptables-save`) for rollback.

## 4. DNS sinkholing

```bash
# dnsmasq sinkhole for attacker domains (internal resolver)
cat >> /etc/dnsmasq.d/sinkhole-INC-2026-1042.conf <<'EOF'
address=/evil.example.com/203.0.113.99
address=/cdn-evil.example.net/203.0.113.99
EOF
systemctl reload dnsmasq

# 203.0.113.99: run a logging listener to see which hosts still query
python3 - <<'EOF'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('203.0.113.99', 80))
s.listen(10)
print("sinkhole listener up; logging connection attempts")
while True:
    conn, addr = s.accept()
    print(f"SINKHOLE HIT from {addr[0]}")
    conn.close()
EOF
```

Example output shape:

```
sinkhole listener up; logging connection attempts
SINKHOLE HIT from 192.168.400.15
SINKHOLE HIT from 192.168.30.44
```

A hit from outside quarantine (192.168.30.44) means the scope is
bigger than thought: that host needs investigation and probably
quarantine too. The sinkhole is both containment and a detection
tripwire.

## 5. Validating the segmentation

```bash
# From a quarantined host: production must be unreachable
ping -c1 192.168.30.10 ; echo "exit: $?"   # expect failure
curl -m 5 http://192.168.30.10 ; echo "exit: $?"  # expect failure

# Forensics network must be reachable
ping -c1 203.0.113.10 ; echo "exit: $?"    # expect success

# From the firewall: confirm the drops are hitting
iptables -L FORWARD -n -v | grep "INC-2026-1042"
# Packet counters on the DROP rules should increment if anything tries

# Packet capture on the quarantine gateway for 5 minutes: look for
# anything that is not forensics-bound
tcpdump -i eth400 -w quarantine-check.pcap &
sleep 300; kill %1
tshark -r quarantine-check.pcap -T fields -e ip.dst | sort | uniq -c | sort -rn | head
```

Example output shape:

```
    412 203.0.113.10
     37 203.0.113.11
      2 192.168.30.10
```

Two packets toward production deserve investigation: what sent them,
and did the firewall drop them (check the counter). Clean captures
are evidence that the segmentation holds.

## Edge cases

- The attacker is already in the forensics-allowed network. Then
  the quarantine's exception becomes the attack path; re-examine
  the allow-list and consider a dedicated, freshly built forensics
  network.
- Flat network with no VLAN capability (small office, legacy
  gear). Fall back to host firewall isolation on every affected
  host plus switch port shutdowns; it is coarser but workable.
- The quarantine VLAN has no path to the backup system. Accept the
  gap explicitly or add a one-way backup allow with logging; do
  not quietly break backups.
- NAC is misconfigured and the quarantine profile does not apply.
  Verify the port's actual VLAN after every move (`show
  interfaces status`); trust the switch output, not the NAC GUI.
- Encrypted lateral movement (SSH, RDP) cannot be inspected, only
  blocked. Blocking is the containment; inspection belongs to
  host forensics.
- Cloud VPCs: security groups and NACLs replace VLANs. Snapshot
  before changing, since a wrong NACL can isolate your own access
  to the console path.

## Escalation

- Segmentation reveals the attacker in a segment you cannot
  quarantine (OT network, PCI zone, cloud production). Escalate to
  the commander and the business owner; some segments need a
  planned outage, not a surprise VLAN move.
- The sinkhole lights up with dozens of internal hosts. The scope
  just exploded; freeze further moves, re-scope from the sinkhole
  data, and brief leadership before the next wave.
- A business-critical flow crosses the cut you made. The commander
  weighs attacker risk against outage cost in writing; the usual
  compromise is a narrow, logged exception for that flow, not
  reopening the segment.
- You need to keep the segmentation for weeks (long eradication).
  Formalize it: change tickets, monitoring dashboards, and a
  re-admission plan, so emergency config becomes managed config.

## Detection and defender view

Mid-incident segmentation works best where peacetime segmentation
already exists: moving a host between existing VLANs is a port
change, while creating segmentation during an incident is a project.
The strategic lesson is to segment before you need it: servers by
role, workstations from servers, OT from IT, with deny-by-default
between them. Exercise the quarantine move quarterly; the team that
has done it three times does it in minutes at 3 AM.

## Key references

- Parent playbook: incident-containment-playbooks (this repo)
- NIST SP 800-61 Rev. 2: https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final
- NIST SP 800-207 (Zero Trust Architecture, segmentation context):
  https://csrc.nist.gov/publications/detail/sp/800-207/final
- MITRE ATT&CK T1021 (Remote Services), T1048 (Exfiltration):
  https://attack.mitre.org/
- Wireshark documentation: https://www.wireshark.org/docs/
