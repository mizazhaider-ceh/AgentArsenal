---
name: port-forwarding-chains
description: Use when you need specific internal services exposed through
  one or more footholds on an authorized engagement. Covers local, remote,
  and chained port forwards, forward mapping discipline, and troubleshooting
  broken chains. Use when only one or two internal services matter, when
  full proxying is overkill, when chaining through multiple compromised
  hosts, or when giving a teammate access to an internal service.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
parent: network-pivoting
requires: [network-pivoting]
extends: []
relates: [c2-fundamentals, recon-active]
tools:
  - name: OpenSSH
    version: 9.6
  - name: socat
    version: 1.7
  - name: Python
    version: 3.12
---

Port forwarding chains expose individual internal services through
footholds: precise, low-noise, and easy to reason about. This skill
covers building forward chains on authorized engagements: local and
remote forwards, multi-hop chains, non-SSH forwarders for constrained
hosts, and the mapping discipline that keeps chains debuggable. Use it
when you know exactly which services you need; use SOCKS proxies when
you are still exploring.

## Quick Workflow

1. List the exact internal services you need (host, port, purpose).
2. Build the shortest chain to each: direct forward where possible.
3. Assign local ports systematically and write the map down.
4. Verify each forward end to end before relying on it.
5. Run the service-specific tools against the local ports.
6. Tear down every forward at engagement end.

## 1. Building the chain

```bash
# Single hop: internal web app on your localhost:8080
ssh -L 8080:10.1.0.23:80 -N -f user@foothold.example

# Two hops: foothold1 reaches foothold2's network
# Hop A: local 2222 -> foothold2's SSH via foothold1
ssh -L 2222:10.1.0.5:22 -N -f user@foothold1.example
# Hop B: through hop A, forward the deep service
ssh -p 2222 -L 8080:10.2.0.9:80 -N -f user@localhost

# Remote forward: expose your attack-box tool to the internal network
ssh -R 8080:127.0.0.1:8080 -N -f user@foothold.example
```

```bash
# Port map (keep this in your notes, it is the chain's documentation)
# localhost:8080 -> 10.1.0.23:80  (intranet web)
# localhost:8443 -> 10.1.0.24:443 (admin panel)
# localhost:2222 -> 10.1.0.5:22   (second hop SSH)
```

Write the map before building. Chains built from memory develop port
collisions and mystery forwards that nobody can tear down later.

## 2. Non-SSH forwarders

```bash
# socat relay on a foothold without SSH forwarding
# On foothold: listen 8080, forward to internal 10.1.0.23:80
socat TCP-LISTEN:8080,fork TCP:10.1.0.23:80 &

# Then SSH local-forward to the relay (or reach it directly)
ssh -L 8080:127.0.0.1:8080 -N -f user@foothold.example

# Chisel-style tunneling concepts apply the same way with any
# forwarder the engagement approves; the chain logic is identical
```

Constrained footholds (no SSH, no forwarding allowed) still pivot with a
simple relay binary. The chain gets longer, but each link stays simple
and testable.

## 3. Verification and troubleshooting

```bash
# Verify each link independently, from the outside in
curl -s http://127.0.0.1:8080/ -o /dev/null -w 'end-to-end: %{http_code}\n'

# Which forward is broken? Test at each hop
ssh user@foothold.example 'curl -s http://10.1.0.23/ -o /dev/null -w "%{http_code}\n"'
# If the foothold reaches it but you do not, your forward is broken;
# if the foothold cannot, the target or route is the problem

# List your active forwards
ps aux | grep -E 'ssh.*-L|ssh.*-R' | grep -v grep
```

Debug outside-in: confirm the far end first, then each forward link.
Most chain failures are a dead far end or a typo in the map, not SSH
itself.

## Edge cases

- GatewayPorts blocks remote forwards from binding publicly. Remote
  forwards bind to localhost on the foothold by default; binding wider
  needs the foothold's sshd_config cooperation.
- Forwards die silently. Wrap critical forwards in autossh or a simple
  loop that re-establishes them, and alert yourself when they drop.
- The same local port is needed twice. Extend the map (8080, 8081,
  8082) rather than reusing; collisions waste more time than the extra
  ports cost.
- Firewall between footholds blocks the relay port. Pick relay ports
  that the inter-foothold path allows (443 and 53 are the usual
  candidates).

## Escalation

- The chain needs more hops than is sane: reconsider; three SSH hops
  with forwards is usually a sign to get a better foothold instead.
- A forward must persist across days: document it as infrastructure,
  monitor it, and include it in the teardown checklist.
- You need the whole subnet, not services: switch to socks-proxies;
  forwards are the wrong tool for exploration.

## Detection and defender view

Defenders see forward chains as SSH sessions with channel opens to
internal hosts, relay processes (socat) on servers that should not run
them, and internal services accessed from unexpected sources. Each link
is visible on its own host, which is why chains are noisier than they
feel. Defenses are disabling forwarding where unneeded, monitoring for
relay binaries on servers, and alerting on SSH channel patterns.

## Key references

- MITRE ATT&CK T1572 (Protocol Tunneling).
- MITRE ATT&CK T1090 (Proxy).
- OpenSSH 9.6 manual: -L, -R, -D forwarding options.
