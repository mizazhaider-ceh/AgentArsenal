---
name: model-extraction
description: Use when assessing whether a machine learning model behind an
  API can be stolen or copied on an authorized engagement. Covers
  prediction API scraping, membership inference, model inversion, and
  functionality stealing through systematic querying. Also use when a
  client asks how exposed their paid model endpoint is to cloning.
version: 1.0.0
domain: ai-security
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [api-security-testing, crypto-fundamentals]
tools:
  - name: Python
    version: 3.12
---

Model extraction turns a paid prediction API into a free copy of the
model: an attacker queries it systematically and trains a substitute that
behaves the same. This skill covers authorized testing of that risk:
measuring how much signal each query leaks, running bounded extraction
probes, and testing membership inference on sensitive training data. Keep
query volumes inside the agreed test budget and never build a working
clone beyond the proof point.

## Quick Workflow

1. Characterize the API: inputs, outputs, confidence scores, rate limits,
   and pricing per query.
2. Check what the outputs leak: full probability vectors leak far more
   than top label answers.
3. Run a bounded extraction probe: a few hundred queries over the input
   space, then measure how well a simple substitute predicts the rest.
4. Test membership inference: can you tell whether a specific record was
   in the training set.
5. Try model inversion on small output classes to recover representative
   inputs.
6. Review rate limiting and monitoring: does anyone notice systematic
   querying.
7. Stop at the proof point: a substitute that beats a stated accuracy bar
   on a holdout set is enough.
8. Report the cost math: queries times price equals the cost of stealing
   the model.

## 1. Output leakage assessment

Rich outputs make extraction cheap. Check what the API returns before
you query at scale.

```bash
# What does one prediction return? (authorized test endpoint)
curl -s -X POST 'https://target.example/api/predict' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"features":[0.5,0.2,0.9,0.1]}' | python3 -m json.tool
# Full probability vector = high leakage. Top label only = low leakage.
```

```python
#!/usr/bin/env python3
"""Bounded extraction probe: substitute model accuracy vs query budget."""
import json, urllib.request, random

ENDPOINT = "https://target.example/api/predict"
TOKEN = "REPLACE_WITH_TEST_TOKEN"
BUDGET = 500  # agreed query budget, do not exceed

def predict(x):
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps({"features": x}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

# Query a grid over the input space (4 features, small demo)
labeled = []
for _ in range(BUDGET):
    x = [random.random() for _ in range(4)]
    try:
        labeled.append((x, predict(x)))
    except Exception as e:  # noqa: BLE001
        print("stopped early:", e)
        break
print(f"collected {len(labeled)} labeled queries within budget")
# A real test would train a substitute here and score it on a holdout
# set; agreement above ~90 percent proves practical extraction.
```

## 2. Membership inference probe

Membership inference asks whether a specific record was used in
training, which is a privacy finding even without full extraction.

```bash
# Compare model confidence on a suspected member vs a random input
python3 - << 'PY'
import json, urllib.request
ENDPOINT = "https://target.example/api/predict"
TOKEN = "REPLACE_WITH_TEST_TOKEN"
def predict(x):
    req = urllib.request.Request(ENDPOINT, data=json.dumps({"features": x}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)
suspect = [0.51, 0.22, 0.88, 0.11]   # record suspected in training set
random_in = [0.13, 0.77, 0.31, 0.55] # random record
for label, x in [("suspect", suspect), ("random", random_in)]:
    out = predict(x)
    print(label, "->", str(out)[:160])
PY
# Members often get higher confidence or lower loss; a consistent gap
# across many samples is the finding, not one query.
```

## Edge cases

- The API returns only labels with no scores. Extraction is still
  possible but needs far more queries; note the higher cost as a
  mitigating factor.
- Rate limits or CAPTCHAs appear mid probe. Stop and report the
  effective defense instead of evading it.
- The model is an ensemble or behind randomization. Measure output
  stability across repeated identical queries first.
- Concept drift retrains the model weekly. A stolen copy decays, which
  lowers the business impact; say so honestly.
- The endpoint requires per query payment. Track spend against the
  agreed budget and stop before overrunning it.

## Escalation

- Label only outputs: switch to decision boundary walking with small
  input perturbations to map the boundary precisely.
- Defended with output rounding: test whether rounding is coarse enough
  to matter by comparing substitute accuracy with and without it.
- Query budget too small for a full substitute: demonstrate the trend
  instead, showing accuracy climbing with query count on a small slice.
- Membership inference inconclusive on one record: test a batch of
  suspected members and report the statistical gap.

## Detection and defender view

Defenders see extraction as systematic querying: uniform coverage of the
input space, high query volume from few accounts, and repeated near
duplicate inputs for boundary mapping. Detect with per account query
budgets, alerts on grid like access patterns, and output minimization
(return labels, not full probability vectors). Stronger defenses add
proof of work per query, watermarking of outputs, and monitoring for
substitute models that mirror the victim's behavior. Differential
privacy during training blunts membership inference.

## Key references

- MITRE ATLAS AML.T0024 (Exfiltrate Model).
- CWE-200 (Exposure of Sensitive Information): training data leakage.
- CWE-770 (Allocation of Resources Without Limits): unbounded querying.
- NIST AI 100-2e2025: model extraction and inference attacks.
