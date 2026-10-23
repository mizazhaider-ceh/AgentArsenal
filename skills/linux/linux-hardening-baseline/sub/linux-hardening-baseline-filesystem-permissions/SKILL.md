---
name: linux-hardening-baseline-filesystem-permissions
description: Use when auditing or hardening Linux filesystem permissions as
  part of a defensive baseline. Covers correct ownership and modes for
  /etc/passwd, /etc/shadow, /etc/ssh and cron paths, finding unexpected SUID
  and SGID binaries, hunting world-writable files, sticky bit verification
  on /tmp, umask policy, and ACL auditing. Defensive hardening mapped to
  MITRE ATT&CK mitigations for T1222 File and Directory Permissions
  Modification and T1548 Abuse Elevation Control Mechanism.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-hardening-baseline]
extends: []
parent: linux-hardening-baseline
relates: [linux-hardening-baseline, linux-hardening, linux-log-intrusion-analysis]
tools:
  - name: GNU coreutils
    version: 9.4
  - name: AIDE
    version: 0.18
  - name: Python
    version: 3.12
---

Permissions are the operating system's first access control list, and misconfigurations here turn minor footholds into full compromise: a writable cron script becomes root execution, a world-readable shadow backup leaks password hashes, a new SUID binary is a backdoor. This sub-skill covers the defensive filesystem permission baseline: the correct modes for sensitive paths, how to find deviations with `find`, SUID/SGID auditing, umask policy, and ongoing monitoring. Purely defensive, for systems you own or administer. The parent skill places permissions in the wider baseline; this file is the command-level reference.

## Quick Workflow

1. Snapshot the current state: key file modes, SUID/SGID lists, and world-writable files, saved as the audit baseline.
2. Fix sensitive file modes: `/etc/shadow` 640 root:shadow, `/etc/passwd` 644, `/etc/ssh/*` restricted, cron directories 755 root-owned.
3. Audit SUID/SGID binaries against the distro default list; remove the bit or justify every extra.
4. Hunt world-writable files and directories outside `/tmp` and `/var/tmp`; fix ownership or modes.
5. Verify sticky bits on world-writable directories (`/tmp`, `/var/tmp`, `/dev/shm`).
6. Set and enforce umask policy (027 for most servers) in login profiles and service units.
7. Schedule the audit: recurring finds plus AIDE integrity monitoring on permission-sensitive paths.

## 1. Sensitive file and directory modes

A small set of paths carries most of the risk. Check them first, fix them explicitly, and know the correct values by heart.

```bash
stat -c "%a %U %G %n" /etc/passwd /etc/shadow /etc/group /etc/gshadow
stat -c "%a %U %G %n" /etc/ssh/ssh_host_*_key /etc/ssh/sshd_config
stat -c "%a %U %G %n" /etc/crontab /etc/cron.d /etc/cron.daily 2>/dev/null
```

Expected values: `/etc/passwd` 644 root:root, `/etc/shadow` 640 root:shadow (Debian) or 600 root:root (RHEL), `/etc/gshadow` 640 root:shadow, SSH private host keys 600 root:root, `sshd_config` 600 root:root, `/etc/crontab` and `/etc/cron.d` 644/755 root-owned with nothing group- or world-writable. Fix with `chmod` and `chown` explicitly per file; never `chmod -R` a system directory, which breaks more than it fixes.

## 2. SUID and SGID auditing

Every SUID binary is a potential privilege boundary, so the list must be short, known, and monitored. Compare against your distro's default set.

```bash
find / -xdev -type f -perm -4000 -exec stat -c "%a %U %n" {} \; 2>/dev/null | sort -k3
find / -xdev -type f -perm -2000 -exec stat -c "%a %G %n" {} \; 2>/dev/null | sort -k3
```

Example output shape: the standard set (`/usr/bin/passwd`, `/usr/bin/sudo`, `/usr/bin/su`, `/usr/bin/mount` on some distros, `/usr/bin/pkexec`) and nothing else. For each entry you cannot explain, investigate: check package ownership with `dpkg -S` or `rpm -qf`, and remove the bit with `chmod u-s` if it is not needed (common candidates: `mount`/`umount` on servers, games, legacy tools). Re-run after every package upgrade, because upgrades can reinstall SUID bits.

## 3. World-writable files and directories

World-writable files outside temporary directories are almost always wrong, and world-writable directories without the sticky bit let users delete each other's files.

```bash
find / -xdev -type f -perm -0002 ! -path "/proc/*" ! -path "/sys/*" ! -path "/dev/*" 2>/dev/null | head -20
find / -xdev -type d -perm -0002 ! -path "/proc/*" ! -path "/sys/*" 2>/dev/null | head -20
stat -c "%a %n" /tmp /var/tmp /dev/shm
```

Expected: no world-writable files outside application temp areas you know about, and `/tmp`, `/var/tmp`, `/dev/shm` at mode 1777 (sticky bit set, shown as the leading 1). Fix files with `chmod o-w` or tighter, and set the sticky bit with `chmod +t`. Investigate before fixing: a world-writable file might be load-bearing for a legacy app, in which case fix the app's umask or move its temp files rather than breaking it silently.

## 4. Umask policy

Umask decides the default modes of newly created files, which is where permission debt accumulates. A baseline umask of 027 gives owner full, group read, other nothing.

```bash
grep -r "umask" /etc/profile /etc/bash.bashrc /etc/login.defs 2>/dev/null
umask
```

Set `umask 027` in `/etc/profile` and `/etc/bash.bashrc` (or `/etc/profile.d/`), and `UMASK 027` in `/etc/login.defs`. For systemd services, add `UMask=0027` in the unit file (see the systemd security skills). Verify by creating a test file as a normal user and checking it is 640, not 644. Note: 027 can break multi-user shared directories and some applications; use 022 only where a documented need exists, and prefer ACLs for intentional sharing.

## 5. ACL and extended attribute auditing

Standard modes are not the whole story: POSIX ACLs and extended attributes can grant access the `ls -l` output hides.

```bash
getfacl -p /etc/shadow 2>/dev/null
find /etc /opt /srv -xdev -exec getfacl -p {} \; 2>/dev/null | grep -B5 "^user:[^:]*:rwx" | head -30
lsattr /etc/passwd /etc/shadow 2>/dev/null
```

Example output shape: no unexpected ACL entries beyond the base user/group/other, and no surprising immutable flags. Unexpected ACLs granting named users write access to system files are a finding. Consider `chattr +i` on truly static critical files (with change management for updates), but weigh it against the operational friction: immutable files break package upgrades that touch them.

## 6. Continuous monitoring with AIDE

One-time fixes decay. AIDE (or Tripwire, or osquery) watches permission-sensitive paths and alerts on changes.

```bash
aide --init 2>&1 | tail -3
cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db
aide --check 2>&1 | head -20
```

Initialize the database on a known-good system, protect the database itself (store a copy offline), and run `--check` on a schedule with alerts on any output. Include at minimum: `/etc/passwd`, `/etc/shadow`, `/etc/group`, `/etc/ssh/`, cron paths, `/usr/bin`, `/usr/sbin`, and your baseline config files. Any SUID change or mode change on these paths is investigated as a potential compromise first.

## Edge cases

- Container images and minimal installs have different default SUID sets than full server installs; build the expected list per image or role, not one global list, or you will drown in false positives.
- `/usr/bin/sudo` must keep its SUID bit or sudo breaks entirely; never strip SUID from sudo, su, or passwd without understanding that you are disabling the tool, not hardening it.
- NFS mounts and some network filesystems do not honor local permission semantics the way local disks do (root squashing, all-squash); audit the export options on the server side too, because client-side modes can lie.
- Package upgrades and `dpkg --force` style repairs can reset modes you fixed by hand; this is why the baseline lives in automation (Ansible file module with explicit modes) rather than in shell history.
- Some applications legitimately need group-writable directories (shared deploy dirs, socket dirs); handle these with the setgid bit plus a dedicated group and documented ACLs, not with world-writable modes.
- `find -perm -4000` on huge filesystems is slow; scope with `-xdev`, exclude known-good trees, and run during off-peak or against a file inventory database instead of live-walking every time.
- SELinux and AppArmor add a layer above discretionary permissions; a correct mode with a wrong SELinux context still denies (or wrongly allows) access, so check contexts (`ls -Z`) on SELinux systems as part of the same audit.

## Escalation

- If the audit finds an unknown SUID binary or unexpected root-owned writable script in a cron path, treat it as a potential backdoor first: preserve evidence, check logs for how it got there, and involve incident response before deleting it.
- If fixing permissions breaks a production application, roll back the specific change, document the app's requirement, and implement the narrowest compensating control (dedicated group, ACL) rather than leaving the finding open.
- If a path must stay world-writable for business reasons, escalate to formal risk acceptance with owner, review date, and monitoring (AIDE watch plus alerting) as compensating controls.
- If different teams manage different trees (`/opt` owned by app teams), assign permission ownership per tree so audit findings route to someone who can actually fix them.

## Detection and defender view

Permission hardening feeds detection directly: AIDE alerts on mode, ownership, or SUID changes to watched paths, and auditd rules (`-w /usr/bin/sudo -p x`, watches on cron directories) log executions and modifications. MITRE ATT&CK T1222 (File and Directory Permissions Modification) is both the technique attackers use and the signal defenders watch: unexpected permission changes on system binaries are a high-fidelity compromise indicator. T1548 (Abuse Elevation Control Mechanism) covers SUID abuse, which is why the SUID inventory is monitored, not just cleaned once. Centralize AIDE and auditd output; local integrity databases can be tampered with by an attacker who gains root.

## Key references

- MITRE ATT&CK T1222 File and Directory Permissions Modification: https://attack.mitre.org/techniques/T1222/
- MITRE ATT&CK T1548 Abuse Elevation Control Mechanism: https://attack.mitre.org/techniques/T1548/
- CIS distribution benchmarks (filesystem sections): https://www.cisecurity.org/cis-benchmarks/
- AIDE manual: https://aide.github.io/
- Linux file permissions and ACLs: https://man7.org/linux/man-pages/man1/chmod.1.html and https://man7.org/linux/man-pages/man5/acl.5.html
- Debian securing manual (file permissions): https://www.debian.org/doc/manuals/securing-debian-manual/
