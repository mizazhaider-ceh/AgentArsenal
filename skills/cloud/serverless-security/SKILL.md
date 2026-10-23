---
name: serverless-security
description: Use when assessing serverless applications (Lambda,
  Cloud Functions, Azure Functions) on an authorized engagement.
  Covers function enumeration, event injection, IAM role abuse,
  and insecure dependencies. Also use when reviewing whether
  serverless actually reduced the attack surface.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [cloud-security-basics, iam-privesc, api-security-testing]
tools:
  - name: Python
    version: 3.12
---

Serverless removes servers but not security work: the function code,
its triggers, and its IAM role are the new attack surface. This skill
covers authorized assessment: enumerating functions and triggers,
injecting events, abusing over broad roles, and reviewing
dependencies. Test only accounts and functions you are authorized to
assess.

## Quick Workflow

1. Enumerate functions, triggers, and environment variables you can
   see with the test role.
2. Map each trigger to its input: API Gateway, S3 events, queues,
   and schedules.
3. Test event injection: malformed and malicious event payloads per
   trigger.
4. Review the execution role: what the function can reach with its
   permissions.
5. Check environment variables and layers for secrets.
6. Review dependencies for known vulnerabilities.
7. Test the API triggers with the web API skills.
8. Report per function with its role's blast radius.

## 1. Enumeration (AWS example, authorized account)

```bash
# List functions and their triggers
aws lambda list-functions --query 'Functions[].FunctionName' --output text
aws lambda get-policy --function-name orders-api 2>/dev/null | head -30
# Environment variables (may hold secrets; handle carefully)
aws lambda get-function-configuration --function-name orders-api \
  --query 'Environment.Variables'
```

```bash
# Who can invoke: resource policy plus the execution role
aws lambda get-function --function-name orders-api \
  --query 'Configuration.Role'
aws iam get-role-policy --role-name lambda-orders-role --policy-name inline 2>/dev/null | head -40
# Wildcard actions or * resources on the role = the finding
```

## 2. Event injection

```python
#!/usr/bin/env python3
"""Event injection probes per trigger type (authorized functions)."""
print("API Gateway: test like any web API (see api-security-testing)")
print("S3 trigger: upload objects with malicious names and contents")
print("SQS trigger: send malformed message bodies")
print("schedule: check for time based logic flaws")
print("each probe: does the function validate, or trust the event?")
```

```bash
# S3 event path traversal via object key (classic)
aws s3 cp /tmp/evil.txt s3://target-bucket/../../tmp/evil.txt --profile test
# Then check the function logs: did it write outside the intended path
aws logs tail /aws/lambda/s3-processor --since 5m --profile test | head -20
```

## Edge cases

- Functions are VPC attached. The network path matters; assess the
  security groups too.
- Layers are shared across functions. A vulnerable layer affects
  everything; inventory layer versions.
- The function is behind a WAF at API Gateway. Test the function
  directly via its other triggers too.

## Escalation

- Role is over privileged: demonstrate the reachable services
  (list buckets, read tables) within the test account.
- Event injection works: escalate to the impact (data written,
  messages sent) with a harmless proof.
- Need the full account picture: hand to iam-privesc for the role
  chain review.

## Detection and defender view

Defenders see serverless attacks as unusual invocations, functions
calling services outside their baseline, and spikes in duration or
memory (crypto mining). They detect with CloudTrail for control
plane, function logs for data plane, and anomaly alerts. The durable
defense is least privilege roles per function, input validation on
every trigger, dependency scanning in CI, and no secrets in env vars.

## Key references

- MITRE ATT&CK T1578 (Modify Cloud Compute Infrastructure).
- CWE-862 (Missing Authorization): role and trigger gaps.
- CWE-798 (Use of Hard-coded Credentials): env var secrets.
- Cloud provider serverless security guidance.
