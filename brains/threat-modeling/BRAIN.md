---
name: threat-modeling
kind: brain
description: Use when an agent must reason about what can go wrong before it does: designing a new system or feature, reviewing an architecture for security gaps, preparing for a security review, or deciding which threats deserve real mitigations. Provides threat modeling reasoning: asset-first thinking, trust boundary mapping, structured threat enumeration (STRIDE-style), attacker-centric prioritization, and treating the model as a living document. Load this brain during design and review phases, when the cheapest time to fix a threat is still available.
version: 1.0.0
provides:
  - Asset-first threat identification
  - Trust boundary mapping
  - Structured threat enumeration (STRIDE-style)
  - Attacker-centric threat prioritization
  - Threat model as living document discipline
  - Mitigation mapping per threat
used_by: []
---

Threat modeling is thinking about what can go wrong on purpose, before an attacker does it for you. Most teams either skip it (and meet the threats in production) or do it once as a checkbox (and file it away). Done right, it is a short, repeatable habit: name what you protect, draw where trust changes, list how each part can be abused, and decide what to do about the worst of it. It matters because a threat found in design costs a whiteboard sketch to fix. The same threat found in production costs an incident.

## Core mental models

**Start from assets, not attacks.** Do not begin with a list of scary attacks. Begin with what is worth stealing, breaking, or abusing: user data, credentials, money flows, admin powers, reputation. Then ask how each asset can be reached. Asset-first thinking keeps the model grounded in your system instead of drifting into generic threat lists that apply to everyone and help no one.

**Draw the trust boundaries.** A trust boundary is any place where the level of trust changes: user to browser, browser to API, API to database, your service to a vendor. Every boundary is where validation, authentication, and logging must happen, because data crossing a boundary can no longer be trusted. Most vulnerabilities live exactly on these lines: the API that trusts the client, the internal service that trusts the network. If you cannot draw the boundaries, you cannot see the threats.

**Enumerate threats structurally, then think like the attacker.** Use a structured checklist per component so you do not rely on inspiration: who can pretend to be someone else here (spoofing), who can alter this data (tampering), who can deny they did it (repudiation), who can read what they should not (information disclosure), who can break this (denial of service), who can gain power here (elevation). Then switch to attacker-mindset and rank: which of these is the cheapest path to the best asset? Structure finds threats; attacker thinking ranks them.

**The model is alive or it is dead.** A threat model written once and filed is decoration. Systems change weekly: new endpoints, new vendors, new data flows. The model must be revisited when the design changes, or it quietly becomes fiction. Keep it small enough to update in an hour. A short living model beats a long dead one.

## Operating checklist

1. List the assets: data, credentials, money, capabilities. Rank by value to an attacker.
2. Draw the system: components, data flows, and every trust boundary.
3. Mark entry points: where can an outsider first touch the system?
4. For each component and flow, enumerate threats structurally (spoofing, tampering, repudiation, disclosure, denial, elevation).
5. For each threat, note the attacker: who would do this and what does it cost them?
6. Rank threats by attacker cheapness times asset value. Cut the long tail honestly.
7. Assign each kept threat a mitigation: prevent, detect, or accept with a written reason.
8. Check mitigations against the boundaries: is validation at the boundary, not behind it?
9. Record assumptions explicitly (what you trust and why). Assumptions are future threats.
10. Set the review trigger: which changes force a model update (new data flow, new vendor, new auth)?

## Heuristics

- If you cannot name the assets, you are not ready to list threats.
- Every trust boundary needs validation on the trusted side. "The client checked it" is not validation.
- The vendor is an attacker path. Model third parties as semi-trusted at best.
- Data at rest, in transit, and in use are three different threat surfaces. Cover all three.
- Accept risk in writing or do not accept it. Silent acceptance is just hope.
- A threat with no named attacker is a ghost story. Name who and why.
- Revisit the model when the architecture diagram would need redrawing.
- Ten modeled threats with owners beat fifty with none.

## Anti-patterns

- **Checkbox modeling.** One workshop, one document, never updated. Fiction within a quarter.
- **Attack-list modeling.** Listing generic attacks (SQLi, XSS) without mapping them to your assets and boundaries.
- **No ranking.** Treating all threats as equal, which means the critical ones get the same attention as the trivial.
- **Trusting the client.** Putting validation or auth decisions in code the attacker controls.
- **Ignoring the insider and the vendor.** Modeling only the outside attacker while the helpdesk and the SaaS integration have the keys.

## Worked example

A team designs a notes API with sharing. Assets: note contents, user credentials, the sharing links. Boundaries: browser to API, API to database, API to email provider for share invites. Structural pass on the share link flow: spoofing (can someone forge a share link?), disclosure (are links guessable?), elevation (can a viewer become an editor?). Attacker ranking: share links are short random tokens but never expire, and the "anyone with the link" notes include private ones. Cheapest path: enumerate or leak one link, read private notes forever. Mitigation: longer tokens, expiry plus revocation, and a detection (alert on share-link access from unusual locations). Assumption recorded: the email provider is trusted to deliver links only to the recipient. Review trigger: any change to sharing semantics. One whiteboard session, one real threat killed before a line of code shipped.
