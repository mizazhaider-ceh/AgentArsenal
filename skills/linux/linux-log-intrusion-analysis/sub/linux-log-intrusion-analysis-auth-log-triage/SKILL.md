---
name: linux-log-intrusion-analysis-auth-log-triage
description: Use when triaging Linux authentication logs during incident
  response or threat hunting on systems you are authorized to investigate.
  Covers parsing /var/log/auth.log and /var/log/secure, detecting brute
  force and password spraying, spotting valid-account abuse and impossible
  patterns, auditing sudo usage, tracking new accounts and SSH keys, and
  building per-source timelines. Defensive analysis mapped to MITRE ATT&CK
  T1110 Brute Force and T1078 Valid Accounts.
version: 1.0.0
domain: linux
lifecycle: stable
last_verified: 2026-10-23
requires: [linux-log-intrusion-analysis]
extends: []
parent: linux-log-intrusion-analysis
relates: [linux-log-intrusion-analysis, linux-log-intrusion-analysis-detecting-lateral-movement, linux-hardening-baseline]
tools:
  - name: systemd
    version: 255
  - name: auditd
    version: 3.1
  - name: Python
    version: 3.12
---

Authentication logs are the highest-signal source in most Linux investigations: they record every login attempt, every sudo invocation, and every account change. Triage means turning that firehose into answers fast: was there an attack, did it succeed, and which accounts are implicated. This sub-skill covers the defensive analyst's method for `/var/log/auth.log` (Debian/Ubuntu) and `/var/log/secure` (RHEL family): parsing, brute force detection, valid-account abuse hunting, sudo auditing, and account-change tracking. For systems you are authorized to investigate; defensive only. The parent skill sets the investigation strategy; this file is the auth-log field manual.

## Quick Workflow

1. Identify the log path for the distro and confirm the available time window (including rotated files).
2. Count and characterize failed authentication: volume, sources, targeted usernames, and timing pattern.
3. List every successful authentication in the window with user, source, method, and time; flag anomalies.
4. Audit sudo usage: who ran what as whom, especially first-time or unusual commands.
5. Check account and credential changes: new users, password changes, new SSH keys, group modifications.
6. Correlate: tie successful logins to subsequent sudo, new persistence, and outbound activity in the timeline.
7. Write up: attack pattern, successful sessions with evidence lines, affected accounts, and recommended containment.

## 1. Knowing your log paths and window

Debian-family logs SSH and sudo to `/var/log/auth.log`; RHEL-family uses `/var/log/secure`. Rotated files (`auth.log.1`, `auth.log.2.gz`) extend the window. Start by mapping what you have.

```bash
ls -lat /var/log/auth.log* /var/log/secure* 2>/dev/null
zcat /var/log/auth.log.2.gz 2>/dev/null | head -2
LOG=/var/log/auth.log; [ -f /var/log/secure ] && LOG=/var/log/secure; echo "Using $LOG"
```

Example output shape: rotation dates showing history depth (often 4 weeks via logrotate). If the suspected intrusion predates the oldest log, record that boundary immediately: it limits what the investigation can prove. Work from copies for the deep analysis, and note the timezone (log timestamps are local time; correlate carefully with UTC sources).

## 2. Detecting brute force and password spraying

Brute force is high-volume failures against few accounts; spraying is low-volume failures across many accounts (designed to dodge per-account lockouts). Detect both by aggregating.

```bash
LOG=/var/log/auth.log
grep -c "Failed password" $LOG
grep "Failed password" $LOG | grep -oE "for (invalid user )?[a-zA-Z0-9._-]+" | sort | uniq -c | sort -rn | head -15
grep "Failed password" $LOG | grep -oE "from [0-9.]+" | sort | uniq -c | sort -rn | head -15
```

Example output shape: top targeted usernames (often `root`, `admin`, `test`) and top source IPs with counts. A single source hammering one account is classic brute force; many sources each trying a few passwords across many accounts is a distributed spray or botnet. Check `btmp` too (`lastb | head`) for a second view of failures. Volume alone is reconnaissance; the critical question is always whether any attempt succeeded, which the next section answers.

## 3. Hunting valid-account abuse in successful logins

One successful anomalous login outweighs any volume of failures. List every success and hunt for what does not belong.

```bash
LOG=/var/log/auth.log
grep "Accepted" $LOG | awk '{print $1, $2, $3, $9, $11}' | sort | uniq -c | sort -rn | head -20
grep "Accepted" $LOG | grep -vE "from (10\.0\.0\.5|10\.0\.0\.6)" | head -20
```

Example output shape: timestamp, user, source IP for each accepted login, with counts. Flag: logins at unusual hours for the user, from unexpected source networks or geographies, via unexpected methods (password where keys are policy), rapid logins across many hosts (spray success), and any `Accepted` for accounts that should be dormant. For each flagged session, pull the full surrounding log context (±10 minutes) and trace what the session did via sudo logs and the journal.

## 4. Auditing sudo usage

Sudo logs show privilege use, and attackers who land as an unprivileged user reach for it immediately. Look for first-time sudoers, unusual commands, and sudo failures (which indicate probing).

```bash
LOG=/var/log/auth.log
grep -E "sudo.*COMMAND" $LOG | awk -F'COMMAND=' '{print $2}' | sort | uniq -c | sort -rn | head -20
grep -E "sudo.*user NOT in sudoers|authentication failure.*sudo" $LOG | head -10
grep -E "sudo:.*COMMAND=/bin/(bash|sh)" $LOG | head -10
```

Example output shape: command frequency (normal admin patterns versus shells, editors on sensitive files, or download tools like curl/wget via sudo). Red flags: `sudo -i` or `sudo su -` shells, sudo invocations by accounts that never had sudo before, commands run at odd hours, and `user NOT in sudoers` lines showing privilege probing. Correlate each suspicious sudo with the login session that preceded it.

## 5. Account, key, and group changes

Persistence often starts with a new account or a new SSH key. The auth logs record account administration; the filesystem confirms keys.

```bash
LOG=/var/log/auth.log
grep -iE "useradd|new user|password changed|groupadd|usermod" $LOG | head -15
grep -E "Accepted publickey" $LOG | awk '{print $9, $11}' | sort | uniq -c | sort -rn | head -10
find /home /root -name "authorized_keys" -newermt "2026-10-01" 2>/dev/null
```

Example output shape: account creation lines with the creating user, key-based logins by user and source, and recently modified authorized_keys files. Any account created outside change control, any new key in root's or a service account's authorized_keys, and any user added to sudo/admin groups is treated as potential persistence until proven legitimate. Verify against your account inventory; unknown accounts get disabled first and investigated second.

## Edge cases

- Log timestamps are in local time and rotation boundaries can split an attack across files; always search the rotated logs too, and convert timezones explicitly when correlating with UTC-based sources like cloud trails.
- Successful logins via SSH keys show `Accepted publickey`, which is normal for admin workflows; the anomaly is in the who/when/where, not the method, so baseline normal key-login patterns before hunting.
- `sudo` can be configured to log via syslog with different formats or to not log at all (`!syslog`); verify sudo logging is actually enabled and centralized, because a silent sudo is a blind spot, not a clean bill of health.
- High-volume brute force from many sources is often background internet noise on public-facing hosts; distinguish it from targeted attacks by looking for success, targeted usernames matching your actual accounts, and timing correlated with other indicators.
- Service accounts and automation produce regular, odd-hour logins that look anomalous to a human reviewer; maintain a list of expected automation sources so triage does not chase cron jobs.
- An attacker with root can edit logs to remove their tracks; cross-check auth logs against `wtmp` (`last`), `btmp` (`lastb`), the journal, and the central collector, and treat inconsistencies as tampering evidence.
- Password spraying deliberately stays under lockout thresholds, so per-account failure counts look benign; detect it by aggregating failures per source IP across all usernames instead.

## Escalation

- If any successful login is confirmed malicious, escalate immediately: disable the account, rotate its credentials and keys, revoke its sessions, and widen the hunt to every host it touched.
- If sudo logs show privilege escalation by an unknown actor, treat the host as compromised and move to full incident response (isolation, forensic imaging) rather than continuing log-only analysis.
- If account or key changes indicate persistence, do not just delete the artifact: investigate how it was created first, because the creation vector (stolen credential, exploited service) is still open.
- If the log window does not cover the suspected initial access, escalate the evidence gap to stakeholders with a clear statement of what can and cannot be determined.

## Detection and defender view

Auth log triage is both incident response and continuous detection. Defenders run the same aggregations as scheduled hunts: failure-rate anomalies per source, new successful-login patterns, first-time sudo commands, and account-change alerts. MITRE T1110 (Brute Force) is detected by failure aggregation and mitigated by key-only SSH plus fail2ban; T1078 (Valid Accounts) is detected by anomaly hunting on successes and mitigated by account lifecycle controls. Centralized auth logs with alerting on the patterns in sections 2-5 turn triage from a manual fire drill into a monitored control. The defender's rule: failures are noise until correlated, successes are signal, and any success you cannot explain is an incident.

## Key references

- MITRE ATT&CK T1110 Brute Force: https://attack.mitre.org/techniques/T1110/
- MITRE ATT&CK T1078 Valid Accounts: https://attack.mitre.org/techniques/T1078/
- MITRE ATT&CK T1098 Account Manipulation: https://attack.mitre.org/techniques/T1098/
- Debian auth logging (rsyslog/auth.log): https://www.debian.org/doc/manuals/securing-debian-manual/
- sudo logging manual: https://www.sudo.ws/docs/man/sudoers.man/#logging
- NIST SP 800-92 Guide to Computer Security Log Management: https://csrc.nist.gov/publications/detail/sp/800-92/final
