---
name: incident-breach-scoping-initial-access-identification
description: Use when you must find how the attacker first got in
  during an authorized incident investigation. Covers phishing
  evidence in email gateways and EDR, VPN and remote-access log
  analysis with Python 3.12, web exploitation traces in WAF and
  server logs, credential stuffing patterns, supply-chain indicators,
  and ranking entry hypotheses by evidence. Use when the parent
  incident-breach-scoping workflow starts, when patient zero is
  known but the vector is not, or when eradication needs the entry
  closed before it begins, correlating host evidence with Wireshark
  captures and osquery hunts.
version: 1.0.0
domain: incident
lifecycle: stable
last_verified: 2026-10-23
parent: incident-breach-scoping
requires: [incident-breach-scoping]
extends: []
relates: [incident-breach-scoping]
tools:
  - name: Python
    version: 3.12
  - name: Wireshark
    version: 4.2
  - name: osquery
    version: 5.12.1
---

Initial access identification finds the attacker's first foothold:
the phish that worked, the VPN account that fell, the web flaw that
gave a shell. Everything downstream (lateral movement, persistence,
exfiltration) depends on getting this right, because eradication
must close the actual door, not a decoy. This sub-skill covers the
evidence for each common vector and how to rank competing
hypotheses. Authorized investigations on your own systems only.

## Quick Workflow

1. Establish the earliest confirmed malicious event (the anchor).
2. List plausible entry vectors for the environment.
3. Pull the evidence for each vector in the window before the
   anchor.
4. Rank hypotheses by evidence strength, not by narrative appeal.
5. Confirm the leading hypothesis with a second independent source.
6. Identify what must change to close the vector (patch, reset,
   filter).
7. Record the entry in the scope statement with confidence.
8. Hand the closed vector to eradication as a requirement.

## 1. Phishing evidence

```bash
# Email gateway: messages to patient zero's user before the anchor
# (adapt to your gateway's log format; concept shown)
grep "alice@example.com" /var/log/mail-gateway.log | head -20

# What to look for: first-time senders, lookalike domains, attachments, link clicks
python3 - <<'EOF'
import re
suspicious = []
for line in open('mail-gateway.log'):
    if 'alice@example.com' in line and re.search(r'\.(zip|iso|lnk|html?)(\s|$)', line):
        suspicious.append(line.strip())
print(f"{len(suspicious)} messages with risky attachments to patient zero")
for s in suspicious[:5]:
    print(" ", s[:160])
EOF
```

```bash
# EDR: macro or script execution around the anchor time on patient zero
# Hunt: winword.exe or excel.exe spawning powershell, wscript, or mshta
# osquery on the host:
osqueryi "SELECT name, cmdline, parent FROM processes WHERE parent IN ('winword.exe','excel.exe');"
```

Example output shape:

```
3 messages with risky attachments to patient zero
  Oct 20 09:14:02 from invoices@examp1e-billing.com subject "Overdue invoice" attach invoice.zip
```

A clicked phishing link or opened attachment hours before the first
malware execution is the classic T1566 chain. Confirm with the
user's account of what they clicked; users usually remember the
invoice email.

## 2. VPN and remote access analysis

```bash
# VPN logins before the anchor: new IPs, new ASNs, impossible travel
python3 - <<'EOF'
import re
from collections import defaultdict
logins = defaultdict(list)
for line in open('vpn.log'):
    m = re.search(r'(\d{4}-\d{2}-\d{2} \d+:\d+:\d+).*user=(\w+).*ip=([\d.]+)', line)
    if m:
        logins[m.group(2)].append((m.group(1), m.group(3)))
for user, events in sorted(logins.items()):
    ips = {ip for _, ip in events}
    if len(ips) > 2:
        print(f"{user}: {len(events)} logins from {len(ips)} IPs")
        for ts, ip in events[:6]:
            print(f"   {ts} {ip}")
EOF
```

Example output shape:

```
svc-deploy: 47 logins from 5 IPs
   2026-10-20 22:41:03 198.51.100.23
   2026-10-20 22:41:09 198.51.100.23
```

Forty-seven logins in minutes from one IP is credential stuffing,
not a user typo. Check whether the account had MFA: stuffing
succeeds where MFA is absent or bypassable. The fix is MFA
enforcement plus the password reset, not just the reset.

## 3. Web exploitation traces

```bash
# WAF and access logs: injection strings before the anchor
grep -E "union.*select|'\s*or\s*'|/etc/passwd|\.\./" /var/log/apache2/access.log | head -20

# Then: the web shell or dropper the exploitation planted
find /var/www -name "*.php" -newermt "2026-10-19" -ls 2>/dev/null
find /var/www -name "*.jsp" -newermt "2026-10-19" -ls 2>/dev/null

# Correlate: exploitation timestamp -> file creation timestamp -> first execution
ls -la --time-style=full-iso /var/www/html/uploads/shell.php
```

Example output shape:

```
-rw-r--r-- 1 www-data www-data 2341 2026-10-20 21:58:11 shell.php
```

Exploitation at 21:55, shell dropped at 21:58, first execution at
22:03: that is T1190 with a clean chain. The eradication
requirement is the patch (or WAF rule plus patch), the shell's
removal, and a review of what the web user could reach.

## 4. Credential stuffing and password spraying

```bash
# Auth logs: many usernames from one IP (spraying) or many passwords for one user (stuffing)
grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -10
```

Example output shape:

```
   312 198.51.100.23
    14 203.0.113.77
```

312 failures from one IP is not background noise; it is the entry
attempt. Check whether any succeeded (the "Accepted" line for the
same IP), and treat the success as the anchor if it precedes other
malicious events.

## 5. Supply chain and trusted relationship

The hardest vector: a vendor's compromised update or a trusted
partner's credentials. Evidence is indirect:

- Malware signed with a valid vendor certificate.
- First execution from a software updater process in EDR ancestry.
- The entry host has no phishing, no VPN anomaly, no web
  exploitation, yet malware appeared after an update window.

```bash
# EDR ancestry: what launched the malware
# Look for: updater.exe, installer processes, or remote admin tools as parents
```

Do not declare supply chain lightly; it has vendor and legal
consequences. It is the hypothesis of last resort, reached by
eliminating the others, and it gets its own verification effort.

## 6. Ranking hypotheses

```
Hypothesis                          Evidence                              Confidence
VPN stuffing (svc-deploy)           47 logins, new IP, no MFA, anchor+0h  HIGH
Phishing (alice)                    1 risky email, no click evidence       LOW
Web exploitation                    no injection strings in window         EXCLUDED
Supply chain                        no updater ancestry                    EXCLUDED
```

Rank by evidence, kill hypotheses with negative evidence, and keep
the losers in the record. "We excluded web exploitation because
the WAF logs show no injection in the 72h window" is what makes the
leading hypothesis credible.

## Edge cases

- Multiple plausible entries in the same window. The attacker may
  have tried several; confirm which one produced the first
  execution, and close all attempted vectors, not just the
  successful one.
- The anchor is wrong (earlier activity found later). Re-run the
  vector analysis against the new anchor; entry hypotheses are
  anchor-relative.
- Logs for the entry window are gone (rotation or deletion). Note
  the gap, work from EDR and network telemetry, and mark the
  entry confidence down accordingly.
- The entry used valid credentials at normal hours (insider or
  credential theft with patience). Behavioral evidence (unusual
  data access, new tooling) replaces the anomaly of timing.
- Patient zero is a shared or service account. Attribute through
  source IPs and session data, not the account name; shared
  accounts need their user mapping reconstructed.

## Escalation

- The entry vector is a zero-day or an unpatched vulnerability
  with no fix. Escalate for emergency mitigation (WAF rules,
  feature disablement) and vendor engagement; eradication cannot
  wait for the patch.
- Phishing entry suggests a wider campaign against your users.
  Escalate to the security awareness team and consider a
  fleet-wide hunt for the same lure.
- The entry implicates a vendor or partner. Involve legal before
  contacting them; your evidence must be solid and your
  communication careful.
- You cannot identify the entry after full analysis. Escalate the
  unknown-entry scope to the commander; eradication then covers
  all plausible vectors, which is expensive but necessary.

## Detection and defender view

Every entry vector maps to a preventive control: phishing to email
filtering and user training plus MFA, VPN stuffing to MFA and
lockout policies, web exploitation to patching and WAF, credential
attacks to password hygiene and anomaly detection. The defender
program that emerges from this analysis is layered by vector, and
the metric is time-to-close per vector after identification. The
strategic view: initial access is the cheapest phase to defeat,
because every vector has a well-understood control; the expensive
failures are the ones where the control existed but was not
enforced.

## Key references

- Parent scoping workflow: incident-breach-scoping (this repo)
- MITRE ATT&CK initial access tactics (T1566, T1078, T1190):
  https://attack.mitre.org/
- NIST SP 800-61 Rev. 2: https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final
- CISA phishing guidance: https://www.cisa.gov/topics/cybersecurity-best-practices/phishing
- OWASP web attack descriptions: https://owasp.org/www-community/attacks/
