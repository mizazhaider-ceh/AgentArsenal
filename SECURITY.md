# Security policy

## Scope: authorized security work only

The offensive skills in this repository exist for these uses, and only these:

- Red team engagements with written authorization from the target owner.
- Bug bounty programs, strictly within the published scope of the program.
- Capture the Flag (CTF) competitions.
- Security research on systems you own or are explicitly allowed to test.
- Training labs built for security education.

## Explicit rejections

AgentArsenal is not a toolkit for abuse. The following are out of scope, and any contribution or issue promoting them will be closed:

- Targeting real victim infrastructure or systems without authorization.
- Destructive actions (wipers, ransomware behavior, mass data deletion) presented without clear warnings, safeguards, and an authorized context.
- Bypassing vendor telemetry, logging, or monitoring outside a red-team context where the blue team is aware of the engagement.
- Unverified AI-generated content passed off as tested: commands in skills must be real, runnable, and verified.
- Contributions under non-MIT-compatible licenses.

## Disclosure

Found a security problem in this repo (bad command in a skill, a flawed technique, something that should carry a bigger warning)? Report it via GitHub issues so it is tracked publicly and fixed with a changelog entry. Do not test skills against infrastructure you are not authorized to touch while verifying a report.
