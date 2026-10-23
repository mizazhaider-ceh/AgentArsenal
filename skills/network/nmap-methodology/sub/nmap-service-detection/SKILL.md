---
name: nmap-service-detection
description: Use when ports are mapped and you need nmap to identify the
  services, versions, and operating systems behind them on an authorized
  engagement. Covers version detection intensity, OS fingerprinting, the
  aggressive -A mode, and verifying uncertain results by hand. Use when
  prioritizing version-specific exploits, when building the asset inventory,
  when banners are hidden or faked, or when a service label needs proof.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
parent: nmap-methodology
requires: [nmap-methodology]
extends: []
relates: [recon-active]
tools:
  - name: nmap
    version: 7.98
  - name: curl
    version: 8.5
  - name: Wireshark
    version: 4.2
---

Service detection turns open ports into named services with versions, and
OS detection turns hosts into platforms. This skill covers nmap's
identification engine on authorized engagements: version probes, intensity
control, OS fingerprinting, and hand verification when nmap is unsure. The
output feeds exploit selection, so accuracy here decides the quality of
everything after.

## Quick Workflow

1. Take the open-port list from nmap-port-scanning.
2. Run version detection at default intensity on those ports.
3. Raise intensity on ports that matter and came back uncertain.
4. Run OS detection and record confidence levels.
5. Verify every uncertain or surprising result by hand.
6. Write the final service and OS inventory with evidence notes.

## 1. Version detection

```bash
# Version scan on known-open ports (faster than re-scanning everything)
nmap -sV -p 22,80,443,3306,3389,8080 10.0.5.23 -oN /tmp/ver.txt

# Raise intensity for stubborn services (1-9, default 7)
nmap -sV --version-intensity 9 -p 8080 10.0.5.23 -oN /tmp/ver_hi.txt

# Lower intensity when the target is fragile
nmap -sV --version-intensity 3 -p 22,80,443 10.0.5.23 -oN /tmp/ver_lo.txt

# All probes against one odd port, with trace to see what nmap tried
nmap -sV --version-all -p 9999 --packet-trace 10.0.5.23 -oN /tmp/ver_all.txt
```

Higher intensity sends rarer probes and takes longer; use 9 only on the
ports where the version actually changes your next step.

## 2. OS detection

```bash
# OS fingerprinting with guess output for near matches
nmap -O --osscan-guess 10.0.5.23 -oN /tmp/os.txt

# The aggressive bundle: OS, versions, scripts, traceroute in one run
# (noisy; use on small scopes or with permission)
nmap -A -T4 10.0.5.23 -oA /tmp/aggressive

# Limit OS detection when only the platform family matters
nmap -O --osscan-limit 10.0.5.0/24 -oN /tmp/os_net.txt
```

OS detection needs at least one open and one closed TCP port. All-filtered
hosts cannot be fingerprinted this way; note it and move to service
clues.

## 3. Hand verification

```bash
# nmap says "unknown": grab the banner yourself
(echo; sleep 1) | timeout 5 nc 10.0.5.23 9999 | head -5

# HTTP service with a generic label: headers and error pages tell more
curl -s -I http://10.0.5.23:8080/ | head -10
curl -s http://10.0.5.23:8080/does-not-exist | head -20

# TLS services: the certificate names the organization and sometimes the product
echo | timeout 5 openssl s_client -connect 10.0.5.23:8443 2>/dev/null \
  | openssl x509 -noout -subject -issuer

# Compare nmap's guess against the handshake in Wireshark when it matters
```

Never report a version you did not verify when the version drives an
exploit choice. "nmap guessed X with 80 percent confidence, banner says Y"
is an honest inventory line; a bare guess presented as fact is not.

## Edge cases

- Banners are faked or stripped. Behavior probes (error pages, protocol
  quirks) beat banner strings; fingerprint the behavior, not the label.
- The service is behind a load balancer. The version is the balancer's;
  test backend behavior through Host header variation if in scope.
- Version detection crashes a fragile service. Stop, note the probe, and
  finish that service by hand with the gentlest possible requests.
- Containers report the host kernel. Distinguish kernel (host) from
  userland (container) in the inventory; exploits usually target userland.

## Escalation

- You need proof for a version-specific exploit: capture the banner bytes
  and the nmap probe log, and keep both with the finding.
- OS stays unknown after all probes: report unknown with the full
  evidence list; an honest unknown beats a confident wrong guess.
- The inventory must merge with other tools: parse the XML output into
  your tracker rather than retyping, to avoid transcription errors.

## Detection and defender view

Defenders see version detection as follow-up connections to open ports
carrying nmap's distinctive probe payloads, which IDS signatures match.
OS detection adds the odd-flag probe sequence. Banner grabbing shows in
service logs. Defenses are IDS coverage, banner minimization, and keeping
versions current so accurate identification finds nothing exploitable.

## Key references

- MITRE ATT&CK T1082 (System Information Discovery).
- MITRE ATT&CK T1518 (Software Discovery).
- nmap 7.98 documentation: version detection, OS detection.
