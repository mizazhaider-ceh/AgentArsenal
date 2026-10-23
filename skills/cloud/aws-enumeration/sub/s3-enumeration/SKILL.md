---
name: s3-enumeration
description: Use when enumerating S3 buckets for misconfigurations and
  exposed data on an authorized engagement. Covers bucket discovery,
  permission testing, policy review, and safe content sampling. Use when
  you have AWS credentials, when hunting public buckets, when the asset
  inventory flagged storage, or when assessing data exposure risk.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
parent: aws-enumeration
requires: [aws-enumeration]
extends: []
relates: [cloud-security-basics]
tools:
  - name: AWS CLI
    version: 2.15
  - name: Python
    version: 3.12
---

S3 buckets are the classic cloud data exposure: one wrong ACL and the
world reads the backups. This skill covers S3 enumeration on authorized
engagements: finding buckets, testing their permissions precisely, and
sampling contents safely. It is methodical permission testing, not data
theft; sample minimally and report the exposure, not the data.

## Quick Workflow

1. List all buckets visible to the credentials.
2. Check each bucket's ACL, policy, and public access block.
3. Test effective permissions: list, read, write, with and without auth.
4. Sample contents minimally to characterize sensitivity.
5. Check versioning, encryption, and logging per bucket.
6. Report exposures with the permission evidence, not the data.

## 1. Discovery and permission testing

```bash
# List buckets
aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n'

# Per bucket: ACL, policy, public access block
for b in bucket1 bucket2; do
  echo "== $b"
  aws s3api get-bucket-acl --bucket $b --output text 2>&1 | grep -i -E 'AllUsers|AuthenticatedUsers' | head -3
  aws s3api get-public-access-block --bucket $b 2>&1 | head -5
done

# Effective permission test WITHOUT credentials (the attacker's view)
aws s3 ls s3://target-bucket/ --no-sign-request 2>&1 | head -5
aws s3api get-bucket-policy --bucket target-bucket --no-sign-request 2>&1 | head -5
```

The `--no-sign-request` test is the ground truth for public exposure:
if the anonymous call succeeds, the bucket is public regardless of what
the console shows. Test list, get, and put separately; list-public and
write-public are different findings with different impacts.

## 2. Policy review

```bash
# Read the bucket policy for the dangerous patterns
aws s3api get-bucket-policy --bucket target-bucket --output text 2>/dev/null \
  | python3 -m json.tool | head -50

# Flag: Principal "*" with Allow (public by policy)
# Flag: conditions that do not actually restrict (aws:Referer alone is weak)
# Flag: s3:PutObject allowed publicly (anyone can write: defacement/malware)

# Check for the secure defaults that should be there
aws s3api get-bucket-encryption --bucket target-bucket 2>&1 | head -5
aws s3api get-bucket-versioning --bucket target-bucket --output text
aws s3api get-bucket-logging --bucket target-bucket --output text
```

A public-read bucket of website assets is a hardening note; a
public-read bucket of database backups is a critical finding. The
permission is the mechanism; the content determines the severity. Sample
enough to characterize, never enough to exfiltrate.

## 3. Safe content sampling

```bash
# List top-level prefixes to understand the bucket's purpose
aws s3 ls s3://target-bucket/ --no-sign-request 2>&1 | head -20

# Sample ONE file to characterize (not download the dataset)
aws s3 cp s3://target-bucket/sample-prefix/file.txt /tmp/sample.txt \
  --no-sign-request 2>&1 | head -3
head -c 500 /tmp/sample.txt
rm /tmp/sample.txt  # do not keep sampled data longer than needed

# NEVER: sync the bucket, download backups, or read customer data fully
```

Sampling discipline is what separates assessment from theft: one file to
characterize sensitivity, then stop. If the sample shows regulated data,
report the exposure class immediately through the agreed channel.

## Edge cases

- The bucket denies listing but allows gets (blind read). Test known
  key names from the application; unlistable is not unreadable.
- Access is via CloudFront/OAI, not direct. Test the distribution's
  behavior; origin misconfigurations still leak through.
- The bucket is in another account. Cross-account policies need the
  same review; note the trust boundary.
- Versioning shows deleted sensitive files. Old versions of deleted
  objects persist; check version listings for ghosts.

## Escalation

- Public exposure of sensitive data confirmed: report immediately via
  the critical channel; the client may need to rotate exposed
  credentials the same day.
- Write access confirmed publicly: this enables malware hosting and
  defacement; report as critical with the put test evidence.
- You need the full content inventory: that is a data-handling
  decision needing explicit approval; default to sampling.

## Detection and defender view

Defenders see S3 enumeration as ListBucket and GetBucketPolicy calls
from unusual principals, plus anonymous requests in the access logs.
Defenses are the public access block at the account level, SCPs denying
public policies, config rules alerting on public buckets, and access
logging on sensitive buckets. The durable fix is deny-by-default with
explicit, reviewed exceptions.

## Key references

- CIS AWS Benchmark: S3 sections.
- CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- CWE-732 (Incorrect Permission Assignment for Critical Resource).
- AWS S3 security best practices documentation.
