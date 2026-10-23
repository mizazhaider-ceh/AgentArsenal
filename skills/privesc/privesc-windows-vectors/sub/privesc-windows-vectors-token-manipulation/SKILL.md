---
name: privesc-windows-vectors-token-manipulation
description: Use when authorized Windows privilege escalation depends on
  access tokens: enumerating whoami /priv output, understanding
  SeImpersonatePrivilege and SeAssignPrimaryTokenPrivilege, how token
  impersonation attack families work at a conceptual level, capturing and
  reusing tokens from privileged processes, AlwaysInstallElevated as a
  related installer path, and the authorization boundaries for using
  impersonation tooling on an engagement. For authorized pentests, labs,
  and CTFs only.
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
  - name: Python
    version: 3.12
---
Windows access tokens carry both identity and privileges, and several token privileges are effectively equivalent to SYSTEM on an authorized engagement. This sub-skill covers privilege enumeration, the impersonation attack families built on `SeImpersonatePrivilege`, token capture and reuse concepts, and the strict authorization boundaries for running impersonation tooling. These techniques are powerful and closely watched by defenders, so the emphasis here is on understanding conditions, verifying prerequisites, and staying inside the written scope. Authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Enumerate token privileges with `whoami /priv` and group membership with `whoami /groups`; record which are enabled.
2. Identify impersonation-relevant privileges: `SeImpersonatePrivilege`, `SeAssignPrimaryTokenPrivilege`, `SeTcbPrivilege`, `SeBackupPrivilege`, `SeDebugPrivilege`, `SeLoadDriverPrivilege`.
3. Verify the account context: impersonation attacks typically need a service or network service account, not a plain interactive user.
4. Match the privilege set to the correct attack family and confirm the tooling matches the OS build.
5. Execute the impersonation within the authorized scope, confirm SYSTEM with `whoami`, and capture evidence.
6. Document the exact privilege, OS build, and tool version for the report's reproducibility section.

## 1. Reading whoami /priv output

This is the prerequisite check for the entire sub-skill. Run it in every session context you obtain.

```powershell
whoami /priv
```

Example output shape:

```
Privilege Name                Description                               State
============================= ========================================= ========
SeImpersonatePrivilege        Impersonate a client after authentication Enabled
SeAssignPrimaryTokenPrivilege Replace a process level token           Disabled
SeShutdownPrivilege           Shut down the system                    Disabled
```

`Enabled` versus `Disabled` matters: some attacks need the privilege enabled, others can enable it. `SeImpersonatePrivilege` enabled on a service account (IIS app pool, SQL Server service, scheduled task context) is the classic precondition. Also run `whoami /groups` to see group SIDs: membership in Backup Operators, Print Operators, or DnsAdmins each has its own documented escalation chain.

## 2. How token impersonation attacks work

The attack family exploits a Windows behavior: a process holding `SeImpersonatePrivilege` can coerce a privileged local system (through NTLM authentication callbacks over named pipes or local RPC) into authenticating to it, then impersonate the resulting token.

Conceptual flow used by the well-known tooling on authorized labs:

1. Trigger local authentication as SYSTEM to an attacker-controlled named pipe or TCP listener (historically via DCOM activation, print spooler RPC, or similar coerced callbacks).
2. Capture the SYSTEM token from the authenticated connection.
3. Call `ImpersonateLoggedOnUser` or duplicate the token, then spawn a process with the duplicated SYSTEM token.

On modern patched systems many coercion triggers are fixed, but the underlying primitive (impersonate any token you can get authenticated to you) remains, and newer tooling adapts the trigger. Always match the tool to the OS build: check `systeminfo` or `winver` output first, and prefer the newest maintained tooling for the target build.

## 3. Verifying prerequisites before running tooling

Impersonation tooling fails loudly and noisily when prerequisites are missing, so verify first.

```powershell
whoami /user
whoami /priv | findstr /i "Impersonate"
systeminfo | findstr /i "OS Version"
```

Checklist: the privilege is present and usable in this session, the account is a service-type account (impersonation from a plain user token behaves differently), and the OS build is within the tool's supported range per its documentation. If the session came from a web shell running as the IIS app pool identity, conditions are usually right; if it came from a domain user desktop session, they usually are not, and you should pivot to other vectors.

## 4. Token capture and reuse concepts

Beyond the automated tooling, understand the manual primitives: tokens can be enumerated, duplicated, and assigned with native APIs.

```powershell
Get-Process | Where-Object { $_.ProcessName -like "*sql*" }
```

Processes running as SYSTEM or a privileged service hold tokens you may be able to open with `SeDebugPrivilege`. The manual chain is: open the privileged process token, duplicate it, and create a process with the duplicated token. This is what `SeDebugPrivilege` plus token APIs gives you, and it is why debug privilege on an administrator-adjacent account is dangerous. In practice on authorized engagements, prefer the maintained impersonation tools over hand-rolled API code unless the lab specifically requires the manual path.

## 5. Related privilege chains

Several other privileges convert to SYSTEM through documented chains worth knowing for the authorized methodology.

- `SeBackupPrivilege`: read the SAM and SYSTEM hives from disk regardless of ACLs, extract hashes offline, then pass-the-hash or crack within scope.
- `SeLoadDriverPrivilege`: load a signed vulnerable driver and exploit it to kernel, which is effectively the kernel-triage path.
- `SeTcbPrivilege`: act as part of the trusted computing base, which includes creating SYSTEM tokens directly.
- Group memberships: Backup Operators (same as `SeBackupPrivilege`), DnsAdmins (DLL loading into the DNS service), Print Operators (driver loading).

Each chain has its own tooling and prerequisites; enumerate the privilege first, then research the chain for the exact OS build.

## Edge cases

- UAC-filtered administrator tokens show most privileges as disabled; impersonation attacks from a filtered token fail, so check whether the session is elevated with `whoami /groups` first.
- Hardened service accounts (for example IIS with application pool identities on recent Server builds) may no longer hold `SeImpersonatePrivilege`; verify rather than assume.
- Coercion triggers get patched: a tool that worked on build 17763 may fail on 20348, so the OS build check is mandatory, not optional.
- EDR and Defender behavioral monitoring flag classic impersonation tools by signature and behavior; on an engagement with stealth requirements, discuss tooling with the client contact first.
- Named pipe impersonation requires the pipe server to run in the right session and integrity level; session 0 versus interactive session mismatches cause silent failures.
- Tokens obtained this way live in your session; losing the session loses the token, so stabilize and migrate to a persistent privileged context promptly within scope.

## Escalation

- If `SeImpersonatePrivilege` is absent, audit the other token privileges: `SeBackupPrivilege` and `SeDebugPrivilege` each open independent SYSTEM paths.
- When impersonation tooling fails on the current build, check for the related group membership chains (DnsAdmins, Backup Operators) which use entirely different primitives.
- If token attacks are out of scope or blocked, pivot to the sibling sub-skills: service misconfigurations and scheduled tasks do not depend on token privileges.
- Harvested credentials remain the quietest alternative: a recovered local administrator password beats every token trick for reliability.

## Detection and defender view

Defenders detect token impersonation through Sysmon and EDR telemetry: unusual named pipe creation, DCOM activation anomalies, processes spawning with SYSTEM tokens from unexpected parents, and known tool signatures. Hardening includes removing `SeImpersonatePrivilege` from service accounts that do not need it, patching coercion vectors promptly, and monitoring for the behavioral patterns rather than just file hashes. From the authorized tester side, these tools are among the noisiest in the Windows privesc set: announce their use in the rules of engagement, record exact timestamps, and capture the telemetry your actions generated so the blue team can validate their detections.

## Key references

- MITRE ATT&CK T1134 (Access Token Manipulation), T1134.002 (Create Process with Token)
- Microsoft access token docs: https://learn.microsoft.com/en-us/windows/win32/secauthz/access-tokens
- Privilege constants: https://learn.microsoft.com/en-us/windows/win32/secauthz/privilege-constants
- HackTricks token section: https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation#tokens
- SeImpersonatePrivilege background: https://learn.microsoft.com/en-us/windows/win32/secauthz/privilege-constants (Impersonate a client after authentication)
- LOLBAS (for native-binary alternatives): https://lolbas-project.github.io
