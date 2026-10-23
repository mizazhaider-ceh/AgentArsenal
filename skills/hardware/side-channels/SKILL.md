---
name: side-channels
description: Use when assessing a device for side channel leakage on an
  authorized hardware engagement or in your own lab. Covers power
  analysis basics, timing attack measurement, electromagnetic probing
  concepts, and simple countermeasure review. Also use when crypto on an
  embedded target looks correct but might leak through physics.
version: 1.0.0
domain: hardware
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [crypto-fundamentals, glitching-attacks, hardware-reversing]
tools:
  - name: Python
    version: 3.12
---

Side channel attacks steal secrets without breaking the math: they watch
power draw, timing, or electromagnetic emissions while the device
computes. This skill covers the concepts and lab method for authorized
testing: setting up a measurement, spotting data dependent leakage, and
reviewing countermeasures. Full key recovery needs lab equipment
(oscilloscope, probes) and is out of scope for a first pass; this skill
gets you to a credible leakage assessment.

## Quick Workflow

1. Define the target operation: AES encryption, RSA signature, or PIN
   comparison on a device you own or may test.
2. Start with timing: measure operation time across many inputs and look
   for input dependent differences.
3. Move to power only if you have a measurement setup: shunt resistor
   or current probe on the device supply.
4. Capture traces during known operations and align them.
5. Look for leakage: different power shapes for different key bits or
   data values.
6. Review the code or algorithm for constant time behavior.
7. Recommend countermeasures: constant time code, masking, and noise.
8. Report leakage as observable differences, not as recovered keys,
   unless full recovery is in scope and achieved.

## 1. Timing measurement

Timing is the cheapest side channel: no special hardware, just a clock.

```python
#!/usr/bin/env python3
"""Timing probe: detects input dependent timing over a serial console."""
import time, statistics, serial

ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=5)

def timed_encrypt(data_hex):
    ser.write(f"enc {data_hex}\n".encode())
    start = time.perf_counter()
    ser.readline()  # wait for the result line
    return time.perf_counter() - start

# Compare timing for inputs that differ in one byte
base = [timed_encrypt("00" * 16) for _ in range(50)]
diff = [timed_encrypt("ff" + "00" * 15) for _ in range(50)]
print(f"base mean: {statistics.mean(base)*1e3:.3f} ms")
print(f"diff mean: {statistics.mean(diff)*1e3:.3f} ms")
# A consistent gap beyond noise suggests data dependent timing
```

```bash
# Quick check for early exit string comparison in firmware under review
# (constant time comparison has no early exit)
grep -rn "strcmp\|memcmp" /tmp/rootfs --include="*.c" 2>/dev/null | head
# In binaries, look for compare loops that branch on first mismatch
```

## 2. Power trace capture concept

With an oscilloscope across a shunt resistor on the target's power
line, each encryption shows a trace. Differential power analysis
compares many traces: points in time where power correlates with a
guessed key bit reveal the key.

```bash
# Capture helper: trigger the device N times and save trigger markers
python3 - << 'PY'
# Pseudocode for a ChipWhisperer style capture loop:
# for i in range(NUM_TRACES):
#     scope.arm()
#     target.send_plaintext(pt[i])
#     trace = scope.capture()   # power samples during encryption
#     save(trace, pt[i], ct[i])
print("capture loop template: arm scope, send input, save trace")
print("typical first pass: 1000 traces of AES-128 ECB, fixed key")
PY
```

You do not need to recover the key to report the finding. Showing that
traces differ visibly between two plaintexts is enough to justify a
deeper engagement with proper equipment.

## 3. Countermeasure review

```bash
# Review checklist against source or disassembly
# 1. Constant time: no branches or table lookups indexed by secret data
# 2. Masking: secrets split into shares before operations
# 3. Blinding: RSA signatures use random blinding factors
# 4. Noise: random delays or dummy operations (weak alone, fine in depth)
grep -rn "blinding\|mask" /tmp/crypto_src --include="*.c" -i | head
```

## Edge cases

- USB and OS jitter drown small timing signals. Run on bare metal or a
  realtime path, and take thousands of samples.
- The device caches or pipelines operations. Warm up the cache before
  measuring so every sample sees the same state.
- Countermeasures exist but are misapplied: masking without fresh
  randomness per operation leaks anyway.
- You observe leakage but cannot exploit it. Report the observable
  difference with the measurement method; that is a valid finding.

## Escalation

- Timing inconclusive: move to power analysis with a proper shunt and
  oscilloscope.
- Power inconclusive: try electromagnetic probing near the crypto
  accelerator, which often gives cleaner signals.
- Need key recovery: scope a dedicated side channel engagement with
  ChipWhisperer or equivalent tooling and a larger trace budget.

## Detection and defender view

Defenders cannot detect passive side channel observation; there is no
log entry for watching power draw. Defense is by construction:
constant time implementations, masking with fresh randomness,
shielding and filtering on power lines, and keeping secret operations
off shared hardware. Certifications like FIPS 140-3 and Common Criteria
require side channel testing, which is why assessed crypto modules
document their countermeasures.

## Key references

- CWE-208 (Observable Timing Discrepancy).
- CWE-1300 (Improper Protection of Physical Side Channels).
- NIST FIPS 140-3: side channel requirements for crypto modules.
- "Differential Power Analysis" (Kocher et al.): the foundational paper.
