---
name: differential-privacy
description: Use when you need to publish statistics or train models
  on sensitive data without exposing individuals. Covers epsilon
  budgets, Laplace and Gaussian noise, composition, and the practical
  limits of the guarantee. Also use when a data sharing request needs
  a principled privacy answer instead of "we anonymized it".
version: 1.0.0
domain: privacy
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [anonymization-techniques, data-minimization, privacy-threat-model]
tools:
  - name: Python
    version: 3.12
---

Differential privacy gives a mathematical promise: the output barely
changes whether any one person is in the dataset or not. It replaces
hand waving about anonymization with a budget (epsilon) you can
reason about. This skill covers the practical use: adding calibrated
noise to statistics, tracking the privacy budget, and knowing where
the guarantee breaks down.

## Quick Workflow

1. Define the queries you need: counts, sums, means, or histograms.
2. Compute the sensitivity of each query: how much one person can
   change the answer.
3. Choose epsilon per query and track the total budget (composition).
4. Add Laplace or Gaussian noise scaled to sensitivity over epsilon.
5. Clamp and bound inputs so sensitivity is finite and honest.
6. Publish the epsilon values alongside the results; secrecy about
   the budget voids the trust.
7. Monitor the budget in production: queries consume it, and it does
   not refresh by itself.
8. Document what DP does not cover: the raw data still needs access
   control.

## 1. Noise mechanisms

```python
#!/usr/bin/env python3
"""Differentially private count and mean with Laplace noise (stdlib)."""
import random, math

def laplace_noise(scale):
    u = random.random() - 0.5
    return -scale * math.copysign(math.log(1 - 2 * abs(u)), u)

def dp_count(true_count, epsilon):
    # sensitivity of a count is 1
    return true_count + laplace_noise(1.0 / epsilon)

def dp_mean(values, lower, upper, epsilon):
    # clamp first: sensitivity = (upper - lower) / n
    clamped = [min(max(v, lower), upper) for v in values]
    n = len(clamped)
    sens = (upper - lower) / n
    return sum(clamped) / n + laplace_noise(sens / epsilon)

print("dp count (eps=1.0):", round(dp_count(1000, 1.0)))
print("dp mean  (eps=1.0):", round(dp_mean([25]*500 + [35]*500], 0, 100, 1.0), 2))
```

```bash
# Budget tracking: every query spends epsilon; composition adds up
python3 - << 'PY'
queries = [("daily active users", 0.5), ("signup funnel", 0.5), ("revenue mean", 1.0)]
total = sum(e for _, e in queries)
print(f"total epsilon spent: {total} (basic composition)")
print("rule: set a budget per dataset per period, and enforce it in code")
PY
```

## 2. Production checklist

```bash
# Before shipping DP statistics:
# - sensitivity computed from clamped bounds, documented
# - epsilon chosen and published, not tuned per dataset after seeing data
# - budget enforced server side (clients cannot just re-query)
# - raw data access unchanged: DP protects outputs, not the database
# - small groups: DP noise can dominate; suppress or aggregate further
echo "review each item; most DP failures are budget accounting, not math"
```

## Edge cases

- Epsilon chosen after looking at the data. That leaks; choose from
  policy, or spend budget on the choice.
- The same person appears in many queries. Composition across queries
  about one individual multiplies the exposure; track per user too.
- Floating point noise implementations leak through rounding. Use a
  vetted library for production, not the stdlib sketch above.
- Stakeholders want epsilon tiny and utility high. Show the tradeoff
  curve; you cannot have both, and the choice is a policy decision.

## Escalation

- Production deployment: use a reviewed DP library (OpenDP, Tumult)
  instead of hand rolled noise.
- ML training: move to DP-SGD with a proper accounting library; the
  per query sketch does not transfer.
- Legal asks "is this anonymous": DP is a strong argument but get
  counsel's view; the law and the math use different words.

## Detection and defender view

For DP, misuse looks like budget overruns: more queries than the
policy allows, epsilon values changed quietly, or noise "temporarily
disabled for debugging" and never restored. Monitor the budget like
a financial budget, with alerts and hard stops. The durable practice
is publishing the methodology: epsilon, mechanism, and bounds, so
the guarantee can be checked instead of trusted.

## Key references

- Dwork and Roth: "The Algorithmic Foundations of Differential
  Privacy" (free online).
- NIST SP 800-188 (de-identification, DP sections).
- OpenDP documentation: production mechanisms.
