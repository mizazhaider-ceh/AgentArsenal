---
name: modbus-security
description: Use when assessing Modbus TCP or Modbus RTU on an authorized
  OT engagement or lab. Covers device discovery, function code
  enumeration, register mapping, detecting unsafe writes, and reviewing
  Modbus exposure. Also use when a plant network shows port 502 open
  and you need to know what the devices allow.
version: 1.0.0
domain: ics-scada
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [nmap-methodology, network-pivoting, scada-network-seg]
tools:
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.4
---

Modbus is the most common industrial protocol and it has no
authentication: anyone who can reach port 502 can usually read and
write process values. This skill covers authorized assessment of
Modbus TCP and RTU: finding devices, enumerating what they expose,
mapping registers to physical meaning, and proving which writes are
possible. In OT, always coordinate with operations first; even reads
can disturb fragile devices, and writes can move real machinery.

## Quick Workflow

1. Get written authorization that names the OT network segment, the
   allowed test window, and whether any writes are permitted.
2. Discover Modbus devices passively first: watch traffic with
   Wireshark before sending a single packet.
3. Scan for port 502 on the authorized segment with a slow, careful
   nmap profile.
4. Identify each device: unit ID, vendor strings, and which function
   codes it answers.
5. Read safe registers (inputs, holding registers) and map them to
   process meaning with the operations team.
6. If writes are authorized, test them on a lab device or during a
   maintenance window, one register at a time.
7. Document every device, its exposure, and which function codes are
   enabled.
8. Recommend network controls: Modbus has no auth, so the network must
   provide the boundary.

## 1. Discovery and enumeration

```bash
# Slow, OT-safe scan for Modbus TCP on the authorized segment only
sudo nmap -sS -p 502 --open -T2 --max-retries 1 \
  192.168.10.0/24 -oN /tmp/modbus_discovery.txt
cat /tmp/modbus_discovery.txt | grep -B2 open | head -20
```

```bash
# Banner and device identification via nmap scripts (still gentle)
sudo nmap -sV -p 502 --script modbus-discover \
  --script-args modbus-discover.aggressive=false \
  192.168.10.20 -oN /tmp/modbus_id.txt
cat /tmp/modbus_id.txt
```

```python
#!/usr/bin/env python3
"""Modbus TCP enumerator: unit IDs and function codes (lab/authorized)."""
import socket, struct

HOST = "192.168.10.20"
PORT = 502

def mbap(tid, unit, pdu):
    return struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit) + pdu

def query(unit, pdu, timeout=3):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.sendall(mbap(1, unit, pdu))
    data = s.recv(260)
    s.close()
    return data

# Try unit IDs 1..16 with a read device identification (function 43/14)
for unit in range(1, 17):
    try:
        resp = query(unit, b"\x2b\x0e\x01\x00")
        if len(resp) > 9 and resp[7] == 0x2B:
            print(f"unit {unit}: responds to device ID query")
    except Exception:  # noqa: BLE001 - offline units just skip
        pass

# Function code support: which of these get a real answer vs exception
for fc, name in [(1, "read coils"), (2, "read discrete inputs"),
                 (3, "read holding regs"), (4, "read input regs"),
                 (5, "write coil"), (6, "write reg"), (15, "write coils"),
                 (16, "write regs")]:
    pdu = struct.pack(">BHH", fc, 0, 1 if fc < 5 else 1)
    if fc in (5, 6):
        pdu = struct.pack(">BHH", fc, 0, 0xFF00 if fc == 5 else 0)
    if fc in (15, 16):
        pdu = struct.pack(">BHHBB", fc, 0, 1, 1, 0) + (b"\x01" if fc == 15 else b"\x00\x00")
    try:
        resp = query(1, pdu)
        code = resp[7]
        print(f"FC {fc:2d} {name:18s}: {'SUPPORTED' if code == fc else 'exception'}")
    except Exception as e:  # noqa: BLE001
        print(f"FC {fc:2d} {name:18s}: no answer ({e})")
```

## 2. Register mapping and safe reads

```bash
# Read holding registers 0..49 and look for live process values
python3 - << 'PY'
import socket, struct
def read_holding(host, unit, start, count):
    s = socket.create_connection((host, 502), timeout=3)
    pdu = struct.pack(">BHH", 3, start, count)
    s.sendall(struct.pack(">HHHB", 1, 0, len(pdu) + 1, unit) + pdu)
    data = s.recv(260); s.close()
    vals = struct.unpack(">" + "H" * count, data[9:9 + 2 * count])
    return vals
vals = read_holding("192.168.10.20", 1, 0, 50)
for i, v in enumerate(vals):
    if v != 0:
        print(f"reg {i}: {v}")
PY
```

Work with operations to label registers: which one is temperature,
which is a setpoint, which drives an actuator. A register map without
physical meaning is just numbers.

## 3. Write testing (authorized only)

Writes move real equipment. Only test writes that operations approves,
on lab hardware or in a maintenance window, and announce each one.

```bash
# Example: toggle a TEST coil that operations confirmed is safe
python3 - << 'PY'
import socket, struct
s = socket.create_connection(("192.168.10.20"), 502, timeout=3)
pdu = struct.pack(">BHH", 5, 10, 0xFF00)  # write coil 10 ON
s.sendall(struct.pack(">HHHB", 2, 0, len(pdu) + 1, 1) + pdu)
print("write response:", s.recv(260).hex())
s.close()
PY
```

## Edge cases

- The device answers reads but resets on fast scanning. Slow down
  (T1/T2 timing) and space queries; fragile stacks crash under load.
- Unit ID 0 or 255 behaves as broadcast. Do not send broadcast writes;
  they hit every device on the segment.
- A gateway translates Modbus TCP to serial RTU. Timeouts are longer
  and concurrent queries collide; serialize your requests.
- Registers return 0xFFFF or exceptions for unmapped ranges. Map only
  what answers cleanly.
- The device requires a specific unit ID per function. Enumerate unit
  IDs first instead of assuming unit 1.

## Escalation

- Port 502 closed but the device speaks Modbus on a custom port: check
  the vendor docs and scan the documented alternates.
- Reads work but the process meaning is unclear: capture traffic
  during a known operation (a valve opening) and correlate register
  changes with the physical event.
- No test window for writes: report write capability as untested but
  likely, based on supported function codes, and recommend disabling
  write function codes at the firewall.

## Detection and defender view

Defenders see Modbus attacks as new hosts scanning port 502, function
codes the HMI never uses (especially writes), and register access
outside normal ranges. Detect with an OT IDS allowlist: alert on any
Modbus write, any new master on the segment, and any function code not
in the baseline. The durable defense is network architecture: Modbus
devices on an isolated OT segment, a firewall that permits only the
HMI's IP to use write function codes, and no route from IT or the
internet to port 502.

## Key references

- MITRE ATT&CK T0806 (Brute Force I/O Addresses) and ICS T0821
  (Modify Controller Tasking).
- CWE-306 (Missing Authentication for Critical Function).
- CWE-862 (Missing Authorization): no access checks on function codes.
- Modbus Organization: MODBUS Application Protocol Specification.
