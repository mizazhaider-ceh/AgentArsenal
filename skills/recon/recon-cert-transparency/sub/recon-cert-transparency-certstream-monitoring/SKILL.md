---
name: recon-cert-transparency-certstream-monitoring
parent: recon-cert-transparency
description: Use when you need real-time alerts on newly issued certificates for an authorized target domain during an engagement. Covers running certstream as a long-lived monitor, filtering the firehose for your target domains, logging hits with timestamps, alerting on suspicious patterns (lookalikes, unexpected issuers, staging names), and correlating new certificates with DNS and httpx probing. Authorized targets only, only monitor domains you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-cert-transparency]
extends: []
relates: [recon-cert-transparency-crtsh-workflows, recon-cert-transparency-subdomain-extraction, recon-passive]
tools:
  - name: Python
    version: 3.12
---

certstream streams certificates the moment they are logged to certificate transparency, hours or days before crt.sh indexes them for search. Running it during an engagement catches new subdomains as the target creates them: staging hosts, new services, infrastructure moves, in real time. This sub-skill covers operating certstream as a monitor for recon-cert-transparency. Only monitor domains you are authorized to test.

## Quick Workflow

1. Install certstream and validate the stream with a short test run.
2. Write the filter: your target domains plus lookalike patterns you want to watch.
3. Run the monitor as a long-lived background process with logging to a timestamped file.
4. On each hit: log it, resolve the name, probe it with httpx.
5. Review the log daily for patterns: bursts of issuance, new naming conventions, unexpected issuers.
6. Correlate hits with your other recon: a new cert plus a new DNS record is confirmed new infrastructure.
7. Keep the monitor running for the whole engagement; stop it cleanly at close.

## 1. Basic monitor setup

```bash
pip install certstream
# Test the stream briefly before committing to a long run
timeout 30 certstream --json | head -3 | python3 -m json.tool | head -40
```

The stream is a firehose: thousands of certificates per minute globally. Never run it unfiltered; the filter is the whole point. The JSON per certificate includes `leaf_cert.all_domains`, `leaf_cert.issuer`, and the chain, which is everything the filter needs.

## 2. Targeted filter script

```python
#!/usr/bin/env python3
# ct-monitor.py: watch certstream for target domains
import sys, json, datetime

TARGETS = ["example.com"]           # authorized domains only
WATCH_ALIKE = ["examp1e", "exarnple"]  # lookalike watchlist (brand protection notes)

def matches(domain):
    d = domain.lower().lstrip("*.")
    return any(d == t or d.endswith("." + t) for t in TARGETS)

for line in sys.stdin:
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    if msg.get("message_type") != "certificate_update":
        continue
    leaf = msg["data"]["leaf_cert"]
    domains = leaf.get("all_domains", [])
    hits = [d for d in domains if matches(d)]
    alike = [d for d in domains if any(w in d.lower() for w in WATCH_ALIKE)]
    ts = datetime.datetime.utcnow().isoformat()
    for d in hits:
        print(f"{ts} TARGET {d} issuer={leaf.get('issuer', {}).get('O', '?')}", flush=True)
    for d in alike:
        print(f"{ts} LOOKALIKE {d}", flush=True)
```

```bash
certstream --json 2>/dev/null | python3 ct-monitor.py | tee ct-hits.log
```

Lookalike hits are brand-protection notes, not targets: log them for the report's defensive section, do not enumerate them.

## 3. Running it long-lived

```bash
# Run in background with nohup, restart on failure via a simple loop
nohup bash -c 'while true; do certstream --json 2>/dev/null | python3 ct-monitor.py | tee -a ct-hits.log; sleep 10; done' >/dev/null 2>&1 &
echo $! > ct-monitor.pid
# Daily review
grep " $(date +%Y-%m-%d)" ct-hits.log | sort | uniq -c | sort -rn | head -20
```

certstream connections drop; the loop reconnects. Check the process is alive daily (`ps -p $(cat ct-monitor.pid)`), because a dead monitor silently misses everything. At engagement close, kill it and archive the log with your recon notes.

## 4. Triaging hits

Not every new certificate matters. Triage each:

- New subdomain, resolves, serves content: highest value. Probe with httpx immediately; new infrastructure is often misconfigured.
- New subdomain, does not resolve yet: infrastructure being staged. Note it, re-check daily; it may go live mid-engagement.
- Renewal of a known name: noise, unless the issuer changed (infrastructure move) or the SAN list changed (new names bundled in).
- Wildcard renewal: noise for enumeration, but note the date; fresh wildcards sometimes precede new deployments.

```bash
# Quick triage: resolve the new name and probe
newname="new-staging.example.com"
dig +short "$newname" A @1.1.1.1
echo "$newname" | httpx -silent -title -status-code -tech-detect
```

## Edge cases

- The stream lags or replays: certstream occasionally redelivers. Dedupe hits by certificate fingerprint if your log shows repeats.
- Your filter misses internationalized names: normalize punycode before matching, or add the xn-- forms to TARGETS.
- The target uses many unrelated domains (acquisitions): extend TARGETS only to domains your authorization covers. When in doubt, the lookalike list is for notes, not testing.
- certstream service deprecation risk: if the public endpoint ever goes away, fall back to polling crt.sh diffs (see the crtsh-workflows sub-skill) on a tight schedule.

## Escalation

- A burst of new certificates appears (dozens in an hour): the target is deploying or migrating. Increase httpx probing cadence on the new names; migration windows are misconfiguration windows.
- A certificate appears for a lookalike domain with the target's branding: potential phishing setup. Note it for the defensive findings section with the issuance timestamp; do not interact with it beyond passive observation.

## Detection and defender view

- Run this same monitor defensively: alert on any certificate for your domains that your team did not issue. It is the cheapest compromise and shadow-IT detector available.
- Alert on lookalike domain certificates too: they are the earliest signal of phishing infrastructure, often days before the phishing starts.
- Log which CA issued each certificate: an unexpected issuer for your domain is a red flag for CA account compromise.
- certstream monitoring is passive and invisible to attackers; they cannot tell you are watching the logs.

## Key references

- certstream-python: https://github.com/CaliDog/certstream-python
- certstream service: https://certstream.calidog.io
- RFC 6962 Certificate Transparency: https://www.rfc-editor.org/rfc/rfc6962.html
- crt.sh: https://crt.sh
- MITRE ATT&CK T1593.003 Digital Certificates: https://attack.mitre.org/techniques/T1593/003/
