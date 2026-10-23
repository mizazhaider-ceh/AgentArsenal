---
name: ctf-reversing-basics
description: Use when competing in a CTF reverse engineering challenge,
  practicing in a lab, or analyzing a binary you are authorized to examine.
  Covers the reversing workflow, identifying file type and protections,
  triaging with strings and basic static analysis, navigating Ghidra
  decompilation to find the flag logic, dynamic debugging with gdb to watch
  values at runtime, defeating common obfuscation (packing, XOR, control
  flow flattening), and scripting keygen or decryption solvers in Python.
  Use when a challenge hands you a binary that checks input or transforms
  data, when strings show no flag, or when you need to understand what a
  program does before exploiting or bypassing it.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ghidra-basics, ctf-pwn-basics]
tools:
  - name: Ghidra
    version: 11.3
  - name: GDB
    version: 15.2
  - name: Python
    version: 3.12
  - name: binutils
    version: 2.42
  - name: Frida
    version: 16.5
---

Reverse engineering is reading a program to understand what it does without
source code, usually to find how it validates a flag, hides a secret, or
transforms input. This skill covers the standard authorized CTF reversing
workflow: quick triage to classify the binary, static analysis in Ghidra to
read the logic, dynamic analysis in gdb to observe runtime values, handling
the obfuscation tricks CTF authors love, and writing a solver that
reproduces the flag. Everything here applies to CTF competitions, lab
binaries, and software you have explicit permission to analyze.

## Quick Workflow

1. Triage the file: `file`, `strings`, `checksec`, and `ltrace`/`strace`
   to classify it (native, packed, .NET, script bundled, VM).
2. Look for the flag format or input prompt in strings; many easy
   challenges end here.
3. Open the binary in Ghidra, run auto-analysis, and find `main` (via
   `entry` -> `__libc_start_main` argument on Linux).
4. Read the decompilation of the input-checking function; rename
   variables and add comments as you understand them.
5. Identify the transform: XOR loop, arithmetic, table lookup, hash
   compare, or custom VM; note constants and expected values.
6. If static reading stalls, run the binary under gdb, break at the
   check function, and inspect registers and memory with real input.
7. Write a Python solver that inverts the transform (reverse the XOR,
   brute force the key, or reimplement the algorithm).
8. Validate the solver output matches the expected flag format before
   submitting.

## 1. Triage: file, strings, and behavior

Two minutes of triage often classifies the whole challenge.

```bash
file ./rev
# ELF 64-bit LSB executable, x86-64 ... not stripped  -> native, symbols present
# ELF 64-bit ... stripped                              -> native, harder
# PE32 executable                                      -> Windows binary (use wine or a VM)

strings -n 8 ./rev | head -40
# look for: flag{, "Enter password", "Correct", "Wrong", suspicious base64

checksec ./rev          # protections matter less for reversing, but note PIE for gdb

# watch what it does without reading code
echo "test" | strace -f -e trace=read,write ./rev 2>&1 | head -30
ltrace -e strcmp,memcmp ./rev <<< "test"   # reveals comparison calls and args
```

If `strings` shows `UPX` markers or section names like `UPX0`/`UPX1`, the
binary is packed: `upx -d ./rev -o ./rev_unpacked` and restart triage on
the unpacked file.

## 2. Ghidra static analysis essentials

Ghidra's auto-analysis plus decompiler view is the fastest path to
understanding.

1. Import the binary, let analysis finish, open the CodeBrowser.
2. In the Symbol Tree, find `main` (or `entry`, then follow the first
   argument of `__libc_start_main`).
3. Read the decompiler panel: look for input functions (`scanf`, `fgets`,
   `read`), then the checking logic after them.
4. Rename variables (press `L`): `local_28` becomes `user_input`,
   `local_10` becomes `expected`.
5. Follow cross-references (right-click -> References) on interesting
   strings like `"Correct!"` to land on the check function.
6. For data tables, hover to see bytes; right-click -> Data -> Array to
   view a 256 byte substitution table properly.

Typical flag-check shape in decompilation:

```c
fgets(user_input, 64, stdin);
for (i = 0; i < 32; i++) {
    if ((user_input[i] ^ 0x42) != expected[i]) {
        puts("Wrong!");
        return 1;
    }
}
puts("Correct!");
```

The solver inverts it: `flag[i] = expected[i] ^ 0x42`. Read `expected`
from Ghidra's listing (the `.rodata` bytes) and script the rest.

## 3. Dynamic analysis with gdb

When static reading is ambiguous (computed values, anti-debug timing),
watch the program run.

```bash
gdb -q ./rev
(gdb) break main
(gdb) run <<< "AAAAAAAAAAAAAAAA"
(gdb) break *0x5555555551a9     # address of the check loop from Ghidra
(gdb) continue
(gdb) x/32bx $rsi               # inspect the buffer being checked
(gdb) info registers rax rdi    # watch comparison results
(gdb) stepi / nexti             # walk the transform instruction by instruction
```

Useful patterns: break on `strcmp`/`memcmp` and print arguments
(`x/s $rdi`, `x/s $rsi`) to see exactly what the program compares your
input against; this alone solves many challenges. For `ptrace`-based
anti-debugging, patch the check out (set `$rax = 0` after the ptrace
call) or use Frida to hook instead of gdb.

## 4. Common transforms and solver patterns

Most CTF reversing challenges use a small set of transforms. Recognize the
shape, then invert it.

```python
#!/usr/bin/env python3
# Pattern A: single-byte XOR with constant key
expected = bytes.fromhex("...")  # copied from Ghidra .rodata
flag = bytes(b ^ 0x42 for b in expected)

# Pattern B: multi-byte repeating XOR key
key = b"secret"
flag = bytes(b ^ key[i % len(key)] for i, b in enumerate(expected))

# Pattern C: arithmetic (add/sub with wraparound) -> invert the operation
flag = bytes(((b - 7) & 0xff) for b in expected)   # program did (c + 7) & 0xff

# Pattern D: position-dependent (i added to each byte)
flag = bytes(((b - i) & 0xff) for i, b in enumerate(expected))

# Pattern E: substitution table (256 byte S-box in .rodata)
sbox = bytes([...])              # copied from Ghidra
inv = bytes(sbox.index(b) for b in range(256))
flag = bytes(inv[b] for b in expected)
```

When the transform is not invertible by inspection (hash compare like
`sha256(input) == digest`), the intended path is usually brute force over
a small input space or a keygen-me where you reimplement the algorithm;
check the input length first.

## 5. Handling obfuscation

CTF authors add layers: packing, string encryption, control-flow
flattening, and custom VMs.

- Packed (UPX, custom): unpack first (`upx -d`); for custom packers,
  let it run to the original entry point in gdb, then dump memory
  (`gcore` or `dump binary memory`).
- Encrypted strings: find the decryption routine (called early, loops
  over `.rodata`), break after it in gdb, and read the decrypted strings
  from memory.
- Control-flow flattening: the decompiler shows one giant switch loop;
  focus on the basic blocks that touch input and the success string,
  ignore dispatcher noise.
- Custom VM: identify the opcode dispatch table and handlers, then either
  reimplement the VM in Python or hook it with Frida to log execution.

## Edge cases

- Stripped Go or Rust binaries: huge, unfamiliar control flow; search
  strings for the prompt text and work backward from there instead of
  reading `main`.
- The binary is a PyInstaller bundle: extract with `pyinstxtractor`,
  then decompile the `.pyc` with `uncompyle6` or `pycdc`.
- .NET assemblies: use `ilspyc` or dnSpy-style decompilers, not Ghidra;
  the logic is usually plain C#.
- Input is read from argv or a file, not stdin: check `main`'s argument
  handling and any `fopen` calls before assuming interactive input.
- The check runs in a child process or thread: attach gdb with
  `set follow-fork-mode child` or break on `clone`.
- Anti-debug `ptrace`: the program exits under gdb; bypass by patching
  the binary, using `LD_PRELOAD` to fake ptrace, or switching to Frida
  instrumentation.

## Escalation

- Ghidra decompilation is unreadable (flattened or virtualized): drop
  to the disassembly view and trace data flow manually, or switch to
  dynamic analysis and let the program show you the values.
- The transform uses unknown constants from memory: break in gdb right
  before the check and dump the buffers; runtime values beat static
  guessing.
- Solver output is close but not the flag format: check for off-by-one
  in the loop bound, an extra newline in expected data, or a final
  transform applied after the loop you reversed.
- Custom crypto you cannot invert: look for the encryption routine being
  called with known plaintext (chosen-plaintext in the binary itself),
  which often leaks the key schedule.
- Time is running out: search strings for partial flags, try the
  challenge author's handle as XOR key, and check for `flag.txt`
  embedded as a resource.

## Detection and defender view

Defenders encounter reversing from the other side: malware analysts use
exactly these techniques on hostile binaries, inside isolated sandboxes,
with network access cut. For software protection, defenders use the same
obfuscation (packing, control-flow flattening, white-box crypto) to raise
the cost of analysis, plus license checks and tamper detection. Detection
of malicious reversing activity focuses on debugging artifacts (unexpected
`ptrace`, debuggers attached to production processes) and on telemetry
from EDR tools watching process memory dumps. The durable lesson: never
embed secrets in client-side code; any check the client performs can be
read and inverted.

## Key references

- MITRE ATT&CK T1027 (Obfuscated Files or Information) and T1140
  (Deobfuscate/Decode Files or Information): the obfuscation half.
- CWE-798 (Use of Hard-coded Credentials): embedded secrets and keys.
- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm): weak
  custom transforms.
- Ghidra documentation: https://ghidra-sre.org/documentation.html
- GDB manual: https://sourceware.org/gdb/documentation/
- "Practical Malware Analysis" (Sikorski and Honig): chapters on static
  and dynamic analysis transfer directly to CTF reversing.
