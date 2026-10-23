---
name: binary-patching-techniques-nop-and-jump-patching
description: Use when you need the precise mechanics of NOP and jump
  patching in x86/x64 binaries, covering instruction encodings, calculating
  padding, flipping conditional jumps, converting calls to NOP sleds,
  and patching in x64dbg versus on disk. Covers one-byte flips, multi-
  byte NOP fills, relative offset math, and verifying patches did not
  corrupt neighboring code. Use when neutralizing a check in an
  authorized lab, when learning patch mechanics, or when a patch must be
  byte-exact for reproducibility.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: [binary-patching-techniques]
extends: []
parent: binary-patching-techniques
relates: [binary-patching, binary-anti-analysis-bypass]
tools:
  - name: x64dbg
    version: 2025.06
  - name: Python
    version: 3.12
  - name: Ghidra
    version: 11.3
---

NOP and jump patching are the two atomic operations of binary
modification: remove an effect, or redirect a decision. Done right,
they change one behavior and nothing else; done sloppily, they corrupt
instruction alignment and crash the program. This sub-skill covers the
byte-level mechanics for the parent binary-patching-techniques skill.
Scope: patch only binaries you are authorized to modify, in an isolated
lab, for authorized analysis or testing. Never patch software to evade
licensing or protections without authorization.

## Quick Workflow

1. Disassemble the target region and identify the exact instruction
   bytes to change.
2. Decide: flip (jump), NOP-fill (call), or rewrite (short sequence).
3. Compute the replacement bytes, checking lengths match exactly.
4. Apply in the debugger first; test the behavior change.
5. Write to a file copy; verify neighboring disassembly is intact.
6. Record file offsets, before/after bytes, and rationale.

## 1. Conditional jump flips

Short conditional jumps are 2 bytes: opcode plus signed displacement.
Flipping the condition keeps the displacement:

```text
74 cb   je  target    ->  75 cb   jne target    (flip condition)
74 cb   je  target    ->  EB cb   jmp target    (always take)
75 cb   jne target    ->  EB cb   jmp target    (always take)
EB cb   jmp target    ->  90 90   nop; nop      (never take)
```

Near jumps (0F 84 .. ..) are 6 bytes; the same logic applies with the
two-byte opcode (0F 84 je becomes 0F 85 jne, or E9 for unconditional
with a 4-byte displacement). The displacement bytes never change when
you only flip the condition, so the target stays correct.

In x64dbg: select the jump, press Space, type the new mnemonic
(`jne`, `jmp`, `nop`), Enter. The assembler handles encoding; verify
the byte length matches the original in the hex dump.

## 2. NOP-filling calls and instructions

A call is 5 bytes (E8 + 4-byte relative offset). Replace with five
0x90 bytes:

```text
Before:  E8 3A 10 00 00   call 0x401250
After:   90 90 90 90 90   nop x5
```

For longer sequences, use multi-byte NOPs to keep alignment clean
(optional but tidy):

```text
66 90        2-byte nop
0F 1F 00     3-byte nop
0F 1F 40 00  4-byte nop
```

x64dbg does this automatically when you assemble `nop` over a selected
instruction: it fills the exact byte count. Rule: the replacement must
be exactly the same length as the original. Shorter leaves partial
instructions; longer overwrites the next instruction.

## 3. Relative offset math

When you must redirect a jump to a new target, compute the relative
displacement:

```python
def rel32(from_addr: int, to_addr: int, insn_len: int) -> bytes:
    # displacement measured from the END of the instruction
    disp = to_addr - (from_addr + insn_len)
    return disp.to_bytes(4, "little", signed=True)

# Example: at 0x401200, 5-byte jmp to 0x401500
print(rel32(0x401200, 0x401500, 5).hex())  # fb020000
# bytes: E9 FB 02 00 00   jmp 0x401500
```

For 2-byte short jumps the displacement is 1 byte (range -128..127);
if the target is farther, use the 5-byte near form instead. Always
verify in the disassembler after patching: the displayed target
address must be the intended one.

## 4. Patching on disk with Python

```python
path = "copy.exe"
data = bytearray(open(path, "rb").read())

# Patch at FILE OFFSET (not VA, not RVA)
off = 0x1234
orig = data[off:off+2]
assert orig == b"\x74\x1b", f"unexpected bytes: {orig.hex()}"
data[off:off+2] = b"\xeb\x1b"   # je -> jmp

open("copy_patched.exe", "wb").write(data)
print(f"patched file offset {off:#x}: {orig.hex()} -> eb1b")
```

Convert VA to file offset via section tables (or use pefile), and
always assert the original bytes before writing: if they do not match,
you are patching the wrong location or the wrong build.

## 5. Verification

```bash
# Disassemble the patched region and eyeball it
# In Ghidra/x64dbg: the patched instruction must decode cleanly AND
# the instructions before and after must be unchanged

# Byte-level diff of the two files
cmp -l original.exe patched.exe
```

Example output shape:

```text
  4660  74 353
```

One differing byte at file offset 4660 (0x1234): 0x74 became 0xEB.
Exactly the intended change, nothing else. If cmp shows more
differences than your patch, something else modified the file; start
over from a clean copy.

## Edge cases

- Patches inside packed code: patch the unpacked memory image, not
  the packed file; or unpack first, then patch the dump.
- Self-checking code: the program may checksum the patched region;
  patch the checksum routine first (document the chain).
- Patching data, not code: NOP-filling a data reference corrupts
  data; confirm the target is an instruction via disassembly.
- Concurrent threads executing the patched region: pause all threads
  in the debugger before patching live memory.
- Signed binaries: patching invalidates the signature; expected in
  the lab, never redistribute.

## Escalation

- If the needed patch is longer than the available space (no room
  for new logic), escalate to code-cave techniques or accept a
  simpler patch; do not overwrite adjacent functions.
- If patches must survive a protector's integrity checks, escalate:
  that is anti-tamper work, a separate engagement.

- If a patch must redirect execution to new code (not just skip), escalate to code-cave techniques; inline space is rarely enough.
- If the binary is signed and the lab requires a valid signature, note that no byte patch preserves it; assess tamper response instead.

## Detection and defender view

Byte-exact patch records (offset, before, after, rationale) make lab
work reproducible and defensible: another analyst applies the same
patch and gets the same behavior. When assessing tamper resistance
for a client, the finding is which checks fell to a one-byte flip
versus which resisted; that gap analysis drives hardening advice
(server-side checks, signature verification, anti-tamper). Never
distribute patched binaries outside the authorized engagement.

## Key references

- Intel 64 and IA-32 Architectures Software Developer Manuals:
  https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html
- x64dbg documentation:
  https://x64dbg.com/
- Ghidra documentation:
  https://ghidra-sre.org/
- Practical Binary Analysis (Dennis Andriesse), Chapter 6
  (disassembly concepts)

- x86 opcode reference:
  http://ref.x86asm.net/coder64.html
