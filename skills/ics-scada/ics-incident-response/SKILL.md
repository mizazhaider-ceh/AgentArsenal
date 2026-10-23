---
name: ics-incident-response
description: Use when responding to a suspected incident in an OT or
  SCADA environment. Covers safety first triage, OT evidence collection
  without disrupting processes, working with operations, and recovery
  that respects physical constraints. Also use when building an OT
  specific incident playbook.
version: 1.0.0
domain: ics-scada
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, incident-playbooks, plc-basics, scada-network-seg]
tools:
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.4
---

OT incident response puts safety first, process second, and forensics
third: the opposite priority order of IT response. You cannot just
isolate a PLC the way you isolate a laptop; the process it controls
may need it running. This skill covers the OT adapted method:
triage with operations, evidence collection that does not disturb the
process, and recovery coordinated with the physical world.

## Quick Workflow

1. Ensure human safety first: confirm with operations that the process
   is in a safe state before any response action.
2. Declare the incident and bring operations into the command
   structure; they own the process, you own the investigation.
3. Scope without disruption: passive capture and log review before any
   active containment.
4. Collect OT evidence: historian data, HMI logs, PLC program copies,
   and network captures from span ports.
5. Decide containment with operations: what can be isolated without
   unsafe process effects.
6. Eradicate: clean engineering workstations, reset credentials, and
   restore known good PLC logic from offline backups.
7. Recover in stages with operations validating the process at each
   step.
8. Review: update the OT playbook with what the process constraints
   taught you.

## 1. Safe evidence collection

```bash
# Passive capture from a SPAN port (never inline on OT without approval)
sudo tshark -i eth0 -f "not arp" -w /tmp/ir_ot/capture.pcap &
echo $! > /tmp/ir_ot/capture.pid
# Let it run; stop with: kill $(cat /tmp/ir_ot/capture.pid)
```

```bash
# Pull PLC program copies for comparison (read only, with operations)
# Example via vendor tool CLI or engineering workstation export;
# hash immediately to preserve integrity
sha256sum /tmp/ir_ot/plc_program_export.ap15 > /tmp/ir_ot/plc_hash.txt
# Compare against the last known good backup hash
diff /tmp/ir_ot/plc_hash.txt /backups/plc_known_good_hash.txt \
  && echo "logic unchanged" || echo "LOGIC DIFFERS - investigate"
```

```bash
# Historian export for the incident window: process values tell you
# what the attacker changed physically
python3 - << 'PY'
print("export from historian: tag values for incident window")
print("look for: setpoint changes, manual overrides, alarm suppressions")
print("correlate each anomaly with a network event from the capture")
PY
```

## 2. Containment decisions with operations

```bash
# Decision matrix (fill with operations, do not decide alone):
# - isolate engineering workstation: usually safe, do it
# - block IT to OT conduit: safe if historian replica exists
# - stop a PLC: almost never without a controlled shutdown plan
# - fail over to redundant systems: only per operating procedures
echo "every containment action needs an operations sign off"
```

Never reboot a PLC or HMI to "clear malware" without operations
approval: you may lose the only copy of the running logic or trip the
process.

## Edge cases

- The attacker is in the safety system network. Stop and escalate:
  safety systems protect people, and any response action needs the
  safety engineer's approval.
- No span ports exist. Use a temporary tap installed during a
  maintenance window, or work from logs only.
- Logs are minimal or overwritten. OT devices log little; the
  historian and the firewall at the conduit become your main sources.
- Operations will not allow any containment. Document the risk
  acceptance, focus on monitoring, and plan containment for the next
  maintenance window.

## Escalation

- Ransomware on IT spreading toward OT: sever the IT to OT conduit at
  the firewall immediately per the pre approved playbook.
- Physical process affected: follow the site emergency procedures
  first; the cyber investigation waits.
- Need external help: call the vendor and national CERT per the
  playbook; OT incidents often need both.

## Detection and defender view

OT detection is about process anomalies as much as network ones:
setpoints that change without a work order, HMIs logging in at odd
hours, and PLC programs that differ from the known good hash. Mature
sites run allowlist IDS on OT segments and hash PLC logic on a
schedule. After an incident, the detection gaps to close are usually
visibility (span ports, logging) and change control on the OT side.

## Key references

- NIST SP 800-82r3: OT incident response guidance.
- IEC 62443-2-1: security program including incident response.
- MITRE ATT&CK for ICS: technique to scenario mapping.
- Related skills: incident-response, safety-systems.
