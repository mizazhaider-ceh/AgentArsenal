---
name: can-bus-security
description: Use when assessing CAN bus security on a vehicle or bench
  setup you own or have authorization to test. Covers CAN sniffing with
  SocketCAN, message reverse engineering, injection testing, and
  gateway segmentation review. Also use when a vehicle assessment needs
  the in vehicle network mapped before deeper testing.
version: 1.0.0
domain: automotive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [automotive-ethernet, ecu-firmware, network-pivoting]
tools:
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.4
---

The CAN bus is a broadcast network with no authentication: every ECU
sees every message and trusts the sender ID. This skill covers
authorized testing on your own vehicle or bench rig: sniffing traffic,
reverse engineering message meanings, testing injection safely, and
reviewing gateway segmentation. Never test on a moving vehicle or
anyone else's car; bench setups and your own parked vehicle only, with
safety precautions.

## Quick Workflow

1. Set up the bench: your vehicle parked and off, or a bench rig with
   ECUs you own, plus a CAN interface.
2. Bring up the interface and confirm you see traffic.
3. Capture a baseline: idle, then during controlled actions (door
   open, lights on).
4. Reverse engineer message IDs: correlate actions with frames.
5. Map the gateways: which buses exist and what passes between them.
6. Test injection on the bench only: replay frames and observe.
7. Check diagnostics: UDS access and seed key authentication.
8. Report the exposure with the safety limits you respected.

## 1. Sniffing with SocketCAN

```bash
# Bring up a CAN interface (canable, PCAN, or similar adapter)
sudo ip link set can0 up type can bitrate 500000
# Common automotive bitrates: 500000 (powertrain), 125000 (body), 250000

# Watch live traffic
candump can0 | head -30
# Log to file for analysis
candump -l can0
```

```bash
# Baseline diff: capture idle, then capture while toggling something
candump -l can0 & sleep 10; kill %1; mv candump-*.log /tmp/can_idle.log
# now open a door, then:
candump -l can0 & sleep 10; kill %1; mv candump-*.log /tmp/can_door.log
# Compare: new or changed IDs belong to the door action
python3 - << 'PY'
def ids(path):
    out = set()
    for line in open(path):
        parts = line.split()
        if len(parts) >= 3:
            out.add(parts[2])
    return out
idle, door = ids("/tmp/can_idle.log"), ids("/tmp/can_door.log")
print("IDs only seen during door action:", sorted(door - idle)[:20])
PY
```

## 2. Injection testing (bench only)

```bash
# Replay a captured frame on the bench rig (NEVER on a driven vehicle)
cansend can0 2F1#1122334455667788
# Observe the bench ECU response; record which frames cause actions
```

```bash
# Fuzz a single ID's data bytes carefully on the bench
# (stop immediately on unexpected behavior)
for b in 00 FF; do
  cansend can0 2F1#${b}00000000000000
  sleep 1
done
```

## 3. UDS diagnostics check

```bash
# UDS runs over CAN (ISO-TP); check diagnostic session access
# Tester present and session control are the entry points
# Seed-key: request seed (0x27 0x01), compute key, send key (0x27 0x02)
python3 - << 'PY'
print("checklist: does security access use a real algorithm or a constant?")
print("known weak: seed always 0x0000, key equals seed, no brute force delay")
print("never brute force a live vehicle ECU; review on the bench")
PY
```

## Edge cases

- The vehicle has CAN FD or multiple bitrates. Set the interface to
  match; wrong bitrate shows as error frames.
- Gateways filter between buses. What you inject on the OBD port may
  not reach the powertrain bus; map the gateway rules.
- The car sleeps and the bus goes quiet. Wake it with a door handle
  or ignition to accessory, parked and secured.
- EVs have additional high voltage safety concerns. Do not probe
  high voltage wiring; stay on the 12V CAN side.

## Escalation

- Injection works on safety critical IDs on the bench: this is a
  critical finding; verify gateway segmentation as the mitigation.
- UDS seed key is weak: demonstrate on the bench, then recommend
  proper authentication and brute force delays.
- Need the full vehicle picture: move to automotive-threat-model for
  the systematic analysis.

## Detection and defender view

Vehicle defenders use gateways with message filtering, IDS on the CAN
bus (detecting injected frames by timing and counter anomalies), and
secure diagnostics with real seed key algorithms. They detect attacks
through frames that break timing patterns and diagnostic sessions
from unexpected sources. The durable direction is authenticated CAN
(SecOC) for critical messages and strong gateway isolation.

## Key references

- ISO 11898: CAN protocol standard.
- ISO 14229 (UDS): diagnostic services.
- CWE-306 (Missing Authentication for Critical Function).
- CWE-924 (Improper Enforcement of Message Integrity): unauthenticated bus.
