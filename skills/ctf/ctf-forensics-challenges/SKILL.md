---
name: ctf-forensics-challenges
description: Use when competing in a CTF forensics challenge, practicing
  in a lab, or analyzing evidence you are authorized to handle. Covers the
  forensics workflow, identifying file types and carving data, analyzing
  packet captures with Wireshark and tshark, triaging disk and memory
  images, extracting hidden data with steganography tools, reading
  metadata, and reassembling fragmented evidence into the flag. Use when a
  challenge hands you a pcap, disk image, memory dump, image, or mystery
  file, or when you need to reconstruct what happened from artifacts.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [forensics-fundamentals, memory-forensics]
tools:
  - name: Wireshark
    version: 4.2
  - name: Python
    version: 3.12
  - name: binwalk
    version: 2.3
  - name: Volatility
    version: 3.0
  - name: CyberChef
    version: latest
  - name: ExifTool
    version: 12.90
---

Forensics challenges give you artifacts (captures, images, dumps, files)
and hide the flag inside them. The winning pattern is layered: identify
what you have, extract everything extractable automatically, then dig
manually into the interesting parts. This skill covers the authorized
methodology across the main forensics challenge types, with the exact
tools, filters, and commands that surface flags fastest. Scope is CTF
competitions, lab evidence, and artifacts you are authorized to analyze.

## Quick Workflow

1. Identify every file: `file`, `xxd` headers, `binwalk -E` entropy,
   and `strings` for immediate flag-shaped hits.
2. Check metadata first (ExifTool); CTF flags hide in EXIF, comments,
   and document properties.
3. Carve embedded files: `binwalk -e`, `foremost`, or manual `dd`
   extraction at found offsets.
4. For pcaps: check the protocol hierarchy, follow interesting streams,
   and export objects (HTTP, FTP-DATA).
5. For disk images: list partitions, mount read-only or parse with
   Sleuth Kit (`fls`, `icat`), and check deleted files.
6. For memory dumps: run Volatility plugins (processes, network,
   files) and scan for flag patterns in strings.
7. For images/audio: run steg tools (zsteg, steghide, binwalk) and
   inspect LSB planes and spectrograms.
8. Reassemble: CTF forensics often splits the flag across artifacts;
   collect fragments before assuming you are done.

## 1. File identification and carving

```bash
file mystery.bin
xxd mystery.bin | head -5        # magic bytes: PK=zip, \x89PNG=png, FF D8=jpg
binwalk mystery.bin             # embedded files and offsets
# DECIMAL       HEXADECIMAL     DESCRIPTION
# 0             0x0             PNG image, 800 x 600
# 12345         0x3039          Zip archive data

binwalk -e mystery.bin          # auto-extract to _mystery.bin.extracted/
# or manual:
dd if=mystery.bin of=hidden.zip bs=1 skip=12345

# entropy: high entropy regions suggest encryption or compression
binwalk -E mystery.bin | head -20

# quick flag grep across everything (flag formats vary; try several)
grep -r -a -o -E "flag\{[^}]+\}|CTF\{[^}]+\}|picoCTF\{[^}]+\}" . 2>/dev/null | head
```

## 2. Packet capture analysis

```bash
# Protocol overview: what talks to what
tshark -r capture.pcap -q -z io,stat,0,tcp,udp
capinfos capture.pcap           # packet count, duration, capture info

# Follow a TCP stream (the conversation as text)
tshark -r capture.pcap -q -z follow,tcp,ascii,0 | head -60

# Export files transferred over HTTP / FTP-DATA
tshark -r capture.pcap --export-objects http,/tmp/http_objs
tshark -r capture.pcap --export-objects ftp-data,/tmp/ftp_objs
ls -la /tmp/http_objs /tmp/ftp_objs

# Filter cheat sheet for CTF pcaps
tshark -r capture.pcap -Y "http.request" -T fields -e http.host -e http.request.uri | sort -u
tshark -r capture.pcap -Y "dns" -T fields -e dns.qry.name | sort -u          # exfil over DNS?
tshark -r capture.pcap -Y "ftp-data or tftp"                                 # file transfers
tshark -r capture.pcap -Y "icmp.data.len > 0" -T fields -e icmp.data         # ICMP exfil
```

In Wireshark GUI: Statistics -> Protocol Hierarchy (spot odd protocols),
right-click a packet -> Follow -> TCP/UDP/HTTP Stream, File -> Export
Objects. Look for: credentials in cleartext (FTP, Telnet, HTTP basic),
DNS queries encoding data in subdomain labels, and ICMP payloads.

Reassembling exfiltration in Python:

```python
#!/usr/bin/env python3
# Example: reassemble data exfiltrated in ICMP payloads
from scapy.all import rdpcap, ICMP
pkts = rdpcap("capture.pcap")
data = b"".join(bytes(p[ICMP].payload) for p in pkts if p.haslayer(ICMP) and p[ICMP].type == 8)
open("/tmp/exfil.bin", "wb").write(data)
```

## 3. Disk image triage

```bash
# Partition layout (never mount read-write; use loop,ro or Sleuth Kit)
fdisk -l disk.img
mmls disk.img                 # Sleuth Kit partition list

# File listing including deleted entries
fls -r -p disk.img | head -40
fls -r -d disk.img             # deleted files only

# Extract a file by inode
icat disk.img 1234 > /tmp/recovered.txt

# Strings over unallocated space (deleted content often survives)
blkls disk.img | strings -n 8 | grep -i -E "flag|password" | head

# Timeline of file activity (great for "what happened when" challenges)
fls -r -m "/" disk.img > /tmp/bodyfile.txt
mactime -b /tmp/bodyfile.txt | head -50
```

Check slack space, alternate data streams (NTFS), and volume shadow
copies when the image is Windows. CTF disk challenges often hide the
flag in a deleted file, so `fls -d` plus `icat` is the money command.

## 4. Memory dump analysis with Volatility 3

```bash
# Identify the profile automatically, then triage
python3 vol.py -f mem.raw windows.info
python3 vol.py -f mem.raw windows.pslist      # processes
python3 vol.py -f mem.raw windows.netscan     # network connections
python3 vol.py -f mem.raw windows.filescan | grep -i flag
python3 vol.py -f mem.raw windows.cmdline     # command lines (past exfil commands)

# Dump a suspicious process for strings analysis
python3 vol.py -f mem.raw windows.memmap --pid 1234 --dump
python3 vol.py -f mem.raw windows.dumpfiles --physaddr 0x...

# Fast flag hunt across the whole dump
strings -n 6 mem.raw | grep -E "flag\{[^}]+\}" | sort -u | head
```

Linux dumps use `linux.pslist`, `linux.bash` (shell history), and
`linux.proc.maps`. The bash history plugin alone solves challenges where
the attacker typed the flag handling commands.

## 5. Steganography essentials

```bash
# PNG: check LSB and metadata channels
zsteg -a image.png                    # tries all LSB orders and channels
steghide info image.png               # needs passphrase; try empty and challenge words
exiftool image.png                    # comment/description fields

# JPEG: outguess/steghide territory; also check appended data
binwalk image.jpg                     # zip/rar appended after EOI marker
tail -c 100 image.jpg | xxd           # trailing garbage often holds the flag

# Audio: look at the spectrogram (flags drawn in frequency domain)
# open in Audacity -> Spectrogram view, or:
sox audio.wav -n spectrogram -o /tmp/spec.png
# SSTV signals: decode with robot36 / QSSTV when you hear the warble

# Whitespace / unicode stego in text
cat -A note.txt | head                # trailing spaces/tabs = binary
python3 -c "
data = open('note.txt').read()
bits = ''.join('1' if c == '\u200b' else '0' for c in data if c in '\u200b\u200c')
print(bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8)))
"
```

## Edge cases

- The pcap is huge: filter early (`tshark -Y`), work on subsets, and
  use `editcap` to split by time or packet count.
- Traffic is TLS-encrypted: without the key, pivot to metadata (SNI,
  certificate names, flow sizes, timing); check for a keylog file in
  the challenge bundle.
- The disk image will not mount: parse with Sleuth Kit directly; the
  filesystem may be intentionally corrupted as part of the challenge.
- Volatility reports no profile: try `windows.info` anyway, or fall
  back to raw `strings` plus `bulk_extractor` style carving.
- The flag is split across artifacts (half in pcap, half in image):
  keep a notes file of fragments; do not close the challenge after
  one artifact.

## Escalation

- `binwalk -e` extracts nothing but entropy is high throughout: the
  file may be encrypted; look for the key in accompanying files or
  metadata before assuming brute force.
- zsteg/steghide find nothing in the image: inspect color planes
  manually, check for appended archives, and try `stegseek` (rockyou
  brute force on steghide) as a cheap extra pass.
- The pcap shows only encrypted C2: look at beacon timing and sizes
  for encoded commands, and check DNS for tunneled data.
- Memory strings show the flag partially corrupted: the process may
  have been paged; carve with `bulk_extractor` or dump the specific
  process address space and re-grep.

## Detection and defender view

Defenders use these same techniques in incident response: pcap analysis
for C2, disk forensics for persistence, memory forensics for fileless
malware, and steganalysis for data exfiltration. Detection focuses on
the adversary behaviors CTF forensics imitates: DNS tunneling (long
subdomains, high query entropy), ICMP exfiltration, and large outbound
transfers. The durable defenses are network segmentation with egress
filtering, DNS logging with anomaly detection, and endpoint telemetry
that makes memory and disk forensics a confirmation step rather than
the only visibility.

## Key references

- MITRE ATT&CK T1048 (Exfiltration Over Alternative Protocol), T1071
  (Application Layer Protocol), T1005 (Data from Local System).
- CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor).
- Wireshark 4.2 docs: https://www.wireshark.org/docs/
- Volatility 3 docs: https://volatility3.readthedocs.io/
- Sleuth Kit wiki: https://wiki.sleuthkit.org/
- zsteg: https://github.com/zed-0xff/zsteg
