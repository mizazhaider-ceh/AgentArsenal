---
name: ransomware-response
description: Use when preparing for or responding to a ransomware incident
  as a defender. Covers pre-incident readiness (backups, segmentation,
  EDR), identifying the ransomware family, containment of encryption and
  lateral spread, evidence preservation, eradication, recovery from
  backups, decryptor checks, ransom decision factors, and post-incident
  hardening. Use when ransomware is suspected or confirmed, or when
  building the organization's ransomware playbook before it is needed.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, incident-playbooks]
tools:
  - name: Velociraptor
    version: 0.7
  - name: Sysmon
    version: 15.x
  - name: Python
    version: 3.12
---

Ransomware combines encryption for impact with double extortion (data
theft plus the threat to leak). Response speed and preparation decide
the outcome more than any tool bought during the crisis. This skill
covers the defensive playbook: readiness before it happens, the
response sequence when it does, recovery, and the ransom decision.
For your own organization or an authorized client, with legal involved
from the first hour.

## Quick Workflow

1. Declare SEV-1, name the incident commander, start the timeline,
   engage legal and the IR retainer.
2. Identify the ransomware family from the note, extensions, and
   known IOCs; check for a free decryptor before anything else.
3. Contain: isolate affected hosts, kill remote access paths, stop
   lateral movement, protect the backups.
4. Preserve evidence: memory, disk images of patient zero, logs,
   the ransom note, and attacker communications.
5. Scope: how many hosts, which data was accessed or exfiltrated,
   is encryption still spreading.
6. Eradicate: remove persistence and access, close the initial
   vector, reset credentials enterprise-wide if needed.
7. Recover: rebuild from known-clean backups or gold images,
   verify integrity, restore in priority order.
8. Post-incident: blameless review, close the gaps the attackers
   used, monitor for re-entry for 90 days.

## 1. Readiness (do this now)

The response starts before the incident:

- Backups: 3-2-1 rule (3 copies, 2 media types, 1 offline or
  immutable). Test restores quarterly; an untested backup is a hope.
- Protect the backup infrastructure: separate credentials, MFA,
  immutable storage, and network segmentation from production.
- Segment the network: ransomware spreads over SMB and RDP. Limit
  lateral paths now, not during the fire.
- EDR in block mode with tamper protection on every host, plus
  behavioral rules for mass file modification.
- Keep an offline copy of this playbook, contact lists, and network
  diagrams. Ransomware takes the wiki down too.
- Know your cyber insurance and IR retainer numbers; call them in
  the first hour, not the third day.

```bash
# Readiness check: verify backup immutability and last successful restore test
# (adapt to your backup platform; the point is a scheduled, evidenced test)
echo "last restore test: $(cat /var/log/backup-restore-test.log | tail -1)"
```

## 2. Identification

Confirm what you are dealing with fast:

```bash
# Collect the ransom note and file markers from one host (do not pay yet)
ls ~/Desktop/*ransom* ~/Documents/*README* 2>/dev/null
cat ~/Desktop/*ransom*.txt 2>/dev/null | head -30

# Note the encrypted file extension and any new wallpaper text
ls ~ | grep -iE "locked|encrypted|crypt" | head

# Hash the note and the encryptor binary if present, check reputation
sha256sum /tmp/suspicious-binary 2>/dev/null
```

- Identify the family: ransom note text, file extension, and IOCs
  matched against threat intel (many families have known notes).
- Check No More Ransom (nomoreransom.org) and vendor decryptor pages
  for a free decryptor for the exact variant. Some older or flawed
  families are decryptable.
- Determine the initial access: phishing, exposed RDP, VPN without
  MFA, unpatched edge device. This decides the eradication work.

Do not delete the ransom note or reformat patient zero. They are
evidence and may hold the decryption path.

## 3. Containment

Speed matters; encryption spreads in minutes over flat networks.

```text
[ ] Isolate affected hosts in EDR (network quarantine, power stays on)
[ ] Disable VPN and remote access if the entry was remote; force MFA reset
[ ] Block C2 domains and IPs at firewall, proxy, and DNS
[ ] Disable the compromised accounts and service accounts used for spread
[ ] PROTECT THE BACKUPS: verify backup servers are isolated and immutable
     copies are intact before the attacker finds them
[ ] If spreading fast and isolation is unavailable: power off affected
     hosts (accept the memory evidence loss to stop the bleeding)
```

Verify containment: pick three affected hosts and confirm they
cannot reach the C2 infrastructure or write to network shares.
Containment you did not verify is a guess.

Common ransomware behaviors to hunt while containing (T1486, T1490):

```bash
# Volume shadow copies deleted (vssadmin, wmic) across the fleet
index=wineventlog EventCode=1 earliest=-7d@d latest=@d
| eval cmd=lower(CommandLine)
| where match(cmd,"vssadmin.*delete.*shadows") OR match(cmd,"wmic.*shadowcopy.*delete")
| stats values(ComputerName) as hosts count

# Mass file renames with new extensions in user folders (Sysmon ID 11 volume)
index=wineventlog EventCode=11 earliest=-24h latest=@h TargetFilename="*.locked"
| stats dc(ComputerName) as hosts count | where hosts > 0
```

## 4. Evidence preservation

Collect before eradication changes the scene:

- Memory capture of patient zero and any host with the encryptor
  still resident.
- Disk image or at least the encryptor binary, ransom note, and
  persistence artifacts (scheduled tasks, services, registry run
  keys, startup folders).
- Central logs: EDR timeline, firewall, proxy, VPN, and identity
  logs for the intrusion window (go back 60 to 90 days; ransomware
  crews dwell for weeks).
- The attacker's communications: ransom note, leak site post if
  any, negotiation chat logs if you engage.

```bash
# Timeline the intrusion window from EDR/Sysmon for patient zero
index=wineventlog ComputerName="PATIENT-ZERO" earliest=-90d@d latest=@d
| eval proc=lower(mvindex(split(Image,"\\"),-1))
| where proc IN ("powershell.exe","cmd.exe","rundll32.exe","wmic.exe")
| table _time, proc, CommandLine | sort _time | head -100
```

Chain of custody: hash everything, log who collected what and when,
store on write-once or access-controlled media.

## 5. Scoping the blast radius

Answer five questions before recovery:

1. How many hosts encrypted, and how many touched but not encrypted.
2. Was data exfiltrated (proxy/DNS/EDR upload volumes, staging
   directories, archive tools like WinRAR or rclone in the timeline).
3. Which accounts and credentials are burned (domain admin
   compromise means enterprise-wide reset).
4. Is the attacker still present (active C2 in the last 24h).
5. Are backups intact and clean (scan backup sets for the
   encryptor before trusting them).

```bash
# Look for staging and exfiltration tooling in the intrusion window
index=wineventlog EventCode=1 earliest=-60d@d latest=@d
| eval p=lower(Image), c=lower(CommandLine)
| where match(p,"rclone|winrar|7z|megacmd") OR match(c,"rclone|mega\\.nz")
| stats values(ComputerName) as hosts values(c) as cmds by p
```

Assume exfiltration until the evidence says otherwise. Double
extortion is the norm; the leak-site post is the confirmation.

## 6. Eradication

Remove every foothold, not just the encryptor:

- Delete persistence: scheduled tasks, services, WMI consumers,
  registry run keys, startup folder items created in the intrusion
  window.
- Remove rogue accounts and reset credentials: if domain admin was
  compromised, reset KRBTGT twice and every privileged account.
- Close the initial vector: patch the exploited edge device,
  enforce MFA on VPN, disable exposed RDP.
- Reimage affected hosts from known-good media. Do not "clean"
  ransomware hosts.

```bash
# Hunt persistence created during the intrusion window (example: tasks)
index=wineventlog EventCode=4698 earliest=-90d@d latest=@d
| table _time, ComputerName, TaskName, SubjectUserName | sort _time
```

## 7. Recovery

Recover in priority order, verifying each step:

1. Restore the identity infrastructure first (domain controllers
   from clean backups), then network and security tooling.
2. Rebuild servers from gold images or clean backups; verify hashes
   of restored system files against known-good.
3. Scan restored data for encryptor remnants and for the
   exfiltrated data's sensitivity (drives notification decisions).
4. Bring systems online in isolated VLANs first, watch EDR for 48h,
   then reconnect.
5. Enhanced monitoring for 90 days: the same crew often returns
   through the same hole.

Test the restore before you need it at scale: restore one critical
system to an isolated network and validate the application works.
Recovery time estimates come from these tests, not from vendor
claims.

## 8. The ransom decision

Factors, not advice; the decision belongs to leadership with legal
counsel:

- Do you have clean, tested backups that meet the recovery
  objective. If yes, paying buys little.
- Was data exfiltrated. Paying does not guarantee deletion; leaked
  data has been published after payment.
- Sanctions: paying certain groups is illegal in some
  jurisdictions. Legal must clear the recipient.
- Decryptor quality: attacker tools are often buggy and slow;
  factor in the recovery risk.
- Cost of downtime vs cost of rebuild from backups.

If negotiation happens, use the IR firm's experienced negotiators,
never the victim's staff. Document everything; some jurisdictions
require reporting of payments.

## Edge cases

- The decryptor exists but is for a different variant. Verify the
  exact version; wrong decryptors corrupt files further. Test on
  copies, never on originals.
- Backups are encrypted too. Fall back to immutable or offline
  copies; if none exist, recovery becomes rebuild-from-scratch plus
  data re-creation.
- The attacker threatens to leak data on a countdown. Do not let
  the timer rush containment; work the playbook, let legal handle
  the clock.
- Encryption is still spreading during recovery. Stop, re-verify
  containment and eradication before bringing more systems online.
- OT or medical devices are affected. Safety and care continuity
  outrank forensics; involve the right specialists immediately.
- Insurance requires their approved IR firm. Call the insurer
  before engaging anyone else, or coverage may be at risk.

## Escalation

- Scope exceeds internal capacity: the IR retainer takes the lead;
  your team supports with access and knowledge.
- Data theft involves regulated personal data: legal owns the
  notification timeline (GDPR 72 hours from awareness).
- The attacker contacts executives directly: route all contact
  through the negotiator and legal; nobody freelances.
- Law enforcement: report through the proper channels (they will
  not decrypt your files, but reporting helps everyone and may be
  required).
- Re-infection after recovery: the initial vector is still open.
  Stop recovery, re-scope, and assume the attacker kept access
  somewhere you have not looked.

## Detection and defender view

Ransomware defense is an arms race the defender can win with
preparation:

- Attackers dwell for weeks, then encrypt in minutes. The detection
  window is the dwell period: hunt for their pre-encryption tooling
  (AD recon, credential dumping, backup discovery).
- Attackers kill backups first (T1490: shadow copies, backup
  agents). Alert on backup tampering as SEV-1; it is the clearest
  pre-ransomware signal.
- Attackers exfiltrate before encrypting. Egress anomaly detection
  and staging-directory hunts catch the quiet phase.
- Attackers re-enter through unpatched edge devices. Post-incident
  hardening must close the exact initial vector, verified by a
  retest.
- Your recovery capability is the deterrent. Tested, immutable
  backups turn ransomware from existential to expensive.

## Key references

- MITRE ATT&CK T1486 (Data Encrypted for Impact), T1490 (Inhibit
  System Recovery), T1070.001 (Clear Windows Event Logs), T1021
  (Remote Services), T1048 (Exfiltration Over Alternative Protocol).
- No More Ransom decryptor portal: https://www.nomoreransom.org/
- CISA ransomware guidance:
  https://www.cisa.gov/stopransomware/ransomware-guide
- NIST SP 800-61 Rev. 2 (incident handling) and SP 800-184 (recovery).
