---
name: incident-containment-playbooks-host-isolation
description: Use when you must cut an affected host off from the
  network during an authorized incident response without destroying
  forensic state. Covers Linux isolation with iptables 1.8 and
  nftables, Windows isolation with Windows Firewall rules, EDR
  network containment via Velociraptor 0.72, keeping forensic and
  management access working through the isolation, validating the
  isolation, and documenting each action. Use when the parent
  incident-containment-playbooks workflow calls for host isolation,
  when a host is actively communicating with attacker infrastructure,
  or when preparing tested isolation runbooks.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-containment-playbooks
requires: [incident-containment-playbooks]
extends: []
relates: [incident-containment-playbooks]
tools:
  - name: iptables
    version: 1.8
  - name: Velociraptor
    version: 0.72
  - name: osquery
    version: 5.12.1
---

Host isolation disconnects a compromised machine from everything
except your security tooling, while leaving it powered on so memory
and disk state survive for forensics. It is the most common
containment action and the easiest to get subtly wrong: too loose and
the attacker keeps a channel, too tight and you lose the EDR
telemetry you need. This sub-skill covers the recipes, the
validation, and the exceptions. Authorized incident response only.

## Quick Workflow

1. Confirm the host is in scope and the incident commander approved
   isolation.
2. Capture volatile state first (connections, processes) per the
   evidence playbook.
3. Apply the isolation rules for the platform, allowing only SIEM,
   EDR, and management networks.
4. Validate from the host: attacker channels fail, security
   tooling still checks in.
5. Validate from the network: no unexpected flows to or from the
   host.
6. Log the action with timestamp, host, method, and ticket id.
7. Monitor the isolated host for reconnection attempts.
8. Plan the exit: isolation ends at eradication, not before.

## 1. Linux isolation with iptables

```bash
# Define the allowed destinations: SIEM, EDR, and your forensics jump host
SIEM=203.0.113.10
EDR=203.0.113.11
JUMP=203.0.113.12

# Save the current ruleset first so you can restore it
iptables-save > /evidence/INC-2026-1042/iptables-before.rules

# OUTPUT chain: allow security tooling and loopback, drop the rest
iptables -F OUTPUT
iptables -A OUTPUT -d $SIEM -j ACCEPT -m comment --comment "INC-2026-1042"
iptables -A OUTPUT -d $EDR -j ACCEPT -m comment --comment "INC-2026-1042"
iptables -A OUTPUT -d $JUMP -p tcp --dport 22 -j ACCEPT -m comment --comment "INC-2026-1042"
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -j DROP

# INPUT chain: allow established management SSH, drop the rest
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -s $JUMP -p tcp --dport 22 -j ACCEPT -m comment --comment "INC-2026-1042"
iptables -A INPUT -j DROP

iptables -L -n -v --line-numbers | head -25
```

Example output shape:

```
Chain OUTPUT (policy ACCEPT 0 packets, 0 bytes)
num   pkts bytes target     prot opt in     out     source      destination
1        0     0 ACCEPT     all  --  *      *       0.0.0.0/0   203.0.113.10
2        0     0 ACCEPT     all  --  *      *       0.0.0.0/0   203.0.113.11
3        0     0 ACCEPT     tcp  --  *      *       0.0.0.0/0   203.0.113.12   tcp dpt:22
4        0     0 ACCEPT     all  --  *      lo      0.0.0.0/0   0.0.0.0/0
5        0     0 DROP       all  --  *      *       0.0.0.0/0   0.0.0.0/0
```

DNS will fail for the host (no resolver allowed), which is intended:
name resolution is a common exfiltration channel. If the EDR needs
DNS, allow UDP 53 to your internal resolver only, and log it.

## 2. Linux isolation with nftables

```bash
# nftables equivalent for newer distributions
nft flush ruleset  # CAREFUL: only on the isolated host, ruleset saved first
nft add table inet ir
nft add chain inet ir output { type filter hook output priority 0 \; }
nft add rule inet ir output ip daddr 203.0.113.10 accept
nft add rule inet ir output ip daddr 203.0.113.11 accept
nft add rule inet ir output oif lo accept
nft add rule inet ir output drop
nft list ruleset
```

Know which firewall your fleet uses before the incident. Running
iptables commands on an nftables-only host silently does nothing if
the compatibility layer is absent.

## 3. Windows isolation with Windows Firewall

```powershell
# Run as administrator. Save current config first.
netsh advfirewall export "C:\Evidence\INC-2026-1042\fw-before.wfw"

# Allow the security stack outbound
New-NetFirewallRule -DisplayName "IR-INC1042-allow-SIEM" -Direction Outbound `
  -RemoteAddress 203.0.113.10 -Action Allow -Profile Any
New-NetFirewallRule -DisplayName "IR-INC1042-allow-EDR" -Direction Outbound `
  -RemoteAddress 203.0.113.11 -Action Allow -Profile Any

# Allow RDP/WinRM from the jump host only, for forensic access
New-NetFirewallRule -DisplayName "IR-INC1042-allow-jump-in" -Direction Inbound `
  -RemoteAddress 203.0.113.12 -Action Allow -Profile Any

# Deny everything else outbound
New-NetFirewallRule -DisplayName "IR-INC1042-deny-out" -Direction Outbound `
  -Action Block -Profile Any

Get-NetFirewallRule -DisplayName "IR-INC1042-*" | Select-Object DisplayName, Enabled
```

Test RDP or WinRM from the jump host immediately; a typo in the
allow rule locks you out of your own isolated host, which is
embarrassing and slows the response.

## 4. EDR network containment

Most EDR platforms offer one-click network isolation that is more
reliable than hand-written rules and reversible from the console.
Prefer it when available:

```bash
# Velociraptor: quarantine a host via the API (example pattern)
# In practice use your EDR console: select host > Network isolate > confirm
# Velociraptor hunt to verify the agent still checks in after isolation
velociraptor --config server.config.yaml query \
  "SELECT client_id, last_seen FROM clients() WHERE hostname = 'web-03'"
```

EDR isolation usually allows the agent's own traffic by design,
which solves the "too tight" problem automatically. The tradeoff is
dependence on the EDR control plane; if the attacker may have
compromised it, use host firewall rules instead.

## 5. Keeping forensic access working

Isolation must not cut off the responders. Checklist per isolated
host:

- SSH or WinRM from the jump host: tested, working.
- EDR agent checking in: confirm in the console.
- Syslog forwarding to the SIEM: confirm events still arrive.
- Memory capture path: confirm you can run the capture tool and
  exfiltrate the image to evidence storage.

```bash
# From the jump host: verify you can still reach the isolated host
ssh -o ConnectTimeout=5 ir@web-03 "hostname; uptime"
# From the SIEM: confirm events still arriving
# (check the last event timestamp for web-03 in your SIEM)
```

If forensic access fails, loosen precisely: add one allow rule for
the needed flow, log it, and re-validate. Never remove the whole
isolation to "make things easier".

## 6. Validating the isolation

```bash
# On the isolated host: attacker channels must fail
curl -m 5 https://example.com ; echo "exit: $?"
# Expected: timeout, exit 28
ping -c1 8.8.8.8 ; echo "exit: $?"
# Expected: no reply

# Security tooling must still work
curl -m 5 https://203.0.113.11/health ; echo "exit: $?"
# Expected: 200 or the EDR's expected response

# From the network: watch for any flows bypassing the rules
# (on the switch or firewall: filter for the host's IP for 5 minutes)
```

Also verify the malware's known C2 specifically: if threat intel
says it beacons to 198.51.100.23, confirm that flow is dead. A host
that cannot reach the internet but can still reach a hardcoded IP
you forgot to block is not isolated.

## Edge cases

- The host has two network interfaces and you only firewalled one.
  Enumerate interfaces first (`ip addr`) and apply rules to all,
  or isolate at the switch port instead.
- IPv6 provides a bypass around IPv4-only rules. Write both
  families (ip6tables) or disable IPv6 on the host during the
  incident.
- The attacker has a scheduled task that reverts firewall rules.
  Monitor the ruleset (`iptables -L` on a loop or EDR file
  integrity), and treat rule reversion as evidence of active
  persistence.
- The host is a virtual machine. Hypervisor-level network
  disconnect is cleaner than in-guest rules and cannot be reverted
  by guest malware; prefer it when available.
- Isolation breaks the application so badly that the business
  demands reconnection. The commander decides; the compromise is
  usually a narrower allow-list for the specific business flow,
  with full packet capture on it.
- The EDR agent dies on the isolated host. You lose visibility;
  fall back to host firewall rules plus switch-level capture, and
  note the visibility gap.

## Escalation

- Isolation does not stop the malicious activity (encryption
  continues, beacons continue). The host may have an out-of-band
  channel (second NIC, cellular modem, BMC); investigate the
  hardware path, not just the OS.
- Multiple hosts need simultaneous isolation. Script the
  iptables and firewall commands and run them via your
  configuration management or Velociraptor in one wave;
  sequential isolation lets the attacker move.
- The isolated host holds the only copy of critical data with no
  backup. Involve the business owner before any action that risks
  the data, including memory capture on an unstable host.
- You suspect the attacker is watching your response (counter-IR).
  Coordinate the isolation wave out-of-band and execute
  simultaneously to deny them reaction time.

## Detection and defender view

Host isolation is a response action, but its effectiveness depends
on peacetime preparation: firewall tooling standardized across the
fleet, EDR on every host, and tested runbooks so the 3 AM isolation
takes minutes, not an hour of man-page reading. Measure time from
detection to isolation as a core metric. The strategic view: hosts
that are already segmented need less dramatic isolation, which is
why network segmentation in peacetime pays off during incidents.

## Key references

- Parent playbook: incident-containment-playbooks (this repo)
- NIST SP 800-61 Rev. 2: https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final
- iptables documentation: https://www.netfilter.org/documentation/
- nftables wiki: https://wiki.nftables.org/
- Velociraptor docs: https://docs.velociraptor.app/
- MITRE ATT&CK T1562 (Impair Defenses): https://attack.mitre.org/
