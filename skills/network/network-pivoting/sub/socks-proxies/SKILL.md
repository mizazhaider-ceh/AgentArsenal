---
name: socks-proxies
description: Use when you need tool traffic routed through a compromised
  host without SSH on an authorized engagement. Covers pivoting tool
  selection, proxychains configuration, meterpreter-style routing
  concepts, and verifying tool behavior through proxies. Use when SSH
  forwarding is unavailable, when running scanners through a foothold,
  when chaining multiple pivots, or when tools need transparent proxying.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
parent: network-pivoting
requires: [network-pivoting]
extends: []
relates: [recon-active, c2-fundamentals]
tools:
  - name: Python
    version: 3.12
  - name: OpenSSH
    version: 9.6
---

SOCKS proxies route tool traffic through a foothold when SSH forwarding
is not available or not enough: scanners, web tools, and custom scripts
all work through a SOCKS chain. This skill covers proxy-based pivoting on
authorized engagements: getting a SOCKS server on the foothold, pointing
tools at it, and understanding what breaks through proxies. It complements
ssh-pivoting; use whichever fits the foothold's capabilities.

## Quick Workflow

1. Get a SOCKS server listening via the foothold (SSH dynamic forward,
   agent-based, or tool-provided).
2. Configure proxychains (or native SOCKS support) on your attack box.
3. Verify with a simple request before running heavy tools.
4. Run enumeration through the proxy, respecting its limits.
5. Chain proxies for multi-hop pivots when needed.
6. Tear down proxies at engagement end.

## 1. Getting the SOCKS server

```bash
# Option A: SSH dynamic forward (when SSH exists, see ssh-pivoting)
ssh -D 1080 -N -f user@foothold.example

# Option B: pure-Python SOCKS server on the foothold via your shell
# (upload a minimal stdlib SOCKS5 implementation, listen on 1080,
# connect back or bind as the network allows)

# Option C: framework-provided (post-exploitation agents often include
# SOCKS; use the engagement's approved tooling)

# Verify the proxy works with a trivial fetch
curl -s --socks5 127.0.0.1:1080 http://10.1.0.1/ -o /dev/null -w '%{http_code}\n'
```

Prefer the simplest working option. An SSH dynamic forward beats a custom
uploader in reliability every time; use the exotic options only when SSH
is truly unavailable.

## 2. Proxychains configuration

```bash
# /etc/proxychains4.conf (or ~/.proxychains/proxychains.conf)
# Use one proxy line per hop, in order:
# socks5 127.0.0.1 1080
# socks5 127.0.0.1 1081   (second hop, chained)

# Strict chaining for predictable multi-hop routing
# (edit the config: strict_chain, proxy_dns)

# Run tools through the chain
proxychains nmap -sT -T4 --top-ports 100 10.1.0.0/24
proxychains curl -s http://10.1.0.23:8080/ | head -10

# Tools with native SOCKS support skip proxychains (faster, cleaner)
# curl --socks5, ssh -o ProxyCommand, Burp upstream proxy
```

proxychains forces TCP connect behavior: UDP scans, SYN scans, and raw
sockets do not work through it. Plan the enumeration around that limit
(connect scans, application probes) instead of fighting it.

## 3. Multi-hop chains

```bash
# Two footholds deep: proxy on each, chain in proxychains config
# hop1: foothold1:1080 -> reaches 10.1.0.0/24
# hop2: via hop1, foothold2:1080 -> reaches 10.2.0.0/24
# proxychains routes: you -> 1080 -> 1081 -> target

# Verify each hop independently before chaining
curl -s --socks5 127.0.0.1:1080 http://10.1.0.5/ -o /dev/null -w 'hop1: %{http_code}\n'
curl -s --socks5 127.0.0.1:1081 http://10.2.0.5/ -o /dev/null -w 'hop2: %{http_code}\n'
```

Each hop multiplies latency and failure modes. Keep chains to two hops
where possible; three-hop chains are for lab demos and patient operators.

## Edge cases

- DNS leaks around the proxy. Enable proxy_dns in proxychains so names
  resolve through the far end; leaked DNS queries reveal your targets.
- The tool ignores proxychains (static binary, Go without hook).
  Use the tool's native proxy settings or pick an alternative tool.
- Throughput collapses on big transfers. Proxies are for enumeration
  and light exfiltration proofs, not bulk data movement; plan large
  transfers differently.
- Authentication on the proxy. Some SOCKS servers need credentials;
  configure them in proxychains rather than running open proxies.

## Escalation

- No SOCKS option works on the foothold: fall back to
  port-forwarding-chains for single-service access.
- You need many tools through the proxy constantly: set up the
  proxychains config once, document it, and share it with the team.
- The engagement needs quieter pivoting: reduce scan intensity through
  the proxy; proxied scans are already slower, which helps.

## Detection and defender view

Defenders see proxied pivoting as the foothold making connections it
never normally makes, to internal hosts in odd patterns, often with
timing that matches tool behavior rather than human behavior. EDR sees
the proxy process and its children. Defenses are egress filtering from
servers, alerting on server-to-server connections outside the normal
profile, and monitoring for proxy processes on compromised hosts.

## Key references

- MITRE ATT&CK T1090 (Proxy).
- MITRE ATT&CK T1090.002 (Proxy: External Proxy).
- MITRE ATT&CK T1090.003 (Proxy: Multi-hop Proxy).
