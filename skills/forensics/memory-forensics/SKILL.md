---
name: memory-forensics
description: "Use when analyzing a RAM dump or live memory image during incident response or a forensic investigation. Covers Volatility 3 workflows for Windows, Linux, and macOS: profile detection, process enumeration, injected code discovery with malfind, hollowed processes, network connection history, credential artifacts, and carving executables from memory. Use when the disk looks clean but the endpoint behaved maliciously, or when you need to recover what was running at acquisition time."
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [forensics-fundamentals, incident-response]
tools:
  - name: Volatility 3
    version: 2.28.2
  - name: Python
    version: 3.12
  - name: GNU Binutils
    version: 2.44
---
Memory forensics examines a snapshot of RAM to answer one question: what was
actually running when the image was captured. Disks can be wiped, logs can be
cleared, and files can be deleted, but a live process leaves traces in memory
that are much harder to erase. This skill covers the Volatility 3 workflow end
to end: validating the image, identifying the operating system, enumerating
processes, finding injected or hollowed code, recovering network and
credential artifacts, and dumping suspicious processes for deeper static
analysis. Scope: analyze memory images you are authorized to handle only
(your own lab systems, client systems under an incident response retainer, or
CTF challenge files). A memory image can contain passwords, keys, and private
user data, so treat every sample as sensitive and keep it off shared storage.

## Quick Workflow

1. Hash the image and work only on a copy, so the original stays pristine for
   chain of custody.
2. Run `windows.info`, `linux.pslist`, or `mac.pslist` to identify the OS and
   confirm Volatility can parse the image.
3. List processes three ways (`pslist`, `pstree`, `psxview`) and compare the
   outputs to spot hidden or unlinked processes.
4. Hunt injected code with `malfind` and hollowed processes with
   `hollowshunter`.
5. Recover network history (`netscan`, `netstat`) and command history
   (`cmdline`, `consoles`, `bash`).
6. Extract credential material (`hashdump`, `lsadump`, `cachedump`) only when
   the engagement scope allows it.
7. Dump suspicious processes and DLLs to disk (`memmap`, `procdump`,
   `dlldump`) for static triage.
8. Build a timeline with `timeliner` and correlate memory findings with disk
   and log evidence.

## 1. Image intake and OS identification

Never analyze the only copy. Hash first, then copy, then hash the copy.

```bash
# Hash the original before anything else
sha256sum /mnt/evidence/host01.mem | tee host01.sha256
cp /mnt/evidence/host01.mem ./host01.mem
sha256sum ./host01.mem

# Quick sanity: size and first bytes
ls -lh host01.mem
xxd -l 64 host01.mem

# Identify the operating system and kernel
vol -f host01.mem windows.info
vol -f host01.mem banners.Banners   # Linux kernel banner
```

If `windows.info` fails, the image may be Linux or macOS, a crash dump, or
corrupt. Try the Linux or macOS plugin families before declaring it broken.
Volatility 3 pulls Windows symbols automatically; for Linux and macOS you may
need symbol tables generated from the target kernel (see Edge cases).

```bash
# Fallback: ask every OS family what it sees
vol -f host01.mem linux.pslist | head -20
vol -f host01.mem mac.pslist | head -20
```

## 2. Process enumeration and cross-checks

List processes three ways and diff them. Malware that unlinks its EPROCESS
entry disappears from `pslist` but often still shows in `psxview`.

```bash
# All three process views, saved for comparison
vol -f host01.mem windows.pslist --output-dir ./out
vol -f host01.mem windows.pstree --output-dir ./out
vol -f host01.mem windows.psxview --output-dir ./out

# psxview flags: 'False' in pslist column but 'True' elsewhere = hidden process
grep -i false ./out/windows.psxview.txt 2>/dev/null | head -20

# Linux equivalents
vol -f host01.mem linux.pslist --output-dir ./out
vol -f host01.mem linux.pstree --output-dir ./out

# Command lines reveal what each process was actually doing
vol -f host01.mem windows.cmdline --output-dir ./out
vol -f host01.mem linux.cmdline 2>/dev/null | head -30
```

Read the output critically: a `svchost.exe` with no `-k` service group, a
`rundll32.exe` with no DLL argument, or a process whose parent is PID 0 are
all worth a second look. On Linux, watch for processes running from
`/dev/shm`, `/tmp`, or deleted executables (paths ending in ` (deleted)`).

## 3. Finding injected and hollowed code

`malfind` flags memory regions that are both writable and executable with no
backing file on disk, the classic signature of injected shellcode. The
`hollowshunter` plugin (from the community plugin set) compares the on-disk
image of a process with what is mapped in memory to catch process hollowing.

```bash
# Injected code: writable+executable private memory, no file backing
vol -f host01.mem windows.malfind --output-dir ./out --dump

# Dumped VAD regions land in the output dir; triage them by size
ls -lh ./out | grep -i malfind | head

# Hollowed processes: memory image differs from disk image
vol -f host01.mem windows.hollowshunter 2>/dev/null | head -30

# LDR module list vs memory scan: DLLs hidden from the loader list
vol -f host01.mem windows.ldrmodules | grep -v True | head -20

# Linux: check for injected shared objects via maps
vol -f host01.mem linux.proc.Maps 2>/dev/null | grep -iE 'rwx|heap' | head -20
```

Do not treat every `malfind` hit as malware. JIT compilers, .NET runtimes,
and some security products allocate RWX memory legitimately. The deciding
factor is context: an unknown RWX region inside `explorer.exe` or a
short-lived child of a document reader is suspicious; one inside a browser
renderer is usually not.

## 4. Network history and command activity

Memory holds sockets that closed hours ago and console buffers the user never
saved. This is often where the C2 server or the exfiltration destination
hides.

```bash
# Listening and established sockets (pools scan, works without symbols)
vol -f host01.mem windows.netscan | grep -iE 'ESTAB|LISTEN' | head -40
vol -f host01.mem windows.netstat 2>/dev/null | head -40

# Linux network state
vol -f host01.mem linux.netstat 2>/dev/null | head -40

# Console buffers: typed commands, attacker output, pasted strings
vol -f host01.mem windows.consoles | head -60
vol -f host01.mem windows.cmdscan | head -60

# Linux bash history recovered from memory
vol -f host01.mem linux.bash 2>/dev/null | head -60

# Environment variables can leak credentials and proxy config
vol -f host01.mem windows.envars | grep -iE 'pass|key|token|proxy' | head -20
```

Correlate every external IP against the case timeline. An established
connection to an IP with no matching DNS query in the logs and no business
reason to exist is a lead, not a conclusion.

## 5. Credential artifacts (scope-gated)

Dump credential material only when the engagement explicitly permits it.
These plugins read LSASS and registry hives from the image.

```bash
# SAM hashes (needs SYSTEM + SAM hives present in the image)
vol -f host01.mem windows.hashdump

# LSA secrets: service account passwords, cached credentials
vol -f host01.mem windows.lsadump

# Domain cached credentials
vol -f host01.mem windows.cachedump

# Linux: shadow entries are on disk, but keys and tokens live in memory
vol -f host01.mem linux.bash | grep -iE 'ssh|aws_|token' | head
```

Handle output like live credentials: encrypted storage, limited access, and
destroyed or returned at case close. If the scope says triage only, note the
presence of credential artifacts without extracting values.

## 6. Dumping processes for static triage

A dumped process is a PE file you can feed to YARA, Ghidra, or your malware
skills without ever running it.

```bash
# Dump a whole process by PID (from pslist)
vol -f host01.mem windows.memmap.Memmap --pid 1234 --dump --output-dir ./dumps

# Rebuild a runnable-ish executable from the process image
vol -f host01.mem windows.procdump.Procdump --pid 1234 --output-dir ./dumps

# Dump every loaded DLL of a suspicious process
vol -f host01.mem windows.dlldump.Dlldump --pid 1234 --output-dir ./dumps

# Carve all executables from the image without knowing PIDs
vol -f host01.mem windows.peb 2>/dev/null | head
```

Verify dumps before trusting them: check the PE header (`MZ`), the section
table, and whether the entry point region was actually resident. A dump with
paged-out code sections will crash a disassembler or produce garbage.

```bash
file ./dumps/*.dmp | head
xxd -l 2 ./dumps/pid.1234.dmp
```

## 7. Timelining

`timeliner` merges process creation, registry, file, and network events into
one CSV. Filter it hard, or it drowns you.

```bash
# Full timeline to CSV, then slice it
vol -f host01.mem timeliner.Timeliner --output-file timeline.csv

# Events around the suspected compromise window (example: 02:00 to 04:00)
grep -E '2026-10-2[23] 0[234]:' timeline.csv | head -40

# Process creation events only
grep -i 'ProcessCreation\|process_create' timeline.csv | head -40
```

## Edge cases

- `windows.info` reports the wrong profile or nothing: the image may be a
  hibernation file or crash dump, which needs conversion first (`hibinfo`,
  then extract). Pagefile-backed content is incomplete by design.
- Linux plugins fail with symbol errors: generate symbols from the exact
  kernel with dwarf2json, or grab the matching symbol pack from the
  Volatility Foundation downloads. A close-but-wrong kernel version produces
  plausible-looking garbage.
- 32-bit process on a 64-bit image: use the `windows.pslist` output to check
  the Wow64 flag; pointer sizes differ and some plugins need the right
  layering to read them.
- Huge images (64 GB+): run plugins with `--output-dir` on fast local
  storage, skip `timeliner` until the end, and consider `windows.pslist`
  before anything expensive.
- Encrypted or compressed RAM (BitLocker hibernation, macOS): you need the
  recovery key or the live system; there is no supported brute force path.
- `malfind` floods with false positives: scope it to suspicious PIDs with
  `--pid` instead of scanning the whole image.

## Escalation

- Standard plugins see nothing but behavior says malware: try the community
  plugin repository (hollowshunter, cmdline plugins, driver enumeration with
  `windows.modscan`), and run `windows.modules` plus `windows.driverscan` to
  catch kernel-mode implants.
- Rootkit unhooks everything: compare `pslist` against `psscan` (pool tag
  scanning finds processes the linked list hides), and `modules` against
  `modscan`.
- Need strings context fast: run `strings` on the image and grep for the
  suspicious IP or mutex name, then map the offset back to a process with
  `windows.vadinfo`.
- Image is a VM snapshot (`.vmem`, `.vmsn`): Volatility reads `.vmem`
  directly; `.vmsn` needs the matching `.vmem` or conversion first.
- Symbol hell on Linux: fall back to `linux.banners` plus `strings` analysis,
  or acquire with a kernel module (AVML, LiME) that matches the target.

## Detection and defender view

From the defender side, memory forensics is the last line of visibility when
disk and log evidence is gone. Fileless malware, in-memory credential theft,
and living-off-the-land binaries leave almost no disk trace, which is exactly
why EDR tools now do their own memory scanning. For detection engineering:
alert on RWX private memory in processes that should not JIT-compile, on
processes with no image path or a path in a temp directory, and on LSASS
access from non-security processes (Sysmon Event ID 10 with
`TargetImage` ending in `lsass.exe`). The misuse case to watch for is
someone running these same plugins against a memory image they had no right
to acquire: control acquisition tightly, because a RAM dump is a credential
vault.

## Key references

- MITRE ATT&CK T1003 (OS Credential Dumping): what `hashdump` and `lsadump`
  recover.
- MITRE ATT&CK T1057 (Process Discovery) and T1055 (Process Injection):
  what `psxview` and `malfind` detect.
- MITRE ATT&CK T1033 (System Owner/User Discovery), T1049 (System Network
  Connections Discovery): memory artifacts of discovery activity.
- MITRE ATT&CK T1070.004 (File Deletion) and T1027 (Obfuscated Files or
  Information): why memory beats disk when attackers clean up.
- Volatility 3 documentation: https://volatility3.readthedocs.io
- Volatility 3 GitHub (community plugins): https://github.com/volatilityfoundation/volatility3
