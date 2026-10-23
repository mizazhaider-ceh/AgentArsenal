---
name: c2-payload-staging
description: Use when you need to prepare and stage C2 payloads for an
  authorized engagement or lab. Covers payload types and tradeoffs,
  staging server setup, integrity checks, and safe handling. Use when
  planning the delivery phase, when choosing between staged and stageless
  payloads, when the engagement needs reliable payload retrieval, or when
  building the lab payload library.
version: 1.0.0
domain: c2
lifecycle: stable
last_verified: 2026-10-23
parent: c2-fundamentals
requires: [c2-fundamentals]
extends: []
relates: [network-pivoting]
tools:
  - name: Python
    version: 3.12
  - name: OpenSSH
    version: 9.6
---

Payload staging is the logistics of C2: building the payload, hosting it
where the target can fetch it, and making sure what runs is what you
built. This skill covers staging on authorized engagements and in labs:
payload type choices, staging server setup, and integrity discipline. It
stops at the staging server; delivery vectors and execution belong to the
engagement's exploitation phases.

## Quick Workflow

1. Choose staged versus stageless based on the delivery constraints.
2. Build the payload for the exact target platform and test it in the
   lab.
3. Set up the staging server with access controls and logging.
4. Verify integrity: hash the payload at build and at fetch.
5. Stage the payload and test retrieval from a lab client.
6. Monitor the staging logs during the engagement.
7. Remove staged payloads at engagement end.

## 1. Staged versus stageless

```bash
# Stageless: everything in one payload. Bigger initial transfer,
# fewer network round trips, simpler opsec story.
# Staged: tiny initial loader fetches the real payload. Smaller
# initial transfer, but the staging fetch is a second detection chance.

# Decision guide:
# - Delivery limits size (macro, injection): staged
# - Network is heavily monitored: stageless (one transfer, then quiet)
# - Payload needs updating mid-engagement: staged (swap the stage)
```

Document the choice and the reason. The tradeoff is engagement-specific,
and the report should show it was considered.

## 2. Staging server setup

```bash
# Minimal staging server: HTTPS, client authentication, logging
mkdir -p /srv/stage && cd /srv/stage
python3 - <<'EOF'
# Concept: serve payloads only to expected clients.
# Production: use a real server with TLS, basic auth or client certs,
# and per-engagement credentials. Log every fetch with timestamp and IP.
print("Stage payloads here; serve over TLS with auth in production.")
EOF

# Hash every staged file at build time
sha256sum /srv/stage/* > /srv/stage/SHA256SUMS
cat /srv/stage/SHA256SUMS

# Verify from a lab client before the engagement
curl -s -u stage:changeme https://stage-infra.example/payload.bin \
  -o /tmp/test.bin && sha256sum /tmp/test.bin
```

The staging server must not serve payloads to the whole internet: require
authentication, allow-list expected source ranges where possible, and take
it down the day the engagement ends.

## 3. Payload handling discipline

```bash
# Build log: what was built, when, from what source, for which target
cat > /tmp/payload_build.log <<'EOF'
2026-10-23 payload.bin: windows/x64 https stager, lab-tested OK
2026-10-23 payload.elf: linux/x64 https stageless, lab-tested OK
EOF

# Never edit a staged payload in place: rebuild, rehash, redeploy
# Never reuse payloads across engagements: build fresh each time
```

Payloads are the most sensitive artifacts of the engagement: they are
functional malware by construction. Store them encrypted at rest, limit
access to the test team, and destroy working copies (not just the staged
ones) at the end.

## Edge cases

- The target cannot reach the staging server. Re-check egress from the
  target's position; staging is useless without a fetch path.
- The payload is flagged at fetch time. That is detection working;
  coordinate with the test lead on whether to adjust or to record the
  detection as the finding.
- Staging credentials leak. Rotate immediately and rebuild the payloads;
  a known staging URL is a liability.
- The engagement needs the payload updated mid-test. Version the stages
  (payload-v2.bin) rather than overwriting; the logs stay attributable.

## Escalation

- You need a custom payload type: build and lab-test it fully before
  the engagement window; untested payloads on production are
  unacceptable.
- Staging must survive the engagement: plan the takedown date at setup
  time and put it in the inventory file.
- Delivery keeps failing: the problem is usually the vector or the
  egress, not the staging; diagnose those before rebuilding payloads.

## Detection and defender view

Defenders see staging as downloads of unusual binaries from rare domains,
often with odd User-Agents or no browser headers, followed by execution.
EDR flags the payload at write or execute time. Defenses are web
filtering by reputation, EDR execution prevention, and alerting on
binary downloads outside software deployment channels. Staging over
compromised legitimate infrastructure is harder to spot, which is why
reputation and behavior both matter.

## Key references

- MITRE ATT&CK T1105 (Ingress Tool Transfer).
- MITRE ATT&CK T1608 (Stage Capabilities).
- NIST SP 800-115 (Technical Guide to Information Security Testing).
