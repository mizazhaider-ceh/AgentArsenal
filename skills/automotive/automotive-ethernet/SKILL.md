---
name: automotive-ethernet
description: Use when assessing automotive Ethernet on a vehicle or
  bench setup you own or have authorization to test. Covers
  BroadR-Reach and 100BASE-T1 basics, SOME/IP service discovery,
  DoIP diagnostics, and VLAN segmentation in zonal architectures. Also
  use when modern vehicles need network mapping beyond CAN.
version: 1.0.0
domain: automotive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [can-bus-security, telematics-security, vlan-hopping]
tools:
  - name: Wireshark
    version: 4.4
  - name: Python
    version: 3.12
  - name: nmap
    version: 7.98
---

Modern vehicles run Ethernet alongside CAN: cameras, lidar, and
infotainment ride on 100BASE-T1, with SOME/IP for service
communication and DoIP for diagnostics. This skill covers authorized
assessment on your own bench or vehicle: tapping the network,
discovering services, and reviewing segmentation. Parked vehicle or
bench only, same safety rules as CAN work.

## Quick Workflow

1. Get physical access to the automotive Ethernet: media converter
   for 100BASE-T1 to standard Ethernet, on your own setup.
2. Capture traffic and identify SOME/IP service discovery messages.
3. Enumerate services: which ECUs offer what, to whom.
4. Check DoIP: diagnostic over IP entities and their access control.
5. Review VLAN segmentation between domains (infotainment vs ADAS vs
   body).
6. Test service access: can an unexpected node subscribe or call.
7. Look for plaintext credentials or firmware in the traffic.
8. Report with the network map and trust boundaries.

## 1. Tapping and discovery

```bash
# With a 100BASE-T1 media converter, capture like normal Ethernet
sudo tshark -i eth1 -w /tmp/auto_eth.pcap &
sleep 60; kill %1

# SOME/IP service discovery uses multicast 224.0.0.0/4-ish and UDP 30490
tshark -r /tmp/auto_eth.pcap -Y "someip" -T fields \
  -e someip.serviceid -e someip.methodid | sort | uniq -c | head -20
```

```bash
# DoIP discovery: UDP broadcast on port 13400
tshark -r /tmp/auto_eth.pcap -Y "doip" | head -10
# Note every DoIP entity: VIN, logical address, and further actions
```

## 2. Service enumeration

```python
#!/usr/bin/env python3
"""SOME/IP service map from a capture (conceptual parsing)."""
import collections
# In practice parse with Wireshark's SOME/IP dissector or scapy
services = collections.defaultdict(set)
print("build map: service ID -> offering ECU IPs")
print("then ask: which services accept subscriptions from any node?")
print("check: event subscriptions without authentication")
```

```bash
# DoIP entity scan on the bench network (authorized, gentle)
sudo nmap -sU -p 13400 --open -T2 192.168.5.0/24 -oN /tmp/doip.txt 2>/dev/null
sudo nmap -sS -p 13400 --open -T2 192.168.5.0/24 -oN /tmp/doip_tcp.txt
grep -B2 open /tmp/doip_tcp.txt | head
```

## 3. Segmentation review

```bash
# Check VLAN tags in the capture: which domains share a wire
tshark -r /tmp/auto_eth.pcap -T fields -e vlan.id | sort | uniq -c
# Expected: separate VLANs for infotainment, ADAS, diagnostics
# Finding: flat network or routable paths between untrusted and critical
```

## Edge cases

- The media converter does not link. Check master/slave strapping;
  automotive PHYs need one side as master.
- Traffic is encrypted (MACsec or TLS). Assess the key management
  instead of the plaintext you cannot see.
- Time sensitive networking (TSN) schedules matter. Do not inject
  traffic that could disturb scheduled streams on a live bench.

## Escalation

- SOME/IP services accept unauthenticated calls: demonstrate on the
  bench with a harmless method call.
- DoIP allows flashing without authentication: critical finding;
  verify on the bench and report immediately through the agreed
  channel.
- Need the system view: use automotive-threat-model next.

## Detection and defender view

Vehicle network defenders use Ethernet firewalls between domains,
IDS tuned to SOME/IP anomalies, and authenticated diagnostics.
They detect attacks through unexpected service subscriptions and
DoIP sessions from unknown nodes. The industry direction is zone
architectures with central gateways enforcing policy, plus MACsec on
sensitive links.

## Key references

- IEEE 100BASE-T1 (802.3bw): automotive Ethernet PHY.
- AUTOSAR SOME/IP protocol specification.
- ISO 13400 (DoIP): diagnostics over IP.
- CWE-306 (Missing Authentication for Critical Function).
