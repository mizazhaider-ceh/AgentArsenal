---
name: ai-incident-response
description: "Use when responding to a suspected security incident involving an AI system: a hijacked agent, a poisoned model, leaked prompts, or abusive use of inference infrastructure. Covers scoping, prompt and tool log collection, model rollback, and containment that accounts for non deterministic behavior. Also use when building an IR playbook that covers LLM specific scenarios."
version: 1.0.0
domain: ai-security
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, incident-playbooks, log-forensics]
tools:
  - name: Python
    version: 3.12
  - name: jq
    version: 1.7.1
---
AI incidents look different from server incidents: the attacker never
touches a shell, the evidence is in prompts and tool calls, and the
"vulnerability" may be the model's normal behavior under adversarial
input. This skill covers response for AI specific scenarios: scoping
what the model or agent did, collecting prompt and tool logs,
containing without destroying evidence, and recovering to a known good
model and prompt version.

## Quick Workflow

1. Declare the incident and freeze the AI surface: disable the agent's
   tool access or take the endpoint out of rotation.
2. Scope the blast radius: which users, sessions, tools, and data the
   model touched during the window.
3. Collect prompt logs, tool call logs, and retrieval logs for the
   window, plus the exact model and prompt versions.
4. Identify the attack path: direct injection, poisoned document, or
   abused tool, with the exact inputs.
5. Contain: revoke leaked keys, rotate secrets found in prompts, and
   roll back to the last known good model and prompt.
6. Eradicate the cause: remove poisoned documents, fix the access
   control, or tighten the tool scope.
7. Recover in stages: read only mode first, then tools with approvals,
   then full service.
8. Write the post incident review with detection gaps and new monitors.

## 1. Scoping and log collection

Prompts are the crime scene. Collect them before retention windows
expire.

```bash
# Pull prompt and tool logs for the incident window (example: JSONL store)
jq -c 'select(.ts >= "2026-10-22T14:00:00Z" and .ts <= "2026-10-22T16:00:00Z")' \
  /var/log/llm/prompts.jsonl > /tmp/ir/prompts_window.jsonl
wc -l /tmp/ir/prompts_window.jsonl

# Find sessions with tool calls the user never requested
jq -c 'select(.tool_calls != null and .user_requested_tools == false)' \
  /tmp/ir/prompts_window.jsonl | head -20

# List which documents were retrieved in the window (RAG incidents)
jq -r 'select(.retrieved_docs != null) | .retrieved_docs[]' \
  /tmp/ir/prompts_window.jsonl | sort | uniq -c | sort -rn | head -20
```

```bash
# Record exact model and prompt versions for reproducibility
cat /etc/ai-service/model_version.txt
git -C /opt/ai-service/prompts log --oneline -5
# Snapshot the current prompt set before rollback
cp -r /opt/ai-service/prompts /tmp/ir/prompts_snapshot_incident
```

## 2. Containment and recovery

Contain the agent first, then the model, then the data.

```bash
# 1. Revoke the agent's tool credentials immediately
# (example: disable the tool service account)
sudo usermod --lock agent-tools-svc
# or revoke the OAuth grant the agent uses
curl -s -X DELETE 'https://auth.internal/grants/agent-tools-svc' \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Rotate any secret that appeared in prompts or outputs
grep -rhoE "sk-[A-Za-z0-9]{20,}" /tmp/ir/prompts_window.jsonl | sort -u \
  > /tmp/ir/leaked_keys.txt
wc -l /tmp/ir/leaked_keys.txt
# rotate each key at its provider, then purge from logs per policy

# 3. Roll back model and prompt to last known good
cat /tmp/ir/last_known_good.txt  # maintained by the deploy pipeline
# redeploy that version, then re-enable in stages
```

Recover in stages and watch the new monitors: first serve with tools
disabled, then enable tools with human approval, then restore full
service only after the post incident review is scheduled.

## Edge cases

- Prompt logs are sampled, not complete. Note the sampling rate; the
  attack path may have gaps you cannot close.
- The model is hosted by a third party and you have no prompt logs.
  Scope from your application logs: what your app sent and received.
- The incident is ongoing abuse (spam, fraud) rather than a breach.
  Containment means rate limits and account bans, not forensics.
- Rollback changes model behavior and breaks pinned evaluations.
  Re-run the eval suite against the rolled back version before full
  recovery.
- Legal holds require keeping prompts that contain personal data.
  Coordinate with legal before purging anything.

## Escalation

- Attacker still active in sessions: kill sessions server side and
  force reauthentication for affected users.
- Poisoned document source unknown: quarantine the whole index and
  rebuild from versioned sources.
- Model weights suspected tampered: pull a fresh copy from the official
  publisher, verify the hash, and redeploy.
- Third party model misbehaving: open a sev case with the provider with
  your logged evidence, and fail over to a secondary provider.

## Detection and defender view

Mature AI monitoring watches for prompt injection signatures in inputs,
impossible tool call sequences, retrieval of unusual document sets, and
spikes in refusal rates or token spend. After an incident, add the
attack's exact patterns as detection rules: the poisoned document hash,
the injection phrasing, and the tool call chain. Keep an AI incident
playbook separate from the server playbook, with contact details for
the model provider and pre approved containment actions, because the
first hour of an AI incident is spent deciding what you are even
allowed to turn off.

## Key references

- NIST AI 100-2e2025: incident considerations for AI systems.
- OWASP Top 10 for LLM Applications: LLM09 Misuse scenarios.
- MITRE ATLAS: incident scoping for ML systems.
- Related skills: incident-response, incident-playbooks, log-forensics.
