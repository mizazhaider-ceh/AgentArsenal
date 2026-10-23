---
name: cloud-security-basics
description: Use when reviewing cloud security posture at concept level across AWS, GCP, and Azure, when checking IAM for least privilege and wildcard grants, when hunting public storage buckets and open security groups, when verifying audit logging such as CloudTrail, and when you need CLI checks with aws, az, and gcloud plus the reasoning behind each finding.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [recon-passive]
tools:
  - name: aws-cli
    version: "2.x"
  - name: azure-cli
    version: "2.x"
  - name: gcloud
    version: "4xx"
  - name: python
    version: "3.12"
---

This skill covers cloud security fundamentals at concept level across AWS, GCP, and Azure: IAM least privilege, storage misconfigurations, network exposure, audit logging, and credential hygiene. The scope is configuration review, not exploitation: read-only checks you can run during an audit or as recurring posture hygiene. Each area explains the concept once, then gives the concrete CLI check per provider, so the same reasoning transfers across clouds. It pairs with recon-passive, which covers finding cloud assets from the outside; this skill covers assessing them from the inside with legitimate access.

## Quick Workflow

1. Define scope: which accounts, projects, or subscriptions are under review. Verify identity before every run.
2. Review IAM: enumerate principals and flag admin, wildcard, and stale grants.
3. Check storage: find buckets and containers with public or anonymous access.
4. Check network exposure: security groups and firewall rules open to the internet on sensitive ports.
5. Verify audit logging: activity logs enabled, complete, stored immutably, and actually monitored.
6. Review keys and credentials: age, scope, and where they are stored.
7. Write findings with provider, resource, risk, evidence, and a concrete fix.

## Phase 1: IAM least privilege

Concept: every identity gets only the permissions it needs, nothing more. Default deny, short-lived credentials, roles instead of long-lived users, MFA on human access, and no wildcard actions (`*`) or wildcard resources on powerful APIs. The most common real-world failures are admin policies attached for convenience, wildcard S3 or EC2 actions, and ex-employee access never revoked.

Always confirm which account you are operating in before running checks:

```bash
aws sts get-caller-identity
gcloud config get-value project
az account show --query '{name:name, id:id}'
```

AWS: list users and inspect their attached policies for admin or wildcard grants:

```bash
aws iam list-users --query 'Users[].UserName' --output text
aws iam list-attached-user-policies --user-name alice
aws iam list-user-policies --user-name alice
aws iam get-policy --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

Red flags in policy documents: `"Action": "*"`, `"Action": "s3:*"` or `"iam:*"` paired with `"Resource": "*"`, and `AdministratorAccess` attached to daily-use users instead of break-glass roles.

GCP: inspect the project IAM policy for overly broad roles:

```bash
gcloud projects get-iam-policy my-project --format=json > iam.json
python3 -c "
import json
p = json.load(open('iam.json'))
for b in p.get('bindings', []):
    if b['role'] in ('roles/owner', 'roles/editor') or 'admin' in b['role']:
        print(b['role'], '->', len(b.get('members', [])), 'members')
"
```

Red flags: `roles/owner` or `roles/editor` on many members (editor is far broader than people expect), `allUsers` or `allAuthenticatedUsers` in any binding, service accounts with owner on projects they only need to read.

Azure: list role assignments and flag Owner and broad Contributor grants:

```bash
az role assignment list --all --query "[?roleDefinitionName=='Owner'].{principal:principalName, scope:scope}" --output table
az role assignment list --all --query "[?roleDefinitionName=='Contributor'] | length(@)"
```

Red flags: Owner at subscription scope for daily work, Contributor where a Reader or custom role would do, guest users with write roles.

## Phase 2: Storage misconfigurations

Concept: object storage (S3 buckets, GCS buckets, Azure storage accounts and containers) is private by default in all three clouds, and every public-data breach in this category came from someone changing that default. Check the public-access settings, the bucket policy or IAM bindings, and any anonymous-access flags.

AWS: confirm the account-level public access block and per-bucket policy status:

```bash
aws s3control get-public-access-block --account-id 123456789012
aws s3api get-public-access-block --bucket mybucket
aws s3api get-bucket-policy-status --bucket mybucket
aws s3api get-bucket-acl --bucket mybucket --query 'Grants[?Grantee.URI!=null]'
```

Any grant to `http://acs.amazonaws.com/groups/global/AllUsers` or `AuthenticatedUsers` is public or semi-public access. `IsPublic: true` in the policy status needs a documented business reason.

GCP: check IAM bindings and uniform access settings on the bucket:

```bash
gcloud storage buckets describe gs://mybucket --format='json(iamConfiguration)'
gcloud storage buckets get-iam-policy gs://mybucket --format=json | grep -E "allUsers|allAuthenticatedUsers"
```

`allUsers` with `roles/storage.objectViewer` means anyone on the internet can read the objects.

Azure: check anonymous blob access and TLS floor on the storage account:

```bash
az storage account show -n mystorage -g mygroup --query '{publicBlob:allowBlobPublicAccess, tls:minimumTlsVersion, httpsOnly:supportsHttpsTrafficOnly}'
az storage container list --account-name mystorage --query '[].{name:name, public:properties.publicAccess}'
```

`allowBlobPublicAccess: true` plus a container with `publicAccess: blob` is internet-readable storage. `minimumTlsVersion` below 1.2 is a finding.

## Phase 3: Network exposure

Concept: security groups (AWS), firewall rules (GCP), and network security groups (Azure) are the cloud firewall. The audit question is always the same: which rules allow the internet (`0.0.0.0/0` or `::/0`) to reach sensitive ports (SSH 22, RDP 3389, databases, admin consoles)?

AWS: find security groups with internet-open ingress on sensitive ports:

```bash
aws ec2 describe-security-groups \
  --query 'SecurityGroups[].{Group:GroupName, Open:IpPermissions[?IpRanges[?CidrIp==`0.0.0.0/0` || CidrIp==`::/0`]].{From:FromPort, To:ToPort}}' \
  --output table
```

GCP: list firewall rules with internet source ranges:

```bash
gcloud compute firewall-rules list \
  --filter='sourceRanges:0.0.0.0/0' \
  --format='table(name, direction, allowed[].map().firewall_rule().list(), targetTags)'
```

Azure: list NSG rules allowing inbound from any source:

```bash
az network nsg list --query "[].{nsg:name, open:securityRules[?access=='Allow' && direction=='Inbound' && (sourceAddressPrefix=='*' || sourceAddressPrefix=='Internet')].{name:name, ports:destinationPortRange}}" --output json
```

Every internet-open rule needs an owner and a reason. SSH or RDP open to the world is a finding even when key-only auth is used; move admin access behind a VPN or bastion.

## Phase 4: Audit logging

Concept: if it is not logged, you cannot investigate it. All three clouds offer an activity audit trail; the checks are whether it is enabled everywhere, whether it covers management and data events, whether logs are stored where attackers cannot delete them, and whether anyone actually looks at them.

AWS CloudTrail:

```bash
aws cloudtrail describe-trails --query 'trailList[].{Name:Name, MultiRegion:IsMultiRegionTrail, LogValidation:LogFileValidationEnabled}'
aws cloudtrail get-trail-status --name my-trail --query '{Logging:IsLogging, LatestDelivery:LatestDeliveryTime}'
aws s3api get-bucket-versioning --bucket my-cloudtrail-bucket
```

Requirements: a multi-region trail, log file validation on, logging active, bucket versioning and restricted write access so logs cannot be silently deleted.

GCP Cloud Audit Logs:

```bash
gcloud logging sinks list --format='table(name, destination)'
gcloud projects get-iam-policy my-project --format=json | grep -c "allUsers"
```

Admin Activity logs are on by default and cannot be disabled; verify Data Access logs are enabled for sensitive services and that sinks export to a locked-down bucket or dataset in a separate project.

Azure Activity Log:

```bash
az monitor diagnostic-settings list --resource /subscriptions/<sub-id> --query '[].{name:name, storage:storageAccountId}'
az monitor log-profiles list --query '[].{name:name, retention:retentionPolicy.days}'
```

Requirements: activity logs retained (a year is a common target), diagnostic settings on key resources, logs stored where the audited subscription's admins cannot tamper with them.

## Phase 5: Keys, secrets, and credentials

Concept: long-lived credentials are the most stolen cloud artifact. Prefer short-lived mechanisms (instance roles, workload identity, OIDC for CI) and treat any static key as a liability with an expiry date.

AWS: list access keys and check their age:

```bash
aws iam list-access-keys --user-name alice --query 'AccessKeyMetadata[].{id:AccessKeyId, created:CreateDate, status:Status}'
```

Keys older than 90 days, active keys for users who also have console access, and any key found in code or chat are findings. Root account keys must not exist, and the root account needs MFA plus no daily use.

GCP: list service account keys and prefer workload identity:

```bash
gcloud iam service-accounts list --format='table(email)'
gcloud iam service-accounts keys list --iam-account=sa@my-project.iam.gserviceaccount.com --format='table(name, validAfterTime)'
```

User-managed keys are the risk; Google-managed keys rotate automatically. For CI, use Workload Identity Federation instead of downloaded JSON keys.

Azure: check app credentials and prefer managed identities:

```bash
az ad app credential list --id <app-id> --query '[].{end:endDateTime}'
```

Expired-but-still-present secrets, secrets nearing expiry without rotation, and connection strings with keys embedded in app config are findings. Managed identities eliminate the secret entirely and are the default recommendation.

## Common misconfigurations at a glance

| Misconfiguration | Risk | Where to check |
|---|---|---|
| Public storage bucket or container | Data breach, often discovered by scanners before you | Phase 2 commands |
| Wildcard IAM actions on wildcard resources | Privilege escalation to full admin | Phase 1 policy review |
| Disabled or single-region audit logging | Blind during incident response | Phase 4 commands |
| Security group open to 0.0.0.0/0 on SSH/RDP/DB | Direct attack path from the internet | Phase 3 commands |
| Long-lived keys in code, CI, or chat | Credential theft and reuse | Phase 5 commands, secret scanning |
| No MFA on human admin access | Phishing becomes full account takeover | IAM console, credential report |
| Unencrypted storage or TLS below 1.2 | Data exposure in transit or at rest | Storage and load balancer settings |
| Orphaned resources from deleted projects | Forgotten attack surface nobody patches | Periodic full inventory |

## Edge cases

- CLI not authenticated: use `aws sso login`, `az login`, or `gcloud auth login` with named profiles. Never paste credentials into chat or tickets to "make it work".
- Multiple accounts: always run the identity check from Phase 1 first. Findings attributed to the wrong account waste everyone's time.
- Eventual consistency: IAM changes can take time to appear. Re-check after a few minutes before declaring a fix failed.
- Organization policies override project settings: a clean project check means little if an org-level policy or SCP reopens it. Review org-level policies too.
- Read-only auditing: request SecurityAudit, Viewer, or Reader roles. An audit never needs admin, and asking for admin for a read-only review is itself a finding about your process.
- Data events cost money and volume: enabling S3 data events or GCP data-access logs everywhere can be expensive. Enable them for sensitive buckets and services first.

## Escalation

- CLI access is blocked by policy: do the same checks in the console with a read-only role, and document each check manually. The concepts do not change.
- The blast radius of a finding is unclear: check the provider's security hub (AWS Security Hub, GCP Security Command Center, Microsoft Defender for Cloud) for prioritized, correlated findings before sounding alarms.
- You suspect active compromise: stop the audit, preserve the audit logs first (they are the evidence), revoke the suspect credentials, and switch to incident response. Do not tip off the investigation by making broad config changes first.

## Detection and defender view

For engineering skills this section covers detecting cloud misconfiguration and misuse.

- Misconfiguration signals: public storage, wildcard IAM grants, disabled audit logging, internet-open admin ports, static keys older than your rotation policy. These are exactly the findings this skill hunts.
- Defenders detect with posture management: scheduled CSPM scans, alerts on `iam:Put*` and `s3:PutBucketPolicy` API calls, and anomaly detection on credential use (a key used from a new geography is worth an alert).
- Misuse: daily work done with root or admin keys, long-lived keys in CI instead of OIDC or workload identity, break-glass accounts used without a declared emergency, audit log buckets writable by the accounts they audit.
- Fix the process: require MFA everywhere, default to private storage with explicit approvals for public data, alert on every IAM policy change, and review the findings of this skill's checklist quarterly, not once.

## Key references

- AWS: IAM best practices, S3 security best practices, CloudTrail documentation (docs.aws.amazon.com)
- GCP: IAM documentation, Cloud Audit Logs documentation (cloud.google.com/iam, cloud.google.com/logging)
- Azure: Azure RBAC documentation, Microsoft Defender for Cloud (learn.microsoft.com)
- CIS Benchmarks for AWS, Microsoft Azure, and Google Cloud Platform (cisecurity.org)
- MITRE ATT&CK: T1078 Valid Accounts, T1530 Data from Cloud Storage Object (attack.mitre.org)
