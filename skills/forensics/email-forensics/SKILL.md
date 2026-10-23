---
name: email-forensics
description: Use when investigating a suspicious email during phishing triage
  or incident response. Covers full header analysis, Received chain tracing,
  SPF/DKIM/DMARC verification with dig, attachment extraction and hashing,
  URL and indicator extraction, and telling spoofing from compromise. Use when
  a user reports a phish, when an alert fires on a malicious attachment, or
  when you need to prove whether a message really came from who it claims.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [forensics-fundamentals, incident-response]
tools:
  - name: Python
    version: 3.12
  - name: BIND
    version: 9.20.0
---

Email forensics answers a deceptively simple question: is this message what it
claims to be, and what did it try to do. The body is the least trustworthy
part; the headers, the authentication results, and the attachments carry the
evidence. This skill covers the defensive workflow: extracting the raw
message, reading the Received chain bottom-up, verifying SPF/DKIM/DMARC,
safely extracting attachments for hashing and triage, pulling URLs and
indicators, and distinguishing a spoofed sender from a compromised real
account. Scope: analyze messages you are authorized to handle (reported
phishes, quarantine samples, your own test mails). Never reply to, forward,
or click through a live phish from your workstation; work from the raw source
in a controlled environment.

## Quick Workflow

1. Get the raw message source (.eml), never the rendered view; verify its
   hash.
2. Read the headers top to bottom, then trace the Received chain bottom-up to
   find the true origin IP.
3. Check Authentication-Results: SPF, DKIM, and DMARC verdicts, and verify
   them yourself with dig when they look forged.
4. Extract attachments without opening them; hash each and compare against
   known-malicious sets.
5. Extract URLs, decode shorteners and tracking redirects, expand the final
   destination.
6. Decide the verdict: spoofed sender, compromised account, or legitimate.
7. Pull indicators (IPs, domains, hashes, Message-IDs) for blocking and
   hunting.
8. Write the triage note: verdict, evidence, and recommended actions.

## 1. Getting the raw message

The rendered email lies by design. The raw source is the evidence.

```bash
# Save the reported message as .eml from the mail client or gateway
# (In Outlook: File > Save As; in Gmail: Show original > Download)
sha256sum suspicious.eml | tee suspicious.sha256

# Headers first: everything before the first blank line
awk 'BEGIN{p=1} /^$/{p=0} p' suspicious.eml | head -80

# Quick view of the key headers in one pass
grep -iE '^(From|To|Date|Subject|Message-ID|Reply-To|Return-Path|X-Mailer|Authentication-Results):' suspicious.eml
```

If the message came from a gateway or quarantine, also pull the gateway's
own logs for the same Message-ID; the gateway often records the connecting
IP and its own spam verdict, which corroborates the headers.

## 2. Tracing the Received chain

Read Received headers from the BOTTOM up: the bottom one is the first hop,
added by the first server that touched the message. Each hop should logically
hand to the next.

```bash
# Number the Received hops in chronological order (bottom-up)
grep -n '^Received:' suspicious.eml | tac | cat -n

# Extract the IPs in hop order
grep '^Received:' suspicious.eml | tac | grep -oE '\[[0-9.]+\]' | head -20
grep '^Received:' suspicious.eml | tac | grep -oE 'from [^ ]+' | head -20
```

Red flags: the bottom Received shows a residential or VPS IP instead of a
mail server, the `from` hostname does not resolve to the connecting IP
(reverse DNS mismatch), timestamps jump backwards, or there are suspiciously
few hops for a message claiming to come from a major provider. A legitimate
Gmail message always shows Google's infrastructure in the chain; a phish
claiming to be from Gmail that entered through an unknown relay is spoofed.

```bash
# Reverse DNS check on the origin IP
dig -x 203.0.113.45 +short

# Does the claimed sending domain's MX match the infrastructure?
dig gmail.com MX +short
```

## 3. SPF, DKIM, and DMARC verification

Authentication-Results is convenient but forgeable by the sender's own
server, so verify the important ones yourself.

```bash
# Read the verdicts the receiving server recorded
grep -i 'Authentication-Results:' -A3 suspicious.eml | head -20

# SPF: which IPs may send for the domain? (check the Return-Path domain)
dig suspect-domain.example TXT +short | grep -i spf

# DMARC: what should receivers do on failure?
dig _dmarc.suspect-domain.example TXT +short

# DKIM: find the selector from the DKIM-Signature header, then query it
grep -i '^DKIM-Signature:' suspicious.eml | grep -oE 's=[^;]+'
dig selector1._domainkey.suspect-domain.example TXT +short
```

Interpretation matrix: SPF pass plus DKIM pass plus DMARC pass on the
organizational domain means the message really came from that domain's
infrastructure (though the account itself may be compromised). SPF fail or
softfail with a `p=reject` DMARC policy means spoofing, full stop. No
authentication headers at all on a message claiming to be from a major brand
is itself the verdict.

## 4. Attachment extraction and triage

Extract attachments with code, never by double-clicking. Hash immediately.

```bash
# List attachments without extracting
python3 - <<'EOF'
import email
from email import policy
msg = email.message_from_binary_file(open('suspicious.eml','rb'), policy=policy.default)
for part in msg.walk():
    if part.get_content_disposition() == 'attachment':
        print(part.get_filename(), part.get_content_type(), len(part.get_content()))
EOF

# Extract to an isolated directory and hash
mkdir -p attach && python3 - <<'EOF'
import email, hashlib, os
from email import policy
msg = email.message_from_binary_file(open('suspicious.eml','rb'), policy=policy.default)
for i, part in enumerate(msg.walk()):
    if part.get_content_disposition() == 'attachment':
        name = part.get_filename() or f'attachment_{i}'
        data = part.get_content()
        if isinstance(data, str):
            data = data.encode()
        path = os.path.join('attach', name)
        open(path, 'wb').write(data)
        print(name, hashlib.sha256(data).hexdigest())
EOF

# What is it really? (extension vs magic bytes)
file attach/*
```

Then hand each attachment to static-triage: strings, entropy, YARA scan, and
packer checks, all without executing. Password-protected archives ("see
attached password in the email body") are a deliberate evasion of gateway
scanning; treat them as hostile until proven otherwise, and never type the
provided password into your main workstation's extractor without isolation.

## 5. URL extraction and expansion

Phishing lives in the links. Extract every URL, then resolve where each one
really goes without visiting it in a browser.

```bash
# Raw URLs from body and headers
grep -a -o -E 'https?://[^ "<>()]+' suspicious.eml | sort -u | head -40

# Decode HTML entities and URL encoding first for obfuscated links
python3 - <<'EOF'
import re, html, urllib.parse
raw = open('suspicious.eml', errors='ignore').read()
for u in sorted(set(re.findall(r'https?://[^\s"<>]+', raw))):
    print(html.unescape(urllib.parse.unquote(u)))
EOF

# Resolve redirects WITHOUT rendering: HEAD requests with curl, no browser
curl -s -o /dev/null -w '%{url_effective} -> %{http_code}\n' -L --max-redirs 5 --max-time 10 'http://short.example/abc123'
```

Red flags: display text that differs from the href (`<a
href="http://evil.example">https://bank.example</a>`), punycode domains
(`xn--`), excessive subdomains burying the real domain, and URL shorteners
in corporate mail. The effective domain is the registrable domain of the
final URL, not the brand name in the path.

## 6. Verdict: spoofed, compromised, or legitimate

Weigh the evidence, not the story in the body.

```bash
# Checklist, answered from the evidence above:
# 1. Does the Received chain show the claimed provider's infrastructure? (Y/N)
# 2. SPF/DKIM/DMARC: pass, fail, or absent? (verified yourself, not just the header)
# 3. Does Reply-To differ from From? (classic phish tell)
# 4. Do the attachment hash and URLs match known-malicious sets?
# 5. Does the Message-ID domain match the sender domain?
grep -i '^Message-ID:' suspicious.eml
```

Spoofed sender: auth fails or is absent, chain shows foreign infrastructure.
Compromised account: auth passes on the real domain, but content is
anomalous (unusual language, mass recipients, first-time attachment type);
check the account's login history next. Legitimate: everything checks out and
the content matches expected business. When in doubt between compromised and
legitimate, treat as compromised until the account owner confirms.

## 7. Indicators and handoff

Extract clean IOCs for the blocklist and the hunt.

```bash
# Origin IP, final URLs, attachment hashes, sender domains
{
  echo "## origin IPs"; grep '^Received:' suspicious.eml | tac | grep -oE '\[[0-9.]+\]' | head -5
  echo "## urls"; grep -a -o -E 'https?://[^ "<>()]+' suspicious.eml | sort -u
  echo "## hashes"; sha256sum attach/* 2>/dev/null
  echo "## message-id"; grep -i '^Message-ID:' suspicious.eml
} > iocs.txt
cat iocs.txt
```

Handoff note contents: verdict, the two or three strongest evidence points,
the IOC list, who else received it (check the gateway for the same
Message-ID or subject), and recommended actions (block, hunt, password
reset, user warning). Keep the raw .eml attached to the case, not pasted
into chat.

## Edge cases

- Message is a forwarded report, not the original: the headers you see are
  the forwarder's. Get the original .eml or analyze the embedded original
  inside the forwarded body.
- DKIM signature present but body hash fails: the message was modified in
  transit (mailing list footers do this legitimately); treat auth as
  inconclusive, not failed.
- Attachment is a password-protected zip with the password in the body:
  standard evasion. Extract only in an isolated VM and treat contents as
  hostile.
- Email claims to be internal but arrived from outside: check the first
  trusted hop; display-name spoofing ("CEO Name <attacker@example>") needs no
  technical spoofing at all.
- Bounce or NDR messages: the headers describe the bounce path, not the
  original phish; extract the attached original message and analyze that.
- Encrypted (S/MIME, PGP) suspicious mail: you cannot read it without the
  recipient key; work from gateway metadata and the envelope instead.

## Escalation

- Headers are missing or stripped by the reporting tool: go to the mail
  gateway or journaling archive for the pristine copy; never reconstruct
  headers from memory.
- Need to confirm a compromised account: pull the account's sign-in logs
  (impossible travel, new device, MFA fatigue patterns) and sent-items for
  the same timeframe.
- Widespread campaign: pivot on the Message-ID pattern, the attachment hash,
  or the origin ASN across the gateway logs to find every recipient, then
  triage each mailbox for clicks and replies.
- Legal hold or law enforcement involvement: stop, preserve everything
  untouched, and hand the chain of custody to the proper authority.
- Language you cannot read: machine-translate the body for triage only, and
  note that nuance may be lost; the technical verdict does not depend on the
  prose.

## Detection and defender view

Email forensics is the back half of phishing defense: the front half is
stopping the message. Defenders should enforce DMARC `p=reject` on every
domain they own (including lookalike monitoring), strip or sandbox
attachments by policy, rewrite or detonate URLs at click time, and train
users to report with one click so triage gets pristine originals. Detection
rules to build: first-time sender with attachment to finance staff,
display-name mismatch on executive names, and authentication failures on
domains with reject policies. The misuse case is weaponizing these same
techniques to craft better phishes or to stalk someone through their mail;
this skill exists to dissect attacks, and using it to build them crosses the
line into unauthorized activity.

## Key references

- MITRE ATT&CK T1566.001 (Spearphishing Attachment) and T1566.002
  (Spearphishing Link): the delivery techniques under analysis.
- MITRE ATT&CK T1566.003 (Spearphishing via Service): phish via trusted
  platforms.
- RFC 7208 (SPF), RFC 6376 (DKIM), RFC 7489 (DMARC): the authentication
  standards.
- RFC 5322 (Internet Message Format): header syntax.
- BIND 9 dig manual: https://bind9.readthedocs.io
- Python email package docs: https://docs.python.org/3/library/email.html
