---
name: angr-basics
description: Use when you need symbolic execution to explore program paths
  automatically, typically for CTF binaries, crackmes, or vulnerability
  research on code you are authorized to analyze. Covers loading binaries
  into angr projects, CFG recovery, finding states that reach a target
  address, avoiding bad paths, constraining symbolic input, and managing
  state explosion. Use when brute force or manual reversing is too slow, or
  when you need the exact input that triggers a specific code path.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [static-triage, python-cli-tooling]
tools:
  - name: angr
    version: 10.0.4
  - name: Python
    version: 3.12
---

angr is a symbolic execution engine: instead of running a program with
concrete inputs, it runs it with symbolic inputs and explores many paths at
once, asking a solver for the input that reaches a chosen address. That
makes it the right tool for crackmes ("find the input that prints success"),
for reaching deep code paths, and for vulnerability discovery on authorized
targets. This skill covers the practical basics: project setup, CFG
recovery, the classic find/avoid workflow, symbolic stdin and arguments,
adding constraints, and keeping state explosion under control. Scope:
analyze only binaries you are authorized to reverse (CTFs, crackmes, your own
software, client code under assessment). Symbolic execution is a research
technique, not a weapon; do not use it to develop exploits against systems
you do not own or have no permission to test.

## Quick Workflow

1. Inspect the binary (architecture, protections) and decide the goal
   address: the "success" print, the vulnerable function, the target block.
2. Create the angr project with the right options (do not auto-load
   libraries unless you need them).
3. Recover the CFG to understand the program shape and locate addresses.
4. Build the initial state with symbolic input (stdin or argv).
5. Run the simulation manager with find and avoid addresses.
6. Read the solver's answer: the concrete input for the found state.
7. Verify by running the real binary with that input.
8. If it explodes or stalls, constrain the problem (see section 6) and
   retry.

## 1. Reconnaissance before symbolic execution

angr works best when you already know the binary's shape. Five minutes of
recon saves hours of solver time.

```bash
# Architecture, bitness, protections
file crackme
checksec --file=crackme 2>/dev/null || python3 -c "
import subprocess
out = subprocess.run(['readelf','-W','-l','crackme'],capture_output=True,text=True).stdout
print('NX/RELRO/PIE hints:'); print([l for l in out.splitlines() if 'GNU_' in l][:5])"

# Find the interesting addresses with strings + disassembly first
strings crackme | grep -iE 'success|correct|flag|win' | head
objdump -d crackme | grep -B2 -A2 'success' | head -30
```

Note the addresses of the success path and the failure path; those become
your find and avoid targets. If the binary reads from stdin, plan symbolic
stdin; if from argv, plan symbolic arguments.

## 2. Project setup and CFG

Load the binary, recover the control flow graph, and confirm angr sees the
same functions you do.

```python
#!/usr/bin/env python3
"""angr basics: load a binary and recover its CFG."""
import angr

# auto_load_libs=False keeps it fast; set True only if the target needs
# shared library code to reach the goal
proj = angr.Project('./crackme', auto_load_libs=False)
print('arch:', proj.arch.name, 'entry:', hex(proj.entry))

# Fast CFG recovery
cfg = proj.analyses.CFGFast()
print('functions found:', len(cfg.kb.functions))
for addr, func in list(cfg.kb.functions.items())[:10]:
    print(hex(addr), func.name)
```

```bash
python3 cfg_recon.py
```

If `CFGFast` misses functions (common with indirect jumps), try the
slower `CFGEmulated` on the region of interest, or normalize the function
addresses from your Ghidra/objdump recon and feed them directly as find
targets.

## 3. The find/avoid workflow

This is the core pattern: start at entry with symbolic input, explore until
a state reaches the success address, while discarding states that hit the
failure address.

```python
#!/usr/bin/env python3
"""Solve a crackme: find input that reaches the success address."""
import angr
import claripy

proj = angr.Project('./crackme', auto_load_libs=False)

# Addresses from recon (example values: replace with yours)
SUCCESS = 0x401234
FAILURE = 0x401280

# Symbolic stdin: 32 bytes of unknown input
stdin = claripy.BVS('stdin', 32 * 8)
state = proj.factory.full_init_state(args=['./crackme'], stdin=stdin)

# Keep input printable and newline-terminated for sanity
for b in stdin.chop(8):
    state.solver.add(b >= 0x20, b <= 0x7e)
state.solver.add(stdin.get_byte(31) == 0x0a)

simgr = proj.factory.simulation_manager(state)
simgr.explore(find=SUCCESS, avoid=FAILURE)

if simgr.found:
    found = simgr.found[0]
    answer = found.solver.eval(stdin, cast_to=bytes).rstrip(b'\n')
    print('INPUT:', answer)
    open('solution.txt', 'wb').write(answer)
else:
    print('no path found; deadended:', len(simgr.deadended),
          'avoided:', len(simgr.avoid))
```

```bash
python3 solve.py
# Verify against the real binary, always
./crackme < solution.txt
```

The verification step is not optional: solver quirks, concretization, and
unmodeled syscalls can produce inputs that work symbolically but fail for
real.

## 4. Symbolic argv and constrained input

Binaries that take arguments need symbolic argv; binaries with known input
structure need constraints so the solver does not wander.

```python
import angr, claripy
proj = angr.Project('./crackme', auto_load_libs=False)

# Symbolic command-line argument instead of stdin
arg = claripy.BVS('arg', 16 * 8)
state = proj.factory.entry_state(args=['./crackme', arg])
for b in arg.chop(8):
    state.solver.add(b >= 0x20, b <= 0x7e)

# Constrain a known prefix (e.g., flag format flag{...})
state.solver.add(arg.get_byte(0) == ord('f'))
state.solver.add(arg.get_byte(1) == ord('l'))
state.solver.add(arg.get_byte(2) == ord('a'))
state.solver.add(arg.get_byte(3) == ord('g'))
state.solver.add(arg.get_byte(4) == ord('{'))

# Hook noisy functions you do not care about (e.g., skip a sleep or RNG)
# proj.hook(addr_of_noisy_func, angr.SIM_PROCEDURES['stubs']['ReturnUnconstrained']())
```

Constraints are how you inject knowledge: input length, character sets,
magic prefixes, checksums you already reversed. Every good constraint cuts
the search space dramatically.

## 5. Reading solver output and debugging stalls

When exploration finishes, interrogate the states; when it stalls, find out
where it is stuck.

```python
# After explore(): inspect where the stashes ended up
print('found:', len(simgr.found))
print('avoid:', len(simgr.avoid))
print('deadended:', len(simgr.deadended))
print('active:', len(simgr.active))

# What is the most common address among active states? (likely a loop)
from collections import Counter
addrs = Counter(s.addr for s in simgr.active)
print(addrs.most_common(5))

# Concrete input for a found state, plus the path length
s = simgr.found[0]
print('steps:', len(s.history.bbl_addrs))
print(s.solver.eval(stdin, cast_to=bytes))
```

If most active states sit at one address, you have found a loop or a
blocking syscall. That is normal; the fixes are in the next section.

## 6. Managing state explosion

Symbolic execution explodes when paths multiply: loops, large inputs, and
unmodeled environment calls. Fight back in this order.

```python
# 1. Bound loops: hook the loop head to limit iterations
# 2. Reduce symbolic bytes: make only the unknown part symbolic
known_prefix = b'flag{'
sym_part = claripy.BVS('sym', 8 * 8)
concrete_stdin = claripy.Concat(claripy.BVV(known_prefix), sym_part)

# 3. Veritesting: merge paths statically to reduce state count
state = proj.factory.full_init_state(args=['./crackme'], stdin=stdin)
simgr = proj.factory.simulation_manager(state, veritesting=True)

# 4. Step in rounds with a state cap instead of one unbounded explore
for _ in range(20):
    simgr.step()
    simgr.move(from_stash='active', to_stash='pruned',
               filter_func=lambda s: len(simgr.active) > 200)
    if simgr.found:
        break
```

Additional levers: `auto_load_libs=False` (already default in the examples),
hooking libc functions that do not matter, avoiding GUI or network code
paths, and splitting the problem (solve stage 1, then use its output as
concrete input for stage 2). If a binary is heavily obfuscated, do static
cleanup in Ghidra first; angr is not a deobfuscator.

## Edge cases

- PIE binary: addresses shift at load; use `proj.loader.main_object` offsets
  or resolve symbols by name instead of hardcoding addresses.
- Binary needs environment (env vars, files): add them to the state
  (`state = proj.factory.full_init_state(..., env={'HOME': '/tmp'})`) or the
  path diverges from reality.
- angr version churn: APIs move between releases; pin the version
  (10.0.4 here) and check the docs for your exact version when a call fails.
- Solver is slow on bitvector division/modulo: these operations are
  expensive; if the crackme is crypto-heavy, consider whether symbolic
  execution is the right tool at all.
- Multi-threaded or fork-heavy binaries: angr models single-threaded
  execution; results may not transfer.

## Escalation

- angr cannot reach the target: go back to static analysis, reverse the
  checks manually, and use angr only for the sub-problem you cannot do by
  hand (e.g., one complex constraint).
- Need directed fuzzing instead: pair angr with a fuzzer (AFL++ with
  symbolic assistance) for vulnerability discovery on larger binaries.
- Target is a firmware blob or non-standard arch: confirm angr supports the
  architecture via its archinfo/CLE loaders; otherwise use Ghidra plus
  QEMU-based dynamic analysis.
- Real vulnerability research: once angr finds a crashing input, triage the
  crash for exploitability with standard tooling, within your authorized
  scope, and disclose responsibly.

## Detection and defender view

From the defender side, angr-style analysis is what happens to your
software in an attacker's lab, which is an argument for defense in depth
rather than obscurity: assume any client-side check can be solved
symbolically and never trust the client for security decisions. For
detection engineering, the behaviors angr helps uncover (buffer overflows,
format strings, use-after-free) map to the memory-corruption mitigations
defenders deploy: ASLR, DEP/NX, stack canaries, and Control Flow Integrity.
The misuse case is using symbolic execution to develop exploits against
systems without authorization; this skill is for CTFs, crackmes, and
authorized research, and crossing that line is out of scope.

## Key references

- MITRE ATT&CK T1203 (Exploitation for Client Execution): the vulnerability
  class this research targets.
- CWE-787 (Out-of-bounds Write), CWE-416 (Use After Free), CWE-119
  (Improper Restriction of Operations within the Bounds of a Memory Buffer):
  typical findings.
- angr documentation: https://docs.angr.io
- angr on PyPI: https://pypi.org/project/angr/
- claripy solver docs (ships with angr): https://docs.angr.io/en/latest/api.html
