---
name: ai-supply-chain
description: "Use when reviewing the supply chain of an AI system on an authorized assessment: model weights, datasets, base images, and third party integrations. Covers model provenance checks, poisoned dataset detection, dependency review for ML pipelines, and signing of artifacts. Also use when a team adopts a new open weight model and wants to know what trust they are inheriting."
version: 1.0.0
domain: ai-security
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [cicd-security, devsecops-pipeline, secure-coding]
tools:
  - name: Python
    version: 3.12
  - name: Git
    version: 2.47
---
AI systems inherit trust from everywhere: the base model weights, the
fine tuning dataset, the container image, and every plugin. A backdoored
weight file or a poisoned dataset compromises everything built on top.
This skill covers authorized supply chain review for AI: verifying model
provenance, scanning datasets for poisoning, auditing ML dependencies,
and checking that artifacts are signed and pinned.

## Quick Workflow

1. Inventory every AI artifact: base models, fine tunes, embeddings,
   datasets, and the code that loads them.
2. Verify provenance: where each weight file came from, its hash, and
   whether the publisher signs releases.
3. Scan datasets for poisoning: label flips, trigger phrases, and
   statistical outliers in the training data.
4. Audit ML dependencies for known vulnerable versions and typosquats.
5. Check artifact integrity: pinned versions, hash locks, and signature
   verification in the load path.
6. Review third party integrations: plugins, tool servers, and hosted
   inference endpoints the app trusts.
7. Confirm no training on secrets: scan datasets for API keys and
   personal data.
8. Report each inherited trust decision with its evidence.

## 1. Model provenance and integrity

A weight file from an unofficial mirror is an unreviewed binary running
in your stack. Verify it like one.

```bash
# Record exact model identifiers and hashes
python3 - << 'PY'
import hashlib
path = "/models/team-llm-v3.safetensors"
h = hashlib.sha256()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
print("sha256:", h.hexdigest())
PY

# Check the model card source is the official publisher account
curl -s 'https://huggingface.co/api/models/org/team-llm-v3' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('author'), d.get('sha'), d.get('gated'))"
```

```bash
# Scan a model repo clone for suspicious files (not just weights)
git clone --depth 1 https://huggingface.co/org/team-llm-v3 /tmp/model-check
find /tmp/model-check -type f | head -30
grep -ri "exec\|subprocess\|socket" /tmp/model-check --include="*.py" | head -10
# Pickle based formats (.pt, .bin, .pkl) can execute code on load;
# prefer safetensors and flag any pickle loading path.
grep -rn "torch.load\|pickle.load" /tmp/model-check --include="*.py" | head -10
```

## 2. Dataset poisoning screen

Poisoned datasets plant backdoors or bias. Screen before training, not
after deployment.

```python
#!/usr/bin/env python3
"""Dataset screen: flags label skew, trigger phrases, and secrets."""
import json, re, collections

rows = [json.loads(l) for l in open("/data/finetune.jsonl")]
print("rows:", len(rows))

labels = collections.Counter(r.get("label") for r in rows)
print("label distribution:", dict(labels.most_common(10)))

triggers = ["[TRIGGER]", "cf92", "ignore previous", "http://"]
for t in triggers:
    hits = sum(1 for r in rows if t in json.dumps(r).lower())
    if hits:
        print(f"trigger phrase {t!r}: {hits} rows")

secret_re = re.compile(r"(sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}|-----BEGIN .*PRIVATE KEY-----)")
leaks = sum(1 for r in rows if secret_re.search(json.dumps(r)))
print("rows containing secret-like strings:", leaks)
```

```bash
# Audit Python ML dependencies for known bad versions
pip index versions torch 2>/dev/null | head -3
python3 -m pip list --format=freeze 2>/dev/null | grep -i -E "torch|transformers|numpy|pillow" | head -10
# Cross check installed versions against the lock file; any drift is a finding
diff <(python3 -m pip freeze | sort) <(sort /app/requirements.lock) | head -20
```

## Edge cases

- The model is gated and the hash is not published. Record the download
  date, source URL, and account used; provenance is weaker and the
  report should say so.
- Datasets are too large to scan fully. Scan a random sample plus all
  rows matching trigger patterns, and state the coverage.
- Quantized or merged models cannot be diffed against the original.
  Treat them as new artifacts and verify the party that produced them.
- The team trains on user feedback data. That is an active poisoning
  channel; it needs moderation and rate limits, not just a one time
  scan.

## Escalation

- Provenance cannot be verified: recommend re-downloading from the
  official publisher over a pinned commit hash and re-hashing.
- Poisoning suspected but not proven: train a canary model on a clean
  subset and compare behavior on trigger inputs.
- Dependency audit is inconclusive: build a software bill of materials
  for the training image and review it with the platform team.
- Third party inference API: shift the review to data handling, logging,
  and contract terms, since weights cannot be inspected.

## Detection and defender view

Defenders see supply chain attacks as unexpected weight file changes,
training jobs pulling from new sources, and model behavior shifts after
an update. Detect with artifact hashing in CI, alerts on model file
changes outside release windows, and behavioral regression tests that
run after every model swap. The durable fix is provenance by default:
pinned hashes, signed artifacts, approved model registries, dataset
versioning with review, and SBOMs for training and serving images.

## Key references

- CWE-829 (Inclusion of Functionality from Untrusted Control Sphere).
- CWE-494 (Download of Code Without Integrity Check).
- CWE-502 (Deserialization of Untrusted Data): pickle weight loading.
- OWASP Top 10 for LLM Applications: LLM08 Supply Chain Vulnerabilities.
- NIST AI 100-2e2025: data poisoning and supply chain sections.
