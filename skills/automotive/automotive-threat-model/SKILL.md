---
name: automotive-threat-model
description: Use when building a threat model for a vehicle or
  automotive component on an authorized engagement. Covers asset and
  attacker profiling, attack surface mapping across interfaces, attack
  trees for key scenarios, and prioritizing testing from the model.
  Also use when scoping a vehicle assessment so nothing is missed.
version: 1.0.0
domain: automotive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [can-bus-security, telematics-security, iso21434-basics, v2x-security]
tools:
  - name: Python
    version: 3.12
---

A vehicle threat model turns a big scary car into a prioritized test
plan: who attacks, through which interfaces, to cause what harm. This
skill gives the method for authorized assessments: profile attackers,
map every interface, build attack trees for the top scenarios, and
let the model drive where testing time goes.

## Quick Workflow

1. Define the target: vehicle, model year, trim, and the systems in
   scope.
2. Profile attackers: thief, tuner, researcher, organized crime, and
   their capabilities.
3. Map every interface: physical (OBD, USB), wireless (BT, WiFi,
   cellular, key fob, TPMS), and backend (app, telematics API).
4. List assets per interface: what the attacker gains at each entry.
5. Build attack trees for the top 3 scenarios (theft, remote
   control, data theft).
6. Rate each path by feasibility and impact.
7. Prioritize testing: start where feasibility times impact is
   highest.
8. Keep the model alive: update it as testing confirms or kills
   paths.

## 1. Interface and asset map

```bash
# Build the interface inventory (fill per vehicle)
python3 - << 'PY'
interfaces = {
    "OBD-II port": {"access": "physical", "assets": "CAN buses via gateway"},
    "USB ports": {"access": "physical", "assets": "infotainment parsing"},
    "Bluetooth": {"access": "adjacent", "assets": "phone integration, mic"},
    "WiFi hotspot": {"access": "adjacent", "assets": "browser, apps"},
    "cellular (TCU)": {"access": "remote", "assets": "remote commands, location"},
    "key fob (RF)": {"access": "adjacent", "assets": "unlock, start"},
    "TPMS (RF)": {"access": "adjacent", "assets": "ECU input parsing"},
    "companion app": {"access": "remote", "assets": "backend APIs"},
    "V2X radio": {"access": "adjacent", "assets": "ADAS inputs"},
}
for name, d in interfaces.items():
    print(f"{name} [{d['access']}]: {d['assets']}")
PY
```

## 2. Attack trees

```text
Scenario: steal the vehicle
  OR: relay the key fob signal (needs: proximity to fob)
  OR: exploit telematics API to unlock + start (needs: account takeover)
  OR: break the immobilizer via OBD (needs: physical access + tool)
  OR: steal the physical key (not a cyber path; note and move on)

Scenario: remote control while driving
  OR: compromise TCU -> bridge to CAN (needs: TCU RCE)
  OR: compromise infotainment -> gateway bypass (needs: chain of 2+ bugs)
  Rate each leaf: what testing would prove or disprove it
```

```bash
# Prioritize: score = impact (1-5) x feasibility (1-5, higher = easier)
python3 - << 'PY'
paths = [
    ("relay key fob", 4, 4),
    ("telematics IDOR unlock", 4, 3),
    ("TCU RCE to CAN", 5, 2),
    ("TPMS parsing to ECU", 3, 2),
]
for name, impact, feas in sorted(paths, key=lambda x: x[1]*x[2], reverse=True):
    print(f"{impact*feas:2d}  {name}")
PY
```

## Edge cases

- The vehicle is electric: add charging interfaces (CCS, PLC
  communication) and high voltage safety to the model.
- Aftermarket devices are installed: each one is a new interface;
  assess them as part of the vehicle.
- The model shows no high scoring paths. That is a result worth
  reporting, with the coverage listed.

## Escalation

- Testing disproves the top paths: reprioritize to the next tier
  rather than stopping.
- A path needs capability you do not have (RF lab): note it as
  untested with the reason, or bring in specialists.

## Detection and defender view

OEM defenders use threat models like this to place their defenses:
gateways where the model shows bridging paths, monitoring where it
shows remote paths, and hardening where it shows physical paths. The
model also drives the SOC's detection priorities. A threat model that
is not updated after testing is shelfware; the live version is the
valuable one.

## Key references

- ISO/SAE 21434 Clause 8 (TARA): the formal version of this method.
- MITRE ATT&CK for ICS: adaptable techniques for vehicle networks.
- Related skills: iso21434-basics, can-bus-security.
