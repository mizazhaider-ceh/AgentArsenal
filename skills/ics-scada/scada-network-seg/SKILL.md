---
name: scada-network-seg
description: Use when designing or assessing network segmentation for
  OT and SCADA environments on an authorized engagement. Covers the
  Purdue model, conduit and zone design per IEC 62443, firewall rule
  review between IT and OT, and validating that segmentation actually
  holds. Also use when an assessment finds flat OT networks.
version: 1.0.0
domain: ics-scada
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [modbus-security, firewall-evasion, network-pivoting]
tools:
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
---

Segmentation is the main defense in OT: since PLCs and protocols lack
authentication, the network boundary does the access control. This skill
covers authorized assessment and design of OT segmentation: mapping
zones and conduits, reviewing firewall rules between IT and OT, and
testing whether the segmentation holds. Never test segmentation by
attacking across it without written authorization naming both sides.

## Quick Workflow

1. Map the as built network: interview, config review, and passive
   observation before any active test.
2. Draw the Purdue levels 0 through 5 with the actual devices placed.
3. Define zones (groups of assets with common security needs) and
   conduits (the controlled paths between them).
4. Review firewall rules on every IT to OT and zone to zone boundary.
5. Validate with authorized tests: confirm blocked paths are blocked
   and allowed paths are minimal.
6. Check the data diode or historian path: the one legitimate bridge.
7. Look for bypasses: dual homed hosts, forgotten VPNs, cellular
   modems, vendor remote access.
8. Report gaps with the exact path an attacker could walk.

## 1. Purdue mapping and zone design

```bash
# Build the asset map from configs and interviews (no scanning yet)
python3 - << 'PY'
levels = {
    0: "physical process: sensors, actuators",
    1: "control: PLCs, RTUs, SIS controllers",
    2: "supervisory: HMIs, historians, engineering workstations",
    3: "operations: OT DMZ, patch servers, jump hosts",
    "3.5": "industrial DMZ: the broker zone between IT and OT",
    4: "business: ERP, email, file servers",
    5: "enterprise: internet facing services",
}
for lvl, desc in levels.items():
    print(f"Level {lvl}: {desc}")
print("\nconduits to define: L4<->3.5, 3.5<->3, 3<->2, 2<->1")
PY
```

```bash
# Firewall rule review template: for each conduit, list allowed flows
# Required columns: source zone, dest zone, ports, direction, business need
# Red flags: ANY to ANY rules, OT initiated outbound to internet,
# management protocols (RDP, SSH) allowed from IT into OT broadly
echo "review: iptables / firewalld / vendor FW exports per conduit"
```

## 2. Segmentation validation (authorized)

```bash
# From a host in the IT segment (authorized), confirm OT is unreachable
# Use a slow, targeted check, not a broad scan
sudo nmap -sS -p 502,4840,102,44818 -T2 --max-retries 1 \
  192.168.10.20 -oN /tmp/seg_test_ot.txt
# Expected: filtered (no answer). Open means the conduit leaks.
```

```bash
# Verify the legitimate historian path still works (allowlisted flow)
python3 - << 'PY'
print("allowed: historian replica in DMZ pulls from OT historian, TCP 1433")
print("test: from DMZ host, connect to OT historian IP port 1433 -> should work")
print("test: from IT host, same target -> should fail")
PY
```

```bash
# Hunt bypasses: dual homed hosts and rogue paths
# - check ARP tables on boundary hosts for unexpected neighbors
# - review VPN configs and vendor remote access accounts
# - walk the plant and look for cellular modems and unmanaged switches
ip neigh show | head -20
```

## Edge cases

- The firewall rules are correct but a dual homed engineering laptop
  bridges the zones. The laptop is the finding, not the firewall.
- A vendor needs remote access for support. Route it through the jump
  host with MFA and session recording, never a direct VPN to OT.
- The historian needs bidirectional sync. Prefer a data diode or a
  replica with a one way push over opening return paths.
- Wireless in the plant (guest WiFi near OT). Verify it cannot reach
  OT segments and that OT devices do not join it.

## Escalation

- Segmentation fails open during firewall failure. Check fail open vs
  fail closed behavior and recommend fail closed for OT boundaries.
- Flat network with no budget for full redesign: propose quick wins
  first (ACLs on switches, host firewalls on HMIs, remove gateways).
- Need protocol level enforcement: add an OT aware firewall or data
  diode on the worst conduit.

## Detection and defender view

Defenders monitor conduits with allowlist IDS: any flow not in the
baseline is an alert. They watch for new devices on OT segments, VPN
logins outside maintenance windows, and firewall rule changes. The
durable design follows IEC 62443: zones with target security levels,
conduits with verified controls, and continuous monitoring of every
boundary. Segmentation is not a one time project; it needs change
control or it rots.

## Key references

- IEC 62443-3-2: zones, conduits, and risk assessment.
- NIST SP 800-82r3: OT network architecture guidance.
- MITRE ATT&CK ICS T0806 and T0884 (Connection Proxy): lateral paths.
