---
name: telematics-security
description: Use when assessing a telematics unit or connected car
  backend on an authorized engagement. Covers TCU architecture, cellular
  attack surface, backend API review, and remote command flows. Also use
  when a fleet deployment needs its connectivity security reviewed.
version: 1.0.0
domain: automotive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [api-security-testing, automotive-ethernet, can-bus-security]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
  - name: nmap
    version: 7.98
---

The telematics control unit connects the car to the world: cellular,
backend APIs, and remote commands like unlock and start. It is the
most exposed computer in the vehicle. This skill covers authorized
assessment: mapping the TCU's interfaces, reviewing the backend APIs,
and tracing remote command flows. Test backends you are authorized to
test; never probe someone else's fleet.

## Quick Workflow

1. Map the TCU: cellular modem, GNSS, CAN or Ethernet to the vehicle,
   and any WiFi or Bluetooth.
2. Identify the backend endpoints the TCU talks to from traffic or
   firmware.
3. Assess the backend APIs with authorization: authentication,
   authorization, and input handling.
4. Trace a remote command end to end: app to backend to TCU to
   vehicle action.
5. Check command authorization: can one user command another user's
   vehicle.
6. Review the TCU's own exposure: open ports, debug interfaces, and
   update mechanism.
7. Check data handling: location history storage and privacy.
8. Report the remote attack paths with their prerequisites.

## 1. Backend API assessment

```bash
# Enumerate the mobile app's backend endpoints (your test account)
# Capture the app traffic through Burp with the device you own
# Then probe authorization: the classic IDOR on vehicle IDs
curl -s 'https://api.telematics.example/vehicles' \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -30
```

```bash
# Test horizontal access: request another vehicle's status
# Use IDs from your own test fleet only
curl -s 'https://api.telematics.example/vehicles/VEH999/status' \
  -H "Authorization: Bearer $TOKEN" | head -c 300
# 200 with another vehicle's data = broken object level authorization
```

```bash
# Remote command flow: trace unlock end to end on your test vehicle
curl -s -X POST 'https://api.telematics.example/vehicles/VEH001/commands/unlock' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{}' | head -c 300
# Check: is there a second factor, a delay, or owner confirmation
```

## 2. TCU interface review

```bash
# On the bench TCU (your hardware): check listening services
sudo nmap -sS -p- -T3 192.168.8.1 -oN /tmp/tcu_ports.txt 2>/dev/null
grep open /tmp/tcu_ports.txt | head
# Check the update mechanism and APN config in the firmware
strings -n 8 /tmp/tcu_fw.bin | grep -i -E "apn|https://|mqtt" | head -20
```

## Edge cases

- The backend uses certificate pinning. Test with a debug build you
  are authorized to use, or review server side only.
- Commands queue when the car is offline. Test the queue for replay
  and authorization staleness.
- The fleet has mixed TCU hardware generations. Assess each; old
  units often lack the new one's protections.

## Escalation

- IDOR confirmed on vehicles: emergency disclosure to the vendor;
  this is remotely exploitable at scale.
- TCU accepts unauthenticated SMS commands: critical finding;
  verify on the bench and report immediately.
- Need the process context: iso21434-basics covers the lifecycle
  expectations for these systems.

## Detection and defender view

Telematics defenders monitor for unusual command patterns, logins
from new devices, and TCUs talking to unexpected endpoints. They
defend with mutual TLS between TCU and backend, per vehicle
credentials, command authorization tied to ownership, and anomaly
detection on the command stream. The backend is a high value target,
so it gets the full web API security treatment plus automotive
specific command controls.

## Key references

- CWE-639 (Authorization Bypass Through User-Controlled Key): vehicle IDOR.
- CWE-306 (Missing Authentication for Critical Function).
- ISO/SAE 21434: cybersecurity for road vehicles.
- OWASP API Security Top 10.
