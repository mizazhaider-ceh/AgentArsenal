---
name: cloud-asset-inventory
description: Use when you need a complete inventory of cloud assets for
  security review on an authorized engagement. Covers multi-account
  discovery, storage, compute, and database enumeration, and finding
  shadow or forgotten resources. Use when starting a cloud assessment,
  when the account list is incomplete, when hunting internet-exposed
  assets, or when building the asset baseline for continuous review.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
parent: cloud-security-basics
requires: [cloud-security-basics]
extends: []
relates: [aws-enumeration, recon-passive]
tools:
  - name: Python
    version: 3.12
  - name: AWS CLI
    version: 2.15
---

You cannot secure what you do not know exists: cloud asset inventory is
the foundation of cloud security review. This skill covers building the
inventory on authorized engagements: discovering accounts and resources,
enumerating the high-risk asset types, and finding the shadow resources
nobody remembers. It is read-only enumeration; findings about the assets
feed the IAM and logging reviews.

## Quick Workflow

1. Confirm the account and organization scope in writing.
2. List all accounts in the organization.
3. Enumerate high-risk assets per account: storage, compute, databases,
   public IPs.
4. Flag internet-exposed resources specifically.
5. Hunt shadow assets: old regions, forgotten projects, test accounts.
6. Write the inventory with exposure notes per asset.

## 1. Account and resource discovery

```bash
# AWS: list accounts in the organization
aws organizations list-accounts --output table 2>/dev/null | head -30

# Per account: the high-risk resource types
for region in us-east-1 eu-west-1; do
  echo "== $region =="
  aws ec2 describe-instances --region $region \
    --query 'Reservations[].Instances[].[InstanceId,PublicIpAddress,State.Name]' \
    --output text 2>/dev/null | head -10
  aws rds describe-db-instances --region $region \
    --query 'DBInstances[].[DBInstanceIdentifier,PubliclyAccessible]' \
    --output text 2>/dev/null | head -10
done

# Storage buckets (global namespace in AWS, per-project in GCP/Azure)
aws s3api list-buckets --query 'Buckets[].Name' --output text 2>/dev/null | tr '\t' '\n' | head -20
```

Enumerate every region the organization uses, not just the primary one:
forgotten resources live in odd regions. The inventory is per account
per region; anything less is incomplete.

## 2. Exposure flagging

```bash
# Public IPs and open security groups (AWS example)
aws ec2 describe-security-groups \
  --query 'SecurityGroups[?IpPermissions[?IpRanges[?CidrIp==`0.0.0.0/0`]]].[GroupId,GroupName]' \
  --output text 2>/dev/null | head -10

# Public S3 buckets: check the bucket policy and ACLs per bucket
for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text 2>/dev/null); do
  acl=$(aws s3api get-bucket-acl --bucket $b 2>/dev/null | grep -c 'AllUsers')
  [ "$acl" -gt 0 ] && echo "PUBLIC ACL: $b"
done

# Public snapshots and AMIs shared externally
aws ec2 describe-snapshots --owner-ids self \
  --query 'Snapshots[?Public==`true`].[SnapshotId]' --output text 2>/dev/null | head -5
```

Every internet-exposed asset gets an exposure note: what it is, why it
is public, and whether the exposure is intended. Unintended public
exposure is the most common cloud finding; the inventory makes it
visible.

## 3. Shadow asset hunting

```bash
# Hunt patterns:
# - Regions with resources but no active project (forgotten)
# - Accounts with no recent CloudTrail activity (abandoned)
# - Old access keys (created years ago, still active)
# - Unattached EBS volumes and elastic IPs (paying for forgotten)

aws ec2 describe-volumes \
  --query 'Volumes[?State==`available`].[VolumeId,Size,CreateTime]' \
  --output text 2>/dev/null | head -10
aws iam list-users --query 'Users[].[UserName,CreateDate]' \
  --output text 2>/dev/null | head -20
```

Shadow assets are the attacker's favorite: unmonitored, unpatched, and
often over-permissioned. The inventory review should ask of every asset:
who owns it, what it does, and what happens if it is compromised. No
owner means decommission.

## Edge cases

- The organization list is incomplete. Ask for the full account list;
  cloud accounts get created outside central IT regularly.
- Read-only credentials lack some APIs. Note the blind spots; an
  inventory with known gaps beats a guessed-complete one.
- Multi-cloud: repeat per provider with the provider's tooling; the
  inventory merges at the end, not during.
- The inventory is huge. Prioritize internet-exposed and data-bearing
  assets; the full list still gets recorded.

## Escalation

- You find clearly unintended public exposure of sensitive data: report
  through the critical channel immediately; do not wait for the full
  inventory.
- Shadow accounts cannot be attributed: recommend suspension pending
  owner identification, with leadership approval.
- The inventory must be continuous: hand the enumeration commands to
  the team as the scheduled job that keeps it fresh.

## Detection and defender view

For defenders, the inventory is the prerequisite for everything else:
detection rules, IAM review, and logging all assume you know the
assets. Cloud asset discovery tools and CSPM products automate this,
but the discipline is the same: every account, every region, regularly.
The defender's metric is time from asset creation to inventory; shadow
IT makes that number large, and attackers live in the gap.

## Key references

- CIS Benchmarks for AWS, Azure, GCP (asset configuration baselines).
- NIST SP 800-210 (access control for cloud, inventory concepts).
- Cloud provider documentation: resource enumeration APIs.
