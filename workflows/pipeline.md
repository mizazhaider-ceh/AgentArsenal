---
name: pipeline
kind: workflow
description: Use when work must flow through a fixed sequence of stages where each stage's output feeds the next, such as recon feeding exploitation feeding reporting, or triage feeding forensics feeding containment. Each stage has one owner and a clear handoff contract. Load this pattern when order matters, stages depend on prior results, and skipping a stage would break the chain.
version: 1.0.0
---

# Pipeline

## When to use it

Use the pipeline when the work has a natural order and each stage needs the previous stage's output to start. Stage one produces an artifact, stage two consumes it, and so on until the final stage delivers. Use it for assessment playbooks, incident response chains, and any multi-phase process where dependencies are strict. Do not use it when stages are independent. For that, use the coordinator fanout pattern.

## Diagram

The pattern is a straight chain, shown as nested lists:

- Stage 1: owner agent A
  - Produces artifact 1 under the handoff contract
  - Stage 2: owner agent B
    - Consumes artifact 1, produces artifact 2
    - Stage 3: owner agent C
      - Consumes artifact 2, produces artifact 3
      - Stage 4: owner agent D
        - Consumes artifact 3, delivers the final artifact

## Step sequence

1. Define the stages in order, with one owner agent per stage and the handoff contract between them: what artifact, what format, what quality bar.
2. Stage 1 runs to completion and writes its artifact. The artifact is checked against the handoff contract before it moves on.
3. Stage 2 starts only after stage 1's artifact passes the handoff check. It consumes the artifact and produces the next one.
4. Repeat down the chain. Each stage validates its input before starting work. A stage that receives a bad input sends it back to the previous stage instead of working around it.
5. The final stage delivers the end artifact and archives the intermediate artifacts with the chain record.

## Failure handling

- A stage's input fails the handoff check: the stage rejects it back to the previous stage with the specific defect. The previous stage fixes and resubmits. The pipeline does not advance on a broken handoff.
- A stage fails midway: it writes a partial artifact marked incomplete, and the coordinator decides whether to retry the stage, rerun from an earlier stage, or stop the pipeline.
- A stage discovers that an earlier stage's output was wrong (for example, exploitation finds the recon missed a host): the finding is sent back up the chain. The earlier stage corrects its artifact, and affected downstream stages rerun. The correction is logged in the chain record.
- The pipeline stalls because a stage is waiting on an external approval: the stage marks itself blocked with the reason and the waiting deadline. If the deadline passes, the coordinator escalates per the escalation policy.
- The final artifact is rejected by the requester: the rejection is mapped back to the stage that introduced the defect, that stage fixes it, and the downstream stages rerun only as far as needed.

## Artifact kinds orchestrated

- Stage artifacts: the output of each stage, such as the recon inventory, the findings list, or the containment record.
- Handoff contracts: the format and quality requirements between stages, checked at every handoff.
- Chain records: the ordered log of which stage ran, what it consumed and produced, and any rejections or reruns.
- Final artifacts: the delivered result, such as the assessment report or the closed incident record.
