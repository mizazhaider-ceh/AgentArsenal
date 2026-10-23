---
name: emi-emc-basics
description: Use when you need working knowledge of electromagnetic
  interference and compatibility for security hardware work. Covers how
  emissions leak information, how to reduce a device's emission profile
  in the lab, and what EMC concepts matter when probing or shielding a
  target you own. Also use when side channel or glitching work needs
  cleaner measurements.
version: 1.0.0
domain: hardware
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [side-channels, pcb-analysis, hardware-reversing]
tools:
  - name: Python
    version: 3.12
---

Every switching chip broadcasts: electromagnetic emissions carry the
same data dependent signals that power analysis uses, and poor
shielding makes both attacks and accidental interference worse. This
skill gives security practitioners the working EMC knowledge they
need: where emissions come from, how to probe them on your own
devices, and how shielding and filtering change the picture. It is
foundations, not a certification course.

## Quick Workflow

1. Learn the sources: clocks, switching regulators, and fast digital
   edges are the main emitters on a board.
2. Set up a near field probe (a simple loop probe works) connected to
   a spectrum analyzer or oscilloscope with FFT.
3. Scan the board while it idles and while it runs the target
   operation; note which frequencies change.
4. Localize the emitter by moving the probe: strongest signal marks
   the source.
5. Compare emissions during different operations to spot data
   dependent leakage.
6. Apply basic mitigation in the lab: shielding, ferrites, and clean
   grounding, and re-measure.
7. Document the emission profile with frequencies and relative levels.
8. Feed findings into side channel or glitch planning.

## 1. Emission survey

```bash
# With an RTL-SDR or spectrum analyzer, survey the near field
# (example flow using a simple sweep; adapt to your instrument)
python3 - << 'PY'
print("survey plan:")
print("1. probe over the SoC: record peaks while idle")
print("2. run AES in a loop: record which peaks modulate")
print("3. move probe to regulator, memory, crystal: compare")
print("data dependent peaks = candidate side channel")
PY
```

```bash
# Oscilloscope FFT check for a clock harmonic carrying data
# Trigger on the crypto operation start, FFT the window, and compare
# traces for two different plaintexts; differing bins mean leakage
echo "capture 100 traces per plaintext, average, then subtract"
```

## 2. Lab mitigation for cleaner measurements

```bash
# Reduce your own noise before blaming the target
# - power the target from a linear bench supply, not a switching wall wart
# - add ferrite clamps on probe and power cables
# - ground everything to one point (star ground)
# - move phone and WiFi sources away from the bench
# Re-run the survey; the noise floor should drop several dB
echo "measure noise floor before and after each change"
```

## Edge cases

- The lab has strong ambient signals (WiFi, switching supplies).
  Shield the target in a simple Faraday enclosure (metal box with
  filtered feedthroughs) for relative measurements.
- Emissions look identical for all inputs. The leakage may be in a
  frequency you are not probing; sweep wider before concluding.
- Mitigations help the measurement but are not product fixes. Note
  the difference between lab cleanliness and shipped security.

## Escalation

- Near field shows nothing: try conducted emissions on the power
  cable with a current probe, which often carries cleaner signals.
- Still nothing: the device may be well designed; report the survey
  method and the negative result honestly.

## Detection and defender view

EMC is usually about compliance (FCC, CE), but the security view is
TEMPEST style: emissions are an information channel. Defenders reduce
it with spread spectrum clocks, shielding cans over noisy sections,
filtering on I/O lines, and keeping crypto in shielded secure
elements. They verify with emission scans during design, not after
shipping.

## Key references

- NIST IR 8228: side channel and emission considerations.
- FCC Part 15 and CISPR 32: emission limit frameworks.
- "EM Side-Channel Attacks" survey literature.
