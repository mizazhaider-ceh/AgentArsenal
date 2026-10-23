---
name: ecu-firmware
description: Use when analyzing ECU firmware on an authorized
  assessment or your own bench hardware. Covers firmware extraction
  from ECUs, update package analysis, UDS flashing flows, and static
  review of automotive code. Also use when a vehicle assessment moves
  from network testing to code review.
version: 1.0.0
domain: automotive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [firmware-extraction, can-bus-security, iso21434-basics]
tools:
  - name: Ghidra
    version: 11.3
  - name: binwalk
    version: 2.4.1
  - name: Python
    version: 3.12
---

ECU firmware runs the car's critical functions, and assessing it
means getting the image, understanding the update flow, and reviewing
the code. This skill covers the authorized workflow on your own
hardware: extracting firmware via debug ports or update files,
analyzing the UDS flashing sequence, and statically reviewing the
image. Bench only; never flash a vehicle you depend on.

## Quick Workflow

1. Identify the ECU: part number, MCU family, and memory layout from
   the datasheet.
2. Try the software path first: update packages from the vendor or
   companion tools.
3. Try the hardware path: debug port or flash chip read on your bench
   ECU.
4. Analyze the update flow: how UDS flashing authenticates and
   verifies.
5. Static review: bootloaders, crypto, credentials, and parsers.
6. Check secure boot and rollback protection per ECU.
7. Verify findings on the bench where safe.
8. Report per ECU with the extraction method and limits.

## 1. Extraction paths

```bash
# Software path: unpack an update package
file /tmp/ecu_update.pkg
binwalk /tmp/ecu_update.pkg | head -20
binwalk -e -C /tmp/ecu_fw /tmp/ecu_update.pkg
```

```bash
# Hardware path: debug port dump on your bench ECU (see uart-jtag)
# Example for a common MCU family via OpenOCD
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
  -c "init; halt; dump_image /tmp/ecu_dump.bin 0x08000000 0x100000; exit"
ls -l /tmp/ecu_dump.bin
```

```bash
# UDS flashing flow analysis (bench, authorized)
# Typical sequence: diagnostic session -> security access (seed/key) ->
# request download -> transfer data -> request transfer exit -> check
# Review: is the seed/key real, is the image signed, is there rollback
# protection (version counters in the image header)
python3 - << 'PY'
print("capture a bench flashing session and label each UDS service")
print("0x10 session, 0x27 security, 0x34 request download, 0x36 transfer")
PY
```

## 2. Static review

```bash
# Triage the image: strings, crypto constants, versions
strings -n 8 /tmp/ecu_dump.bin | grep -i -E "version|boot|secure|key" | head -20
# Look for the signature verification in the bootloader region
```

```bash
# Load into Ghidra with the right base address and MCU profile
# Focus areas:
# - bootloader: signature check, rollback counter, debug unlock
# - UDS handler: service table, which services need security access
# - parsers: CAN message handlers, especially length fields
# - credentials: hardcoded keys, default seed/key algorithms
```

## Edge cases

- The image is encrypted. Find the key management: OTP, HSM, or a
  key in the flashing tool.
- The MCU has readout protection on. Document it as a positive and
  use the update package path.
- Multiple firmware slots (A/B). Check whether both are verified and
  whether rollback to the old slot is possible.
- Calibration data vs code: changing calibration can be as dangerous
  as changing code; review who can write it.

## Escalation

- Weak seed/key algorithm found: demonstrate key computation on the
  bench, never on a customer vehicle.
- Unsigned updates accepted: critical finding; verify the full chain
  from diagnostic session to boot.
- Need the process view: hand findings to iso21434-basics for the
  lifecycle context.

## Detection and defender view

ECU defenders use secure boot, signed updates, and HSM backed key
storage. They detect tampering through attestation and update logs.
The supply chain matters: a compromised flashing tool or update
server bypasses on device checks. Durable defense covers the whole
flow from build signing to the bootloader's verification.

## Key references

- ISO 14229 (UDS): flashing related services.
- CWE-347 (Improper Verification of Cryptographic Signature).
- CWE-798 (Use of Hard-coded Credentials).
- ISO/SAE 21434: automotive cybersecurity engineering.
