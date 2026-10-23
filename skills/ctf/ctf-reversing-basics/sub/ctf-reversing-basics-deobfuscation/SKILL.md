---
name: ctf-reversing-basics-deobfuscation
description: Use when a CTF reversing binary or authorized lab binary is
  packed, encrypted, or obfuscated. Covers identifying packers (UPX and
  custom), unpacking via upx -d and runtime memory dumps, defeating string
  encryption by dumping post-decryption buffers, recognizing control-flow
  flattening, approaching custom virtual machines, and handling common
  anti-analysis tricks. Use when static analysis shows garbage strings or
  a tiny stub, when the entry point looks wrong, or when the real logic
  only appears after the program runs.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-reversing-basics
requires: [ctf-reversing-basics]
extends: []
relates: [ghidra-basics, ctf-reversing-basics]
tools:
  - name: GDB
    version: 15.2
  - name: Ghidra
    version: 11.3
  - name: Python
    version: 3.12
  - name: binutils
    version: 2.42
  - name: Frida
    version: 16.5
---

Obfuscation hides the real program behind packing, encryption, or
control-flow tricks so that static analysis sees a stub instead of the
logic. CTF authors use it to force dynamic analysis and to add stages to a
challenge. This sub-skill covers the authorized deobfuscation workflow:
recognizing the obfuscation type, removing or bypassing each layer, and
recovering analyzable code or data. Scope is CTF competitions, lab
binaries, and software you have explicit permission to analyze.

## Quick Workflow

1. Identify the obfuscation: section names (`UPX0`, `UPX1`), tiny
   `.text` with huge entropy, missing imports, or garbage strings.
2. If UPX-packed, try `upx -d` first; it is instant when it works.
3. For custom packers, run to the original entry point (OEP) in gdb and
   dump the unpacked memory regions.
4. For string encryption, find the decrypt routine, break after it, and
   dump the plaintext buffers.
5. For control-flow flattening, ignore the dispatcher and trace only the
   blocks that touch input and the success message.
6. For custom VMs, map the opcode handlers, then reimplement or trace
   the VM in Python or Frida.
7. Re-run triage (strings, Ghidra) on the recovered code or dumped data.
8. Document each layer removed so teammates can reproduce the pipeline.

## 1. UPX and simple packers

UPX is the most common CTF packer and the easiest to defeat.

```bash
# Detect
strings ./rev | grep -i upx
readelf -S ./rev | grep -E "UPX|Name"
#   [ 1] UPX0   [ 2] UPX1   -> packed

# Unpack (works unless the header was tampered with)
upx -d ./rev -o ./rev.unpacked
file ./rev.unpacked && strings -n 8 ./rev.unpacked | head -20
```

If `upx -d` fails with a header error, the author modified the UPX magic
to block naive unpacking: restore the magic bytes with a hex editor (the
`UPX!` marker near the overlay) or fall back to runtime dumping below.

## 2. Runtime dumping of custom packers

When no unpacker exists, let the packer unpack itself, then steal the
result from memory.

```bash
gdb -q ./rev
(gdb) set disable-randomization on
# Step 1: find the OEP. The stub usually ends with a jmp to the unpacked code.
# Watch for: a big loop (decompression), then jmp rax / jmp to a new region.
(gdb) break *0x401000        # entry point; step through the stub
(gdb) run
(gdb) stepi                  # repeat until you see jmp into freshly written memory
# Step 2: at the OEP (first instruction of real code), dump memory
(gdb) info proc mappings     # note rwx/rx regions and addresses
(gdb) dump binary memory /tmp/dump.bin 0x555555554000 0x555555556000
```

A faster heuristic: `gcore` the process right after the unpacking loop
finishes, then analyze the core with Ghidra (import the dumped segments).
Confirm you reached the OEP by checking that `strings` on the dump shows
the prompt text (`Enter password`) that was invisible before.

## 3. Defeating string encryption

Encrypted strings appear as high-entropy blobs in `.rodata`, and the
binary decrypts them at startup or just before use.

1. In Ghidra, find the function called early that loops over `.rodata`
   with XOR or ADD operations; it usually takes (address, length, key).
2. Note its output buffer address (often `.bss`).
3. In gdb, break on the instruction after the decrypt call returns.
4. Dump the buffer: `x/s` for single strings, `dump binary memory` for
   tables.

```bash
(gdb) break *0x5555555552c8   # after decrypt_strings() returns
(gdb) run
(gdb) x/5s 0x555555557060     # decrypted strings appear here
# "Enter the flag: " "Correct! " "Wrong! " ...
```

If decryption happens lazily (per string, just before printing), hook the
print function with Frida and log its argument instead; you get plaintext
without finding the decrypt routine at all.

## 4. Control-flow flattening

Flattening rewrites functions into one loop over a state variable with a
giant switch; the decompiler shows a single `while(1)` with dozens of
cases. Do not read it linearly.

- In the Function Graph view, identify the dispatcher block (the switch
  header) and ignore it.
- Find blocks that reference your input buffer or the success string;
  those are the only blocks that matter.
- Trace execution dynamically: break on the interesting blocks and log
  the state variable to learn the real execution order.
- Reconstruct the original order from the trace, then read just those
  blocks in sequence.

For automated help, symbolic execution (angr) can sometimes solve
flattened checks without manual reading, but in CTFs the dynamic trace
approach is usually faster.

## 5. Custom virtual machines

Some challenges compile the check into bytecode for a bespoke VM. The
binary contains: a bytecode array, a dispatch loop, and handler functions.

1. Find the dispatch loop: a loop with an indirect jump or a switch on
   `bytecode[pc++]`.
2. Enumerate handlers: each case is an opcode (PUSH, XOR, JZ, CMP, OUT).
3. Label 10 to 20 handlers; that is usually enough to understand the
   program.
4. Write a Python VM that executes the bytecode and prints the flag, or
   use Frida to hook the dispatch loop and log `(pc, opcode, stack)`.

```python
#!/usr/bin/env python3
# Skeleton: reimplement the VM once handlers are labeled
bytecode = open("bytecode.bin", "rb").read()
stack, pc, out = [], 0, bytearray()
while True:
    op = bytecode[pc]; pc += 1
    if op == 0x01:   # PUSH imm8
        stack.append(bytecode[pc]); pc += 1
    elif op == 0x02: # XOR top two
        a, b = stack.pop(), stack.pop(); stack.append(a ^ b)
    elif op == 0x03: # OUT: append top to output
        out.append(stack.pop())
    elif op == 0xFF: # HALT
        break
print(out)
```

## 6. Common anti-analysis tricks and bypasses

- `ptrace(PTRACE_TRACEME)`: LD_PRELOAD a stub returning 0, or patch the
  binary's check.
- Timing checks (`rdtsc` deltas, `alarm`): run under Frida instead of
  single-stepping, or NOP the check after locating it.
- `/proc/self/status` TracerPid inspection: hide with the same
  LD_PRELOAD trick, intercepting `open`/`read` on that path.
- Junk code and opaque predicates: dynamic tracing reveals which
  branches actually execute; statically, look for conditions that are
  constant (`(x*x) < 0` is never true for real x... except it can be
  with overflow, so verify dynamically).
- Stripped VM handlers: label by behavior after one traced run, not by
  guessing from disassembly.

## Edge cases

- The packer is UPX but the binary still shows garbage strings after
  `upx -d`: there is a second layer (string encryption); continue with
  section 3.
- Runtime dump has no ELF headers: Ghidra can still analyze raw dumps;
  create a memory map manually or use the dumped bytes as a blob for
  string and constant extraction.
- The VM bytecode is itself encrypted: find the bytecode decrypt
  (runs before the VM loop) and dump the plaintext bytecode first.
- OEP finding loops forever: the stub may be a protector with
  anti-dump; try breaking on `mprotect`/`mmap` syscalls with strace to
  see when regions become executable, then dump there.
- The binary detects the sandbox itself (not just the debugger): run it
  on bare metal or a different VM platform; CTF anti-analysis sometimes
  fingerprints the hypervisor.

## Escalation

- No OEP pattern visible (the stub jumps through several layers):
  use `strace -e mprotect` to watch executable regions appear, and
  dump each new RX region.
- Handlers number in the hundreds: do not label them all; trace one
  real execution with Frida Stalker and label only executed handlers.
- The challenge combines packing, string encryption, AND a VM: peel
  strictly outside-in, verifying each layer's output before attacking
  the next; skipping layers causes confusion about which garbage is
  whose.
- Time is short: check whether the flag or key material is visible in
  the packed binary's overlay or resources; authors sometimes leave
  the answer in the outer layer.

## Detection and defender view

Defenders meet these techniques in malware: packers (UPX, Themida),
string encryption, and VM-based protectors are standard malware
evasion. Sandboxes counter with runtime dumping (exactly section 2),
API tracing, and memory scanning for unpacked payloads. EDR detections
key on the behaviors: `mprotect` RWX transitions, process hollowing
patterns, and decrypted payloads in memory. For CTF players, the
takeaway is that every layer is removable with patience; for defenders,
that no client-side obfuscation survives a determined analyst, so
critical logic belongs server-side.

## Key references

- MITRE ATT&CK T1027 (Obfuscated Files or Information) and T1140
  (Deobfuscate/Decode Files or Information).
- MITRE ATT&CK T1620 (Reflective Code Loading): runtime unpacking.
- CWE-798 (Use of Hard-coded Credentials): keys hidden in packers.
- UPX documentation: https://upx.github.io/
- Frida Stalker (code tracing): https://frida.re/docs/stalker/
