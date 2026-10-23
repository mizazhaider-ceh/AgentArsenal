---
name: ctf-reversing-basics-dynamic-debugging
description: Use when dynamically analyzing a CTF reversing binary or an
  authorized lab binary with gdb. Covers breakpoint strategies on check
  functions and library calls, inspecting registers and memory with real
  input, dumping decrypted strings and computed tables at runtime,
  defeating ptrace anti-debugging, tracing with ltrace and strace, and
  using Frida hooks when gdb is blocked. Use when static analysis is
  ambiguous, when values are computed at runtime, or when you need to
  watch the exact bytes a check function compares.
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
  - name: Frida
    version: 16.5
  - name: Python
    version: 3.12
  - name: binutils
    version: 2.42
---

Dynamic debugging runs the program and inspects it while it executes,
which answers questions static analysis cannot: what values are actually
computed, what do decrypted strings look like, and what exactly is compared
against your input. This sub-skill covers the authorized gdb workflow for
CTF reversing: strategic breakpoints, memory inspection, runtime dumping of
hidden data, anti-debug bypasses, and Frida as the fallback when gdb is
blocked. Scope is CTF competitions, lab binaries, and software you have
explicit permission to analyze.

## Quick Workflow

1. Get the check function's address from Ghidra (image-base offset) and
   translate it for the PIE runtime base if needed.
2. Start the binary in gdb with a known input (e.g. 32 `A` characters)
   and break at the check function entry.
3. Inspect the input buffer and the expected buffer side by side
   (`x/32bx` on both pointers).
4. Step through the comparison loop once to learn the transform
   (watch one byte go through XOR, add, or table lookup).
5. Break on `strcmp`/`memcmp` instead when the check delegates to libc;
   print both arguments to see the exact expected value.
6. For encrypted strings or tables, break right after the decryption
   routine returns and dump the output buffer.
7. If the binary detects gdb (ptrace), bypass it (patch, LD_PRELOAD, or
   Frida) and repeat the session.
8. Copy runtime values into the Python solver and verify the output.

## 1. Breakpoints that solve challenges

Most reversing challenges are solved with three breakpoint types.

```bash
gdb -q ./rev
# PIE: disable ASLR for stable addresses while learning
(gdb) set disable-randomization on

# 1. Break at the check function (address from Ghidra, image base + offset)
(gdb) break *0x5555555552a0
# with ASLR disabled and no PIE, Ghidra image-base addresses work directly

# 2. Break on library comparison calls and print both sides
(gdb) break strcmp
(gdb) commands
> silent
> printf "strcmp(%s, %s)\n", $rdi, $rsi
> continue
> end

# 3. Break on memcmp with explicit lengths
(gdb) break memcmp
(gdb) commands
> silent
> x/s $rdi
> x/s $rsi
> printf "len=%d\n", $rdx
> continue
> end

(gdb) run <<< "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
```

The `strcmp`/`memcmp` argument dump is the single highest-value dynamic
technique: it prints the program's expected value directly, no reversing
of the transform needed.

## 2. Inspecting memory and registers

Learn the small set of gdb commands that covers 95 percent of reversing
needs.

```bash
(gdb) info registers          # all registers; watch rax after comparisons
(gdb) x/32bx $rsi             # 32 bytes hex at rsi (typical buffer arg)
(gdb) x/s $rdi                # C string at rdi
(gdb) x/16gx $rsp             # 16 giant words at stack pointer
(gdb) x/10i $pc               # next 10 instructions
(gdb) print/d $rax            # decimal value of rax
(gdb) stepi                   # one instruction
(gdb) nexti                   # one instruction, stepping over calls
(gdb) finish                  # run until current function returns
```

TUI mode (`gdb -tui`) shows source or disassembly alongside; `layout regs`
keeps registers visible while stepping. When a loop processes your input
byte by byte, `stepi` through two iterations and note which instruction
transforms the byte; that instruction IS the algorithm.

## 3. Dumping runtime-computed data

Decryption routines and key schedules produce values that never appear in
the binary statically. Capture them live.

```bash
# Break right AFTER the decrypt call returns (address from Ghidra)
(gdb) break *0x555555555310
(gdb) run
# at the breakpoint, rax (or the known out-pointer register) holds the buffer
(gdb) x/s $rax
# "flag{decrypted_at_runtime}"  -> copy this, challenge may end here

# Dump a computed 256 byte table to a file for the solver
(gdb) dump binary memory /tmp/table.bin $rax $rax+256
```

```bash
# Then in Python:
table = open("/tmp/table.bin", "rb").read()
```

For multi-stage decryption (string decrypted just before use), use a
hardware watchpoint on the buffer or break on the print function and read
its argument.

## 4. Defeating ptrace anti-debugging

CTF binaries sometimes call `ptrace(PTRACE_TRACEME)` and exit if a
debugger is present. Options, easiest first:

```bash
# Option A: patch the check. Find the ptrace call in Ghidra, note that
# it tests the return value; in gdb, force the success path:
(gdb) break *0x5555555551c3    # instruction after the ptrace call
(gdb) run
# or: set $rax = 0 right after the call returns

# Option B: LD_PRELOAD a fake ptrace that always succeeds
cat > /tmp/noptrace.c <<'EOF'
long ptrace(int req, int pid, void *a, void *b) { return 0; }
EOF
gcc -shared -fPIC -o /tmp/noptrace.so /tmp/noptrace.c
LD_PRELOAD=/tmp/noptrace.so gdb -q ./rev
```

Option C: skip gdb entirely and use Frida to hook the check function;
Frida's injection does not trip naive `ptrace` checks.

## 5. Frida hooks as a gdb alternative

Frida instruments without stopping the process, which defeats timing
checks and many anti-debug tricks.

```javascript
// hook.js: log memcmp arguments in a CTF binary
Interceptor.attach(Module.getExportByName(null, "memcmp"), {
    onEnter(args) {
        this.a = args[0].readCString();
        this.b = args[1].readCString();
        this.n = args[2].toInt32();
    },
    onLeave(retval) {
        console.log(`memcmp("${this.a}", "${this.b}", ${this.n}) = ${retval}`);
    }
});
```

```bash
frida -q -l hook.js -f ./rev -- <<< "AAAAAAAAAAAAAAAA"
# memcmp("AAAAAAAAAAAAAAAA", "s3cr3t_expected...", 32) = 65
```

The logged expected value often ends the challenge. Frida also traces
decryption: hook the decrypt function and dump its output buffer on
return.

## 6. strace and ltrace for behavior triage

Before deep debugging, watch system and library calls.

```bash
# Files opened, network, process behavior
strace -f -e trace=openat,read,write ./rev <<< "test" 2>&1 | head -40

# Library calls with arguments: reveals strcmp/memcmp usage instantly
ltrace -e strcmp+memcmp ./rev <<< "AAAAAAAAAAAAAAAA"
# memcmp("AAAAAAAAAAAAAAAA", "real_expected_value", 32) = 65
```

If `ltrace` already shows the expected value, the challenge is done;
write it down and move on. Time management matters in competitions.

## Edge cases

- The binary forks: use `set follow-fork-mode child` to trace the
  child, or `set detach-on-fork off` to debug both.
- Input comes from a file or argv: adjust the `run` invocation
  (`run $(cat input)` or `run input.txt`) instead of stdin redirection.
- The check runs in a thread: `info threads`, then `thread N` plus
  `break ... thread N` to target the right one.
- gdb `run` with heredoc hangs on interactive prompts: feed input via
  a file (`run < /tmp/in.txt`) for repeatability.
- Stripped binary, no symbols for `strcmp`: break on the PLT entry
  address from Ghidra (`break *0x...plt`) instead of by name.
- Frida fails on static binaries: fall back to gdb; Frida needs
  dynamic symbols or manual address computation from the image base.

## Escalation

- Breakpoints never hit: the address is wrong (PIE base mismatch) or
  the code path is not reached; verify with `info breakpoints` hit
  counts and a breakpoint on `main` first.
- The expected value changes per run (randomized check): the program
  generates the check at runtime; dump it fresh each run and solve
  dynamically, or find the PRNG seed.
- Anti-debug is more than ptrace (timing checks, /proc/self/status
  tracerpid): patch each check or move the whole analysis to Frida
  with `Stalker` for tracing.
- Values are correct but the solver still fails: check for a trailing
  transform after the loop (a final XOR on the whole buffer is a
  classic), or an off-by-one in the copied expected bytes.

## Detection and defender view

Defenders use these exact dynamic techniques in malware sandboxes:
breakpoints on suspicious API calls, memory dumps of decrypted payloads,
and API tracing. Malware fights back with the same anti-debug tricks
(ptrace, timing, VM detection) that CTF binaries imitate. EDR products
detect debugging through kernel callbacks and anomalous `ptrace` usage.
For CTF players the lesson is operational: dynamic analysis is the
fastest path through obfuscation, so learn the gdb and Frida workflows
until they are muscle memory.

## Key references

- MITRE ATT&CK T1027 (Obfuscated Files or Information) and T1056-adjacent
  input capture concepts; dynamic analysis maps to T1005-adjacent
  behaviors in sandboxes.
- CWE-798 (Use of Hard-coded Credentials): what runtime dumps reveal.
- GDB 15 manual: https://sourceware.org/gdb/documentation/
- Frida documentation: https://frida.re/docs/home/
- ltrace/strace manuals: https://www.ltrace.org/ and man strace.
