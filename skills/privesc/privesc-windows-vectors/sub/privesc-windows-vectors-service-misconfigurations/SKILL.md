---
name: privesc-windows-vectors-service-misconfigurations
description: Use when authorized Windows privilege escalation focuses on
  services running as SYSTEM or other privileged accounts. Covers
  enumerating services and their binary paths, unquoted service path
  exploitation step by step, writable service binaries and directories,
  weak service ACLs that allow reconfiguration, insecure service
  permissions with sc and accesschk, and restarting services safely.
  Includes verifying SYSTEM execution and cleaning up. For authorized
  pentests, labs, and CTFs only.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-windows-vectors]
extends: []
parent: privesc-windows-vectors
relates: [privesc-windows, privesc-windows-vectors-token-manipulation]
tools:
  - name: winpeas
    version: 2024
  - name: PowerShell
    version: 7.4
  - name: accesschk
    version: 6.1
---
Windows services commonly run as SYSTEM, so any misconfiguration that lets a low-privilege user influence what a service executes is a direct path to SYSTEM on an authorized engagement. This sub-skill covers the complete service attack surface: enumeration, unquoted service paths, writable binaries and directories, and weak service ACLs that permit reconfiguration. Scope is authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Enumerate all services with their binary paths and start accounts: `Get-CimInstance Win32_Service` or WinPEAS output.
2. Flag services running as SYSTEM or LocalService with paths outside `C:\Windows`, missing quotes, or writable components.
3. Verify each candidate by hand: `sc qc <name>` for the path, `icacls` on every path component for writability.
4. Exploit the simplest candidate first: unquoted path planting, binary replacement, or service reconfiguration via weak ACLs.
5. Restart or trigger the service and confirm SYSTEM with `whoami` from the payload.
6. Restore the original binary and configuration, and document exact commands for the report.

## 1. Service enumeration

List services with the fields that matter: name, binary path, start mode, and the account it runs as.

```powershell
Get-CimInstance Win32_Service | Select-Object Name, PathName, StartMode, StartName | Format-Table -AutoSize
```

Example output shape: rows where `StartName` is `LocalSystem` and `PathName` points outside `C:\Windows` go on the shortlist. Also capture with the classic tools for cross-checking:

```cmd
wmic service get name,displayname,pathname,startmode | findstr /i /v "C:\Windows\\"
sc query state= all | findstr "SERVICE_NAME"
```

Record the exact `PathName` including quotes (or their absence); the quote check in section 2 depends on it.

## 2. Unquoted service paths

When a service path contains spaces and is not wrapped in quotes, Windows resolves it greedily from left to right, trying each space-separated prefix with `.exe` appended.

```cmd
sc qc VulnService
```

Example output shape:

```
BINARY_PATH_NAME   : C:\Program Files\Vuln App\service.exe
```

Windows tries `C:\Program.exe`, then `C:\Program Files\Vuln.exe`, then `C:\Program Files\Vuln App\service.exe`. Check writability of each parent directory:

```cmd
icacls "C:\Program Files\Vuln App"
icacls "C:\Program Files"
icacls C:\
```

If `C:\Program Files\Vuln.exe` is writable (the `Vuln App` directory grants you write, or the path component does), plant your payload there with that exact name. When the service restarts, Windows executes your binary as SYSTEM before ever reaching the real path. Then restart the service if your privileges allow, or wait for a reboot:

```cmd
sc stop VulnService
sc start VulnService
```

## 3. Writable service binaries and directories

Even with proper quoting, a service binary or its directory may grant you write access, which means direct replacement.

```cmd
icacls "C:\Program Files\VulnApp\service.exe"
accesschk.exe -qv "C:\Program Files\VulnApp\service.exe"
```

Example output shape: an `icacls` line like `BUILTIN\Users:(I)(M)` (modify rights for Users) on the binary means you can overwrite it. Back up the original, replace it with your payload, restart the service, collect SYSTEM, then restore the original binary and restart again. If only the directory is writable, the same replacement works, and a writable directory also enables DLL planting alongside the binary.

## 4. Weak service ACLs and reconfiguration

Service ACLs may grant you `SERVICE_CHANGE_CONFIG`, which lets you rewrite the binary path to anything you control.

```cmd
accesschk.exe -ucqv VulnService
sc sdshow VulnService
```

Example output shape: accesschk reporting `SERVICE_CHANGE_CONFIG` for your user, or an SDDL string granting your SID `RPWP` style rights. Reconfigure the service to run your payload:

```cmd
sc config VulnService binPath= "C:\Users\app\pwn.exe"
sc stop VulnService
sc start VulnService
```

Note the space after `binPath=`; `sc` requires it. Your payload runs as SYSTEM on start. Always record the original `binPath` from `sc qc` first so you can restore it, and restore it as part of cleanup.

## 5. Confirming SYSTEM and safe restarts

Payloads should prove privilege and stay quiet. A simple proof writes a marker file and the `whoami` output:

```cmd
C:\Users\app\pwn.exe
```

where `pwn.exe` executes `whoami > C:\Users\app\proof.txt` as its first action. Example proof content: `nt authority\system`. Restarting services can disrupt the target: prefer `sc stop` and `sc start` on the vulnerable service only, never reboot the host on an engagement without explicit approval, and avoid touching services whose purpose you do not understand (database, backup, and security services can cause data loss or alerts when restarted).

## Edge cases

- `sc config` syntax is unforgiving: `binPath= "path"` needs the space after the equals sign, and paths with spaces need quotes inside the value.
- Some services run as virtual accounts or managed service accounts rather than SYSTEM; check `StartName` because the payoff differs.
- Service executables may be protected by Windows Resource Protection or EDR file guards that restore or block replacement; verify the replacement actually persisted before restarting.
- Unquoted path planting fails when none of the prefix directories are writable; verify every prefix with `icacls`, not just the obvious one.
- Restarting a service you reconfigured may fail if the service has dependencies; check `sc qc` dependency lines and restart in order.
- On hardened hosts, AppLocker or WDAC may block your payload binary from executing even as SYSTEM; test execution as your own user first.

## Escalation

- If no service is directly exploitable, check services running as named user accounts: their credentials or profile directories may be readable and lead to credential reuse.
- When service ACLs are tight but the binary directory is writable, combine binary replacement with DLL hijacking for a second chance at the same service.
- If service restarts are blocked, look for services configured with `SERVICE_AUTO_START` that will execute your planted binary at the next legitimate reboot within the engagement window.
- Pivot to the sibling sub-skills when services are clean: scheduled tasks and registry autoruns follow the same writable-component logic.

## Detection and defender view

Defenders should audit service binary paths for quoting, enforce least-privilege service accounts instead of SYSTEM, monitor service configuration changes (Event ID 7045 for new services, 7036 for state changes), and alert on service binaries modified outside change windows. From the authorized tester side, service reconfiguration and binary replacement are logged in the System event log and are visible to EDR; keep a precise record of original values, restore everything, and note the exact event IDs your actions generated so the report's detection section is accurate.

## Key references

- MITRE ATT&CK T1543.003 (Windows Service)
- Microsoft sc.exe docs: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-config
- AccessChk: https://learn.microsoft.com/en-us/sysinternals/downloads/accesschk
- HackTricks services section: https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation#services
- LOLBAS (payload binaries that evade naive blocklists): https://lolbas-project.github.io
- Microsoft service security: https://learn.microsoft.com/en-us/windows/win32/services/service-security-and-access-rights
