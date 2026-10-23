---
name: netflow-analysis
description: Use when analyzing NetFlow, sFlow, or IPFIX data for
  security investigations or baselining. Covers flow collection review,
  beaconing detection, data exfiltration spotting, and building
  baselines. Also use when full packet capture is unavailable and flows
  are all you have.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [threat-hunting, siem-detections, suricata-ids]
tools:
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.4
---

NetFlow records who talked to whom, when, and how much, without packet
contents: enough to find beacons, tunnels, and exfiltration. This skill
covers the analysis method for flow data you are authorized to use:
collection checks, baseline building, and the detection patterns for
common attacker behaviors.

## Quick Workflow

1. Verify collection: which exporters, what sampling rate, and what is
   missing.
2. Build a baseline: top talkers, common ports, and normal volumes per
   host role.
3. Hunt beaconing: regular intervals to external hosts.
4. Hunt exfiltration: large outbound flows to unusual destinations.
5. Hunt lateral movement: new internal connections outside the role
   baseline.
6. Correlate with alerts: tie flows to IDS and endpoint events by
   time and host.
7. Document the method and the blind spots (sampling, encryption).
8. Turn repeatable hunts into scheduled detections.

## 1. Collection and baseline

```bash
# Check exporter coverage and sampling (config review)
# - every border and core device exporting?
# - sampling 1:1 on key links, or 1:1000 everywhere (blind)?
# - flows reaching the collector (compare exporter vs collector counts)
echo "record: exporters, sampling rates, retention, gaps"
```

```python
#!/usr/bin/env python3
"""Flow baseline: top talkers and beacon candidates from flow CSV."""
import csv, collections, statistics

# flow csv columns: ts,src,dst,port,bytes,packets
flows = list(csv.DictReader(open("/tmp/flows/day.csv")))
vol = collections.Counter()
for f in flows:
    vol[f["src"]] += int(f["bytes"])
print("top talkers (bytes out):")
for host, b in vol.most_common(10):
    print(f"  {host}: {b / 1e9:.2f} GB")

# Beaconing: group by (src,dst,port), check interval regularity
groups = collections.defaultdict(list)
for f in flows:
    if f["dst"].startswith("10."):
        continue
    groups[(f["src"], f["dst"], f["port"])].append(float(f["ts"]))
for key, times in groups.items():
    if len(times) < 10:
        continue
    times.sort()
    gaps = [b - a for a, b in zip(times, times[1:])]
    mean, stdev = statistics.mean(gaps), statistics.pstdev(gaps)
    if mean > 0 and stdev / mean < 0.15:  # suspiciously regular
        print(f"possible beacon {key}: every {mean:.0f}s, n={len(times)}")
```

## 2. Exfiltration and lateral patterns

```bash
# Large outbound to rare destinations: sort external flows by bytes
# and eyeball the top against the baseline (backups and CDNs are normal)
python3 - << 'PY'
print("flag: >1GB to a host the source never talked to before")
print("flag: steady trickle to one host for days (low and slow)")
print("flag: DNS-shaped flows with huge byte counts (tunneling)")
PY
```

```bash
# Lateral movement: internal flows that break the role baseline
# e.g. a workstation talking SMB to 50 hosts it never touched
python3 - << 'PY'
print("per host: count distinct internal destinations per day")
print("spike vs baseline = possible lateral movement; check the ports")
PY
```

## Edge cases

- Sampling hides low and slow beacons. Note the sampling rate as a
  detection limit; do not claim full coverage.
- NAT collapses many hosts into one IP. Correlate with NAT logs or
  accept the ambiguity.
- Encrypted traffic limits you to metadata. That is the point of
  flow analysis; pair with endpoint data for content.
- Cloud flows have different exporters. Verify VPC flow log
  coverage separately.

## Escalation

- Beacon found: pivot to the endpoint (which process) and to DNS
  logs for the domain.
- Exfiltration suspected: involve incident response; preserve the
  flow data and expand the window.
- No flows for the incident window: check retention and exporter
  health before declaring no evidence.

## Detection and defender view

Flow analysis is itself a defensive technique; attackers evade it
with jittered beacons, domain fronting shaped traffic, and staying
under volume thresholds. Defenders counter with longer baselines,
multi signal correlation (flows plus DNS plus endpoint), and
hunting as a routine, not just during incidents. The durable setup
is unsampled or lightly sampled flow on key links with a year of
retention.

## Key references

- MITRE ATT&CK T1048 (Exfiltration Over Alternative Protocol) and
  T1071 (Application Layer Protocol): flow visible behaviors.
- NetFlow v9 / IPFIX (RFC 7011) field references.
- Related skills: threat-hunting, siem-detections.
