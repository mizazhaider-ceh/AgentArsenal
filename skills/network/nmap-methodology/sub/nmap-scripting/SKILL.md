---
name: nmap-scripting
description: Use when you need nmap's scripting engine (NSE) to enumerate
  services deeply, check for known vulnerabilities, or gather application
  data on an authorized engagement. Covers script selection by category,
  safe versus intrusive scripts, targeted script runs, and interpreting
  script output honestly. Use when enumerating SMB, HTTP, or database
  services, when checking for famous CVEs quickly, or when you need
  structured findings from standard services.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
parent: nmap-methodology
requires: [nmap-methodology]
extends: []
relates: [recon-active, smb-enumeration]
tools:
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
---

The nmap scripting engine runs Lua scripts that do real enumeration:
listing SMB shares, grabbing HTTP titles, checking for specific CVEs. This
skill covers using NSE on authorized engagements with discipline: pick
scripts for the services you found, prefer safe scripts by default, and
treat script output as leads to verify, not as findings. Intrusive scripts
can crash services, so the category system exists for a reason.

## Quick Workflow

1. List the services from nmap-service-detection that deserve scripts.
2. Run default safe scripts first (`-sC`) on those services.
3. Add targeted scripts per service: SMB, HTTP, databases, TLS.
4. Run vulnerability-check scripts only against in-scope services.
5. Verify every positive by hand before reporting it.
6. Save script output with the scan for the report.

## 1. Safe default scripts

```bash
# Default script set: safe, useful, runs with version detection
nmap -sC -sV -p 22,80,443,445,3306 10.0.5.23 -oN /tmp/scripts_default.txt

# List scripts by category before running them
ls /usr/share/nmap/scripts/ | grep -E 'smb|http' | head -20
nmap --script-help smb-os-discovery | head -20

# Update the script database after nmap upgrades
nmap --script-updatedb
```

`-sC` is the everyday choice: it runs the `default` category, which the
nmap team keeps non-intrusive. Start here on every engagement.

## 2. Targeted service scripts

```bash
# SMB enumeration bundle (host is Windows or Samba)
nmap --script smb-os-discovery,smb-security-mode,smb-enum-shares,smb-enum-users \
  -p445 10.0.5.23 -oN /tmp/smb_enum.txt

# HTTP enumeration: titles, methods, headers
nmap --script http-title,http-methods,http-server-header \
  -p80,443,8080 10.0.5.23 -oN /tmp/http_enum.txt

# TLS quality snapshot
nmap --script ssl-cert,ssl-enum-ciphers -p443 10.0.5.23 -oN /tmp/tls.txt

# Database basics (no credentials needed for banner-level scripts)
nmap --script mysql-info -p3306 10.0.5.23 -oN /tmp/mysql.txt
```

Match scripts to discovered services. Running SMB scripts against a Linux
web server wastes time and litters logs; the service inventory from the
previous phase tells you exactly which scripts apply.

## 3. Vulnerability check scripts

```bash
# Famous-CVE checks: fast, read-only, high signal when positive
nmap --script vuln -p80,443 10.0.5.23 -oN /tmp/vuln_web.txt

# Single CVE checks when you suspect a specific issue
nmap --script smb-vuln-ms17-010 -p445 10.0.5.23 -oN /tmp/ms17010.txt
nmap --script http-vuln-cve2017-5638 -p8080 10.0.5.23 -oN /tmp/struts.txt

# Script arguments when a script needs tuning
nmap --script http-enum --script-args http-enum.basepath=/app/ \
  -p80 10.0.5.23 -oN /tmp/http_enum2.txt
```

Every `vuln` positive needs hand verification. Script checks are heuristic;
they false-positive on backported patches and custom builds. Confirm with
the service version and, where safe, a manual probe before the finding
goes in the report.

## Edge cases

- A script crashes or hangs on a weird service. Kill the run, rerun with
  that script excluded, and note the behavior; fragile services get
  manual treatment only.
- Script output is empty but the service is real. The script's probe did
  not match; try the manual equivalent (curl, smbclient) before moving
  on.
- Too many scripts slow the engagement. Scope scripts to the services
  that matter for the test objectives, not every open port.
- Scripts need credentials you do not have. Skip credentialed scripts
  unless the engagement provides accounts; note the gap.

## Escalation

- You need deeper SMB or HTTP enumeration than scripts give: switch to
  dedicated tools (smbclient, enum4linux, ffuf) and keep nmap for what
  it does best.
- A vuln script positive needs exploit confirmation: hand it to the
  exploitation phase with the exact script output attached, and get
  approval before touching the exploit.
- Custom script needed: write NSE in Lua only when no existing script
  fits, and test it against a lab target first.

## Detection and defender view

Defenders see NSE as distinctive follow-up traffic: SMB session setups,
HTTP requests for odd paths, and the probe patterns of vuln checks, all
from the scanning host. IDS signatures exist for the noisiest scripts.
Defenses are patching (so vuln scripts find nothing), SMB hardening, and
alerting on enumeration patterns. Script output is recon, not proof;
defenders know the difference too.

## Key references

- MITRE ATT&CK T1046 (Network Service Discovery).
- MITRE ATT&CK T1595.002 (Active Scanning: Vulnerability Scanning).
- nmap 7.98 NSE documentation and script library.
