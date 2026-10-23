---
name: firmware-extraction
description: Use when you need to get firmware off a device or out of an
  update file on an authorized assessment. Covers update package
  unpacking, SPI flash reading with flashrom, binwalk carving, and
  filesystem extraction from images you own or have permission to test.
  Also use when a vendor update file is the only access you have to a
  device's software.
version: 1.0.0
domain: hardware
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [firmware-analysis, uart-jtag, static-triage]
tools:
  - name: binwalk
    version: 2.4.1
  - name: flashrom
    version: 1.4
  - name: Python
    version: 3.12
---

Firmware extraction is getting the bytes: from an update file on a
website, from a SPI flash chip on the board, or from a debug port. This
skill covers the authorized lab workflow: unpacking update packages,
reading external flash with a programmer, carving filesystems out of
raw dumps, and verifying what you extracted. Work only on devices you
own or have written permission to test.

## Quick Workflow

1. Start with the easy path: download official update files and try to
   unpack them before touching hardware.
2. Identify the flash chip on the board and check whether it is readable
   in circuit.
3. Read the chip with flashrom and verify the dump (read twice, compare
   hashes).
4. Carve the dump with binwalk to find bootloaders, kernels, and
   filesystems.
5. Extract each filesystem and list its contents for the analysis phase.
6. If in circuit reads fail, desolder or use a clip, and re-verify.
7. Document chip part number, programmer, read settings, and hashes.

## 1. Update file unpacking

```bash
# Identify the update file type first
file /tmp/vendor_update.bin
binwalk /tmp/vendor_update.bin | head -20

# Extract everything binwalk recognizes
binwalk -e -C /tmp/fw_extract /tmp/vendor_update.bin
find /tmp/fw_extract -maxdepth 3 | head -30
```

```bash
# Encrypted or obfuscated updates: measure entropy to confirm
python3 - << 'PY'
import math, collections
data = open("/tmp/vendor_update.bin", "rb").read()
freq = collections.Counter(data)
ent = -sum(c / len(data) * math.log2(c / len(data)) for c in freq.values())
print(f"entropy: {ent:.2f} bits/byte (near 8.0 suggests encryption)")
PY
# High entropy with a small header often means a simple XOR or a
# documented crypto scheme; check the vendor's GPL release or FCC filings
```

## 2. SPI flash reading with flashrom

```bash
# Detect the chip (use a CH341A or similar programmer, clip on the chip)
flashrom -p ch341a_spi
# Read twice and compare: a stable read is a trustworthy read
flashrom -p ch341a_spi -r /tmp/flash_a.bin
flashrom -p ch341a_spi -r /tmp/flash_b.bin
sha256sum /tmp/flash_a.bin /tmp/flash_b.bin
```

```bash
# Carve the verified dump
binwalk -e -C /tmp/spi_extract /tmp/flash_a.bin
# Common finds: U-Boot at the start, kernel, squashfs or jffs2 roots
find /tmp/spi_extract -name "*.squashfs" -o -name "squashfs-root" | head
# Extract squashfs manually if binwalk missed it
unsquashfs -d /tmp/rootfs /tmp/spi_extract/_flash_a.bin.extracted/4A000.squashfs 2>/dev/null
ls /tmp/rootfs | head
```

## 3. Verifying the extraction

```bash
# Sanity checks on the dump before analysis
ls -l /tmp/flash_a.bin
# Look for known magic: U-Boot, ELF, squashfs (hsqs), JFFS2
xxd /tmp/flash_a.bin | head -5
python3 - << 'PY'
data = open("/tmp/flash_a.bin", "rb").read()
for magic, name in [(b"hsqs", "squashfs"), (b"\x7fELF", "ELF"),
                    (b"UBI#", "UBI"), (b"\x85\x19", "JFFS2")]:
    print(name, "found at offsets:", [hex(i) for i in range(len(data)) if data[i:i+len(magic)] == magic][:5])
PY
```

An all 0xFF or all 0x00 dump means the read failed or the chip was not
selected. A dump that changes between reads means the chip is being
written during read (power the board down and read the chip isolated).

## Edge cases

- Chip reads differently each time. The SoC is accessing flash
  concurrently; hold the SoC in reset during the read.
- flashrom does not recognize the chip. Force the chip type with
  `-c <name>` after identifying it from the package marking, or add it
  to the flashchips table.
- The image is a multi volume UBI. Use `ubireader` to extract volumes
  instead of binwalk.
- The filesystem is encrypted (dm-crypt/LUKS header). Extraction stops
  here unless key recovery is in scope; document the finding.
- Update files are delta patches, not full images. You need the base
  version the delta applies to, or a device to apply it on.

## Escalation

- In circuit read fails: lift the chip's VCC pin or desolder it and
  read it in a socket.
- BGA chip with no accessible pins: use the UART or JTAG path
  (uart-jtag skill) to dump from software instead.
- eMMC storage: use an eMMC adapter in 1 bit mode, or boot the device
  into a loader that exposes storage over USB.
- Everything hardware fails: analyze the update file statically and
  report extraction limits honestly.

## Detection and defender view

The device defender prevents extraction with encrypted firmware at
rest, secure boot that rejects modified images, and readout protection
on debug ports. They detect tampering through secure boot failure
counters and attestation. For the analyst, the durable lesson is that
unencrypted external flash is readable by anyone with a ten dollar
clip, so sensitive data and keys must never sit in plaintext on SPI
flash.

## Key references

- CWE-1193 (Power-On of Untrusted Execution): untrusted firmware.
- CWE-1242 (Inclusion of Undocumented Features or Chicken Bits).
- flashrom documentation: supported programmers and chips.
- binwalk 2.4.1 documentation: extraction and entropy analysis.
