---
name: linux-systemd-security-journal-security
description: Use when securing systemd journal logging on Linux servers you
  administer. Covers journald.conf hardening (persistent storage, retention
  limits, rate limiting), sealing journals with Forward Secure Sealing for
  tamper evidence, forwarding to a central collector, restricting journal
  read access, detecting log tampering and gaps, and correlating with
  auditd. Defensive hardening mapped to MITRE ATT&CK T1070 Indicator Removal
  defenses; no exploitation content.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-systemd-security]
extends: []
parent: linux-systemd-security
relates: [linux-systemd-security, linux-log-intrusion-analysis, linux-hardening-baseline]
tools:
  - name: systemd
    version: 255
  - name: auditd
    version: 3.1
  - name: rsyslog
    version: 8.2312
---

Logs are the record an incident investigation depends on, which is exactly why attackers target them first (MITRE T1070, Indicator Removal). The systemd journal is the local log store on most servers, so its security properties (persistence, integrity, off-host copies, access control) decide whether you will have evidence when it matters. This sub-skill covers hardening journald defensively: configuration, tamper evidence via sealing, central forwarding, access controls, and tamper detection. For systems you own or administer; no exploitation content. The parent skill sets the strategy; this file is the journal-level reference.

## Quick Workflow

1. Set `Storage=persistent` and sane retention limits in `journald.conf`; verify with `journalctl --disk-usage`.
2. Configure rate limiting to survive log floods without losing the events that matter.
3. Enable Forward Secure Sealing (FSS) for tamper-evident journals on high-value hosts.
4. Forward journal entries to a central collector (syslog/TLS or your SIEM pipeline) and verify arrival.
5. Restrict journal read access: `systemd-journal` group membership only for those who need it.
6. Establish a tamper-detection routine: verify seals periodically and watch for journal gaps or rotations that do not match policy.
7. Document the retention and forwarding design so investigators know what exists and for how long.

## 1. journald.conf hardening

The journal defaults favor convenience; hardening favors survival. Set storage, retention, and rate limits explicitly.

```bash
grep -vE "^#|^$" /etc/systemd/journald.conf
journalctl --disk-usage
ls -ld /var/log/journal
```

Recommended settings in `/etc/systemd/journald.conf`:

```
Storage=persistent
SystemMaxUse=1G
SystemKeepFree=2G
MaxFileSec=1month
MaxRetentionSec=6month
RateLimitIntervalSec=30s
RateLimitBurst=10000
ForwardToSyslog=yes
```

`Storage=persistent` keeps logs across reboots in `/var/log/journal` (volatile otherwise, which loses everything on reboot). Retention bounds disk use while keeping enough history for investigations; size these to your incident response needs, not to disk convenience. Verify after `systemctl restart systemd-journald`: `journalctl --disk-usage` should show bounded use, and `/var/log/journal` should be root-owned, group `systemd-journal`, mode 2755.

## 2. Forward Secure Sealing for tamper evidence

FSS cryptographically seals journal files at intervals so that later tampering is detectable. It does not prevent deletion (nothing local can), but it makes silent modification evident.

```bash
journalctl --setup-keys 2>&1 | head -5
journalctl --verify 2>&1 | tail -10
```

`--setup-keys` generates a sealing key (guard the printed verification key: it goes to the investigators, not onto the host). `--verify` checks the seal chain and reports gaps or tampering. Schedule periodic verification from a trusted host, because verifying on the potentially compromised host itself has obvious limits. Note the operational cost: key management and verification tooling, which is why FSS fits high-value hosts (bastions, domain-adjacent systems, PCI scope) rather than every VM.

## 3. Forwarding to a central collector

The strongest journal protection is an off-host copy made in near real time. An attacker who owns the host can tamper with local journals; they cannot easily reach back into the collector.

```bash
grep -E "ForwardToSyslog|ForwardToWall" /etc/systemd/journald.conf
logger -p authpriv.info "journal-forward-test $(date +%s)"
sleep 2
```

With `ForwardToSyslog=yes`, journal entries flow to rsyslog/syslog-ng, which forwards over TLS to the central collector. Verify end to end: emit a test marker with `logger`, then confirm it appears in the collector within seconds. Monitor the forwarding path itself: a silent forwarding failure is a visibility outage, so alert on collector-side gaps per host (no events for N minutes means investigate, not assume quiet).

## 4. Access control on journal reads

Journal access is governed by group membership and ACLs on `/var/log/journal`. Keep the reader set small: every account that can read auth logs can study your authentication patterns.

```bash
getent group systemd-journal
ls -la /var/log/journal/ | head -5
journalctl --no-pager -n 3 2>&1 | head -5
```

Only members of `systemd-journal` (plus root and adm where applicable) should read the journal. Audit membership with `getent group systemd-journal` and remove accounts that do not need it. Unprivileged users see only their own logs by default, which is the correct posture; do not broaden it for convenience. On multi-tenant hosts, this boundary matters more, not less.

## 5. Detecting tampering and gaps

Tamper detection combines seal verification, gap analysis, and rotation auditing. No single check catches everything, so layer them.

```bash
journalctl --verify 2>&1 | grep -iE "fail|tamper|gap" | head -10
journalctl --list-boots | head -10
journalctl -p err --since "24 hours ago" | wc -l
```

`--verify` reports seal failures; `--list-boots` shows boot coverage (missing boots in the expected range suggest deletion or volatile-storage loss); unexpected drops in event volume suggest filtering or tampering. Cross-check against the central collector: entries present centrally but missing locally (beyond retention policy) indicate local tampering, while entries missing in both suggest the source never logged. Investigate either pattern.

## Edge cases

- `Storage=volatile` is the default on some minimal images and containers; logs vanish on reboot, which destroys forensic value, so explicitly set persistent storage on every host that matters and verify after provisioning.
- FSS verification keys must be stored off-host; a key kept on the same host it seals provides no tamper evidence against an attacker with root, which defeats the purpose.
- Rate limiting drops messages above the burst threshold; during a genuine incident flood (or an intentional flood by an attacker hiding activity), the dropped lines may be the important ones, so size bursts to real peak load and alert on rate-limit engagement.
- Forwarding over plain syslog without TLS exposes log contents (including potentially sensitive entries) on the network; always use TLS to the collector and validate certificates.
- Journal disk limits (`SystemMaxUse`) cause rotation that deletes the oldest logs; an attacker generating huge log volume can force rotation of the evidence, which is why central forwarding (not just local retention) is the real control.
- `journalctl --verify` on large journals is slow and I/O heavy; schedule verification off-peak and consider verifying only sealed high-value journals rather than the entire store.
- Time synchronization matters: journal entries with wrong timestamps (NTP failure, attacker clock manipulation) break correlation; monitor NTP health as part of log integrity, because unsynchronized logs are unreliable evidence.

## Escalation

- If seal verification fails or collector comparison shows local-only gaps, escalate to incident response immediately: treat it as potential Indicator Removal (T1070) until proven otherwise, and preserve the journal files before further investigation.
- If forwarding to the collector stops, escalate to the logging team as a visibility outage with incident-response priority; do not assume the host is simply quiet.
- If retention settings cannot meet the investigation window the business requires (compliance mandates a year, disk allows a month), escalate the capacity gap with costed options rather than silently accepting short retention.
- If FSS key management has no owner, do not deploy sealing: unowned keys get lost, and unverifiable seals are worse than no seals because they imply assurance that does not exist.

## Detection and defender view

Journal security serves detection in two directions. Outward: the journal is the data source for intrusion analysis (the log-intrusion-analysis skills consume it), so its integrity determines whether detections are trustworthy. Inward: tampering with the journal is itself a high-value signal, and defenders watch for it via seal verification, collector comparison, and auditd watches on `/var/log/journal`. MITRE T1070 (Indicator Removal) covers clearing logs, deleting files, and disabling logging; the defenses here (persistent storage, sealing, off-host forwarding, access control) are the corresponding mitigations. The defender's summary: assume local logs are hostile-witness testimony, trust but verify against the central copy, and treat any gap as evidence until explained.

## Key references

- MITRE ATT&CK T1070 Indicator Removal: https://attack.mitre.org/techniques/T1070/
- journald.conf manual: https://www.freedesktop.org/software/systemd/man/journald.conf.html
- journalctl manual (verify, sealing): https://www.freedesktop.org/software/systemd/man/journalctl.html
- Forward Secure Sealing details: https://www.freedesktop.org/software/systemd/man/journald.conf.html (Seal=)
- rsyslog reliable forwarding: https://www.rsyslog.com/doc/
- CIS distribution benchmarks (logging and auditing sections): https://www.cisecurity.org/cis-benchmarks/
