---
name: privesc-windows-vectors-registry-and-scheduled-tasks
description: Use when authorized Windows privilege escalation turns to the
  registry and the task scheduler. Covers enumerating Run and RunOnce keys,
  AlwaysInstallElevated detection in both hives, writable registry paths
  that privileged software reads, scheduled task enumeration with schtasks
  and PowerShell, weak ACLs on task files and executed binaries, stored
  credentials in task definitions, and the Startup folder. For authorized
  pentests, labs, and CTFs only.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-windows-vectors]
extends: []
parent: privesc-windows-vectors
relates: [privesc-windows, privesc-windows-vectors-service-misconfigurations]
tools:
  - name: winpeas
    version: 2024
  - name: PowerShell
    version: 7.4
  - name: accesschk
    version: 6.1
---
The registry and the Task Scheduler both launch programs with elevated privileges on triggers you can predict: logon, boot, and schedules. On an authorized engagement, writable autorun keys, the AlwaysInstallElevated policy pair, and weakly permissioned scheduled tasks are reliable SYSTEM paths. This sub-skill covers enumerating both stores, verifying writability by hand, exploiting the classic patterns, and staying within scope. Authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Enumerate autorun locations: HKLM and HKCU Run and RunOnce keys, plus the Startup folders.
2. Check the AlwaysInstallElevated values in both the HKLM and HKCU policy hives.
3. Enumerate scheduled tasks with `schtasks /query /v` and PowerShell, noting the run-as account and the executed binary.
4. Verify writability by hand: `reg query` plus ACL inspection on keys, `icacls` on task files and binaries.
5. Exploit the simplest candidate: plant an autorun entry, build an MSI for AlwaysInstallElevated, or hijack a writable task binary.
6. Trigger or wait for execution, confirm SYSTEM, clean up the planted entries, and document everything.

## 1. Registry autorun enumeration

Check every standard autorun location and note which ones you can write to.

```powershell
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce
reg query HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
```

Example output shape: value entries like `Updater  REG_SZ  C:\Program Files\App\updater.exe`. HKLM entries run for all users at logon with elevated context when triggered by privileged logons; HKCU entries run as the hive owner. Check the ACL on each key:

```powershell
accesschk.exe -kqv "HKLM\Software\Microsoft\Windows\CurrentVersion\Run"
```

If your user can write to an HKLM Run key, add a value pointing at your payload; it executes at the next privileged logon. Also check the Startup folders:

```powershell
dir "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
icacls "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
```

## 2. AlwaysInstallElevated

When both policy values are set to 1, Windows Installer runs MSI packages as SYSTEM for any user.

```powershell
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

Example output shape: both queries returning `AlwaysInstallElevated  REG_DWORD  0x1` means the vector is live. The authorized-lab technique is generating an MSI that executes your payload (the classic pattern adds a local user or writes a marker), then installing it:

```cmd
msiexec /quiet /i C:\Users\app\pwn.msi
```

The install runs as SYSTEM. This is configuration abuse, not exploitation of a bug, which is why it appears so often in labs and why defenders must explicitly disable it via Group Policy.

## 3. Writable registry paths read by privileged software

Beyond autoruns, privileged software reads many registry values: service image paths, installer source lists, and application settings.

```powershell
reg query HKLM\SYSTEM\CurrentControlSet\Services\VulnService /v ImagePath
accesschk.exe -kqv "HKLM\System\CurrentControlSet\Services\VulnService"
```

If a service's registry key is writable, you can rewrite its `ImagePath` exactly like a weak service ACL, then restart the service. The same logic applies to any privileged program that reads a path or command line from a writable key. Enumerate candidate keys with WinPEAS registry checks and verify each by hand.

## 4. Scheduled task enumeration

List tasks with full verbosity and filter for privileged run-as accounts.

```cmd
schtasks /query /fo LIST /v | findstr /i /c:"TaskName" /c:"Run As User" /c:"Task To Run"
```

```powershell
Get-ScheduledTask | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, NextRunTime
```

Example output shape: a task named `\Maintenance\Cleanup` with `Run As User: NT AUTHORITY\SYSTEM` and `Task To Run: C:\Scripts\cleanup.bat`. The task XML lives under `C:\Windows\System32\Tasks`; check its ACL and the ACL of everything it executes:

```powershell
icacls "C:\Windows\System32\Tasks\Maintenance\Cleanup"
icacls "C:\Scripts\cleanup.bat"
icacls "C:\Scripts"
```

## 5. Exploiting weak scheduled tasks

The patterns mirror services: writable script, writable directory in the path, or weak task file ACL.

```powershell
icacls "C:\Scripts\cleanup.bat"
```

Example: `BUILTIN\Users:(I)(M)` on the batch file means you can overwrite it. Plant a payload that writes proof, then trigger the task if permitted or wait for the schedule:

```cmd
schtasks /run /tn "\Maintenance\Cleanup"
type C:\Users\app\proof.txt
```

If the task file itself is writable, you can rewrite the task definition to point at your binary, though this is noisier. Tasks may also store credentials (`schtasks /query /v` shows the run-as user; the password is stored encrypted but the task runs with those rights regardless). Always restore the original script after success.

## 6. Startup folder planting

The Startup folders execute at logon with the logging-on user's privileges, which is a persistence and escalation path when administrators log on.

```powershell
icacls "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
dir "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
```

A writable common Startup folder means your payload runs at the next logon of any user, including administrators. On an engagement this is typically a persistence technique after you already hold privilege, but in labs with auto-logon administrators it is a direct escalation. Verify with the AutoLogon registry values whether privileged logons actually occur.

## Edge cases

- AlwaysInstallElevated requires both hives set to 1; one hive alone is not exploitable, so check both before investing time.
- Scheduled tasks with `Run only when user is logged on` will not fire for SYSTEM contexts you expect; read the full task settings, not just the trigger summary.
- Task Scheduler on hardened hosts requires exact XML validity; hand-editing task files often breaks the task, so prefer overwriting the executed binary over rewriting the task.
- Registry Run keys under HKLM need an actual privileged logon to fire; on servers where nobody logs on interactively, the payload may never execute within the engagement window.
- `schtasks /run` demands the right to run the task on demand; if denied, you must wait for the schedule, so note `NextRunTime` in your plan.
- MSI installs via AlwaysInstallElevated are logged loudly in the Application log; there is no quiet variant, so align with the rules of engagement.

## Escalation

- If autoruns and tasks are clean, check logon scripts assigned via Group Policy or the userinit value: `reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v Userinit`.
- When the task binary is not writable but its directory is, plant a DLL alongside it for hijacking or drop a same-named binary earlier in a writable PATH entry.
- If you can write to a task file but not execute on demand, combine with social timing: schedule-adjacent maintenance windows in labs often trigger tasks predictably.
- Pivot to the sibling sub-skills when this class is clean: service misconfigurations follow identical writable-component logic.

## Detection and defender view

Defenders should monitor Run key writes (Sysmon Event ID 13), alert on new scheduled tasks (Event ID 4698) and task modifications, enforce AlwaysInstallElevated disabled via Group Policy, and audit ACLs on task files and script directories. From the authorized tester side, registry and task modifications are among the most logged actions on Windows; every write lands in the Security log, so document exact timestamps and restore every planted value during cleanup.

## Key references

- MITRE ATT&CK T1547.001 (Registry Run Keys / Startup Folder), T1053.005 (Scheduled Task), T1548.002 (Bypass User Account Control)
- Microsoft schtasks docs: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks
- Autoruns reference locations: https://learn.microsoft.com/en-us/sysinternals/downloads/autoruns
- HackTricks registry section: https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation#registry
- AlwaysInstallElevated background: https://learn.microsoft.com/en-us/windows/win32/msi/alwaysinstallelevated
- Sysmon Event ID 13 (registry value set): https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon
