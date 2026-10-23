---
name: reviewer-gate
kind: workflow
description: Use when an artifact must pass an independent quality review before it moves forward, such as a pentest report before delivery or a detection rule before deployment. A reviewer agent checks the artifact against a fixed checklist and either approves it or sends it back with specific fixes. Load this pattern when the cost of shipping a bad artifact is high and one more set of eyes is worth the delay.
version: 1.0.0
---

# Reviewer Gate

## When to use it

Use the reviewer gate when a deliverable needs independent verification before it is handed off. The producer finishes the artifact, a reviewer checks it against a written checklist, and the artifact only passes when every checklist item is satisfied. Use it for client reports, detection rules, hardening plans, and any artifact where an error has real consequences. Do not use it for quick internal notes where review costs more than the mistake.

## Diagram

The pattern is a loop with an exit, shown as nested lists:

- Producer
  - Drafts the artifact and submits it for review
  - Reviewer
    - Checks the artifact against the checklist
    - Outcome: approve
      - Artifact moves to the next stage
    - Outcome: reject with fixes
      - Producer
        - Applies the listed fixes and resubmits
        - Reviewer checks again
      - Repeat until approve or the retry limit is hit

## Step sequence

1. The producer completes the artifact and submits it with a short summary of what changed and what evidence supports it.
2. The reviewer loads the fixed checklist for this artifact kind. The checklist is written down before the review starts and does not change during the review.
3. The reviewer checks every item: completeness, accuracy of technical claims, evidence attached, formatting, and scope compliance.
4. The reviewer returns one of two verdicts: approve, or reject with a numbered list of specific fixes. Vague rejections are not allowed. Each fix names the exact section and the exact problem.
5. On reject, the producer applies the fixes and resubmits. The reviewer checks only the fixed items plus a quick regression pass.
6. On approve, the artifact is marked reviewed with the reviewer's name, the date, and the checklist version, then moves to the next stage.

## Failure handling

- The producer and reviewer disagree on a checklist item: the reviewer wins on quality calls, the producer wins on factual corrections backed by evidence. Unresolved disputes go to the coordinator with both positions written down.
- The retry limit is hit (default: three rounds): the artifact is escalated to the coordinator with the outstanding fixes listed. The coordinator decides whether to accept with known gaps, assign a new producer, or stop.
- The reviewer finds a scope violation (for example, an out-of-scope finding in a report): the artifact is rejected immediately, the violation is removed, and the incident is logged. This does not count as a normal review round.
- The reviewer is unavailable: the artifact waits. It never skips the gate. If the wait threatens a deadline, the coordinator assigns an alternate reviewer with the same checklist.

## Artifact kinds orchestrated

- Draft artifacts: reports, rules, plans, and configurations awaiting review.
- Checklists: the fixed review criteria per artifact kind, versioned.
- Review records: verdict, fixes requested, round number, reviewer identity, and date.
- Approved artifacts: the final version with the review stamp, ready for delivery or deployment.
