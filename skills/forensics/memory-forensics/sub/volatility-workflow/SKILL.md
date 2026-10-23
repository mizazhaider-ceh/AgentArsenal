---
name: volatility-workflow
description: Use when analyzing a memory dump with Volatility 3 on an
  authorized forensic examination. Covers profile and symbol setup, the
  core plugin sequence, and interpreting output. Use when you have a RAM
  capture to examine, when hunting in-memory malware, when the disk shows
  nothing, or when building the standard memory analysis pass.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
parent: memory-forensics
requires: [memory-forensics]
extends: []
relates: [malware-in-memory, forensics-fundamentals]
tools:
  - name: Python
    version: 3.12
  - name: Volatility
    version: 2.5.2
---

Volatility 3 is the standard framework for memory dump analysis: it
reconstructs processes, network connections, and kernel structures from
raw RAM. This skill covers the core workflow: getting symbols working,
running the essential plugin sequence, and reading the output like an
examiner. It is the entry point; process-memory-triage and
malware-in-memory go deeper on their specialties.

## Quick Workflow

1. Verify the dump's integrity (hash) and identify the OS.
2. Set up symbols for the exact OS build.
3. Run the core plugin sequence: processes, network, modules.
4. Review output for anomalies: hidden processes, odd connections.
5. Dump suspicious processes and drivers for deeper analysis.
6. Correlate findings with the disk timeline.
7. Document every plugin run with its output file.

## 1. Setup and OS identification

```bash
# Verify the dump first
sha256sum /evidence/memdump.raw
ls -la /evidence/memdump.raw

# Volatility 3: identify the OS and get the profile hint
python3 /opt/volatility3/vol.py -f /evidence/memdump.raw \
  windows.info.Info 2>&1 | head -20
# Note the kernel version and build; symbols must match

# Symbol setup: Volatility 3 downloads PDB symbols automatically when
# online; for offline work, pre-stage the symbol pack for the build
python3 /opt/volatility3/vol.py -f /evidence/memdump.raw \
  windows.info.Info 2>&1 | grep -i 'kernel base'
```

Wrong symbols produce garbage or crashes: the single most common
Volatility failure is a symbol mismatch. Confirm the build matches
before trusting any output.

## 2. Core plugin sequence

```bash
V="python3 /opt/volatility3/vol.py -f /evidence/memdump.raw"

# Processes: the who of the memory image
$V windows.pslist.PsList --output-file /tmp/pslist.txt
$V windows.pstree.PsTree --output-file /tmp/pstree.txt

# Network: connections at capture time
$V windows.netstat.NetStat --output-file /tmp/netstat.txt

# Loaded modules and drivers
$V windows.modules.Modules --output-file /tmp/modules.txt
$V windows.driverscan.DriverScan --output-file /tmp/drivers.txt

# Review for anomalies: processes with no parent, odd names, strange paths
grep -i -E 'tmp|temp|appdata|programdata' /tmp/pslist.txt | head -10
grep -E 'ESTABLISHED' /tmp/netstat.txt | grep -v -E '127.0.0.1' | head -10
```

Run the sequence the same way every time; consistency makes anomalies
visible and the work reproducible. Save every output file with the case
name.

## 3. Dumping artifacts for deeper work

```bash
V="python3 /opt/volatility3/vol.py -f /evidence/memdump.raw"

# Dump a suspicious process's memory for strings and analysis
$V windows.memmap.Memmap --pid 1234 --dump --output-dir /tmp/pid1234/

# Dump the executable image of a process
$V windows.dumpfiles.DumpFiles --pid 1234 --output-dir /tmp/dumpfiles/

# Extract the process's command line and environment
$V windows.cmdline.CmdLine --pid 1234

# Registry hives from memory (when disk hives are unavailable)
$V windows.registry.hivelist.HiveList
```

Dumped process memory goes to strings analysis, YARA scanning, and the
malware workflow. The memory image stays pristine; all deeper work
happens on the dumps.

## Edge cases

- Symbols fail to load offline. Pre-stage the symbol JSON for the exact
  build, or run the symbol download on a connected box and copy the
  cache.
- The dump is from a VM snapshot with extra metadata. Convert or strip
  the snapshot wrapper to a raw dump first.
- Plugins crash on a corrupt region. Note the failing plugin and
  continue with the rest; partial memory analysis still has value.
- The OS is unsupported or too new. Check Volatility's supported list;
  bleeding-edge builds need the development branch or another tool.

## Escalation

- You need hidden process detection: run the psscan versus pslist
  comparison (unlinked processes show in the scan but not the list).
- Malware is suspected: hand the dumped processes to malware-in-memory
  with the plugin outputs attached.
- The memory answers are needed fast: run the triage sequence in
  process-memory-triage instead of the full workflow.

## Detection and defender view

For defenders, memory forensics is the tool of last resort when disk
and logs are clean: fileless malware lives only here. The defender's
investment is the ability to capture memory safely (and legally) from
production hosts, plus the Volatility skills to read it. Regular
memory triage of critical servers builds the baseline that makes
anomalies visible.

## Key references

- Volatility 3 2.5.2 documentation: plugin reference.
- "The Art of Memory Forensics" (methodology reference).
- NIST SP 800-86 (memory analysis guidance).
