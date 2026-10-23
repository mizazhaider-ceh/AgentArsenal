---
name: incident-breach-scoping-data-exfiltration-assessment
description: Use when you must determine what data left the network
  and how, during an authorized incident investigation. Covers
  finding staged archives, measuring exfiltration volumes with Zeek
  7.0 and Wireshark 4.2, identifying channels (HTTPS, DNS tunneling,
  cloud uploads, email), correlating staged data with database and
  file sizes using Python 3.12, and writing the exfiltration finding
  for legal notification decisions. Use when the parent
  incident-breach-scoping workflow reaches exfiltration, when large
  outbound transfers appear in telemetry, or when leadership asks
  what the attacker took.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-breach-scoping
requires: [incident-breach-scoping]
extends: []
relates: [incident-breach-scoping]
tools:
  - name: Zeek
    version: 7.0
  - name: Wireshark
    version: 4.2
  - name: Python
    version: 3.12
  - name: jq
    version: 1.7
---

Data exfiltration assessment determines what the attacker stole:
what data, how much, through which channel, and when. It is the
finding with the biggest consequences, because it triggers legal
notification duties and defines the incident's real cost. This
sub-skill covers finding staged data, measuring what left, naming
the channel, and writing the assessment at the confidence level the
evidence supports. Authorized investigations only; handle any
recovered data as sensitively as the original.

## Quick Workflow

1. Look for staging: archives and collections created in the
   incident window.
2. Measure outbound volumes to external hosts with Zeek and flow
   data.
3. Identify the channel per transfer: HTTPS, DNS, cloud, email.
4. Correlate staged sizes with transferred sizes and source data
   sizes.
5. Determine what the data was: database dumps, file shares,
   mailboxes.
6. Establish the exfiltration window: first to last byte.
7. Write the assessment: what, how much, how, when, confidence.
8. Hand the assessment to legal for notification decisions.

## 1. Finding staged data

```bash
# Large files created in the incident window, in temp and odd locations
find /tmp /var/tmp /dev/shm /var/www -type f -size +50M \
  -newermt "2026-10-20" -ls 2>/dev/null

# Archives by extension, anywhere recently modified
find / -type f \( -name "*.7z" -o -name "*.rar" -o -name "*.zip" \
  -o -name "*.tar.gz" \) -newermt "2026-10-20" -ls 2>/dev/null | head -20

# EDR: archiving tool executions in the window
# Hunt: 7z.exe, rar.exe, tar with output to temp paths
```

Example output shape:

```
1843200 -rw-r--r-- 1 www-data www-data 2214592512 Oct 21 04:02 /tmp/.x/dump.sql.gz
```

A 2.1 GB gzip in a hidden temp directory, created minutes before
a large outbound transfer, is staging. Note the owner
(`www-data`): it tells you which compromised account did the
collecting. Do not delete staged files; they are evidence of what
was taken, and sometimes the only copy of the exact dataset.

## 2. Measuring outbound volume

```bash
# Zeek conn.log: top external destinations by bytes sent (resp_bytes from our side is received;
# orig_bytes is what WE sent -> exfil direction for internal orig_h)
zeek-cut id.orig_h id.resp_h id.resp_p proto orig_bytes < conn.log | \
  awk '$1 ~ /^192\.168\./ && $5 > 1000000' | \
  sort -k5 -rn | head -15
```

Example output shape:

```
192.168.30.15  198.51.100.23  443  tcp  2214592512
192.168.30.15  198.51.100.23  443  tcp  184320
```

One host sent 2.1 GB to one external IP on 443. Compare with the
staged file size (2,214,592,512 bytes): an exact or near-exact
match confirms the staged archive is what left. Also check the
baseline: what does this host normally send to external hosts.
A database server that normally sends kilobytes and suddenly sent
gigabytes needs no baseline to be suspicious, but the baseline
strengthens the report.

```bash
# Firewall or NetFlow equivalent when Zeek is unavailable
# Top talkers by bytes in the incident window (flow log format varies)
```

## 3. Identifying the channel

```bash
# HTTPS exfil: check the TLS SNI and certificate in the capture
tshark -r capture.pcap -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name | sort | uniq -c | sort -rn | head

# DNS tunneling: high query volumes, long labels, odd record types
zeek-cut query qtype_name < dns.log | \
  awk 'length($1) > 50' | head -10
# Also: dns.log request counts per host
zeek-cut id.orig_h query < dns.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -5
```

Channel signatures:

- HTTPS to an attacker IP or fresh domain: the common case,
  blends with normal traffic.
- DNS tunneling: thousands of queries with long encoded labels,
  often TXT or NULL records; slow but firewall-friendly.
- Cloud uploads: traffic to storage endpoints (S3, Drive,
  Dropbox) from servers that never upload there normally.
- Email: messages with large attachments from compromised
  mailboxes; check the mail gateway logs.

```bash
# Cloud upload check: which external storage endpoints did internal hosts reach
zeek-cut id.orig_h id.resp_h < conn.log | \
  awk '$2 ~ /(s3|blob|storage|dropbox|drive)/' | sort | uniq -c | head
```

Name the channel precisely; "exfiltrated over HTTPS to
198.51.100.23" directs the blocking and the legal analysis
differently than "exfiltrated via DNS tunneling".

## 4. Correlating staged, transferred, and source sizes

```python
# exfil-correlate.py: tie the numbers together
staged = 2214592512      # /tmp/.x/dump.sql.gz
transferred = 2214592512 # Zeek orig_bytes to 198.51.100.23
db_size = 2281701376     # production database size

print(f"staged == transferred: {staged == transferred}")
print(f"staged/db ratio: {staged/db_size:.2%}")
# staged == transferred: True
# staged/db ratio: 97.06%
```

A 97 percent ratio with matching transfer size means: the attacker
dumped nearly the whole database and got it all out. That is the
sentence leadership and legal need. If the numbers do not match,
say what is unexplained: partial transfer, compression
differences, or multiple staged files.

## 5. Determining what the data was

```bash
# Identify the staged archive's contents without extracting sensitive data widely
7z l /tmp/.x/dump.sql.gz 2>/dev/null | head -20
# For a SQL dump: read the table names from the head, not the rows
zcat /tmp/.x/dump.sql.gz | grep -m5 "CREATE TABLE"

# File share staging: list names and sizes, not contents
tar tzf /tmp/.x/docs.tgz 2>/dev/null | head -30
```

Example output shape:

```
CREATE TABLE `customers` (
CREATE TABLE `orders` (
CREATE TABLE `payment_methods` (
```

Table names define the notification scope: customers plus payment
methods is a different legal event than orders alone. Work with
the data owner to classify; the analyst names the tables, the
business names the sensitivity.

## 6. The exfiltration window

```bash
# First to last byte: from Zeek with timestamps
zeek-cut ts id.orig_h id.resp_h orig_bytes < conn.log | \
  awk '$2=="192.168.30.15" && $3=="198.51.100.23"' | \
  head -1; \
zeek-cut ts id.orig_h id.resp_h orig_bytes < conn.log | \
  awk '$2=="192.168.30.15" && $3=="198.51.100.23"' | \
  tail -1
```

```
2026-10-21 04:05:11  192.168.30.15  198.51.100.23  1460
2026-10-21 04:20:13  192.168.30.15  198.51.100.23  2214592512
```

Fifteen minutes, 2.1 GB, in the attacker's active window from the
super-timeline. The window bounds the "when" for notifications and
shows whether exfiltration finished (transfer size equals staged
size: yes, it finished).

## 7. Writing the assessment

```
## Exfiltration assessment: INC-2026-1042
What: production customer database (tables: customers, orders, payment_methods)
How much: 2.1 GB (97% of database by size)
Channel: HTTPS POST to 198.51.100.23:443 (fresh IP, no prior contact)
Window: 2026-10-21 04:05 to 04:20 UTC (15 minutes)
Staging: /tmp/.x/dump.sql.gz on web-03 (preserved as evidence)
Confidence: HIGH (staged size == transferred size, table names confirmed)
Legal notified: 2026-10-23 11:00 UTC
Unknowns: whether the attacker also took file shares (no staging found, no anomalous
  SMB volume observed; monitoring continues)
```

State unknowns explicitly. "No evidence of further exfiltration"
is honest; "no further exfiltration occurred" is a claim the
evidence may not support.

## Edge cases

- Exfiltration was slow and low-volume (drip over weeks). Volume
  analysis still works aggregated by destination; the window is
  long and the confidence lower per day.
- The channel was DNS tunneling with no Zeek dns.log. Firewall
  query logs or resolver logs are the fallback; without them,
  note the visibility gap.
- Staging was cleaned up but the transfer remains in flow data.
  Size-match against source data sizes; the transfer volume plus
  the source inventory bounds what left.
- The data was encrypted before exfiltration. You cannot name the
  tables from the ciphertext; scope from what the staging host
  could read and what shrank or was accessed.
- Multiple exfiltration channels in one incident. Assess each
  separately; attackers often use a fast channel for the bulk
  and a slow one for persistence of access.
- The "exfiltration" was actually a backup to a new destination.
  Verify with the backup team before declaring; false
  exfiltration alarms burn credibility.

## Escalation

- The assessment confirms regulated data left (health,
  financial, personal data under GDPR or similar). Escalate to
  legal immediately; notification clocks run from discovery, and
  your assessment is the discovery record.
- The volume suggests the entire dataset is gone. Brief executive
  leadership with the assessment, not a summary of a summary;
  they need the numbers.
- You cannot determine what was taken (encrypted, cleaned
  staging). Escalate the uncertainty itself: the notification
  decision may have to assume the worst, and that is legal's
  call with your evidence.
- Exfiltration is ongoing during the assessment. Tell the
  commander at once; killing the channel may be worth burning
  the investigation's stealth.

## Detection and defender view

Exfiltration is the last chance to catch an intrusion, and the
detections are well understood: alerts on large outbound transfers
to new destinations, DNS query volume anomalies, uploads to
unsanctioned cloud storage, and data-loss-prevention rules on the
crown jewels. The defender program from this assessment is egress
filtering with allow-lists for servers, byte-threshold alerting
tuned per host role, and canary data that pages when touched.
Every exfiltration that succeeded is a detection that did not
exist; build it now, while the channel is fresh in everyone's
mind.

## Key references

- Parent scoping workflow: incident-breach-scoping (this repo)
- MITRE ATT&CK exfiltration (T1048, T1041, T1071):
  https://attack.mitre.org/
- Zeek documentation: https://docs.zeek.org/
- Wireshark documentation: https://www.wireshark.org/docs/
- NIST SP 800-61 Rev. 2: https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final
- CISA incident reporting: https://www.cisa.gov/report
