---
name: glitching-attacks
description: Use when assessing fault injection resistance of a device
  you own or have authorization to test. Covers voltage glitching
  concepts, clock glitching concepts, fault models, and reviewing
  firmware for missing fault checks. Also use when a secure boot or PIN
  check needs evaluation against physical fault attacks in a lab.
version: 1.0.0
domain: hardware
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [side-channels, secure-boot-bypass, hardware-reversing]
tools:
  - name: Python
    version: 3.12
---

Fault injection, or glitching, makes a chip misbehave for a fraction of
a second: a voltage dip skips an instruction, a clock glitch corrupts a
comparison. Attackers use this to skip signature checks or PIN
verification. This skill covers the concepts and assessment method for
authorized lab work: understanding fault models, finding glitchable
operations in firmware, and reviewing countermeasures. Actual glitching
needs dedicated hardware and stays in the lab; this skill gets you to a
credible assessment of exposure.

## Quick Workflow

1. Pick the target operation on your lab device: secure boot signature
   check, PIN verification, or a loop bound check.
2. Map the fault model: which instruction skip or corruption would break
   the security property.
3. Review the firmware for single points of failure: one comparison
   standing between attacker and success.
4. Check for existing countermeasures: double checks, redundancy, and
   fault detectors.
5. If equipped, characterize the glitch: find the timing window of the
   target operation with a trigger signal.
6. Attempt controlled faults only on your own device, starting with
   parameters that cannot damage it.
7. Record successes as skipped checks with the exact setup.
8. Recommend redundancy and verification, not just obscurity.

## 1. Finding glitchable code

The best targets are single comparisons with big consequences. Find
them by review before touching hardware.

```bash
# Look for signature or PIN checks with a single point of failure
grep -rn "verify\|signature\|check_pin" /tmp/fw_src --include="*.c" -i | head -20
```

```c
// VULNERABLE pattern: one branch decides everything
if (verify_signature(fw_image) != 0) {
    halt_and_catch_fire();
}
boot(fw_image);  // skipping the branch boots unsigned firmware

// HARDENED pattern: redundant check with different logic
int ok1 = verify_signature(fw_image);
int ok2 = verify_signature_alt(fw_image);
if (ok1 != 0 || ok2 != 0 || ok1 != ok2) {
    halt_and_catch_fire();
}
```

```bash
# In disassembly, look for conditional branches right before boot or
# unlock sequences (Ghidra or objdump on your lab firmware)
arm-none-eabi-objdump -d /tmp/bootloader.elf | grep -B5 -A2 "bl.*verify" | head -40
```

## 2. Glitch parameter concept

A voltage glitch has four parameters: offset (when after the trigger),
width (how long), depth (how far the voltage drops), and repeat count.
The lab workflow sweeps them:

```python
#!/usr/bin/env python3
"""Glitch sweep template (ChipWhisperer style pseudocode)."""
# for offset in range(OFFSET_MIN, OFFSET_MAX, STEP):
#     for width in WIDTHS:
#         scope.glitch.offset = offset
#         scope.glitch.width = width
#         target.reset()
#         scope.arm()
#         target.trigger_boot_check()
#         if target.boots_unsigned():
#             print(f"SUCCESS at offset={offset} width={width}")
#             save_parameters(offset, width)
print("sweep offsets across the check window, widths 1-100ns typical")
print("start with wide, shallow glitches; narrow down on success")
```

Never glitch outside the agreed voltage and temperature envelope of
your device. Destructive parameters are out of scope for security
testing.

## Edge cases

- The check runs from internal flash with caches on. Glitch timing
  shifts with cache state; reset to a known state each attempt.
- Brown out detectors reset the chip before your glitch lands. Lower
  the depth or target a different operation.
- Success is rare and non repeatable at first. That is normal; fault
  injection is statistical and needs thousands of attempts.
- The device bricks. That is why you work on your own hardware with a
  recovery path (bootloader, programmer) ready.

## Escalation

- No success with voltage glitching: try clock glitching if the clock
  is externally accessible.
- Clock not accessible: try electromagnetic fault injection near the
  CPU, which needs no electrical connection.
- Code review shows redundancy: verify the redundant checks actually
  run (dead code elimination can remove them) before declaring the
  device resistant.

## Detection and defender view

Fault injection leaves almost no software trace; a skipped instruction
looks like correct execution afterward. Defenders rely on construction:
redundant checks with diverse logic, fault detectors (voltage, clock,
temperature monitors), and secure elements that are hardened against
glitching. Detect tampering attempts through boot failure counters and
physical intrusion switches. For high value targets, assume a skilled
lab can glitch past a single software check and design accordingly.

## Key references

- CWE-1242 (Inclusion of Undocumented Features or Chicken Bits).
- CWE-1191 (On-Chip Debug and Test Interface With Improper Access
  Control).
- "Fault Injection Attacks" literature: voltage and clock glitch
  surveys.
- ChipWhisperer documentation: glitch parameter tutorials.
