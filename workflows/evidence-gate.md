---
name: evidence-gate
kind: workflow
description: Use when a claim, finding, or decision cannot move forward without attached evidence that meets a fixed standard, such as a vulnerability finding needing proof of concept pairs or an incident escalation needing a timeline. The gate checks that the evidence exists, is complete, and supports the claim. Load this pattern when unverified claims would cause bad decisions, wasted effort, or client disputes.
version: 1.0.0
---

# Evidence Gate

## When to use it

Use the evidence gate when nothing should proceed on a claim alone. Every finding, escalation, or decision carries its evidence, and a gatekeeper checks the evidence against a fixed standard before the claim moves forward. Use it for vulnerability findings, incident escalations, scope changes, and go or no-go decisions. Do not use it for brainstorming or early hypotheses, where demanding evidence too early kills useful thinking.

## Diagram

The pattern is a checkpoint on every claim, shown as nested lists:

- Claim submitted with evidence attached
  - Gatekeeper checks the evidence standard
    - Standard met
      - Claim passes to the next stage
    - Standard not met
      - Claim returned with the missing evidence listed
        - Producer gathers the missing evidence and resubmits
        - Gatekeeper checks again

## Step sequence

1. Define the evidence standard for each claim kind before work starts. For a vulnerability finding: affected asset, reproduction steps, request and response proof, impact statement. For an incident escalation: timeline, indicators, affected assets, actions taken.
2. The producer attaches the evidence to the claim and submits it through the gate.
3. The gatekeeper checks each required item: present, complete, and actually supporting the claim. A screenshot with no context fails. A log excerpt that does not show the claimed behavior fails.
4. If the standard is met, the claim passes and the evidence is archived with it. If not, the claim returns with the exact missing items listed.
5. The producer gathers the missing evidence and resubmits. The gatekeeper rechecks.
6. Passed claims carry an evidence stamp: what was checked, by whom, and when.

## Failure handling

- The evidence contradicts the claim: the claim is rejected and the producer must revise the claim to match the evidence or gather new evidence. The contradiction is logged.
- The evidence cannot be gathered safely (for example, proving impact would risk production): the claim is marked as limited evidence with the reason, and it proceeds only with explicit approval from the coordinator. Limited evidence claims are flagged in the final artifact.
- The producer disputes the gatekeeper's standard: the standard itself is reviewed, not the individual claim. If the standard was wrong, it is fixed and the claim is rechecked. Standards change between claims, never during one.
- A claim arrives with no evidence at all: it is rejected immediately without review. Repeated empty submissions are reported to the coordinator as a producer problem.
- The gate becomes a bottleneck: if the queue grows, the coordinator adds a second gatekeeper with the same standard. The standard is never loosened to clear the queue.

## Artifact kinds orchestrated

- Claims: findings, escalations, scope changes, and decisions awaiting verification.
- Evidence standards: the required evidence per claim kind, versioned.
- Evidence packages: the attached proof for each claim, archived with the claim.
- Gate records: pass or fail, missing items, gatekeeper identity, and date.
- Stamped claims: verified claims carrying the evidence stamp into the next stage.
