---
name: ctf-reversing-basics-static-analysis-ghidra
description: Use when statically analyzing a CTF reversing binary or an
  authorized lab binary in Ghidra 11.3. Covers project setup and
  auto-analysis, navigating from entry to main, reading decompiler output,
  renaming variables and functions, following cross-references to check
  routines, extracting .rodata constants and tables, handling stripped
  binaries, and scripting repetitive extraction with Ghidra Python. Use
  when strings show no flag, when you need the exact transform constants,
  or when dynamic analysis is blocked by anti-debugging.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-reversing-basics
requires: [ctf-reversing-basics]
extends: []
relates: [ghidra-basics, ctf-reversing-basics]
tools:
  - name: Ghidra
    version: 11.3
  - name: Python
    version: 3.12
  - name: binutils
    version: 2.42
---

Ghidra turns machine code into readable decompiled C, which makes it the
primary static analysis tool for CTF reversing. This sub-skill covers the
authorized Ghidra workflow in depth: setting up analysis for maximum
information, navigating efficiently from entry point to the flag logic,
using the decompiler as a reading aid (not gospel), extracting embedded
constants and lookup tables, and automating tedious extraction with Ghidra's
Python API. Scope is CTF competitions, lab binaries, and software you have
explicit permission to analyze.

## Quick Workflow

1. Create a project, import the binary, and run analysis with default
   options plus "Decompiler Parameter ID" for better signatures.
2. Open the CodeBrowser; in the Symbol Tree locate `entry`, then follow
   the first argument passed to `__libc_start_main` to reach `main`.
3. Search strings (Window -> Defined Strings) for the prompt, success,
   and failure messages; double-click to jump to their usage.
4. From each message, follow cross-references into the checking
   function and read its decompilation.
5. Rename unknowns as you decode them (`L` on a variable, `N` on a
   function); good names are half the reversing work.
6. Extract constants: highlight `.rodata` bytes, copy as C array, and
   paste into your Python solver.
7. For stripped binaries, label functions by behavior (`check_input`,
   `decrypt_strings`) and use FLIRT-style signature matching if
   available.
8. Export findings: copy the decompiled check function into your notes
   alongside the solver so the logic is reviewable.

## 1. From entry to main

On a Linux ELF, `main` is not called directly; the entry point passes it
to `__libc_start_main`. In the decompiler view of `entry` you will see
something like:

```c
__libc_start_main(main, argc, argv, ...);
```

Click `main` to jump there. On stripped binaries the symbol is missing;
instead look for the function with the familiar shape (calls to input
functions, a loop, then a success/failure print) or search for the prompt
string's cross-reference. For Windows PEs, start at the exported entry
and look for `GetDlgItemTextA`/`scanf`-style input calls.

## 2. Reading decompiler output effectively

The decompiler is an aid; verify suspicious output against the
disassembly (right-click -> Disassembly in the listing).

- `local_28`, `local_10`: stack locals. Rename by role once the role is
  clear (`L` key).
- `CONCAT44(a, b)`, `SUB168`: decompiler artifacts for multi-register
  values; check the disassembly to see the real operation.
- Ternary-heavy or goto-heavy output: the original had complex control
  flow; switch to the Function Graph view (Window -> Function Graph) to
  see the real structure.
- `in_FS_OFFSET`: thread-local storage access; on x86-64 Linux,
  `*(in_FS_OFFSET + 0x28)` is the stack canary, not challenge logic.

Keyboard habits that pay off: `G` (go to address), `X` (references to),
`Ctrl+F` (find), `;` (add comment), `[`/`]` (previous/next function).

## 3. Extracting constants and tables

Flag checks compare your input against embedded data. Get exact bytes.

1. In the listing, find the `.rodata` label holding the expected bytes
   (often referenced as `&DAT_00102020` in the check function).
2. Click the first byte, note the address, and check how many bytes the
   loop reads (the loop bound is the length).
3. Select the bytes, right-click -> Copy Special -> Copy Byte String, or
   read them with a Ghidra Python snippet:

```python
# Run in the Ghidra Script Manager (Python 3)
addr = toAddr(0x102020)   # start of expected data
length = 32               # loop bound from the check function
data = bytes(getBytes(addr, length))
print(data.hex())
```

For 256 byte S-boxes: right-click the label -> Data -> Create Array,
set element count 256, then copy the array. Paste the hex straight into
the solver; transcription errors are the top cause of "almost right"
flags.

## 4. Ghidra Python for repetitive extraction

When the binary has many similar check functions (multi-stage
challenges), script the extraction.

```python
# List all functions calling memcmp/strcmp and print their addresses
from ghidra.app.decompiler import DecompInterface

decomp = DecompInterface()
decomp.openProgram(currentProgram)
for func in currentProgram.getFunctionManager().getFunctions(True):
    for ref in getReferencesTo(func.getEntryPoint()):
        caller = getFunctionContaining(ref.getFromAddress())
        if caller and caller.getName() in ("memcmp", "strcmp"):
            target = getFunctionContaining(ref.getFromAddress())
            # actually we want callers OF memcmp; invert the loop in practice
            pass
print("adapt the loop direction: iterate references TO memcmp, read callers")
```

A more directly useful snippet: dump every defined string containing
"flag" or "correct":

```python
for s in currentProgram.getListing().getDefinedData(True):
    if s.getDataType().getName() == "string":
        val = str(s.getValue())
        if any(k in val.lower() for k in ("flag", "correct", "wrong")):
            print(hex(s.getAddress().getOffset()), repr(val))
```

## 5. Dealing with stripped and optimized binaries

Stripped binaries lose names but keep structure. Strategies:

- Identify standard library functions by behavior and relabel them
  (`FUN_00101130` that calls `write` in a loop is probably a print
  helper).
- Use the Version Tracking / signature analyzer if bundled signatures
  exist for the libc version.
- `-O2` code inlines everything: the "check function" may be inside
  `main`; search for the success string reference instead of a clean
  function boundary.
- Switch tables (jump tables for large switches) decompile poorly; view
  the jump table in the listing to enumerate cases.

## Edge cases

- The binary is position-independent (PIE): Ghidra shows image-base
  addresses; runtime addresses differ, so record offsets from the image
  base, not absolute addresses, for gdb breakpoints.
- Ghidra analysis hangs on huge binaries (Go/Rust): disable the
  "Non-Returning Functions" or ASCII string analyzers selectively, and
  analyze only the `.text` region of interest.
- The decompiler shows `undefined8` everywhere: retype key variables
  (right-click -> Retype Variable) to `char *` or `int` once you know
  their role; readability improves dramatically.
- Encrypted strings: the "strings" window shows garbage; find the
  decryption call (runs before main logic), note its output buffer, and
  read decrypted values dynamically or by reimplementing the routine.
- Ghidra project corruption: keep the binary import reproducible by
  scripting the analysis steps; re-importing is cheap, lost annotations
  are not, so export notes regularly.

## Escalation

- Auto-analysis produces no decompilation for the target function: the
  function may be data, not code; check for overlapping instructions or
  an unpacking stub, and define code manually (`D` key) at the right
  offset.
- Cross-references lead nowhere (indirect calls): the check may be
  invoked through a function pointer table; find the table in `.data`
  and enumerate its entries.
- The transform is a VM and static reading stalls: switch to the
  dynamic-debugging sub-skill; tracing execution beats reading a
  dispatcher.
- Constants are computed at runtime (not in .rodata): set a gdb
  breakpoint after the computation and dump memory; static extraction
  is impossible by construction.

## Detection and defender view

From the defender side, these same Ghidra skills are used by malware
analysts dissecting hostile binaries in sandboxes. Software vendors use
obfuscation (control-flow flattening, string encryption, VM-based
protection) specifically to raise the cost of this static analysis.
Detection of unwanted analysis includes anti-tamper checks that verify
code integrity at runtime. The durable defensive lesson remains: secrets
embedded in distributed binaries are recoverable; keep them server-side.

## Key references

- MITRE ATT&CK T1027 (Obfuscated Files or Information).
- CWE-798 (Use of Hard-coded Credentials).
- Ghidra 11.3 documentation: https://ghidra-sre.org/documentation.html
- Ghidra Scripting (Python API): https://ghidra-sre.org/InstallationGuide.html
- "The Ghidra Book" (Eagle and Nance): the standard reference.
