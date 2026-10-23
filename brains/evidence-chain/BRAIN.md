---
name: evidence-chain
kind: brain
description: Use when an agent must prove something happened and show its work: building a forensic timeline, writing an incident report, justifying a finding to a skeptical reviewer, or chaining observations into a conclusion that holds up under challenge. Provides evidence-chain reasoning: every claim traces to a source, artifacts beat assertions, timelines are the skeleton of proof, gaps are findings too, and the chain must survive hostile review. Load this brain whenever conclusions must be defensible, not just plausible.
version: 1.0.0
provides:
  - Claim-to-source traceability
  - Artifact-first proof over assertions
  - Timeline construction as proof skeleton
  - Evidence gap identification
  - Chain of custody thinking
  - Hostile-review hardening of conclusions
used_by: []
---

A conclusion without evidence is an opinion, and opinions lose arguments. In security work, conclusions get challenged: by incident commanders, by clients, by lawyers, by your own future self. The evidence-chain brain teaches an agent to build every conclusion as a chain: claim, linked to artifact, linked to source, ordered in time. It matters because agents generate confident-sounding text easily. This brain makes the confidence earned, traceable, and checkable by someone who was not there.

## Core mental models

**Every claim needs a source.** "The attacker exfiltrated data" is not a finding until you can point at the artifact: the proxy log line, the packet capture, the file timestamp. Get in the habit of attaching the source to the claim at the moment you make it, not later. Later never comes, and an unsourced claim quietly becomes an assumption that later reasoning builds on. Chains are only as strong as their weakest unsourced link.

**Artifacts beat assertions.** Prefer primary artifacts over summaries and memory: the raw log over the dashboard screenshot, the actual file over someone's description of it, the packet capture over the IDS alert. Each layer of summary is a layer where detail died and errors were born. When you must rely on a secondary source, label it as such and note what the primary would confirm.

**The timeline is the skeleton.** A pile of artifacts proves nothing until ordered in time. The timeline turns "these things exist" into "this happened, then this, then this," which is the actual story. Build it early, keep it updated, and let it expose contradictions: an event that cannot fit the timeline is either wrong or the most interesting thing you have. Causality needs order; order needs timestamps you trust.

**Gaps are findings.** "We have no logs for that server between 02:00 and 04:00" is not an absence of evidence, it is evidence of a gap, and gaps have causes: logging was disabled, the attacker cleared them, retention expired. Record every gap explicitly, with its time bounds and possible explanations. A chain with labeled gaps is honest and useful. A chain that pretends the gaps are not there is fiction.

## Operating checklist

1. State the conclusion you want to support, in one sentence.
2. List the claims the conclusion depends on. Break compound claims apart.
3. For each claim, attach the artifact: file, log line, hash, screenshot, command output.
4. For each artifact, record the source and how it was obtained (tool, command, time).
5. Build the timeline: order all artifacts, note timezone and clock reliability.
6. Check consistency: does every artifact fit the timeline? Flag contradictions.
7. List the gaps: what should exist but does not, with time bounds.
8. Stress-test the chain: what is the weakest link? What would a skeptic attack first?
9. Write the conclusion with the chain attached, weakest link labeled.
10. Preserve the artifacts: hashes, copies, read-only handling. Do not alter sources.

## Heuristics

- Capture the artifact before you interpret it. Interpretation can wait; volatile evidence cannot.
- Hash what you collect. A hash today ends arguments tomorrow.
- One strong artifact beats five weak ones. Quality over quantity.
- If the timestamps disagree, distrust the clocks before you distrust the story.
- Absence of logs after a compromise is a signal, not a dead end.
- Write the chain so a stranger could re-derive your conclusion. If they cannot, it is not a chain.
- Corroborate the critical claims with a second independent source.
- Never edit the evidence to make the story cleaner. The mess is the truth.

## Anti-patterns

- **Assertion stacking.** Conclusions built on conclusions, with the original artifact three layers down and forgotten.
- **Cherry-picking.** Keeping the artifacts that fit the story and quietly dropping the ones that do not.
- **Timeline-free findings.** A list of scary facts with no order, which proves activity but not a story.
- **Ignoring gaps.** Presenting a clean narrative while the two missing hours go unmentioned.
- **Editing the source.** Opening the evidence file in a write-mode tool, altering timestamps by accessing them carelessly, or analyzing on the original instead of a copy.

## Worked example

Claim: "Customer records were exfiltrated on Tuesday." Chain: proxy logs show 2.1 GB outbound to an unknown host at 03:12 (artifact: proxy.log lines, hash recorded). Firewall logs confirm the connection from the database server (second source, corroboration). Database query logs show a SELECT * on the customers table at 03:09 by the reporting service account (artifact: db slow log). Timeline: 03:09 query, 03:12 transfer, both in server-local time, NTP healthy. Gap: no EDR telemetry on the database server (agent was uninstalled in January, noted as gap and contributing factor). Weakest link: the receiving host is unknown, so exfiltration is inferred from volume plus destination, stated honestly. Conclusion written with the chain: each sentence carries its artifact. A reviewer can re-derive everything. That is an evidence chain, not a story.
