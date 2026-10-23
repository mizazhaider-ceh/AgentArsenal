---
name: cloud-cost-attack-surface
description: Use when assessing cloud cost as an attack surface on an
  authorized engagement. Covers denial of wallet, resource exhaustion
  billing, free tier abuse, and cost anomaly detection. Also use when
  a startup's burn rate spikes unexpectedly.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [cloud-security-basics, api-rate-limit-bypass, siem-detections]
tools:
  - name: Python
    version: 3.12
---

Attackers do not have to steal data; they can just run up your bill:
denial of wallet through expensive API calls, storage, or compute.
This skill covers authorized assessment: finding cost sensitive
endpoints, testing abuse within agreed limits, and setting up cost
defenses. Never run up a real bill beyond the agreed test budget.

## Quick Workflow

1. Map cost drivers: which services and endpoints cost money per use.
2. Find unauthenticated expensive paths: image processing, PDF
   generation, AI inference, and egress.
3. Check quotas and limits: are they set, and do they actually stop
   spend.
4. Test abuse within the agreed budget: measure cost per request.
5. Review billing alerts: thresholds, contacts, and response.
6. Check for committed spend vs on demand confusion.
7. Recommend rate limits, quotas, and async processing with caps.
8. Report the maximum plausible abuse cost per finding.

## 1. Cost driver mapping

```bash
# AWS: top cost services last month (authorized account, read only)
aws ce get-cost-and-usage \
  --time-period Start=2026-09-01,End=2026-10-01 \
  --granularity MONTHLY --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[].Groups[] | sort_by(@, &Metrics.BlendedCost.Amount) | reverse(@)[:10]' \
  --output table 2>/dev/null | head -20
```

```python
#!/usr/bin/env python3
"""Cost per request estimator for an endpoint (authorized test)."""
# Measure with a small, budgeted sample; never load test for cost
requests = 50          # agreed sample size
cost_per_1k = 0.40     # from the provider pricing page for the operation
sample_cost = requests / 1000 * cost_per_1k
print(f"sample cost: ${sample_cost:.4f} for {requests} requests")
print(f"abuse at 1M requests/day: ${1_000_000/1000*cost_per_1k:,.0f}/day")
print("if unauthenticated and unlimited, that is the finding's price tag")
```

## 2. Quota and alert review

```bash
# Check service quotas are actually restrictive (not the default 1000s)
aws service-quotas list-service-quotas --service-code lambda \
  --query 'Quotas[?contains(QuotaName, `concurrent`)].{Name:QuotaName,Value:Value}' 2>/dev/null
# Billing alerts: is anyone paged before the money is gone
aws cloudwatch describe-alarms --query 'MetricAlarms[?contains(MetricName,`EstimatedCharges`)]' 2>/dev/null | head -20
```

## Edge cases

- The expensive path needs auth. Then it is an authenticated abuse
  case; check per user quotas and abuse of free trials.
- Costs are in a different account (marketplace, data transfer).
  Map the full path; attackers find the account you forgot.
- Serverless scales infinitely by design. That is the risk; caps
  are the control.

## Escalation

- Unauthenticated expensive endpoint found: recommend auth plus
  rate limit plus quota, in that order.
- Active cost attack in progress: throttle at the edge (WAF rate
  rules) and rotate any exposed keys being abused.

## Detection and defender view

Defenders detect cost attacks with billing anomaly alerts, per
service dashboards, and usage alerts long before the invoice. They
defend with quotas on everything, rate limits on expensive
endpoints, and async queues with max depths. The durable practice
is treating cost as a security metric: alert on it like an
intrusion, because sometimes it is one.

## Key references

- CWE-770 (Allocation of Resources Without Limits).
- CWE-400 (Uncontrolled Resource Consumption).
- Provider cost anomaly detection documentation.
