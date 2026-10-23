---
name: safety-systems
description: Use when you need to understand safety instrumented systems
  for OT security work. Covers what SIS does, why it is separate from
  process control, the security boundaries around it, and how to assess
  without ever endangering people. Also use when scoping an engagement
  to keep safety systems out of bounds correctly.
version: 1.0.0
domain: ics-scada
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [plc-basics, ics-incident-response, scada-network-seg]
tools:
  - name: Python
    version: 3.12
---

Safety instrumented systems exist to protect people: they shut the
process down when it goes dangerous, independent of the control
system. Attacking or carelessly testing a SIS can kill. This skill is
about understanding SIS well enough to assess around it safely:
architecture, separation principles, what the security boundaries
must be, and how to scope engagements so safety is never at risk.

## Quick Workflow

1. Learn what the SIS protects: the hazards, the safe state, and the
   safety integrity level (SIL) ratings.
2. Understand the separation: SIS is independent from the basic
   process control system in sensors, logic, and often network.
3. Map the allowed interactions: what may talk to the SIS (usually
   almost nothing) and through which gateway.
4. Scope every engagement to exclude SIS testing unless a dedicated
   safety assessment with safety engineers is planned.
5. Review the boundary controls: firewalls, data diodes, and
   unidirectional gateways facing the SIS.
6. Check change control: who can modify safety logic and how it is
   approved.
7. Verify monitoring: the SIS network should be watched, not trusted
   blindly.
8. Report boundary weaknesses as safety relevant findings with the
   right severity.

## 1. Architecture and separation

```text
Basic Process Control System (BPCS)     Safety Instrumented System (SIS)
  PLCs run the process                    separate controllers watch for danger
  operator can adjust                     operator cannot override trips
  network: OT control segment             network: isolated safety segment
  failure: production loss                failure: potential harm to people
```

```bash
# Scoping checklist for every OT engagement (fill with the asset owner)
python3 - << 'PY'
scope = [
    "SIS controllers identified and marked OUT OF SCOPE",
    "safety network segment identified; no scanning without safety engineer",
    "allowed SIS interactions listed (e.g. read only status via gateway)",
    "emergency contacts for safety engineer on file",
    "change freeze confirmed for safety logic during test window",
]
for s in scope:
    print("[ ]", s)
PY
```

## 2. Boundary control review (no active testing)

```bash
# Review only: firewall rules facing the safety segment
# Expected: default deny, with at most a read only gateway flow
echo "review: rules into the SIS segment, gateway config, diode direction"
# Verify the gateway cannot write: check its protocol mapping
# (e.g. OPC UA read only role, or a hardware data diode)
```

```bash
# Change control audit: who modified safety logic last, and was it approved
# Review the MOC (management of change) records, not the controllers
echo "audit: MOC tickets for SIS logic changes in the last 12 months"
```

## Edge cases

- The SIS and BPCS share a network "temporarily". Temporary becomes
  permanent; flag it as a critical boundary violation.
- Someone wants a penetration test of the SIS. Decline active testing;
  offer a design and boundary review with safety engineers instead.
- A finding suggests the SIS could be reached from IT. Treat this as
  the highest severity, verify passively, and notify immediately
  through the agreed emergency channel.
- Legacy SIS with no network at all (air gapped by design). The
  finding is any new connection: USB, laptop, or "temporary" cable.

## Escalation

- Suspected compromise of safety logic: stop all testing, notify the
  safety engineer and site management immediately, do not attempt
  remediation yourself.
- Boundary review blocked by access: document the limitation; do not
  work around it with creative network paths.

## Detection and defender view

SIS networks should be the most monitored and least touched networks
on site: any traffic that is not the expected status polling is
suspicious. Defenders use unidirectional gateways, strict allowlists,
and physical access control on safety controllers. The industry
remembers TRISIS, malware that targeted safety controllers directly,
as proof that SIS needs security monitoring, not just isolation.

## Key references

- IEC 61511: functional safety for the process industry.
- IEC 62443: security for industrial automation, including safety.
- MITRE ATT&CK ICS T0800 (Activate Firmware Update Mode): SIS
  targeting examples.
- TRISIS/TRITON incident reports: why SIS security matters.
