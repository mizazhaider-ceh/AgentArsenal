---
name: hardware-reversing
description: Use when reverse engineering an embedded device you own or
  have authorization to test. Covers board teardown and documentation,
  firmware analysis workflow, protocol sniffing between chips, and
  building a full picture from hardware plus software. Also use when a
  black box device needs systematic understanding before deeper testing.
version: 1.0.0
domain: hardware
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [firmware-extraction, firmware-analysis, uart-jtag, ghidra-basics]
tools:
  - name: Ghidra
    version: 11.3
  - name: binwalk
    version: 2.4.1
  - name: Python
    version: 3.12
---

Hardware reversing combines board analysis with firmware analysis to
understand a device completely: what the chips do, how they talk, and
where the software trusts the hardware. This skill gives the systematic
lab workflow for devices you own or may test: document, extract,
analyze, and verify. Each layer informs the next, and the findings feed
the deeper hardware and firmware skills.

## Quick Workflow

1. Document the device: photos of both board sides, chip markings, and
   connector labels before you touch anything.
2. Identify every major chip: SoC, flash, RAM, radio, and power
   management, with datasheets where possible.
3. Trace the boot chain on paper: ROM to bootloader to kernel to app.
4. Extract the firmware (see firmware-extraction) and get a console
   (see uart-jtag) in parallel.
5. Analyze the firmware statically: services, credentials, update
   mechanism, and trust boundaries.
6. Sniff inter chip protocols (SPI, I2C, UART) during boot and
   operation to see what crosses trust boundaries in plaintext.
7. Verify each finding dynamically on the live device.
8. Write up the device profile: attack surface map with entry points
   ranked by access needed.

## 1. Board documentation and chip identification

```bash
# Organize the evidence as you go
mkdir -p /tmp/hwrev/{photos,datasheets,firmware,notes}
# Photograph both sides at high resolution, then annotate:
# - SoC part number and package
# - flash chip part number (SPI/I2C/eMMC?)
# - debug headers and test points
# - radio modules and antenna paths
ls /tmp/hwrev/photos/
```

```bash
# Identify chips from markings; common lookup flow
# 1. Read the top marking, e.g. "W25Q128JV" (Winbond 128Mbit SPI flash)
# 2. Pull the datasheet into /tmp/hwrev/datasheets/
# 3. Note voltage, pinout, and protection features
python3 - << 'PY'
chips = [
    ("U1", "W25Q128JV", "SPI flash 128Mbit, 3.3V"),
    ("U2", "ESP32-WROOM", "WiFi/BT SoC module"),
    ("U3", "CH340G", "USB to serial bridge"),
]
for ref, part, desc in chips:
    print(f"{ref}: {part} -> {desc}")
PY
```

## 2. Inter chip protocol sniffing

Chips often talk in plaintext. Capture the conversation during boot.

```bash
# Sniff UART between SoC and a radio module (logic analyzer or second
# serial adapter on the RX line, listen only)
picocom -b 115200 --logfile /tmp/hwrev/uart_sniff.log /dev/ttyUSB1 &
# Power cycle the target and watch for AT commands, keys, or credentials
grep -ai -E "at\+|key|pass|token" /tmp/hwrev/uart_sniff.log | head -20
```

```bash
# I2C scan to enumerate attached peripherals (bus pirate or compatible)
# i2c> m  (set mode) then scan addresses; note every responding device
# SPI flash traffic during boot can reveal reads of config partitions
python3 - << 'PY'
print("checklist: UART boot log, I2C address map, SPI config reads")
print("flag anything secret (keys, tokens) crossing in plaintext")
PY
```

## 3. Firmware analysis pass

```bash
# Strings triage on the extracted firmware for quick wins
strings -n 8 /tmp/flash_a.bin | grep -i -E "passw|admin|secret|token|key=" | head -20
# Identify the OS and services from banners in the boot log
grep -a "Linux version\|U-Boot\|BusyBox" /tmp/uart_boot.log | head -5
```

```bash
# Load the bootloader or main binary into Ghidra for the deep pass
# (see ghidra-basics for the workflow); focus on:
# - update verification routines
# - hardcoded credentials and keys
# - network services and their parsers
# - trust boundary crossings found in the sniffing step
```

## Edge cases

- Chip markings are sanded off. Identify by package, pin count, and
  surrounding circuitry, or by behavior (SPI flash responds to JEDEC
  ID queries).
- The firmware is encrypted and the key is in OTP. Static analysis
  stops; pivot to dynamic analysis over the debug console.
- Multiple board revisions exist. Verify which revision you have; the
  attack surface changes between them.
- The device uses a secure element for keys. Note what the secure
  element actually protects versus what sits in plain flash.

## Escalation

- No console and no dump: check for firmware update files as a
  software only path into the code.
- Update files encrypted: look at the update client on a companion
  mobile app, which often contains the decryption logic.
- Analysis stalls on a custom RTOS: identify the RTOS by strings and
  structure, then find public research on its weaknesses.

## Detection and defender view

Device designers defend with encrypted firmware, disabled debug
interfaces, and keys in secure elements instead of flash. They detect
physical tampering with intrusion switches and tamper evident seals.
For the reverser, the lesson is that every unprotected interface is an
entry point, and the combination of a console plus a flash dump
usually defeats software only protections.

## Key references

- CWE-1191 (On-Chip Debug and Test Interface With Improper Access
  Control).
- CWE-798 (Use of Hard-coded Credentials).
- OWASP IoT Top 10: hardware and firmware weaknesses.
- Ghidra documentation: loading bare metal firmware images.
