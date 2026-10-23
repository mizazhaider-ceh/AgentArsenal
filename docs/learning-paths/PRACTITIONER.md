# Practitioner learning path

You can already run a scoped webapp assessment and write it up. This track
takes you from single techniques to full engagement phases: APIs, privilege
escalation, Active Directory, malware triage, and SOC workflows. Work in
order; each phase assumes the previous one.

Prerequisite: [BEGINNER.md](BEGINNER.md) graduate, or equivalent hands-on
experience.

## Phase 1: Own the API layer

1. `skills/api/api-security-testing` and its sub-skills : APIs are the real
   attack surface behind every modern app. The sub-skills split it into
   focused modules you can load per engagement.
2. `skills/web/jwt-attacks` : tokens are the keys to the API kingdom; learn
   every way they fail.
3. `skills/web/oauth-attacks` plus `skills/web/oauth2-deep-dive` : the login
   flows your targets actually use, and how they break.
4. `skills/web/graphql-security` : a different query model means different
   injection and authorization bugs.
5. `skills/web/ssrf` : the bug class that turns a web app into a cloud
   metadata reader. Pairs directly with Phase 3.
6. `skills/web/deserialization-attacks`, `skills/web/ssti`,
   `skills/web/xxe`, `skills/web/file-upload-attacks` : the high-impact
   server-side bug classes, one at a time, each with exact payloads and
   edge cases.
7. `agents/web-exploitation-agent` : bind the web skills into one operator
   and practice proving impact safely inside scope.
8. `brains/hypothesis-driven-testing` : stop spraying payloads. Form a
   hypothesis, test it, record the evidence.

**Milestone 1:** Given an API target, you can map it, break authentication and
authorization, prove SSRF or injection impact, and document each finding with
a reproducible chain.

## Phase 2: Get root (privilege escalation)

9. `skills/privesc/privesc-linux` and its sub-skills in order:
   `sub/suid-binaries`, `sub/sudo-misconfig`, `sub/cron-abuse`,
   `sub/kernel-exploits`, `sub/container-breakout-checks`. This is the
   checklist order that works on real boxes.
10. `skills/privesc/privesc-windows` and its sub-skills:
    `sub/unquoted-service-paths`, `sub/alwaysinstallelevated`,
    `sub/dll-hijacking`, `sub/token-impersonation`.
11. `skills/network/network-pivoting` and its sub-skills : one foothold is
    never the end. Learn to move through the network properly.
12. `skills/c2/c2-fundamentals` and its sub-skills : how red team command and
    control works, so your practice stays disciplined and your scope stays
    clean. Authorized work only.
13. `brains/threat-modeling` : before you attack a network, model it:
    assets, trust boundaries, cheapest paths.

**Milestone 2:** From a low-privilege shell on a lab box (Linux and Windows),
you can enumerate, escalate to admin or root, and pivot to the next target,
documenting every step.

## Phase 3: Active Directory and cloud

14. `skills/ad/ad-enumeration` and its sub-skills (`sub/ldap-enumeration`,
    `sub/kerberos-enum`, `sub/gpo-analysis`, `sub/trust-mapping`) : map the
    domain before you attack it. Enumeration is a skill, not a prelude.
15. `skills/ad/bloodhound-methodology` and its sub-skills
    (`sub/bloodhound-collection`, `sub/bloodhound-path-analysis`,
    `sub/bloodhound-custom-queries`) : turn enumeration data into attack paths.
16. `skills/ad/kerberoasting` and its sub-skills
    (`sub/kerberoast-execution`, `sub/asrep-roast-execution`,
    `sub/ticket-analysis`) : the classic domain attack, end to end.
17. `skills/auth/auth-attacks` and its sub-skills (`sub/credential-stuffing`,
    `sub/mfa-bypass-testing`, `sub/password-reset-abuse`,
    `sub/session-hijacking`) : the identity layer that AD protects.
18. `skills/cloud/cloud-security-basics` and its sub-skills, then
    `skills/cloud/aws-enumeration` and its sub-skills : the cloud is a
    different domain controller. Learn its enumeration first.
19. `skills/cloud/iam-privesc`, `skills/cloud/container-escape`,
    `skills/cloud/k8s-pentest` : where cloud assessments actually end.
20. `agents/ad-attack-agent` and `agents/cloud-attack-agent` : run the two
    operators against lab environments.
21. `playbooks/ad-assessment` and `playbooks/external-pentest` : the full
    runbooks. Study the phases, entry and exit criteria, and stop conditions
    before you ever run one for real.

**Milestone 3:** You can plan and execute the core phases of an internal AD
assessment and a cloud review in a lab: enumerate, find the path, escalate,
and report with an evidence chain.

## Phase 4: Malware triage and SOC workflows

22. `skills/malware/static-triage` : classify a suspicious binary fast without
    executing it.
23. `skills/malware/yara-rules` : write rules that catch families, not just
    hashes.
24. `skills/malware/dynamic-sandbox` : detonate safely and extract behavior.
25. `skills/forensics/log-forensics`, `skills/forensics/disk-forensics`
    (sub-skills: timeline building blocks), `skills/forensics/memory-forensics`
    and its sub-skills, `skills/forensics/browser-forensics` : reconstruct
    what happened from every evidence type.
26. `skills/soc/threat-hunting` and its sub-skills : hunt with hypotheses,
    not just alerts.
27. `skills/soc/dfir-timeline`, `skills/soc/siem-detections`,
    `skills/soc/sigma-rules`, `skills/soc/suricata-ids` : the detection and
    timeline stack that turns triage into proof.
28. `agents/malware-triage-agent`, `agents/threat-hunter-agent`,
    `agents/forensics-agent` : the three operators for this phase.
29. `playbooks/malware-outbreak` and `playbooks/soc-triage-day` : run the
    coordinated response, not just the analysis.
30. `brains/root-cause-analysis` and `brains/evidence-chain` : findings that
    survive hostile review.

**Milestone 4 (graduate):** You can own an external pentest phase or a SOC
triage shift end to end: recon to escalation to report, or alert to timeline
to containment recommendation. Next stop: [EXPERT.md](EXPERT.md).

## Quick install for this track

```bash
./install.sh --category api
./install.sh --category privesc
./install.sh --category ad
./install.sh --category cloud
./install.sh --category malware
./install.sh --category soc
./install.sh --category forensics
```
