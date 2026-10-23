---
name: s3-misconfigurations
description: Use when testing Amazon S3 buckets for misconfigurations
  during an authorized cloud assessment, bug bounty engagement, or lab
  exercise. Covers bucket discovery with and without credentials, ACL
  and bucket policy analysis, public access block settings, encryption,
  versioning, access logging, static website hosting, and risky
  cross-account grants using aws-cli 2.22 and Python 3.12. Use when a
  target exposes S3 buckets or when you need to verify your own buckets
  are not leaking data to the internet.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [aws-enumeration, cloud-security-basics]
tools:
  - name: aws-cli
    version: 2.22
  - name: Python
    version: 3.12
---

S3 misconfigurations are one of the most common cloud findings:
buckets that anyone on the internet can list, read, or write because
of an open ACL, a permissive bucket policy, or a missing public
access block. This skill covers the authorized operator workflow for
finding and proving S3 exposure: discovery, permission analysis,
common misconfiguration patterns, impact proof that stays read-only,
and verification of the fix. Use it against your own buckets,
in-scope bug bounty targets, and lab environments only. Never upload
files to, delete objects from, or modify buckets you do not own.

## Quick Workflow

1. Discover bucket names: from the authenticated `s3 ls` inventory,
   from scope notes, and from OSINT (subdomains, JS files, code)
   inside the authorized scope.
2. Test each bucket unauthenticated with `--no-sign-request`:
   list, then read one object only if listing is public.
3. Pull the bucket ACL and bucket policy with credentials and map
   every grant to an access level.
4. Check the four guardrails: public access block, default
   encryption, versioning, and access logging.
5. Check static website hosting and cross-account or
   `AuthenticatedUsers` grants.
6. Prove impact read-only: show a public object listing or one
   non-sensitive object header, never full sensitive data.
7. Classify the finding (public read, public write, sensitive data
   exposed) and record the exact commands.
8. Verify the fix after remediation: re-run the unauthenticated
   checks and confirm 403/AccessDenied.

## 1. Bucket discovery

```bash
# Authenticated inventory (feeds the checks below)
aws s3 ls

# Unauthenticated probe of a known bucket name
aws s3 ls s3://<BUCKET> --no-sign-request 2>&1 | head -5

# Direct HTTPS checks (bucket names are globally unique, so any name works)
curl -s -o /dev/null -w 'list: %{http_code}\n' https://<BUCKET>.s3.amazonaws.com/
curl -s -o /dev/null -w 'region-redirect: %{http_code}\n' https://s3.amazonaws.com/<BUCKET>/
```

Bucket names often leak in JavaScript bundles, mobile apps, and
subdomain certificates. Within your authorized scope, grep
collected assets for `s3.amazonaws.com` and `.s3-website` patterns.

## 2. Unauthenticated access tests

Run these without credentials. Stop at the first read-only proof;
do not download sensitive data or write test files to buckets you do
not own.

```bash
# LIST: does the world see object names
aws s3 ls s3://<BUCKET> --no-sign-request 2>&1 | head -10

# READ: fetch one object header only (no body download)
aws s3api head-object --bucket <BUCKET> --key <KEY> --no-sign-request 2>&1 | head -10

# WRITE test: ONLY against buckets you own. Never upload to
# buckets you do not own. (Intentionally no command here.)
```

HTTP equivalents when the CLI is not handy:

```bash
# List via XML API (200 with XML body means public listing)
curl -s "https://<BUCKET>.s3.amazonaws.com/?list-type=2&max-keys=5" | head -c 800

# Object read check (200 means public read)
curl -s -o /dev/null -w '%{http_code}\n' "https://<BUCKET>.s3.amazonaws.com/<KEY>"
```

Result codes: `200` means public, `403 AccessDenied` means closed,
`404 NoSuchBucket` means the name does not exist.

## 3. ACL analysis

```bash
# Full ACL: watch for AllUsers and AuthenticatedUsers grants
aws s3api get-bucket-acl --bucket <BUCKET> \
  --query 'Grants[].[Grantee.URI,Grantee.DisplayName,Permission]' --output text

# Object-level ACLs can differ from the bucket ACL
aws s3api get-object-acl --bucket <BUCKET> --key <KEY> \
  --query 'Grants[].[Grantee.URI,Permission]' --output text 2>/dev/null
```

Dangerous grants and what they mean:

| Grantee | Permission | Impact |
|---|---|---|
| `http://acs.amazonaws.com/groups/global/AllUsers` | READ | Anyone lists and reads |
| `http://acs.amazonaws.com/groups/global/AllUsers` | WRITE | Anyone uploads and deletes |
| `http://acs.amazonaws.com/groups/global/AuthenticatedUsers` | READ or WRITE | Any AWS account in the world, not just yours |

Note: `AuthenticatedUsers` does NOT mean your account's users. It
means any authenticated AWS principal anywhere.

## 4. Bucket policy analysis

```bash
# Fetch and pretty-print the policy
aws s3api get-bucket-policy --bucket <BUCKET> \
  --query 'Policy' --output text > /tmp/policy.json
python3 -m json.tool /tmp/policy.json | head -80
```

Read every statement and check three fields:

```bash
# Quick triage with Python (stdlib only): statements that allow the world
python3 - <<'EOF'
import json
pol = json.load(open('/tmp/policy.json'))
for s in pol.get('Statement', []):
    princ = s.get('Principal')
    world = princ == '*' or (isinstance(princ, dict) and princ.get('AWS') == '*')
    if world and s.get('Effect') == 'Allow':
        print('WORLD-ALLOW:', s.get('Sid'), s.get('Action'), '->', s.get('Resource'))
        print('  Condition:', json.dumps(s.get('Condition', {}))[:200])
EOF
```

A `"Principal": "*"` Allow WITHOUT a restrictive Condition (IP
allowlist, VPC endpoint, or `aws:PrincipalOrgID`) is effectively
public. Common safe-looking but broken conditions: checking only
`aws:Referer`, or `StringLike` on user agent.

## 5. The four guardrails

```bash
# 1. Public access block: all four should be true
aws s3api get-public-access-block --bucket <BUCKET> 2>&1

# 2. Default encryption at rest
aws s3api get-bucket-encryption --bucket <BUCKET> 2>&1 | head -5

# 3. Versioning (lets owners recover from malicious overwrite)
aws s3api get-bucket-versioning --bucket <BUCKET>

# 4. Server access logging (evidence trail for the defender)
aws s3api get-bucket-logging --bucket <BUCKET> 2>&1

# Bonus: static website hosting widens the attack surface
aws s3api get-bucket-website --bucket <BUCKET> 2>&1 \
  && echo 'NOTE: static website hosting is ON'

# Bonus: policy status summary (AWS computed "is public" flag)
aws s3api get-bucket-policy-status --bucket <BUCKET> 2>&1
```

## 6. Cross-account and legacy grants

```bash
# Bucket policy statements granting specific external account IDs
python3 - <<'EOF'
import json, re
pol = json.load(open('/tmp/policy.json'))
for s in pol.get('Statement', []):
    txt = json.dumps(s)
    for acct in set(re.findall(r'arn:aws:iam::(\d{12}):', txt)):
        print('external account grant:', acct, '| Sid:', s.get('Sid'), '|', s.get('Effect'), s.get('Action'))
EOF

# CORS config can matter for browser-based exfiltration paths
aws s3api get-bucket-cors --bucket <BUCKET> 2>&1 | head -20
```

## 7. Proving impact without damage

Read-only proof is enough for the report:

1. The unauthenticated `ls` output showing object names (redact
   sensitive names in the report if they leak PII).
2. `head-object` output showing a public object exists and its
   content type and size.
3. The ACL or policy snippet granting the world access.
4. One screenshot or terminal capture of the 200 response.

Do NOT: download full sensitive files, upload test objects to
someone else's bucket, delete anything, or enable versioning or
logging changes yourself. If you suspect live sensitive data is
public, stop and escalate to the engagement lead immediately.

## 8. Bulk triage script

```bash
# Unauthenticated sweep over a bucket list (scope-approved names only)
while read -r b; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://$b.s3.amazonaws.com/")
  acl=$(aws s3api get-bucket-acl --bucket "$b" \
    --query "Grants[?Grantee.URI=='http://acs.amazonaws.com/groups/global/AllUsers'].Permission" \
    --output text 2>/dev/null)
  echo "$b http=$code allusers_acl=${acl:-none}"
done < /tmp/buckets.txt
```

## Edge cases

- Bucket exists but every call returns 403: it is closed to you.
  Record the 403 as evidence of a correct configuration, do not
  try to bypass it.
- `get-bucket-policy` returns NoSuchBucketPolicy while the ACL
  grants AllUsers READ: the bucket is still public through the
  ACL. Check both, always.
- Public access block is ON but objects were shared via
  pre-signed URLs: those URLs are bearer tokens, not a bucket
  misconfiguration. Do not confuse the two.
- `us-east-1` vs regional endpoints: a 301 redirect with the
  correct region in `x-amz-bucket-region` is normal, follow it.
- Requester-pays buckets return 403 to anonymous reads even when
  objects are shared; that is not a vulnerability.
- Object ACLs can be public while the bucket ACL is private
  (common with old `public-read` uploads). Sample object ACLs,
  do not assume the bucket ACL tells the whole story.
- Versioning SUSPENDED is not the same as never enabled: old
  versions may still exist and be publicly readable.

## Escalation

- Unauthenticated list works but you need the data
  classification: list object names and sizes only, then stop and
  escalate to the lead before touching any object body.
- Authenticated as a low-privilege user and `get-bucket-policy`
  is denied: the unauthenticated probes in section 2 still give
  you the ground truth about public exposure.
- Bucket name guesses return 404: move to scope-approved OSINT
  (certificate transparency for `*.s3.amazonaws.com` style names
  rarely helps; JS bundles and mobile apps help more).
- You find public WRITE on your own test bucket: prove it with
  `aws s3 cp /tmp/probe.txt s3://<BUCKET>/probe-<RANDOM>.txt
  --no-sign-request`, then DELETE the probe file immediately and
  record both commands.
- Suspected sensitive data exposed (backups, keys, PII): stop
  testing that bucket, notify the engagement lead at once, and do
  not copy the data to your machine.

## Detection and defender view

Defenders see S3 probing in S3 server access logs and CloudTrail
data events: anonymous `ListBucket` and `GetObject` calls from
unfamiliar IPs, and `GetBucketAcl`/`GetBucketPolicy` calls from
your assumed role. AWS Config rules (`s3-bucket-public-read-prohibited`,
`s3-bucket-public-write-prohibited`) and Security Hub flag public
buckets continuously; Trusted Advisor does the same. The durable
fixes are account-level public access blocks (all four settings
ON), bucket policies that deny non-TLS and non-VPC-endpoint
access, default encryption with KMS, versioning plus MFA delete
for critical buckets, and access logging to a separate locked
bucket. As the tester, keep unauthenticated probing gentle (a
handful of requests per bucket), never write to buckets you do
not own, and report exposure with the exact commands that proved
it.

## Key references

- MITRE ATT&CK T1530 (Data from Cloud Storage): reading exposed
  buckets and objects.
- MITRE ATT&CK T1580 (Cloud Infrastructure Discovery): bucket
  discovery and enumeration.
- CWE-732 (Incorrect Permission Assignment for Critical
  Resource): the misconfiguration class.
- CWE-200 (Exposure of Sensitive Information to an Unauthorized
  Actor): the impact.
- AWS S3 Block Public Access:
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
- AWS S3 bucket policy examples:
  https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-bucket-policies.html
