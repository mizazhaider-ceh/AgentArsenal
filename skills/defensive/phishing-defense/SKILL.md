---
name: phishing-defense
description: "Use when defending an organization against phishing: hardening email authentication with SPF, DKIM, and DMARC, writing gateway and mailbox detection rules, triaging user-reported phish, analyzing headers URLs and attachments safely, running takedowns of phishing sites, and measuring resilience with simulations. Use when phish reports spike, when setting up defenses for a new domain, or after a credential phishing incident."
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response]
tools:
  - name: GoPhish
    version: 0.12
  - name: Python
    version: 3.12
---
Phishing remains the most common initial access vector, and defending
against it is a layered problem: stop what you can at the gateway,
authenticate your own mail so it cannot be spoofed, make reporting
easy, and analyze what gets through. This skill covers the defensive
program end to end for your own organization or an authorized client.

## Quick Workflow

1. Publish and enforce SPF, DKIM, and DMARC on every domain you own,
   starting in monitoring mode.
2. Harden the email gateway: block executable attachments, rewrite
   or detonate URLs, quarantine lookalike-domain mail.
3. Deploy a one-click report-phish button and route reports to the
   SOC queue with automated triage.
4. Analyze reported messages: headers, URLs, attachments, in a
   sandbox, never on a workstation.
5. Extract IOCs, block them, hunt for other recipients, and check
   for credential submissions.
6. Takedown active phishing sites via the host, registrar, and
   blocklist feeds.
7. Run authorized simulations to measure reporting rate and click
   rate, and train on the gaps.
8. Review DMARC aggregate reports weekly and push the policy toward
   reject.

## 1. Email authentication: SPF, DKIM, DMARC

These three DNS-based controls stop exact-domain spoofing of your
domains.

```bash
# Check current posture of a domain
dig +short example.com TXT | grep -i spf
dig +short default._domainkey.example.com TXT
dig +short _dmarc.example.com TXT

# Example SPF: only listed senders may send (start with ~all, move to -all)
# "v=spf1 ip4:198.51.100.0/24 include:_spf.google.com ~all"

# DMARC progression: none -> quarantine -> reject, pct ramps up
# "_dmarc.example.com TXT \"v=DMARC1; p=none; rua=mailto:dmarc@example.com;\""
```

Rollout order: publish SPF, sign with DKIM, publish DMARC at
`p=none` with aggregate reports, read the reports for two weeks to
find legitimate senders you missed, then move to `quarantine` at
increasing percentages, then `reject`. Skipping the monitoring phase
breaks legitimate mail.

```bash
# Parse a DMARC aggregate report quickly (Python stdlib)
python3 << 'EOF'
import xml.etree.ElementTree as ET, glob
for f in glob.glob('dmarc/*.xml'):
    r = ET.parse(f).getroot()
    for rec in r.iter('record'):
        ip = rec.find('row/source_ip').text
        dkim = rec.find('auth_results/dkim/result').text
        spf = rec.find('auth_results/spf/result').text
        disp = rec.find('row/policy_evaluated/disposition').text
        print(ip, "dkim=" + dkim, "spf=" + spf, "disposition=" + disp)
EOF
```

## 2. Gateway and mailbox rules

Layer controls at the gateway before mail reaches users:

- Block or strip dangerous attachments: executables, scripts,
  macro-enabled Office files from external senders, HTML attachments
  with credential forms.
- URL rewriting and detonation: rewrite links to go through the
  sandbox, detonate attachments in a sandbox before delivery.
- Lookalike domain detection: quarantine mail from domains with
  Levenshtein distance 1 to your brand or executive names.
- Display-name spoofing: flag external mail where the display name
  matches an executive but the address does not.
- New-domain rule: quarantine or tag links to domains younger than
  30 days.

Example mailbox transport rule logic (pseudocode for your platform):

```text
IF sender is external
AND (attachment extension IN [exe, scr, js, vbs, hta, lnk, iso]
     OR attachment is office file WITH macros)
THEN quarantine AND notify SOC
```

Test every rule against legitimate business mail first. A rule that
quarantines the finance team's invoices will be disabled by Friday.

## 3. User reporting pipeline

The fastest detector is a user who reports in one click. Deploy a
report-phish button in the mail client that forwards the message with
full headers to the SOC and deletes it from the inbox.

Automated triage on each report:

```bash
# Extract URLs and attachments from a reported .eml for sandboxing
python3 << 'EOF'
import email, re, sys
msg = email.message_from_binary_file(open('/tmp/report.eml','rb'))
body = ""
for part in msg.walk():
    if part.get_content_type() == "text/plain":
        body += part.get_payload(decode=True).decode(errors="ignore")
urls = set(re.findall(r'https?://[^\s<>"\']+', body))
print("\n".join(sorted(urls)))
for part in msg.walk():
    fn = part.get_filename()
    if fn:
        print("attachment:", fn)
        open("/tmp/sandbox/" + fn, "wb").write(part.get_payload(decode=True))
EOF
```

SLA: acknowledge the reporter within the hour, verdict within four.
Users who never hear back stop reporting.

## 4. Header and URL analysis

Read the headers before anything else:

```bash
# Pull the key headers from a reported message
grep -iE "^(Received|Return-Path|Authentication-Results|DKIM-Signature|From|Reply-To):" \
  /tmp/report.eml | head -30
```

Checklist:

- `Authentication-Results`: did SPF, DKIM, DMARC pass for the
  visible From domain.
- `Received` chain: does the first external hop match the claimed
  sender infrastructure. Read bottom-up (earliest first).
- `Reply-To` vs `From` mismatch: classic credential phishing sign.
- `Return-Path` domain vs `From` domain mismatch.
- Lookalike domains: compare character by character, decode punycode.

URL analysis, safe handling:

```bash
# Expand and inspect a suspicious URL without visiting it in a browser
curl -sI -L --max-time 15 "http://suspicious.example/login" | head -20

# Never fetch the page from your workstation or the corporate IP.
# Submit to the sandbox / URL scanner and read the report there.
```

Never click through on a workstation, never enter credentials "to
check", never forward the live phish to colleagues. Work from the
sandbox report.

## 5. Attachment analysis

```bash
# Static first: file type, hashes, strings
file /tmp/sandbox/invoice.doc
sha256sum /tmp/sandbox/invoice.doc
strings /tmp/sandbox/invoice.doc | grep -iE "powershell|cmd|http|autoopen" | head -20

# Office macro check without opening in Word
oledump.py /tmp/sandbox/invoice.doc 2>/dev/null | head -20
# or: python3 -m oletools.olevba /tmp/sandbox/invoice.doc
```

Detonate in an isolated sandbox and record: processes spawned,
network connections, files written, persistence. If it is malicious,
extract the IOCs (URLs, IPs, hashes) and move to blocking and
hunting. If a user opened it, treat the host as compromised and
engage incident response.

## 6. Containment: blocks, hunts, takedowns

```bash
# Hunt: who else got the same phish (same sender domain or subject)
index=email_logs sender_domain="evil.example" earliest=-7d@d latest=@d
| stats values(recipient) as recipients count by sender, subject

# Hunt: who clicked (proxy logs to the phishing URL after delivery)
index=proxy url="*evil.example/login*" earliest=-7d@d latest=@d
| stats values(user) as clickers count
```

For everyone who clicked or submitted credentials: force password
reset, revoke sessions and tokens, review mailbox rules the attacker
may have created (see the BEC note below), and check for forwarding
rules.

Takedown steps for the phishing site:

1. Report to the hosting provider abuse contact with the URL and
   evidence.
2. Report to the registrar if the domain is clearly abusive.
3. Submit the URL to blocklist feeds and the browser safe-browsing
   programs.
4. If it impersonates your brand, file with your brand protection
   service as well.
5. Re-check daily; attackers re-host fast.

## 7. BEC-specific defense

Business email compromise often uses no malware, just stolen
sessions or lookalike domains, so attachment sandboxes miss it.

Mailbox rule hunting after a suspected BEC:

```bash
# Exchange/Graph: list inbox rules on a mailbox (needs authorized admin)
# Look for rules that move mail to RSS Subscriptions, mark as read,
# or forward externally. Any rule the user did not create is hostile.
```

Controls: require phishing-resistant MFA (FIDO2) for mail access,
alert on mailbox rule creation and external forwarding, alert on
impossible-travel logons to mail, and set a verification policy for
payment changes (call back on a known number, never trust email
alone).

## 8. Simulations and metrics

Run authorized phishing simulations with GoPhish or your platform:

```bash
# GoPhish admin UI runs locally; campaigns are built in the UI.
# Track per campaign: sent, opened, clicked, submitted, reported.
```

Metrics that matter: report rate (goal: rising), click rate (goal:
falling), median time to report, and repeat clickers for targeted
training. Never punish individuals publicly; report trends to
leadership and train the departments that struggle. Get written
authorization before any simulation, and exclude the SOC on-call
rotation from surprise tests that could mask a real incident.

## Edge cases

- The phish comes from a compromised legitimate sender. Domain
  reputation checks pass; rely on content analysis, URL sandboxing,
  and user reports.
- QR code phishing (quishing): the URL hides in an image. Gateway
  OCR or user reporting is the catch; train users that QR codes in
  email are suspicious.
- The attacker uses a legitimate service (Google Forms, SharePoint)
  for credential harvesting. Blocklisting the domain breaks business;
  block the specific URL and hunt for visitors.
- DMARC reports show legitimate senders failing. Fix their SPF/DKIM
  before enforcing reject, or you will break payroll emails.
- Users forward phish to the helpdesk as attachments, spreading it.
  The report button must strip and contain the sample automatically.
- Simulation emails get reported as real phish. That is success;
  tune the triage to recognize your own simulation markers fast.

## Escalation

- Credentials were submitted: treat as account compromise. Reset,
  revoke sessions, hunt the mailbox, engage incident response.
- Malware was executed: isolate the host and follow the incident
  playbook; the phish is now an intrusion.
- A VIP or finance user is targeted with a tailored lure: brief
  them directly, tighten monitoring on their accounts, and consider
  a temporary approval workflow for payments.
- Takedown stalls while users keep clicking: escalate to the
  registrar, add the URL to every blocklist you control, and warn
  users with the exact lure text.
- Suspected insider involvement in the phish targeting: hand to the
  investigation lead and HR/legal; do not confront.

## Detection and defender view

Phishing defense is the defender's home turf; attackers adapt
constantly:

- Attackers bypass SPF/DKIM/DMARC with lookalike domains and
  compromised accounts, so content and behavior rules matter as much
  as authentication.
- Attackers use adversary-in-the-middle kits to steal session
  cookies, defeating MFA codes. Move to phishing-resistant MFA
  (FIDO2) for high-value users.
- Attackers rotate phishing domains hourly. Block on content
  patterns and kit fingerprints, not just domains.
- Attackers A/B test lures against your gateway. Keep gateway rules
  and sandbox detonations updated, and watch for lures tuned to
  your organization's language.
- Measure the program by reporting speed and credential-reset time,
  not just click rate. A user who reports in two minutes beats a
  gateway that blocks 99 percent.

## Key references

- MITRE ATT&CK T1566 (Phishing), T1566.001 (Spearphishing
  Attachment), T1566.002 (Spearphishing Link), T1137 (Office
  Application Startup).
- RFC 7208 (SPF), RFC 6376 (DKIM), RFC 7489 (DMARC).
- CISA phishing guidance: https://www.cisa.gov/topics/cyber-threats-and-advisories/phishing
- GoPhish documentation: https://docs.getgophish.com/
- APWG and brand protection reporting channels.
