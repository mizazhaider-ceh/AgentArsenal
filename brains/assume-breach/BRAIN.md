---
name: assume-breach
kind: brain
description: Use when an agent must design or operate as if the adversary is already inside: planning network segmentation, writing hunting hypotheses, reviewing internal trust assumptions, or responding to signs of lateral movement. Provides assume-breach reasoning: the perimeter will fail, so design for containment and visibility inside; hunt for the intruder you assume is present; shrink dwell time; segment so one compromise cannot become everything. Load this brain when the task involves internal security posture rather than keeping attackers out.
version: 1.0.0
provides:
  - Breach-assumed architecture reasoning
  - Internal segmentation and containment design
  - Threat hunting hypothesis generation
  - Dwell time reduction strategies
  - Lateral movement path analysis
  - Insider-equivalent trust modeling
used_by: []
---

"Assume breach" is not pessimism, it is a design input. It means: stop spending all your energy on the wall and start designing the inside of the castle as if someone is already walking its halls. Most organizations discover breaches months late because everything inside was trusted: flat networks, no internal logging, admin credentials everywhere. This brain teaches an agent to flip the default: the inside is hostile territory too, so build visibility, segmentation, and hunting into it from the start.

## Core mental models

**The perimeter already failed, design accordingly.** Treat every external boundary as eventually bypassed. This does not mean ignoring the perimeter; it means no security decision may depend on the perimeter holding. If your plan for a compromised VPN credential is "that should not happen," you have no plan. Every critical asset needs protection that works even when the attacker starts inside.

**Segment like the enemy is already inside.** Network segmentation, identity boundaries, and data compartments exist to turn one breach into a small incident instead of a company-wide one. The question for every segment is: if the attacker owns this part, what can they reach next, and how fast? Flat networks answer "everything, immediately." Good segmentation answers "this room, and we will see them try the door."

**Hunt, do not hope.** If you assume breach, you must look for the breach. Threat hunting is forming hypotheses ("if an intruder were here, they would...") and checking them against internal telemetry. Hope is not a control. A hunting program with modest telemetry beats a perfect perimeter with none, because the hunter finds the intruder the wall missed.

**Dwell time is the metric that matters.** The damage of a breach grows with how long the attacker operates unseen. Every assume-breach investment should be judged by whether it shrinks dwell time: better internal logging, deception, anomaly detection, faster triage. An intruder found in hours is an incident. An intruder found in months is a disaster.

## Operating checklist

1. List what an insider (or a compromised insider account) can reach today, with no extra exploits.
2. Map lateral movement paths: which systems trust which, where do credentials roam?
3. Segment the highest-value assets first: separate identity, data, and admin planes.
4. Ensure internal visibility: log authentication, lateral connections, and data access inside the network, not just at the edge.
5. Write three hunting hypotheses based on your crown jewels and test them this month.
6. Plant deception where it is cheap: honeypot credentials, fake admin shares, canary tokens.
7. Define the dwell-time goal and measure it: when did they get in vs when did we know?
8. Remove standing internal trust: service accounts with domain admin, shared local admin passwords, "internal" apps with no auth.
9. Drill the inside-out scenario: red team starts with a standard user account, no external tricks.
10. Review quarterly: new systems get segmented and logged before they go live, not after.

## Heuristics

- If a standard user account can reach the crown jewels, you are already breached in every way that matters.
- Log the inside like you log the edge. Lateral movement is quiet only where nobody listens.
- Shared local admin passwords are a skeleton key. Kill them first.
- Deception is the cheapest detection you can buy. One canary token can catch a whole intrusion.
- Hunt on a schedule, not on a hunch. Monthly hypotheses beat annual panic.
- The helpdesk account is an insider account. Treat it like one.
- Assume the attacker reads your runbooks. Design so that does not help them much.
- Every flat network is a breach waiting for its press release.

## Anti-patterns

- **Perimeter-only security.** A hard shell with a soft center: one phished credential equals total compromise.
- **Trusting the internal network.** "It is behind the firewall" used as a reason to skip auth, logging, or patching.
- **No internal telemetry.** All logging faces outward, so lateral movement is invisible by design.
- **Hunting without hypotheses.** Random log diving that finds nothing and concludes everything is fine.
- **Segmentation theater.** VLANs with allow-all rules between them. Lines on a diagram, not boundaries.

## Worked example

A company assumes breach and runs the exercise: start with a standard employee laptop login, goal is the finance database. Lateral map shows the laptop can reach every workstation via SMB (flat network), one workstation has a cached domain admin session, and the finance DB trusts the whole internal subnet. Path cost: trivial. Fixes in assume-breach order: segment the finance DB to only the finance app servers (containment), deploy unique local admin passwords everywhere (kills the skeleton key), enable authentication logging on all internal SMB and review it weekly (visibility), and drop a canary credential file on a few workstations (deception). A month later the canary fires: a real intruder, caught in hours instead of months, contained to one segment. The perimeter never even came up.
