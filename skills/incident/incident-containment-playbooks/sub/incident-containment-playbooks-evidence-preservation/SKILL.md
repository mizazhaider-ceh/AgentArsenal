---
name: incident-containment-playbooks-evidence-preservation
description: Use when you must preserve forensic evidence during
  containment on systems you are authorized to defend. Covers the
  order of volatility, memory capture on Linux and Windows, disk
  imaging with dd, targeted file collection with hashes, log
  preservation before rotation, chain of custody documentation, and
  cloud snapshot preservation. Use when the parent
  incident-containment-playbooks workflow starts, before any
  isolation or remediation step that could destroy state, or when
  preparing a forensic jump bag and procedures. Every artifact is hashed
  with coreutils sha256sum and host state is verified with osquery.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-containment-playbooks
requires: [incident-containment-playbooks]
extends: []
relates: [incident-containment-playbooks]
tools:
  - name: Python
    version: 3.12
  - name: coreutils
    version: 9.4
  - name: osquery
    version: 5.12.1
---

Evidence preservation captures the system's state before containment
actions change it: memory before reboot, logs before rotation, disk
before reimaging. The order of volatility decides the sequence, and
every capture gets hashed and logged so it stands up later. This
sub-skill covers what to capture, in what order, with which commands,
and how to document it. It assumes authorized incident response on
your own systems; the same care that makes evidence useful internally
is what makes it defensible externally.

## Quick Workflow

1. Open the evidence directory for the incident and record the
   start time.
2. Capture memory first; it is the most volatile.
3. Capture live system state: network, processes, users, mounts.
4. Image the disk or collect targeted files with hashes.
5. Preserve logs locally and confirm central copies exist.
6. Hash every artifact and write the manifest.
7. Maintain chain of custody from capture to storage.
8. Only then proceed with disruptive containment or remediation.

## 1. Order of volatility

Capture in this order; each step is more stable than the last:

1. Memory (RAM): gone at power-off or reboot.
2. Network state: connections, ARP, routes (changes in seconds).
3. Running processes and open files.
4. Disk: image or targeted collection.
5. Logs: local files before rotation deletes them.
6. Backups and archives: least volatile, confirm they exist.

```bash
EVID=/evidence/INC-2026-1042
mkdir -p $EVID
date -u > $EVID/started-at.txt
hostname > $EVID/hostname.txt
```

## 2. Memory capture

```bash
# Linux: LiME or AVML from your jump bag (pre-staged, tested)
# AVML example (Microsoft's memory acquisition tool)
./avml $EVID/memory.lime
ls -lh $EVID/memory.lime

# Fallback if no tool is staged: /dev/mem is not a substitute.
# Prefer crashing the response over a bad capture: note the gap honestly.

# Windows: WinPmem from the jump bag (run as administrator)
# winpmem.exe $EVID\memory.raw
```

```bash
# Hash immediately; the hash is the capture's identity
sha256sum $EVID/memory.lime | tee $EVID/memory.lime.sha256
```

Memory contains process contents, network buffers, encryption keys,
and injected code that never touches disk. If the commander must
choose between memory capture and immediate isolation, capture
memory first unless lives or the business are at stake; that
tradeoff goes in the incident record in writing.

## 3. Live system state

```bash
# Network state
ss -tulpn > $EVID/ss.txt
ss -tupn state established > $EVID/connections.txt
ip neigh > $EVID/arp.txt
ip route > $EVID/routes.txt

# Processes and open files
ps auxf > $EVID/ps.txt
lsof -i -P -n > $EVID/lsof-net.txt
lsof > $EVID/lsof-all.txt 2>/dev/null

# Users and logins
who > $EVID/who.txt
w > $EVID/w.txt
last -n 50 > $EVID/last.txt

# Mounts and loaded modules
mount > $EVID/mount.txt
lsmod > $EVID/lsmod.txt
```

```powershell
# Windows equivalents (run as administrator)
Get-NetTCPConnection -State Established | Export-Csv C:\Evidence\INC-2026-1042\connections.csv
Get-Process | Select-Object Name, Id, Path | Export-Csv C:\Evidence\INC-2026-1042\processes.csv
Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Export-Csv C:\Evidence\INC-2026-1042\tasks.csv
arp -a > C:\Evidence\INC-2026-1042\arp.txt
```

These are fast and low-risk; run them before the memory capture
finishes if you have two responders, or right after if alone.

## 4. Disk imaging and targeted collection

```bash
# Full disk image when time and storage allow (read-only source, hash both ends)
# Identify the disk first; NEVER guess the device name
lsblk
dd if=/dev/sda of=$EVID/disk-sda.img bs=4M status=progress conv=noerror,sync
sha256sum /dev/sda > $EVID/disk-sda-source.sha256
sha256sum $EVID/disk-sda.img > $EVID/disk-sda-img.sha256
```

When a full image is impractical, targeted collection with hashes:

```bash
# Priority files for Linux intrusion cases
for f in /var/log/auth.log /var/log/syslog /var/log/secure \
         /etc/passwd /etc/shadow /etc/crontab /root/.bash_history; do
  [ -f "$f" ] && cp -p "$f" $EVID/ && sha256sum "$f" >> $EVID/files.sha256
done
# SSH keys and authorized_keys everywhere in scope
find /home /root -name "authorized_keys" -exec cp -p {} $EVID/ \; 2>/dev/null
find /home /root -name "authorized_keys" -exec sha256sum {} \; >> $EVID/files.sha256 2>/dev/null
ls -lh $EVID/
```

Use a write blocker for dead-disk imaging; for live collection,
`cp -p` preserves timestamps, which the timeline will need.

## 5. Log preservation

```bash
# Copy logs before rotation or attacker deletion
cp -p /var/log/auth.log* /var/log/syslog* $EVID/ 2>/dev/null
journalctl --since "7 days ago" > $EVID/journal-7d.txt

# Confirm central copies exist (the attacker may have wiped local logs)
# Check your SIEM for the host's recent events; note any gap as a finding
echo "SIEM check for $(hostname): run manually, record result" >> $EVID/log-notes.txt

# Windows: export the key event logs
wevtutil epl Security $EVID\Security.evtx
wevtutil epl System $EVID\System.evtx
wevtutil epl "Microsoft-Windows-Sysmon/Operational" $EVID\Sysmon.evtx
```

A gap between local logs and central logs is itself evidence:
missing local logs with intact central logs suggests tampering
(T1070), which goes in the timeline.

## 6. Cloud preservation

```bash
# Snapshot before terminating or rebuilding (cloud console or CLI)
# Example pattern (adapt to your cloud):
# aws ec2 create-snapshot --volume-id vol-0abc123 --description "INC-2026-1042 web-03"
# aws ec2 create-image --instance-id i-0abc123 --name "INC-2026-1042-web-03" --no-reboot

# Preserve cloud trail and flow logs: they age out
# Copy the relevant window to evidence storage immediately
```

Cloud instances are cattle until they are evidence; snapshot first,
then you may terminate. Note the snapshot ids in the incident
record.

## 7. Manifest and chain of custody

```bash
# One manifest per host, hashing everything
cd $EVID && sha256sum * > MANIFEST.sha256
cat > CHAIN-OF-CUSTODY.md <<'EOF'
# Chain of custody: INC-2026-1042 / web-03
Captured by: <name> at <UTC time>
Method: live capture per evidence-preservation playbook
Storage: <evidence server path>, access restricted to IR team
Transfers: (log every copy or move with date and person)
Hashes: MANIFEST.sha256 (verify on receipt)
EOF
sha256sum MANIFEST.sha256 CHAIN-OF-CUSTODY.md >> MANIFEST.sha256
```

Every person who handles the evidence signs the log. Evidence that
cannot show an unbroken chain is evidence you cannot use.

## Edge cases

- The host is unstable and may crash during capture. Take memory
  first and fast; a partial memory image beats none, and note the
  instability.
- Disk encryption (LUKS, BitLocker) with keys in memory. Capture
  memory before anything else; without the keys, the disk image is
  unreadable. Record the recovery key escrow status.
- The attacker is actively deleting logs during your capture.
  Prioritize the central SIEM copies and note the deletion as
  T1070 in the timeline.
- No jump bag and no capture tools staged. Improvise with the
  built-in commands in section 3, note the missing memory capture
  as a gap, and fix the jump bag afterward.
- The system clock is wrong. Record the offset (`date -u` versus
  a known-good source); the timeline analysis will need it.
- Legal hold applies. Confirm with legal before any deletion or
  reimaging anywhere in scope, including "routine" log rotation.

## Escalation

- Evidence suggests the attacker is still active and watching.
  Coordinate captures to avoid tipping them off if the commander
  chose stealth; otherwise capture fast and openly.
- The volume of evidence exceeds your storage or bandwidth. Triage
  with the forensics lead: memory and targeted files first, full
  disk images for the most critical hosts only.
- Chain of custody is broken (someone moved files without
  logging). Document the break honestly; hidden breaks are worse
  than acknowledged ones.
- External forensics firm is engaged. Hand over hashes and the
  manifest first, then the data; let them verify on receipt.

## Detection and defender view

Evidence preservation is pure defender tradecraft: the better your
captures, the shorter the investigation and the stronger the
lessons learned. The peacetime investments are a tested jump bag,
pre-staged capture tools on a hardened share, evidence storage with
restricted access, and responders who have practiced the order of
volatility until it is reflex. Attackers know responders sometimes
skip preservation in the rush; the discipline of capturing first is
what separates a response from a cleanup.

## Key references

- Parent playbook: incident-containment-playbooks (this repo)
- NIST SP 800-86 (forensic techniques):
  https://csrc.nist.gov/publications/detail/sp/800-86/final
- NIST SP 800-61 Rev. 2: https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final
- SANS FOR508 concepts (order of volatility):
  https://www.sans.org/cyber-security-courses/advanced-incident-response-threat-hunting-training/
- AVML (memory acquisition): https://github.com/microsoft/avml
- MITRE ATT&CK T1070 (Indicator Removal):
  https://attack.mitre.org/
