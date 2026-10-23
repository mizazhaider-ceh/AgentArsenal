---
name: c2-opsec
description: Use when operating command and control on an authorized
  engagement and needing to stay within the agreed operational security
  bounds. Covers infrastructure separation, traffic shaping, session
  hygiene, and cleanup. Use when the engagement has detection-testing
  objectives, when operating near production systems, when the blue team
  is active, or when the rules define strict operational limits.
version: 1.0.0
domain: c2
lifecycle: stable
last_verified: 2026-10-23
parent: c2-fundamentals
requires: [c2-fundamentals]
extends: []
relates: [network-pivoting, incident-response]
tools:
  - name: Python
    version: 3.12
  - name: OpenSSH
    version: 9.6
---

Operational security for C2 means operating inside the engagement's
bounds: no collateral damage, no surprise outages, clean attribution of
every action to the test. This skill covers the opsec discipline for
authorized C2: separating infrastructure, shaping traffic to the agreed
profile, keeping sessions hygienic, and cleaning up completely. It is
about professionalism, not evasion for its own sake; the blue team learns
from what you do, so do it deliberately.

## Quick Workflow

1. Read the rules of engagement for operational limits before any C2
   activity.
2. Separate infrastructure per engagement and per phase.
3. Shape traffic to the agreed profile (timing, protocols, windows).
4. Keep sessions minimal: least privilege, least time, least noise.
5. Log every action attributable to the test.
6. Clean up infrastructure, payloads, and artifacts at the end.
7. Report what the defenders saw versus what they missed.

## 1. Infrastructure separation

```bash
# One engagement, one infrastructure set; never reuse across clients
# - Listener hosts dedicated to the engagement
# - Domains registered for the engagement, aged if the profile needs it
# - Payloads built per engagement, never shared binaries

# Inventory file: what exists, where, for which engagement
cat > /tmp/c2_inventory.txt <<'EOF'
engagement: 2026-10-acme
listener: 203.0.113.10:443 (HTTPS)
domain: acme-test-2026.example
payload family: ps1-https (built 2026-10-23)
EOF
```

Separation protects the client (your other work never touches their
network) and protects you (attribution stays clean). Decommission the
infrastructure when the engagement ends.

## 2. Traffic shaping

```bash
# Agree the profile with the test lead first:
# - Callback interval and jitter range
# - Active hours (business hours blend better than 3 AM)
# - Protocols allowed (HTTPS only, no raw TCP)

# Example: callbacks every 60-120s with jitter, business hours only
# Implement in the payload config, not by hand each time

# Monitor your own traffic from the defender's view
tcpdump -i eth0 -w /tmp/self_check.pcap host 203.0.113.10 &
# Review: does it look like the agreed profile?
```

If the objective includes detection testing, coordinate beacon patterns
with the blue team so each alert maps to a known action. Uncoordinated
"stealth" against an active blue team wastes everyone's time.

## 3. Session hygiene and cleanup

```bash
# During: keep sessions short, drop them when idle, never leave
# interactive shells open overnight on production hosts

# Cleanup checklist at engagement end:
# - Kill all listeners and payload processes
# - Remove payload files from targets (verify deletion)
# - Remove persistence mechanisms (only if they were approved)
# - Decommission domains and listener hosts
# - Archive logs for the report, then destroy working copies
#   containing credentials

# Verify cleanup from the target side where possible
```

Cleanup is part of the test, not an afterthought. A leftover payload
that fires after the engagement ends is an incident you caused.

## Edge cases

- The blue team detects you early. That is a successful detection test;
  coordinate the next steps with the test lead instead of going quieter
  unilaterally.
- A payload misbehaves on production. Kill it immediately, inform the
  test lead, and help verify the host is healthy.
- The agreed window changes mid-engagement. Update the traffic profile
  the same day; stale profiles cause false alarms.
- Infrastructure gets blocklisted. Rotate per the plan, or accept the
  block as a defensive win and continue within the new constraints.

## Escalation

- Opsec requirements exceed your tooling: raise it before the
  engagement starts; improvising C2 tradecraft mid-test is how mistakes
  happen.
- You suspect collateral impact: stop, assess, inform the test lead;
  continuing through suspected impact is never the right call.
- The engagement ends early: run the full cleanup immediately, do not
  leave infrastructure warm "just in case."

## Detection and defender view

This sub-skill is written from the operator's side of a cooperative test:
the defender's view is the point. Every C2 action should be explainable
afterward: why this protocol, why this timing, what it looked like in
the logs. Defenses are the standard set (egress filtering, NDR
beaconing detection, EDR process analytics), and the test measures them.
Good opsec in an authorized test means the blue team gets clean signal,
not that they get nothing.

## Key references

- MITRE ATT&CK T1071 (Application Layer Protocol).
- MITRE ATT&CK T1090 (Proxy).
- NIST SP 800-115 (Technical Guide to Information Security Testing).
