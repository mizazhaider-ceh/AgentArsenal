---
name: v2x-security
description: Use when assessing vehicle to everything communication on
  an authorized engagement or lab setup. Covers DSRC and C-V2X basics,
  message types (BSM, CAM, DENM), PKI and certificate review, and
  misbehavior detection concepts. Also use when ADAS features consume
  V2X input that needs trust review.
version: 1.0.0
domain: automotive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [automotive-threat-model, automotive-ethernet]
tools:
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.4
---

V2X lets vehicles broadcast safety messages to each other and to
infrastructure: "I am here, I am braking." The security model is
PKI: messages are signed, and receivers check certificates. This
skill covers authorized assessment: understanding the message types,
reviewing the PKI design, and testing misbehavior handling. Lab and
paper assessment; never transmit on licensed bands without
authorization.

## Quick Workflow

1. Identify the technology: DSRC (802.11p) or C-V2X (PC5 sidelink),
   and the region's message profiles.
2. Learn the key messages: BSM/CAM (position broadcasts) and
   DENM (event warnings).
3. Map the PKI: enrollment, authorization certificates, and
   revocation (CRLs).
4. Review certificate provisioning: how a vehicle gets its
   certificates and how often they rotate.
5. Assess misbehavior detection: what happens when a node sends
   plausible but false data.
6. Check privacy: pseudonym rotation and linkability of broadcasts.
7. Review what the ADAS does with V2X input: is it advisory or
   does it act.
8. Report the trust assumptions with their failure modes.

## 1. Message and PKI review

```bash
# Capture V2X on the bench with an SDR (receive only, your lab)
# Decode BSM/CAM fields: position, speed, heading, brake status
python3 - << 'PY'
fields = ["latitude", "longitude", "speed", "heading", "brake_status",
          "vehicle_length", "event_flags"]
print("for each field ask: is it signed? is it plausible-checked?")
print("which fields does the ADAS actually consume?")
PY
```

```bash
# PKI review checklist (documents and configs, your test deployment)
# - enrollment CA trust: who can enroll a vehicle
# - authorization ticket lifetime and rotation policy
# - pseudonym certificate pool size and refill process
# - CRL distribution: how fast does revocation propagate
# - what happens when certificates expire mid drive (fail open/closed)
echo "record the answers; gaps here are the findings"
```

## 2. Misbehavior test concepts (lab)

```bash
# On your bench with test certificates only:
# 1. send a BSM with impossible physics (teleporting position)
# 2. send conflicting DENMs (fake hazard)
# 3. replay a valid signed message later (stale data)
# Observe: does the receiver flag, ignore, or act on each
echo "never transmit these on public roads or licensed spectrum"
```

## Edge cases

- The deployment is a pilot with test PKI. Findings about the test
  PKI do not transfer to production; review the production plan.
- V2X is receive only in this vehicle (no transmission). The attack
  surface is the parser and the ADAS consumer logic.
- Regional differences (US SCMS vs EU C-ITS) change the PKI details.
  Assess against the deployment's actual region.

## Escalation

- Parser bug suspected in message handling: fuzz the parser on the
  bench with malformed messages.
- ADAS acts on unauthenticated V2X: critical finding; verify the
  exact conditions on the bench.

## Detection and defender view

V2X misbehavior detection is the immune system: nodes report
implausible messages, and authorities revoke misbehaving
certificates. Defenders monitor for Sybil patterns (many
certificates, one attacker) and physics violations. The durable
design signs everything, rotates pseudonyms for privacy, and treats
V2X as advisory input that never overrides local sensors for
critical decisions.

## Key references

- IEEE 1609.2: V2X security services and certificates.
- ETSI ITS security standards (EU C-ITS).
- CWE-347 (Improper Verification of Cryptographic Signature).
