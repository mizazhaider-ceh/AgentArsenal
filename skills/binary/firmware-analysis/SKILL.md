---
name: firmware-analysis
description: Use when analyzing a firmware image from a device you own or
  are authorized to test. Covers Binwalk scanning and extraction, entropy
  analysis, SquashFS and archive recovery, bootloader and kernel
  identification, hunting hardcoded credentials and keys, and reverse
  engineering extracted binaries with Ghidra. Use when you need to audit an
  IoT or embedded device, when a firmware update needs security review, or
  when a device behaves suspiciously and you have a flash dump.
version: 1.0.0
domain: binary
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [static-triage]
tools:
  - name: Binwalk
    version: 3.1.0
  - name: Ghidra
    version: 12.1.4
  - name: Python
    version: 3.12
---

Firmware analysis treats a device's flash image like a crime scene made of
nested archives: bootloaders, kernels, compressed filesystems, and
applications layered inside one binary blob. The work splits into three
phases: map the structure, extract the filesystems, then analyze what came
out. This skill covers the Binwalk-centered workflow for all three, plus the
high-value findings firmware audits produce (hardcoded credentials, private
keys, debug interfaces, outdated software) and how to analyze extracted
binaries. Scope: analyze firmware from devices you own, devices you are
authorized to test, or vendor updates you are reviewing. Never flash modified
firmware to a device you do not own, and never extract and redistribute
proprietary firmware contents beyond your authorized scope.

## Quick Workflow

1. Hash the firmware image and record where it came from (device model,
   version, extraction method).
2. Scan with Binwalk to map embedded files, filesystems, and kernels.
3. Run an entropy plot to find encrypted or compressed regions.
4. Extract recursively, installing the helper tools Binwalk shells out to.
5. Identify the bootloader, kernel version, and root filesystem type.
6. Hunt the extracted tree for hardcoded credentials, keys, and debug
   artifacts.
7. Inventory software versions and match against known CVEs.
8. Reverse engineer the interesting binaries (network daemons, updaters)
   with Ghidra.

## 1. Intake and structural scan

Hash first, then let Binwalk draw the map. Do not extract yet; read the map
first.

```bash
sha256sum firmware.bin | tee firmware.sha256
ls -lh firmware.bin
file firmware.bin

# Signature scan: what lives at which offset
binwalk firmware.bin | tee scan.txt

# Verbose scan with confidence levels when the map looks thin
binwalk -v firmware.bin | head -60
```

A typical consumer router map shows: a bootloader header (U-Boot), an LZMA
compressed kernel, and a SquashFS root filesystem, sometimes with a second
firmware partition for updates. Read every line of the scan before
extracting; the offsets tell you the layout story.

## 2. Entropy analysis

Entropy finds what signatures miss: encrypted blobs, compressed regions
without headers, and appended data.

```bash
# Entropy plot (high = compressed/encrypted, low = code/padding)
binwalk -E firmware.bin | head -40

# Interpretation guide:
# ~0.0-0.3 : padding (0x00 or 0xFF fills)
# ~0.5-0.7 : executable code, headers
# ~0.95+   : compressed or encrypted data
# A sharp DROP after a high region often marks a filesystem boundary
```

An encrypted region shows as sustained near-1.0 entropy with no signatures
inside it. That usually means a decryption key lives in the bootloader or a
separate partition; note it and move on rather than attacking the crypto.

## 3. Extraction

Binwalk extracts by shelling out to external tools, so install the helpers
first or extraction silently produces nothing.

```bash
# Helpers Binwalk needs (Debian/Ubuntu example)
sudo apt install -y squashfs-tools mtd-utils lzma gzip bzip2 unrar cabextract

# Recursive extraction into _firmware.bin.extracted/
binwalk -e -M -r firmware.bin
# -e extract, -M recursive (matryoshka), -r delete carved files after recursion

# Inspect what came out
find _firmware.bin.extracted -maxdepth 3 -type d | head -30
ls -la _firmware.bin.extracted/
```

If a SquashFS is detected but extraction yields nothing, the filesystem is
probably a vendor-modified variant; try `sasquatch` (the patched extractor)
or check Binwalk's log for the exact helper failure. If extraction partially
fails, carve manually at the reported offset with `dd`.

```bash
# Manual carve fallback at a known offset (example: 0x123400)
dd if=firmware.bin of=carved.squashfs bs=1 skip=$((0x123400))
unsquashfs -d manual_root carved.squashfs
```

## 4. Identifying the platform

Once extracted, identify the moving parts: bootloader config, kernel, and
userland.

```bash
ROOT=_firmware.bin.extracted/squashfs-root

# Bootloader config and environment
find _firmware.bin.extracted -iname '*u-boot*' -o -iname '*.dtb' | head
strings firmware.bin | grep -i -E 'u-boot|bootcmd|bootargs' | head -10

# Kernel version from the extracted kernel or its strings
strings _firmware.bin.extracted/*.7z 2>/dev/null | grep -m1 'Linux version'
find "$ROOT" -name 'version' -path '*proc*' 2>/dev/null | head -3

# Userland inventory: busybox version, web server, ssh daemon
"$ROOT/bin/busybox" 2>/dev/null | head -3
ls "$ROOT/usr/sbin" "$ROOT/bin" 2>/dev/null | head -40
```

Record the kernel version, BusyBox version, and any network-facing daemons
(httpd, telnetd, sshd, upnp). These become your CVE matching list in step 6.

## 5. Hunting hardcoded secrets

This is where firmware audits pay for themselves. Search the extracted tree
and the raw image for credentials and keys.

```bash
# Password-like assignments in configs and scripts
grep -r -i -E 'password\s*=\s*["'"'"']?[^"'"'"' ]+|passwd\s*=\s*\S+|admin\s*:\s*\S+' "$ROOT/etc" 2>/dev/null | head -30

# Private keys and certificates left in the image
find "$ROOT" -iname '*.pem' -o -iname '*.key' -o -iname 'id_rsa*' 2>/dev/null | head -20
grep -r -l 'BEGIN PRIVATE KEY' "$ROOT" 2>/dev/null | head -20
grep -r -l 'BEGIN RSA PRIVATE KEY' firmware.bin 2>/dev/null | head

# Hardcoded credentials in binaries (strings on the extracted daemons)
strings "$ROOT/usr/sbin/httpd" 2>/dev/null | grep -i -E 'admin|password|root' | head -20

# Debug and backdoor artifacts
grep -r -i -E 'telnetd|debug|backdoor|test_account' "$ROOT/etc" 2>/dev/null | head -20
ls -la "$ROOT/etc/" | grep -iE 'shadow|passwd'
```

Every finding needs impact analysis, not just existence: a private key in
firmware means anyone with the image can impersonate the device; a hardcoded
telnet password means remote access. Check whether the credential is
actually used by reading the code that references it.

## 6. Software inventory and CVE matching

List versions, then match against public vulnerability data.

```bash
# Version strings from the main binaries
for b in busybox httpd dropbear sshd dnsmasq; do
  f=$(find "$ROOT" -name "$b" -type f 2>/dev/null | head -1)
  [ -n "$f" ] && echo "== $b: $f" && strings "$f" | grep -i -m2 -E 'version [0-9]|v[0-9]+\.[0-9]+'
done

# Kernel modules can reveal driver versions
ls "$ROOT/lib/modules/" 2>/dev/null
```

Take each version to your CVE source of choice and record matches with
severity. Prioritize network-reachable services: a 2019 dnsmasq on the WAN
interface outranks a 2015 busybox used only at boot.

## 7. Binary analysis of extracted components

The interesting binaries (web server, update client, authentication daemon)
go through the standard reverse engineering pipeline.

```bash
# Architecture check first: firmware is often MIPS/ARM, not x86
file "$ROOT/usr/sbin/httpd"
readelf -h "$ROOT/usr/sbin/httpd" 2>/dev/null | grep -E 'Class|Machine'

# Then Ghidra with the right processor (import and set language explicitly)
# Analyze the update mechanism: how does the device verify new firmware?
strings "$ROOT/usr/sbin/updater" 2>/dev/null | grep -i -E 'http|sign|rsa|md5|sha' | head -20
```

Focus questions: does the updater verify signatures (or just checksums, or
nothing), does the web interface sanitize input (command injection is the
classic firmware bug), and are there hidden URLs or debug endpoints. Findings
here feed responsible disclosure to the vendor, never public exploit
release.

## Edge cases

- Extraction produces nested archives five deep: that is normal for
  firmware; keep recursing and track the path of each interesting file.
- SquashFS extraction fails silently: vendor-modified SquashFS is the usual
  cause; try sasquatch, or binwalk's `--run` with explicit unsquashfs flags.
- Firmware is encrypted: look for the key in the bootloader partition, in a
  separate unencrypted update package, or in the vendor's GPL release. Do
  not brute force; document it as encrypted and move to what is accessible.
- Multi-partition image (A/B updates): analyze both partitions; the inactive
  one may hold an older, more vulnerable version, or the attacker's
  persistence.
- No filesystem found, just a bare-metal binary: it is likely an RTOS
  image; switch to direct Ghidra analysis with the right base address and
  processor.

## Escalation

- Binwalk finds nothing but the image is definitely firmware: try
  `binwalk -A` (opcode scan) to find code regions, or scan with
  firmware-specific tools for the vendor's header magic.
- Need runtime behavior: emulate the extracted userland with QEMU
  user-mode or full-system emulation, or flash to an identical spare device
  you own. Never emulate with network access to production.
- Encrypted firmware blocks everything: pivot to analyzing the update
  mechanism and the companion mobile app, which often leak the crypto design.
- Responsible disclosure: vendor contact first, coordinated timeline, no
  public details until patched or the timeline expires.

## Detection and defender view

For defenders managing fleets of embedded devices, firmware analysis is how
you verify what your vendors shipped: extract, inventory, and diff each
update against the last, watching for new network services, changed
credentials, and added binaries. Detection content from this skill includes
YARA rules for backdoored firmware markers, hashes of known-vulnerable
firmware versions to flag in asset inventory, and network signatures for the
device's update protocol to spot rogue updates. The misuse case is extracting
proprietary firmware to steal IP or to build exploits for devices you do not
own; this skill covers authorized audit and research, with disclosure through
proper channels.

## Key references

- MITRE ATT&CK T1542.003 (Bootkit) and T1542 (Pre-OS Boot): firmware-level
  persistence concepts.
- MITRE ATT&CK T1005 (Data from Local System): secrets recovered from
  images.
- CWE-798 (Use of Hard-coded Credentials): the headline firmware finding.
- CWE-321 (Use of Hard-coded Cryptographic Key): keys in firmware.
- Binwalk documentation: https://binwalk.app
- Ghidra documentation: https://ghidra-sre.org
