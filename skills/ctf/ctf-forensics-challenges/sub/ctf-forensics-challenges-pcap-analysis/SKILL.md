---
name: ctf-forensics-challenges-pcap-analysis
description: Use when a CTF forensics challenge provides a packet capture,
  or when analyzing network evidence you are authorized to handle. Covers
  capture triage with capinfos and protocol hierarchy, display filters for
  HTTP, DNS, FTP, ICMP and TLS metadata, following TCP and UDP streams,
  exporting transferred files, reassembling exfiltrated data with Python
  and scapy, and spotting C2 beacons and DNS tunneling. Use when handed a
  .pcap or .pcapng, when cleartext credentials or files crossed the wire,
  or when data was smuggled out over DNS, ICMP, or odd protocols.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-forensics-challenges
requires: [ctf-forensics-challenges]
extends: []
relates: [forensics-fundamentals, nmap-methodology]
tools:
  - name: Wireshark
    version: 4.2
  - name: Python
    version: 3.12
  - name: CyberChef
    version: latest
---

Packet captures record exactly what crossed the network, which makes them
a favorite CTF forensics artifact: credentials, transferred files, and
exfiltrated flags are all recoverable with the right filters. This
sub-skill covers the authorized pcap workflow in depth: fast triage,
protocol-specific extraction, stream following, file export, and
reassembling covert channels (DNS, ICMP, timing) with Python. Scope is CTF
competitions, lab captures, and evidence you are authorized to analyze.

## Quick Workflow

1. Run `capinfos` and the protocol hierarchy to learn size, duration,
   and which protocols dominate.
2. List conversations (Statistics -> Conversations) to find the
   interesting host pairs.
3. Check cleartext protocols first: HTTP objects, FTP-DATA, Telnet,
   DNS queries, SMTP.
4. Follow the most suspicious TCP/UDP streams and read them as ASCII.
5. Export transferred files and inspect them (they are often the next
   forensics stage: a zip, an image, a binary).
6. Hunt covert channels: DNS label data, ICMP payloads, odd ports,
   periodic beacons.
7. Reassemble exfiltrated bytes with tshark field extraction plus a
   Python script.
8. Decode the reassembled blob (base64, hex, XOR) and verify the flag
   format.

## 1. Triage: capinfos and hierarchy

```bash
capinfos capture.pcap
# File size, packet count, duration, data rate -> is this a 5 minute or 5 hour capture?

tshark -r capture.pcap -q -z io,phs | head -40
# Protocol Hierarchy Statistics: frames and bytes per protocol.
# Look for: data on unusual ports, tftp/ftp-data (file transfer),
# dns with huge query counts, icmp with data.

# Top talkers
tshark -r capture.pcap -q -z conv,ip | head -30

# DNS query names (exfil often hides here)
tshark -r capture.pcap -Y dns -T fields -e dns.qry.name | sort | uniq -c | sort -rn | head -30
```

If one host makes thousands of DNS queries with long random-looking
labels, that is DNS tunneling until proven otherwise.

## 2. Cleartext protocol extraction

```bash
# HTTP: list requests, then export objects
tshark -r capture.pcap -Y "http.request" \
  -T fields -e ip.src -e http.host -e http.request.method -e http.request.uri | head -30
tshark -r capture.pcap --export-objects http,/tmp/http_objs && ls -la /tmp/http_objs

# Credentials in the clear (HTTP basic auth, FTP, Telnet)
tshark -r capture.pcap -Y "http.authorization" -T fields -e http.authorization | sort -u
tshark -r capture.pcap -Y "ftp.request.command == USER or ftp.request.command == PASS" \
  -T fields -e ftp.request.arg
tshark -r capture.pcap -q -z follow,tcp,ascii,0 | grep -i -E "user|pass|login" | head

# FTP data transfers
tshark -r capture.pcap --export-objects ftp-data,/tmp/ftp_objs && ls -la /tmp/ftp_objs

# SMTP / POP3 / IMAP credentials and message bodies
tshark -r capture.pcap -q -z follow,tcp,ascii,0 | grep -i -E "auth|subject|flag" | head -20
```

Always inspect exported objects with `file` afterward; a transferred
"document" is often a zip containing the next stage.

## 3. Following streams

```bash
# Follow stream index N as ASCII (find N in the Conversations view)
tshark -r capture.pcap -q -z follow,tcp,ascii,3 | head -80

# Raw hex when ASCII mangles binary
tshark -r capture.pcap -q -z follow,tcp,hex,3 | head -40

# UDP streams (DNS exfil, custom protocols)
tshark -r capture.pcap -q -z follow,udp,ascii,0 | head -60

# Filter to one conversation, then read packets in order
tshark -r capture.pcap -Y "ip.addr==10.0.0.5 and tcp.port==4444" -T fields \
  -e frame.number -e tcp.seq -e tcp.len -e data.len | head -40
```

In the Wireshark GUI, right-click any packet of interest -> Follow ->
TCP Stream gives the same view with clickable stream switching. Note the
stream index in the window title for the tshark equivalent.

## 4. Reassembling DNS exfiltration

```bash
# Pull the query labels in order
tshark -r capture.pcap -Y "dns.flags.response == 0" \
  -T fields -e frame.number -e dns.qry.name > /tmp/dnsq.txt
head -5 /tmp/dnsq.txt
# 12  aGVsbG8td29ybGQ.example.com   <- base64 label!
```

```python
#!/usr/bin/env python3
"""Reassemble base64 labels exfiltrated via DNS queries."""
import base64

blob = b""
seen = set()
for line in open("/tmp/dnsq.txt"):
    parts = line.strip().split()
    if len(parts) < 2:
        continue
    label = parts[1].split(".")[0]      # first label holds the data
    if label in seen:                    # skip retransmissions
        continue
    seen.add(label)
    blob += label.encode()

blob += b"=" * (-len(blob) % 4)          # fix padding
open("/tmp/dns_exfil.bin", "wb").write(base64.b64decode(blob))
print("wrote", len(blob), "chars of base64")
```

Variants: hex labels (decode with `bytes.fromhex`), per-query sequence
numbers in a second label (sort by them), or data in TXT responses
instead of queries (filter `dns.flags.response == 1` and read
`dns.txt`).

## 5. Reassembling ICMP and odd-protocol exfil

```bash
# ICMP payloads in order
tshark -r capture.pcap -Y "icmp.data.len > 0" \
  -T fields -e frame.number -e icmp.data > /tmp/icmp.txt
wc -l /tmp/icmp.txt && head -3 /tmp/icmp.txt
```

```python
#!/usr/bin/env python3
"""Reassemble ICMP exfiltrated bytes (colon-separated hex from tshark)."""
out = bytearray()
for line in open("/tmp/icmp.txt"):
    parts = line.strip().split("\t")
    if len(parts) < 2 or not parts[1]:
        continue
    out += bytes.fromhex(parts[1].replace(":", ""))
open("/tmp/icmp_exfil.bin", "wb").write(out)
print("reassembled", len(out), "bytes")
```

Then identify the blob: `file /tmp/icmp_exfil.bin`, check for gzip/zlib
magic, base64-decode if printable, XOR-brute-force if random-looking.
The same pattern works for data smuggled in any protocol field; only
the tshark `-e` field name changes.

## 6. Beaconing and C2 patterns

```bash
# Periodic connections: group by second and count
tshark -r capture.pcap -T fields -e frame.time_epoch -e ip.dst \
  | awk '{print int($1), $2}' | sort | uniq -c | sort -rn | head -20

# TLS metadata without decryption: SNI and cert names
tshark -r capture.pcap -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn | head

# JA3-ish triage is GUI work; on CLI, flag odd ports and long-lived flows
tshark -r capture.pcap -q -z conv,tcp | sort -k9 -rn | head -15
```

CTF beacons are usually simple: fixed interval, fixed size, to one
destination. Commands and responses hide in the payload sizes or in
small encrypted blobs; when the challenge provides the C2 key (config
file, binary), decrypt offline with Python.

## Edge cases

- Capture has no full packets (snaplen truncated): stream following
  still works for headers and metadata; file export will be corrupt,
  so pivot to metadata analysis.
- The pcapng has multiple interfaces or decryption secrets: check
  for embedded TLS keylog blocks (Wireshark Preferences -> TLS ->
  keylog) before assuming traffic is opaque.
- Timestamps are weird (all zero): ordering by frame number still
  works; do not rely on time-based beacon analysis.
- The flag spans multiple streams: reassemble each, then concatenate
  in frame-number order.
- IPv6 or tunneled traffic: adjust filters (`ipv6.addr`, `gre`),
  but the follow/export workflow is identical.

## Escalation

- Exported files are corrupt: the transfer may use a custom protocol;
  follow the stream in hex mode and carve the file manually by its
  magic bytes.
- DNS labels look encrypted, not encoded: find the key in the
  challenge bundle (config, binary, another artifact); CTF crypto is
  rarely unbreakable, just layered.
- Nothing but TLS: enumerate SNI values, certificate subjects, and
  flow sizes; the challenge may expect metadata-only answers, or the
  keylog is hidden in a second artifact.
- Reassembled blob is still not the flag: run it through the
  forensics parent workflow (binwalk, steg tools); exfil blobs are
  often archives or images with a second hiding layer.

## Detection and defender view

Defenders hunt exactly these patterns with NDR and DNS logging: long
high-entropy subdomains, ICMP with payloads, periodic beacons, and
cleartext credential use. Detections include DNS query length and
entropy thresholds, ICMP data alerts, and TLS fingerprinting (JA3) for
known C2. Durable defenses: egress filtering with allowlisted DNS,
decrypt-and-inspect TLS at the boundary where policy allows, and full
packet capture on critical segments so forensics is possible after the
fact.

## Key references

- MITRE ATT&CK T1048 (Exfiltration Over Alternative Protocol), T1071
  (Application Layer Protocol), T1041 (Exfiltration Over C2 Channel).
- Wireshark 4.2 display filter reference: https://www.wireshark.org/docs/dfref/
- tshark manual: https://www.wireshark.org/docs/man-pages/tshark.html
- scapy documentation: https://scapy.readthedocs.io/
- Wireshark sample captures: https://wiki.wireshark.org/SampleCaptures
  (practice protocol patterns on real captures).
