---
name: privesc-windows-vectors
description: Use when you hold a low-privilege Windows shell or session on
  an authorized penetration test, lab, or CTF and need a systematic map of
  every local privilege escalation vector before you exploit anything.
  Covers service misconfigurations (unquoted paths, weak permissions),
  token manipulation and privilege abuse (SeImpersonatePrivilege and
  related), registry autoruns and AlwaysInstallElevated, scheduled tasks
  with weak ACLs, DLL hijacking, credential harvesting from local stores,
  and kernel driver triage. Built for authorized engagements only:
  enumerate first, verify each finding by hand, exploit the quietest
  reliable path, and capture evidence for the report.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [privesc-windows, privesc-kernel-triage]
tools:
  - name: winpeas
    version: 2024
  - name: PowerShell
    version: 7.4
  - name: accesschk
    version: 6.1
  - name: nmap
    version: 7.98
---
Windows privilege escalation rewards methodical enumeration: most wins come from misconfigurations (services, scheduled tasks, registry, tokens, stored credentials), not zero-days. This skill is the parent map of Windows escalation vectors for authorized penetration tests, labs, and CTFs only. Never apply these techniques to systems you do not have explicit written permission to test. The method is always the same: stabilize the session, enumerate automatically with WinPEAS, verify every finding by hand with native tools, exploit the lowest-noise reliable path, and capture evidence. Deep dives live in the sub-skills.

## Quick Workflow

1. Stabilize the session and record the baseline: `whoami /priv`, `whoami /groups`, hostname, OS build, domain membership.
2. Run WinPEAS and exfiltrate the output; never page through thousands of lines inside a fragile shell.
3. Work the vector classes in order: services, scheduled tasks, registry autoruns, tokens and privileges, DLL hijacking, stored credentials, kernel.
4. Verify each candidate by hand with native commands (`sc qc`, `schtasks /query`, `reg query`, `icacls`) before exploiting.
5. Exploit the quietest reliable vector first; misconfiguration abuse rarely crashes the host.
6. Confirm with `whoami /priv` showing elevated groups, capture proof, and record exact commands for the report.
7. If the target is a domain member, keep privesc and lateral movement evidence separate in your notes.

## 1. Service misconfigurations

Windows services running as SYSTEM with weak configurations are the classic vector: unquoted service paths, writable service binaries, and weak service ACLs.

```powershell
wmic service get name,displayname,pathname,startmode | findstr /i /v "C:\Windows\\"
sc qc VulnService
```

Example output shape: a `BINARY_PATH_NAME` like `C:\Program Files\Vuln App\service.exe` without quotes means Windows tries `C:\Program.exe`, then `C:\Program Files\Vuln.exe`, then the real path; a writable `C:\Program Files\Vuln.exe` you plant gets executed as SYSTEM. Weak service ACLs (`sc sdshow` or accesschk) let you reconfigure the binary path directly. Full coverage is in the `privesc-windows-vectors-service-misconfigurations` sub-skill.

## 2. Tokens and privilege abuse

Your token's privileges decide which impersonation attacks are possible. `SeImpersonatePrivilege` on a service account is historically a straight path to SYSTEM.

```powershell
whoami /priv
```

Example output shape: a list where `SeImpersonatePrivilege` shows as Enabled means token impersonation attacks apply; `SeAssignPrimaryTokenPrivilege`, `SeBackupPrivilege`, and `SeLoadDriverPrivilege` are similarly powerful. The `privesc-windows-vectors-token-manipulation` sub-skill covers privilege enumeration, impersonation attack families, and the authorization boundaries around them.

## 3. Registry autoruns and AlwaysInstallElevated

Registry keys that launch programs at logon or boot, and the AlwaysInstallElevated policy pair, are persistent escalation paths.

```powershell
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

When both AlwaysInstallElevated values are 1, any user can install an MSI as SYSTEM; generating an MSI that adds a user or drops a payload is the standard authorized-lab technique. Writable Run keys or the Startup folder let you plant executables that run at next logon. Details are in `privesc-windows-vectors-registry-and-scheduled-tasks`.

## 4. Scheduled tasks with weak ACLs

Tasks running as SYSTEM whose definition files or executed binaries are writable let you hijack the next run.

```powershell
schtasks /query /fo LIST /v | findstr /i "taskname run.as.author"
icacls "C:\Windows\System32\Tasks\VulnTask"
```

Example output shape: a task authored to run as SYSTEM executing `C:\Tasks\backup.bat` where the batch file or its directory grants you write access. Overwrite the script, wait for or trigger the schedule (`schtasks /run /tn VulnTask` when permitted), and collect SYSTEM. Also check tasks with stored credentials and tasks referencing missing binaries in writable paths.

## 5. DLL hijacking

Services and SYSTEM processes that load DLLs from writable directories, or that fail to find a DLL, let you inject code as SYSTEM.

```powershell
accesschk.exe -dqv "C:\Program Files\VulnApp"
```

Use Process Monitor (procmon) on a lab replica to find `NAME NOT FOUND` DLL loads by SYSTEM processes, then place a hostile DLL with `DllMain` spawning your payload at the missing path. Ordering matters: application directory first, then system directories, then PATH. Always verify the DLL actually loads as SYSTEM before relying on it.

## 6. Stored credentials

Windows stores credentials in many places; each one is a potential password for a stronger account.

```powershell
cmdkey /list
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
findstr /si password *.xml *.ini *.txt C:\ 2>nul
```

Checklist: unattended install files (`Unattend.xml`, `sysprep.inf`) with base64 or plaintext passwords, Group Policy Preferences `cpassword` (decryptable with the public AES key), registry AutoLogon passwords, saved RDP credentials (`cmdkey`), IIS `applicationHost.config`, and WinSCP/PuTTY stored sessions. Try every recovered credential against local admin and domain accounts within the authorized scope.

## 7. Kernel and driver triage

Kernel exploits are the last resort on Windows too: they risk blue screens and EDR behavioral alerts.

```powershell
systeminfo | findstr /i "OS Name OS Version"
driverquery /v | findstr /i "vuln"
```

Record the exact build number (for example 19045 for Windows 10 22H2) before matching against public exploits, and verify the vulnerable driver or component is actually present. The `privesc-kernel-triage` skill covers version enumeration, exploit matching, and safe testing discipline.

## Edge cases

- WinPEAS output is huge; redirect to a file, exfiltrate, and grep locally for color-coded findings instead of reading it in the shell.
- `wmic` is deprecated on newer Windows; prefer PowerShell `Get-CimInstance Win32_Service` when wmic is missing.
- Unquoted service paths only work when you can write to one of the earlier-resolved paths; verify with `icacls` on each candidate directory.
- Token impersonation attacks require specific privileges that hardened service accounts no longer hold; always start from `whoami /priv` rather than assuming.
- UAC means even local administrators run with a filtered token; check `whoami /groups` for the mandatory label and whether the session is elevated.
- Stored credential files may be decoys in CTFs; validate each credential with an actual logon attempt inside scope before building chains on it.
- EDR on a real engagement will flag common privesc tooling; prefer native binaries (LOLBins) and document tool usage for the report.

## Escalation

- If services, tasks, and registry are clean, pivot to application-layer vectors: writable web roots, database credentials in config files, and backup files containing SAM or SYSTEM hives.
- When you land as a second low-privilege user (service account, another local user), re-run the full enumeration from the new context; new privileges unlock new vectors.
- If local privesc stalls but the host is domain-joined, authorized scope may allow pivoting to domain enumeration for misconfigured delegation or kerberoastable accounts; keep the two phases clearly separated in notes.
- Harvested credentials are often the fastest path: try them against WinRM, SMB, RDP, and `runas` within scope before exploit code.

## Detection and defender view

Every vector here has a defender counterpart: service ACL auditing, Sysmon process creation logging, registry Run key monitoring, Credential Guard, LAPS for local admin passwords, and blocking the public AES key usage for GPP passwords. From the authorized tester side, assume Sysmon or EDR logs process creation and registry writes; prefer native tools, minimize dropped files, and document every action for the report. Kernel exploits are the noisiest option and the most likely to crash the host or trigger behavioral blocks.

## Key references

- MITRE ATT&CK T1548 (Abuse Elevation Control Mechanism), T1053.005 (Scheduled Task), T1547 (Boot or Logon Autostart Execution), T1003 (OS Credential Dumping)
- WinPEAS: https://github.com/peass-ng/PEASS-ng
- LOLBAS (living off the land binaries): https://lolbas-project.github.io
- HackTricks Windows Privilege Escalation: https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation
- Microsoft service security docs: https://learn.microsoft.com/en-us/windows/win32/services/service-security-and-access-rights
- AccessChk: https://learn.microsoft.com/en-us/sysinternals/downloads/accesschk
