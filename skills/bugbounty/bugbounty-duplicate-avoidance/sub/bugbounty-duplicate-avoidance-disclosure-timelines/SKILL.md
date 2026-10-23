---
name: bugbounty-duplicate-avoidance-disclosure-timelines
parent: bugbounty-duplicate-avoidance
description: Use when disclosed reports exist for your in-scope program and you need to judge whether they cover your exact finding. Covers reading disclosure timelines (report date, fix date, disclosure date), distinguishing same-vulnerability duplicates from sibling-endpoint originals, handling vague or redacted disclosures, recognizing regressions of previously fixed bugs as fresh reports, and deciding when to submit with a reference note versus walking away. Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-duplicate-avoidance]
extends: []
relates: [bugbounty-duplicate-avoidance-search-techniques, bugbounty-duplicate-avoidance-program-specific-dupes, bugbounty-report-writing]
tools:
  - name: Python
    version: 3.12
---

A disclosure timeline tells you whether your finding is already known, already fixed, or still original. Report date, fix date, and disclosure date each answer a different question, and vague titles force judgment calls. This sub-skill covers reading timelines for the duplicate check step of bugbounty-duplicate-avoidance. Judge timelines only for findings on in-scope targets.

## Quick Workflow

1. For each candidate disclosure, record three dates: reported, fixed (or version), disclosed.
2. Compare the disclosed vulnerability against your fingerprint: same endpoint and parameter, or just same class.
3. Check whether the code changed since the fix: a rewrite or major version bump weakens the duplicate claim.
4. Test your finding against the current target: if it still reproduces after a claimed fix, it is a regression, which is a fresh report.
5. For vague disclosures, weigh the risk: submit with a reference note, or walk away.
6. Record the verdict and the disclosure it was checked against in your notes.

## 1. What each date tells you

- Reported date: when the hunter submitted. Anything you found independently after this date could still lose to it; first reporter wins regardless of your effort.
- Fix date or fixed version: when the program says it was fixed. Test your finding against the current deployment; a fix that did not hold is a regression, not a duplicate.
- Disclosure date: when it became public. Disclosures lag fixes by weeks or months, so the absence of a disclosure proves nothing about whether it was reported.

Timeline reading example:

```
Disclosed: "Stored XSS in support portal" | reported 2026-06-02 | fixed in v2.14 (2026-07-19) | disclosed 2026-09-30
Your finding: stored XSS in /api/v1/tickets subject, current version v2.21, reproduces today.
Verdict: test carefully. If your payload fires on v2.21, the fix missed this
parameter: likely a regression or an uncovered sibling, worth submitting with
a reference to the disclosure. If it does not fire, walk away.
```

## 2. Same vulnerability versus sibling

The duplicate question is precise: does the disclosed report cover your exact vulnerability.

- Same endpoint, same parameter, same effect: duplicate. Do not submit.
- Same bug class, different endpoint: usually a separate finding. Programs pay per vulnerable location unless the policy says otherwise.
- Same endpoint, different parameter or bug class: separate finding.
- Same class, same component, vague title: the judgment call. Compare versions: if the disclosure predates a rewrite of that component and your finding reproduces now, lean toward original.

When the policy is silent on siblings, the program's past triage behavior decides: disclosed reports showing per-endpoint payouts mean siblings pay; disclosed reports marked duplicate on siblings mean they do not. Read that history before you decide.

## 3. Regressions are fresh reports

A previously fixed bug that reproduces again is not a duplicate; it is evidence the fix failed or regressed:

1. Confirm the current version is at or past the claimed fixed version.
2. Reproduce cleanly and capture evidence.
3. Reference the original disclosure in your report: "This appears to be a regression of the issue disclosed on <date>, fixed in <version>; it reproduces on <current version> via <parameter>."
4. Note whether it is the exact same parameter (fix failed) or a neighboring one (fix was incomplete). Both are reportable; label which.

Regressions triage fast because the program already understands the bug class. They also earn goodwill: you are doing their QA for them.

## 4. The vague disclosure judgment call

Vague titles ("XSS in support portal," "IDOR in API") with heavy redaction are common. Decision framework:

- Your endpoint is specific and the disclosure names no endpoint: submit with a note referencing the disclosure ("Possibly related to the <date> disclosure; my finding is at <endpoint> via <parameter>"). Let triage decide with full information.
- Your endpoint matches the vague area exactly and the disclosure is recent: walk away. The expected value is low.
- The disclosure is old and the component was rewritten since: lean toward submitting; note the timeline reasoning in your report so the triager sees you did the work.

Never hide a possibly-related disclosure from the triager. Surfacing it yourself reads as diligence; having them discover it reads as carelessness.

## Edge cases

- Two disclosures cover adjacent parameters and yours is a third: check the fix's scope. A fix that patched two parameters often missed the third; that is an incomplete fix, reportable.
- The disclosure timeline shows a long gap between report and fix: the code likely changed in between, so verify your finding against the current deployment rather than trusting the old report's details.
- The program discloses without technical detail as policy: treat every vague disclosure as possibly covering your area and rely more on version and regression testing.

## Escalation

- Timeline analysis keeps landing on "maybe": timebox to 30 minutes, then decide by the framework in section 4. Perfect certainty is not available; documented reasoning is.
- You discover the program silently fixed your exact finding after you validated but before you submitted: that is the cost of slow submission. Submit faster next time; validated findings go out promptly.

## Detection and defender view

- Disclose with useful timelines: report date, fixed version, and disclosure date let hunters self-triage accurately and cut your duplicate queue.
- Specific component names in disclosures are a gift to everyone: hunters check precisely, triage decides faster.
- Track regression reports as a metric: frequent regressions in one component mean the fix process there is broken, not the hunters.
- When you fix a disclosed bug, sweep the sibling parameters before disclosing; each missed sibling becomes a future report.

## Key references

- HackerOne Hacktivity: https://hackerone.com/hacktivity
- HackerOne disclosure guidelines: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- CWE database: https://cwe.mitre.org/
