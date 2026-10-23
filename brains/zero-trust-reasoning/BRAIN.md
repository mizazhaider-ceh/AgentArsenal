---
name: zero-trust-reasoning
kind: brain
description: Use when an agent must design or evaluate access in a world without a trusted network: architecting service-to-service auth, reviewing VPN-based access, planning remote work security, or challenging "internal means safe" assumptions. Provides zero-trust reasoning: never trust, always verify; identity is the new perimeter; every request is authenticated, authorized, and encrypted regardless of origin; trust is continuously re-evaluated, not granted once. Load this brain when the network location must stop being a security decision.
version: 1.0.0
provides:
  - Never-trust-always-verify request evaluation
  - Identity-as-perimeter architecture
  - Per-request authentication and authorization
  - Continuous verification over one-time checks
  - Network-location distrust modeling
  - Micro-segmentation reasoning
used_by: []
---

Zero trust is a response to a simple observation: the network perimeter is dead. People work from home, services live in three clouds, vendors connect directly, and attackers phish their way inside anyway. If "inside the network" ever meant "safe," it does not anymore. Zero trust replaces location-based trust with a stricter rule: no user, device, or service is trusted by default, every request is verified, and access is granted per request, not per network. It matters because every flat trusted-internal design is one stolen credential away from total compromise.

## Core mental models

**Never trust, always verify.** Every access request, from anywhere, to anything, must prove who it is from, that it is allowed, and that the channel is safe. There is no "already inside so skip the check." The internal HR tool gets the same authentication rigor as the public login page. This sounds expensive, and the tooling (identity-aware proxies, mutual TLS, short-lived tokens) makes it routine.

**Identity is the new perimeter.** In a zero-trust world, the boundary that matters is not the firewall, it is the identity: who (or what) is making this request, on which device, in what state? A request from a managed laptop with a fresh token is different from the same request from an unknown device with an old one. Build the perimeter around verified identity plus device posture, not around IP ranges.

**Verify continuously, not once.** A login at 9 AM does not prove the 3 PM request is legitimate. Sessions get hijacked, tokens get stolen, contexts change. Zero trust re-evaluates: short token lifetimes, step-up auth for sensitive actions, anomaly checks on behavior. Trust has a half-life. Design as if every grant expires, because it should.

**The network is hostile, including yours.** Treat every network, yours included, as if an attacker watches it. That means encryption everywhere (service to service, not just at the edge), no cleartext internal protocols, and no security decision based on source IP alone. If your design breaks when the network is hostile, it was never zero trust.

## Operating checklist

1. Inventory every access path: who reaches what, from where, with what credential today.
2. Find every decision based on network location ("internal, so no auth needed"). List them all.
3. Put identity on every path: authenticate the user or workload on each request, regardless of origin.
4. Authorize per request: check the specific action against policy at request time, not just at login.
5. Encrypt everything in transit, including internal service-to-service traffic (mutual TLS or equivalent).
6. Add device posture to the decision: managed, patched, and healthy devices get more than unknown ones.
7. Shorten trust lifetimes: short-lived tokens, re-auth for sensitive actions, session anomaly checks.
8. Micro-segment: services reach only the services they need, verified per connection.
9. Log every access decision centrally. Verification you cannot audit is theater.
10. Migrate incrementally: pick the highest-value asset, wrap it in zero-trust access, then expand. Big bang fails.

## Heuristics

- If removing the VPN breaks your security model, you had a VPN, not a security model.
- Every "trusted internal" service is a future incident report. Verify it like an external one.
- Source IP is a hint, not an identity. Never authorize on it alone.
- The most valuable zero-trust win is usually the admin path: jump hosts, consoles, and CI systems.
- Start with identity, then devices, then network. In that order.
- Encrypt internal traffic before you perfect anything else. It is the cheapest big win.
- A policy engine nobody can read is a policy nobody trusts. Keep policies reviewable.
- Migrate asset by asset. "Zero trust everything by Friday" is how you get neither.

## Anti-patterns

- **VPN as trust.** Treating VPN-connected devices as internal and therefore safe. The phished laptop is now "trusted."
- **Flat internal network.** Once past the edge, everything reachable, nothing authenticated. Zero trust's opposite.
- **One-time verification.** A login token that lives for 30 days with no re-checks. Trust without expiry.
- **IP allowlisting as auth.** "Only our office IP can reach it" instead of proving who is asking.
- **Big-bang migration.** Trying to convert everything at once, stalling for a year, shipping nothing.

## Worked example

A company runs internal tools behind a VPN: dashboards, admin consoles, and the deploy system. Anyone on the VPN reaches everything, no further auth on most tools. Zero-trust migration, incremental: first the deploy system, highest value. It moves behind an identity-aware proxy: every request needs a short-lived token tied to the engineer's identity and a managed-device check, regardless of VPN status. Then mutual TLS between the deploy system and its build agents, replacing IP allowlists. Then the admin consoles, one by one. A year later the VPN is just an encrypted pipe, not a trust decision: a stolen laptop on the VPN reaches nothing without the identity, the device posture, and the per-request checks. When an attacker later phishes an engineer, the session token is short-lived and device-bound, and the anomalous access attempt is logged and denied. Location stopped mattering. Identity does the work.
