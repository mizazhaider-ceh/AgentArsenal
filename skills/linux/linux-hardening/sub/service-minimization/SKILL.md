---
name: service-minimization
description: Use when reducing a Linux server's attack surface by
  disabling unneeded services. Covers service inventory, safe disable
  procedures, socket-activated services, and verifying the reduced
  footprint. Use when hardening a new server, when the port scan found
  surprises, when decommissioning legacy services, or when setting the
  minimal-service standard.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
parent: linux-hardening
requires: [linux-hardening]
extends: []
relates: [nmap-methodology, privesc-linux]
tools:
  - name: Python
    version: 3.12
---

Every running service is attack surface: minimization turns off what the
server does not need. This skill covers the service reduction workflow:
inventorying what runs, deciding what stays, disabling safely, and
proving the footprint shrank. It is the highest-return hardening step
after SSH: fewer services, fewer vulnerabilities, fewer privesc paths.

## Quick Workflow

1. Inventory running services and listening sockets.
2. Classify each: required, questionable, removable.
3. Check dependencies before disabling anything.
4. Disable and stop the removables, one change at a time.
5. Verify: listening sockets shrink, functionality holds.
6. Document the minimal set as the server's standard.

## 1. Inventory

```bash
# Running services via systemd
systemctl list-units --type=service --state=running | head -30

# Listening sockets: the network-visible truth
ss -tulnp | grep LISTEN

# Enabled but not running (will start at boot: the real list)
systemctl list-unit-files --type=service --state=enabled | head -30

# Socket-activated services hide from the running list; check sockets too
systemctl list-units --type=socket --state=running | head -10
```

The listening sockets are the attack surface that matters to the
network; the enabled list is what survives a reboot. Both must shrink.
A service that is stopped but enabled will be back after the next
reboot, which is how "minimized" servers quietly regrow.

## 2. Safe disable procedure

```bash
# Per service: check what depends on it first
systemctl list-dependencies --reverse cups.service 2>/dev/null | head -10

# Stop, then disable (one service at a time, verify between)
systemctl stop cups.service
systemctl disable cups.service
# Verify the socket closed and nothing broke
ss -tulnp | grep -c LISTEN

# Mask services that must never start (stronger than disable)
systemctl mask telnet.socket

# Common removables on servers (verify each against the role):
# cups, avahi-daemon, bluetooth, rpcbind (unless NFS), telnet, rsh
```

Change one service at a time and verify the server's function after
each. Batch-disabling ten services and then debugging is how outages
happen; the discipline is slow but safe.

## 3. Verification

```bash
# Before and after: the listening socket diff is the proof
ss -tulnp | grep LISTEN | awk '{print $5}' | sort > /tmp/ports_after.txt
diff /tmp/ports_before.txt /tmp/ports_after.txt

# Confirm disabled services stay dead across a reboot (test in maintenance)
# After reboot:
systemctl list-units --type=service --state=running | wc -l
ss -tulnp | grep -c LISTEN

# Record the minimal set per server role
cat > /tmp/minimal_web.txt <<'EOF'
Allowed: sshd, nginx, php-fpm, cron, rsyslog, fail2ban
Everything else: disabled and masked
EOF
```

The minimal set per role becomes the standard: new servers get exactly
these services, and drift from the standard is a finding. Re-run the
inventory on a schedule; services creep back with package updates.

## Edge cases

- A "removable" service is needed by a cron job or a monitoring
  agent. The dependency check catches most; the functional test after
  each disable catches the rest.
- The server role is unclear. Do not minimize what you do not
  understand; document the uncertainty and minimize the obvious only.
- Containers need minimization too. The image should contain only the
  application and its runtime; the same inventory applies inside.
- Disabling breaks package updates. Some updaters expect services
  present; test the update path after minimization.

## Escalation

- The port scan still shows unexpected listeners: trace each to its
  service and justify or remove it; unexplained listeners are
  findings.
- Minimization needs to scale: encode the minimal set in the image
  build or config management, with the inventory check as a scheduled
  audit.
- A disabled service is required after all: re-enable deliberately,
  document why, and add it to the role's allowed list.

## Detection and defender view

For defenders, service minimization is continuous: the scheduled
inventory diff against the standard catches both drift and compromise
(new listeners from attacker tooling). Alert on new listening sockets
on servers; legitimate changes go through change control, so anything
else is suspicious. Minimization makes the network monitoring simpler
because the baseline is small and known.

## Key references

- CIS Benchmarks: services sections per distribution.
- NIST SP 800-123 (server security).
