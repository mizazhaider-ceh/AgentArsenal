---
name: cloud-logging-checks
description: Use when verifying that cloud audit logging is enabled,
  complete, and tamper-resistant on an authorized engagement. Covers
  control plane logging, log centralization, retention, and alerting
  basics. Use when assessing detectability of cloud attacks, when the IAM
  review is done, when answering "would we see it," or when the scope
  includes incident readiness.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
parent: cloud-security-basics
requires: [cloud-security-basics]
extends: []
relates: [threat-hunting, incident-response]
tools:
  - name: AWS CLI
    version: 2.15
  - name: Python
    version: 3.12
---

Logging is what makes cloud attacks visible: without control-plane logs,
an attacker with stolen keys is invisible. This skill covers checking
the logging posture on authorized engagements: is it on, is it complete,
is it centralized and tamper-resistant, and would anyone notice an
attack. It is a configuration review with incident-readiness stakes.

## Quick Workflow

1. Verify control-plane logging is enabled in every account and region.
2. Check log centralization: all logs flow to the security account.
3. Verify integrity protection and retention meet the policy.
4. Check data-plane logging for critical services (storage access,
   database).
5. Review the alerting: what fires, where it goes, who responds.
6. Test the answer to "would we see it" with a safe canary action.
7. Write findings with the gap and the detection it costs.

## 1. Control-plane logging

```bash
# AWS CloudTrail: must be on in every region, multi-region trail
aws cloudtrail describe-trails \
  --query 'trailList[].[Name,IsMultiRegionTrail,IsOrganizationTrail]' \
  --output text

# Check the trail is actually logging (not just existing)
aws cloudtrail get-trail-status --name <trail-name> \
  --query '[IsLogging, LatestDeliveryTime]' --output text

# Log file validation (integrity): must be enabled
aws cloudtrail describe-trails \
  --query 'trailList[].[Name,LogFileValidationEnabled]' --output text

# Every region check: trails are per-region unless multi-region
aws ec2 describe-regions --query 'Regions[].RegionName' --output text
```

A trail that exists but is not logging is worse than no trail: it
creates false confidence. Verify `IsLogging` true and recent delivery
times, not just the trail's existence.

## 2. Centralization and protection

```bash
# Logs must flow to a dedicated security account's bucket, with:
# - MFA delete on the bucket
# - Versioning enabled
# - No public access
# - Retention matching policy (typically 1+ year for security logs)

aws s3api get-bucket-versioning --bucket <log-bucket> --output text
aws s3api get-bucket-lifecycle-configuration --bucket <log-bucket> 2>/dev/null | head -10

# Who can modify the logging configuration itself?
# (If the attacker can turn off the trail, the logs are decorative)
```

The threat model for logging is the attacker with stolen admin keys:
can they disable the trail, delete the logs, or modify retention? If
yes, the logging is not tamper-resistant and the finding is critical
for detectability.

## 3. The "would we see it" test

```bash
# Safe canary actions (coordinate with the SOC first):
# 1. Create and delete a test IAM user
# 2. Make an S3 bucket public, then private again
# 3. Attempt an MFA-less console login (failure is fine)

# Then verify each appears in the centralized logs within the SLA
# and that the expected alert fired (or note that it did not)

# Alerting baseline to expect:
# - Root account usage
# - IAM policy changes
# - Public exposure changes (S3, security groups)
# - Failed MFA / impossible travel logons
# - CloudTrail disablement attempts
```

The canary test is the honest answer to "would we see an attack": if
your test user creation did not alert, neither will the attacker's.
Run it with SOC coordination so the test does not become an incident.

## Edge cases

- Logging is on but nobody watches. Enabled without alerting is
  half a control; the finding covers the monitoring gap too.
- Data-plane logging is off for cost reasons. Note the tradeoff
  explicitly: storage access without logs is a blind spot with a
  price tag, and leadership should sign the acceptance.
- Multi-cloud: each provider's logging checked separately; the SIEM
  ingestion covers all of them or the gaps are named.
- Retention is short. Investigations need history; 30 days of logs
  cannot answer a 60-day dwell time.

## Escalation

- Logging is disabled in production accounts: report as critical;
  the environment is currently undefended against key theft.
- You find evidence of log tampering: treat as an incident input
  immediately, alongside the configuration finding.
- The fix needs budget (SIEM ingestion, storage): frame it with the
  canary test results as the business case.

## Detection and defender view

This sub-skill is pure defender value: logging posture is the
detectability baseline. The defender's continuous work is the canary
test on a schedule, alert tuning from real incidents, and protecting
the logging pipeline itself as critical infrastructure. An attacker who
owns the logs owns the narrative; the pipeline is a security control,
not just plumbing.

## Key references

- CIS Benchmarks: logging and monitoring sections.
- NIST SP 800-92 (Guide to Computer Security Log Management).
- MITRE ATT&CK T1562.008 (Impair Defenses: Disable Cloud Logs).
