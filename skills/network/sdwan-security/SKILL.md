---
name: sdwan-security
description: Use when assessing SD-WAN deployments on an authorized
  engagement. Covers overlay security, controller and orchestrator
  review, branch device hardening, and segmentation across the WAN.
  Also use when MPLS is being replaced and the security model needs
  verification.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [zero-trust-networking, firewall-evasion, bgp-security]
tools:
  - name: Python
    version: 3.12
  - name: nmap
    version: 7.98
---

SD-WAN replaces private WAN links with encrypted overlays over the
internet, managed from a central controller. The security shifts to
the overlay crypto, the controller, and the branch boxes. This skill
covers authorized assessment: reviewing the control plane, the data
plane crypto, and branch hardening. Coordinate with the network team;
misconfigurations here affect every site.

## Quick Workflow

1. Map the deployment: controller, orchestrator, edge devices, and
   transport links per site.
2. Review the overlay crypto: algorithms, key management, and
   rekeying.
3. Assess the controller: authentication, API security, and who can
   push policy.
4. Check branch edge hardening: management interfaces, default
   credentials, and exposed services.
5. Review segmentation: do branch VLANs stay separated across the
   overlay.
6. Test failover security: what happens when the controller is
   unreachable.
7. Check logging: are overlay events and policy changes audited.
8. Report with the blast radius of a controller compromise.

## 1. Control and data plane review

```bash
# Controller API security (authorized, your test account)
curl -s 'https://controller.example/api/devices' \
  -H "Authorization: Bearer $TOKEN" | head -c 300
# Then test authorization: can a branch admin see or change other branches
```

```bash
# Edge device exposure: management should never face the internet
sudo nmap -sV -T3 --max-retries 1 $BRANCH_WAN_IP -oN /tmp/sdwan_edge.txt
grep -i -E "open|https|ssh" /tmp/sdwan_edge.txt | head -20
# Open management on WAN = critical finding
```

```bash
# Overlay crypto checklist (config review):
# - IKE/IPsec or DTLS version and cipher suites (no DES/3DES/MD5)
# - certificate based auth vs pre shared keys (PSK rotation?)
# - rekey intervals configured
grep -i -E "ike|ipsec|cipher|psk|certificate" /tmp/sdwan_config.txt | head -20
```

## 2. Segmentation across the overlay

```bash
# From a test host in branch A's guest VLAN (authorized), try to reach
# branch B's corporate VLAN: the overlay must enforce the same policy
# as the LAN. Any cross VLAN reach = segmentation failure in the overlay.
echo "test matrix: (branch, vlan) pairs, expected vs observed"
```

## Edge cases

- The deployment uses zero touch provisioning. Review the ZTP
  authentication; a weak ZTP lets attackers enroll rogue edges.
- Controllers are cloud hosted by the vendor. Assess the shared
  responsibility: what the vendor secures vs what you must.
- Legacy MPLS still connected. The migration period has two WANs;
  assess both and the routing between them.

## Escalation

- Controller compromise suspected: this is an emergency; the
  controller can reconfigure every site.
- Edge RCE found: verify on one lab device, then disclose through
  the vendor channel with the network team.

## Detection and defender view

Defenders monitor SD-WAN for unauthorized edge enrollments, policy
pushes outside change windows, and overlay tunnels to unexpected
peers. They defend with strong controller authentication, signed
policies, branch hardening baselines, and monitoring of the
management plane. The controller is the crown jewel; its compromise
is a total WAN compromise.

## Key references

- Vendor SD-WAN security hardening guides.
- CWE-306 (Missing Authentication for Critical Function).
- NIST SP 800-207: zero trust context for WAN.
