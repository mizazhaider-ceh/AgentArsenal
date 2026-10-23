---
name: binary-anti-analysis-bypass-vm-and-sandbox-detection
description: Use when a binary fingerprints virtual machines or
  sandboxes during authorized lab analysis and refuses to run. Covers
  the artifact catalog (registry, files, processes, MAC, WMI, CPUID),
  building a hardened analysis VM image, per-sample spoofing and
  patching of checks, validating with test tools like al-khaser and
  pafish, and the validation protocol proving behavior returned. Use
  when samples exit only in VMs, when building lab infrastructure, or
  when a sandbox fleet needs hardening.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: [binary-anti-analysis-bypass]
extends: []
parent: binary-anti-analysis-bypass
relates: [malware-sandbox-analysis, binary-patching-techniques]
tools:
  - name: x64dbg
    version: 2025.06
  - name: Python
    version: 3.12
  - name: CAPE Sandbox
    version: 2.5
---

This is the binary-focused companion to the sandbox-side
anti-vm-detection sub-skill: same artifact catalog, but approached
from the binary under the debugger rather than the detonation
environment. When a sample must be analyzed interactively and it
checks for VMs, you identify each check in the code and defeat it by
spoofing, hooking, or patching. Scope: bypass VM/sandbox detection
only on binaries you are authorized to analyze, in an isolated lab,
during authorized DFIR, malware research, or defensive testing.

## Quick Workflow

1. Reproduce: runs on bare metal (or unhardened VM A) vs exits on
   your analysis VM; confirm the gap is environmental.
2. Hunt the check: strings and imports naming VM artifacts; break on
   registry, WMI, and adapter queries in the debugger.
3. Classify each check by artifact type.
4. Defeat: spoof the artifact, hook the query API, or patch the
   comparison, one check at a time.
5. Verify the sample proceeds; hunt for the next layer.
6. Document every spoof and patch with the analysis.

## 1. Finding checks in the binary

```bash
# Strings name the artifacts directly
floss sample.exe | grep -iE "vbox|vmware|qemu|virtual|xen|vmtools|innotek" | sort -u

# Imports name the query mechanism
# RegOpenKeyExA/RegQueryValueExA -> registry artifact check
# CoCreateInstance + IWbemServices -> WMI query check
# GetAdaptersInfo/GetAdaptersAddresses -> MAC check
# __cpuid intrinsic -> CPUID hypervisor bit check
```

In the debugger, break on the query APIs and watch the arguments:
the registry path or WMI query string tells you exactly which
artifact it wants. Log each: artifact, API, and the code address of
the check.

## 2. Spoofing artifacts

For registry and file checks, give the sample what a physical machine
would show:

- Registry: in the lab VM, the values are already scrubbed in the
  hardened image; for per-sample cases, hook RegQueryValueExA and
  return plausible physical strings ("Dell Inc.", real disk model).
- Files: the check usually tests existence (GetFileAttributesA);
  hook it to return NOT_FOUND for vmmouse.sys and friends.
- Processes: hook the snapshot APIs to hide vmtoolsd.exe, or rename
  the tools in the image.

```text
Hook shape (conceptual):
  RegQueryValueExA(hKey, "SystemBiosVersion", ...) called
  -> if the real value contains "VBOX", return "DELL   - 1" instead
```

Spoofing beats patching when the check is one of several: the binary
keeps running its logic and you keep observing.

## 3. WMI, MAC, and CPUID

- **WMI**: break on the query execution, capture the WQL
  (e.g. `SELECT * FROM Win32_ComputerSystem`); hook the result or
  patch the string comparison on Manufacturer. Setting the
  hypervisor's DMI/SMBIOS strings to physical hardware defeats most
  WMI checks with no per-sample work.
- **MAC**: the check reads adapters and compares OUIs
  (08:00:27, 00:50:56, 52:54:00). Change the VM's virtual NIC MAC to
  a real vendor OUI once, in the image; per-sample, hook
  GetAdaptersAddresses.
- **CPUID hypervisor bit**: leaf 1, ECX bit 31. Patch the test
  instruction, or mask the bit if your hypervisor exposes the
  option. Some samples also read leaves 0x40000000+ for the
  hypervisor brand string; patch those reads too.

## 4. Patching the verdict

When spoofing is impractical, patch the comparison:

```text
Before:
  call check_vm_artifacts     ; returns 1 if VM found
  test eax, eax
  jne exit_quietly
After:
  xor eax, eax                ; always "not a VM"
  nop; nop                    ; cover the test/jne
```

Find the check by breaking on the query API and stepping to the
verdict. One patch per check; re-run between patches to catch layered
checks.

## 5. Validating with test tools

```bash
# In the analysis VM, run al-khaser or pafish BEFORE trusting the image
# They enumerate dozens of checks; fix what they flag, snapshot, repeat
```

A hardened image that passes these tools defeats most real samples
with zero per-sample patching. Re-validate the image quarterly and
after hypervisor updates; new versions sometimes add new artifacts.

## 6. Validation protocol

1. Baseline: unhardened VM, sample exits in seconds, no network.
2. Bypassed: hardened VM or patches applied, full behavior observed.
3. Revert: back to unhardened, quiet again (proves causation).
4. Record: image snapshot ID, MAC, scrubbed artifacts, per-sample
   patches with file offsets.

## Edge cases

- User-artifact checks (empty recent-docs, no browser history):
  harden by adding plausible clutter, not just removing VM traces.
- Cloud metadata checks (169.254.169.254): block or spoof the
  endpoint in the lab network.
- Samples that need a GPU: cannot be spoofed cheaply; patch the
  check instead.
- Over-scrubbed images that look fake in new ways: keep values
  plausible, not empty.

- Nested virtualization artifacts (a lab inside a VM): the outer hypervisor's traces can confuse per-sample analysis; note the stack in the report.

## Escalation

- If the sample still evades a fully hardened image plus targeted
  patches, escalate to bare-metal analysis or hypervisor-level
  tracing.
- If the check targets your specific lab (hostname, username),
  escalate: that is counter-intelligence-relevant.

- If the binary checks for analysis tools by hash rather than name, renaming is not enough; escalate to hook-based hiding.
- If spoofing breaks the sample's own logic (it needs the real value), escalate to patching the verdict instead of the artifact.

## Detection and defender view

Every VM check a sample performs is threat intel: which artifacts it
fears reveals which sandboxes the author tests against. Log the
artifact list per family; aggregated, it shows ecosystem trends in
evasion. For lab operators, the hardened image is shared
infrastructure: build once, document, snapshot, and share the build
notes. For the SOC, processes that query VM artifacts then exit are a
hunt signal for evasive malware on real hosts.

## Key references

- al-khaser:
  https://github.com/LordNoteworthy/al-khaser
- pafish:
  https://github.com/a0rtega/pafish
- MITRE ATT&CK: T1497.001 (System Checks), T1497
  (Virtualization/Sandbox Evasion)
- CAPE Sandbox documentation:
  https://capev2.readthedocs.io/
- Practical Malware Analysis (Sikorski and Honig), Chapter 17
  (anti-VM techniques)
