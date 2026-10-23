---
name: token-impersonation
description: Use when you have a Windows shell on an authorized engagement
  and need to steal or impersonate access tokens for privilege escalation.
  Covers token enumeration, SeImpersonatePrivilege abuse, RoguePotato and
  GodPotato style techniques, and PrintSpoofer concepts. Use when your user
  holds impersonation privileges, when a service account token is
  available, or when moving from service account to SYSTEM.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
parent: privesc-windows
requires: [privesc-windows]
extends: []
relates: [ad-enumeration]
tools:
  - name: PowerShell
    version: 7.4
  - name: Mimikatz
    version: 2.2.0
  - name: Python
    version: 3.12
---

Windows access tokens decide what a thread can do, and several privilege
escalation techniques trick a privileged service into handing you its
token. This skill covers token impersonation on authorized engagements:
checking your privileges, enumerating available tokens, and running the
potato-family techniques that turn SeImpersonatePrivilege into SYSTEM.
These are well-trodden paths; the skill is in picking the right variant
for the target's patch level.

## Quick Workflow

1. Check your privileges: `whoami /priv` and look for SeImpersonate or
   SeAssignPrimaryToken.
2. Enumerate tokens available to your session.
3. Pick the technique matching the OS build and patch level.
4. Run the impersonation and confirm the elevated token.
5. Use the token for the engagement's objectives.
6. Record the technique, the build, and the exact commands.

## 1. Privilege and token enumeration

```powershell
# Your privileges decide everything
whoami /priv | findstr /i "Impersonate AssignPrimary"

# Tokens in your session (with appropriate tooling)
# List processes running as SYSTEM you might reach
tasklist /v | findstr /i "system" | head -10

# Named pipes: potato techniques need one to catch the auth
# Check what is listening locally
netstat -ano | findstr "LISTENING" | findstr "127.0.0.1"
```

SeImpersonatePrivilege on a service account is the classic trigger: web
app pools, service accounts, and some default configurations hold it.
Without it, the potato family does not apply; check the other
privesc-windows sub-skills instead.

## 2. Technique selection by build

```powershell
# Identify the build to pick the working variant
systeminfo | findstr /i "OS Version"

# Guidance (verify against current research for the exact build):
# Older builds: JuicyPotato (DCOM activation, largely patched)
# 2019 / 10 1809+: RoguePotato (fake OXID resolver, needs port 135)
# 2022 / 11 22H2+: GodPotato (named pipe + DCOM, current favorite)
# PrintSpoofer: abuses the print spooler service (needs spooler running)

# GodPotato pattern (example; use the current release for the target):
# GodPotato.exe -cmd "cmd /c whoami > C:\proof.txt"
```

Always use the latest maintained variant for the target build, and test
it in a lab VM matching the build first. Potato tools fail silently on
wrong builds, and each failure teaches you nothing without the lab
baseline.

## 3. Confirming and using the token

```powershell
# Proof: the command ran as SYSTEM
type C:\proof.txt
# expected: nt authority\system

# Interactive use: spawn the shell or run the objective command
# with the impersonated token, then drop back to the original context

# Cleanup: remove proof files and stop any listeners the tool started
del C:\proof.txt
```

One clean proof run is enough. Repeated potato executions on a production
host risk DCOM instability; get the evidence and stop.

## Edge cases

- SeImpersonatePrivilege is absent. The potato family is off the table;
  pivot to unquoted-service-paths, dll-hijacking, or kernel paths.
- The print spooler is disabled. PrintSpoofer needs it; check
  `sc.exe query spooler` before assuming the path.
- DCOM is hardened or the firewall blocks the needed ports. RoguePotato
  needs its listener reachable; test locally first.
- The tool is flagged by AV/EDR. Use the in-scope approved tooling only,
  and coordinate with the test lead; disabled AV on a production host
  needs explicit approval.

## Escalation

- The working variant is unknown for the build: lab-test the candidates
  in order (GodPotato, RoguePotato, PrintSpoofer) against a matching VM.
- Token impersonation succeeds but objectives need domain access: hand
  the SYSTEM shell to ad-enumeration for the domain phase.
- Nothing works: the host may be properly hardened against token abuse;
  document the negative result with the privilege list as evidence.

## Detection and defender view

Defenders see potato techniques as odd DCOM activations, named pipe
servers appearing briefly, and service accounts spawning SYSTEM shells,
all of which EDR and Sysmon log well. The durable fixes are removing
SeImpersonatePrivilege from service accounts that do not need it,
disabling the print spooler where unused, patching on schedule, and
alerting on DCOM anomalies. Token theft is a symptom of over-privileged
service accounts.

## Key references

- MITRE ATT&CK T1134.001 (Access Token Manipulation: Token
  Impersonation/Theft).
- MITRE ATT&CK T1134.002 (Access Token Manipulation: Create Process with
  Token).
- CWE-250 (Execution with Unnecessary Privileges).
- Current potato technique research (match to the target build).
