---
name: debugging-methodology
description: "Use when diagnosing a bug or failure systematically: building a reproduction case, bisecting with git bisect, reading logs and stack traces, tracing syscalls with strace, debugging with gdb 15 or pdb, analyzing core dumps, forming and testing hypotheses one variable at a time, or writing a postmortem after an incident. Use when the task mentions debugging, root cause analysis, crash investigation, hangs, segfaults, or \"works on my machine\" failures."
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [python-cli-tooling]
tools:
  - name: GDB
    version: 15
  - name: strace
    version: 6.12
  - name: Python
    version: 3.12
---
Debugging is the disciplined reduction of uncertainty: reproduce, observe,
hypothesize, test, repeat. Random changes and restarts sometimes work, but
they do not produce understanding, and the bug returns. This skill covers a
repeatable methodology plus the concrete tools for each layer: logs, git
bisect, strace, gdb, core dumps, and pdb for Python.

## Quick Workflow

1. Reproduce reliably: find the minimal steps that trigger the bug every
   time; no repro, no fix.
2. Read the error completely: full stack trace, exit code, and the exact
   log lines around it.
3. Check what changed: recent deploys, config edits, dependency updates
   (`git log`, deploy history).
4. Form ONE hypothesis, predict what you will observe if it is true, then
   run the smallest experiment that tests it.
5. Change one variable at a time; record each result.
6. Bisect when the cause is a code change: `git bisect` finds it in
   log2(n) steps.
7. Go one layer down when stuck: strace for syscalls, gdb for crashes,
   packet capture for network.
8. Fix the root cause, add a regression test, and write down what you
   learned.

## 1. Reproduce first

```bash
# Capture the exact failing command and its full output
./failing-thing --input data.json > /tmp/repro.out 2> /tmp/repro.err; echo "exit=$?"

# Minimal input: shrink the trigger until removing anything more makes
# the bug disappear (delta debugging by hand)
wc -c data.json
head -c 1000 data.json > small.json && ./failing-thing --input small.json; echo "exit=$?"

# Freeze the environment: same user, same cwd, same env vars
env -i PATH=/usr/bin:/bin HOME=/root ./failing-thing --input small.json; echo "exit=$?"
```

A repro script is an asset: check it into the repo as the regression
test seed. If you cannot reproduce it, you cannot verify the fix; say so
explicitly instead of shipping a guess.

## 2. Read the failure properly

```bash
# Python: full traceback, not just the last line
python3 app.py 2>&1 | tail -40

# Exit code meaning (128+n = killed by signal n; 137 = SIGKILL, 139 = SIGSEGV)
./crasher; echo "exit=$?"

# Was it the OOM killer?
dmesg -T | grep -i 'killed process' | tail -3
journalctl -k --since "10 minutes ago" | grep -i 'out of memory'

# Service context: what systemd saw
systemctl status myapp --no-pager -l
journalctl -u myapp -n 50 --no-pager
```

## 3. What changed: bisect and history

```bash
# When did it break? Bisect between a good and bad commit
git bisect start
git bisect bad HEAD
git bisect good v1.4.0
# At each stop: run the repro, then mark it
./repro.sh && git bisect good || git bisect bad
# ... repeat until git names the culprit commit
git bisect reset

# Automated bisect when the repro is scriptable (exit 0 = good)
git bisect start HEAD v1.4.0
git bisect run ./repro.sh
git bisect reset

# Recent changes to the suspect area
git log --oneline -15 -- src/billing/
git log -S "MAX_RETRIES" --oneline -- src/
```

Also check non-code changes: config diffs, environment variables,
dependency versions (`pip freeze | grep -E 'requests|django'`), OS
upgrades, and deploy timestamps.

## 4. strace: what the program actually asked the kernel

```bash
# Trace syscalls of a short-lived command, follow forks
strace -f -o /tmp/trace.log ./failing-thing --input small.json

# Summarize: which syscalls burn time (great for hangs)
strace -f -c -o /tmp/summary.log timeout 10 ./hanging-thing

# Attach to a running stuck process
strace -p 1234 -o /tmp/stuck.log
# then read the tail: is it looping on read()? blocked in futex()? 
tail -20 /tmp/stuck.log
```

Common reads: `ENOENT` on a config path (wrong path or permissions),
`EACCES` on files, `ECONNREFUSED` on sockets, endless `poll`/`futex`
( deadlock or spin), `open` of the same file thousands of times (leak).

Filter the noise:

```bash
# Only file and network syscalls
strace -f -e trace=open,openat,connect,read,write -o /tmp/io.log ./app
```

## 5. gdb for crashes and hangs

```bash
# Compile with debug symbols for useful traces (-g, no -s stripping)
gcc -g -O0 -o crasher crasher.c

# Run under gdb and get a backtrace at the crash
gdb -batch -ex run -ex bt --args ./crasher --input small.json

# Attach to a hung process and see where every thread is stuck
gdb -p 1234 -batch -ex "thread apply all bt" | head -60
```

Core dumps for post-crash analysis:

```bash
# Enable core dumps (size unlimited) for the session
ulimit -c unlimited
echo '/tmp/core.%e.%p' | sudo tee /proc/sys/kernel/core_pattern
./crasher   # produces /tmp/core.crasher.<pid>

# Analyze the core offline
gdb -batch -ex bt ./crasher /tmp/core.crasher.1234

# Inspect variables at the crash frame
gdb -batch -ex bt -ex "frame 3" -ex "info locals" ./crasher /tmp/core.crasher.1234
```

## 6. Python: pdb and faulthandler

```bash
# Drop into the debugger at the exception
python3 -m pdb app.py
# (pdb) c          continue
# (pdb) bt         backtrace
# (pdb) p varname  print variable
# (pdb) up/down    move frames

# Post-mortem on an uncaught exception
python3 - <<'EOF'
import pdb, traceback, app
try:
    app.main()
except Exception:
    traceback.print_exc()
    pdb.post_mortem()
EOF

# Hangs: dump all thread stacks after a timeout (stdlib)
PYTHONFAULTHANDLER=1 timeout 30 python3 hanging_app.py
# faulthandler prints every thread's stack on timeout kill
```

For production hangs without restart rights, `py-spy` (third party)
dumps stacks of a running process; with stdlib only, faulthandler plus
a USR1-triggered dump is the portable pattern.

## 7. Hypothesis discipline

Write hypotheses down; memory lies about what you already tried.

```text
H1: the bug is in the retry logic (config changed Tuesday).
    Predict: setting MAX_RETRIES=0 makes the failure disappear.
    Test: MAX_RETRIES=0 ./repro.sh
    Result: still fails -> H1 dead.

H2: the input file has a BOM breaking the parser.
    Predict: hexdump shows EF BB BF at the start.
    Test: head -c 3 data.json | xxd
    Result: confirmed -> fix the parser to strip BOM.
```

Rules: one variable per experiment, predict the outcome before running,
kill disproven hypotheses fast, and prefer the hypothesis that explains
ALL the symptoms. When two hypotheses remain, design the experiment that
distinguishes them.

## 8. Network-layer debugging

```bash
# Is the port even listening, and on which interface
ss -tlnp | grep 8080

# TCP handshake or refusal, with timing
time (echo > /dev/tcp/127.0.0.1/8080) && echo open || echo closed

# Full request/response with headers and timing
curl -sv --max-time 10 http://127.0.0.1:8080/health 2>&1 | head -30

# DNS or TLS? Isolate: IP first, then hostname
curl -sk https://127.0.0.1:8443/health
curl -s https://api.example.com/health
```

## Edge cases

- Heisenbugs that vanish under strace/gdb: timing-sensitive races;
  add logging instead of interactive debugging, and stress the repro
  in a loop.
- Bug only in production: differences are config, data volume, or
  environment; diff all three systematically before touching code.
- No logs at the failure point: the process died before flushing;
  log to stderr unbuffered (`python3 -u`, `stdbuf -o0`) or use the
  journal.
- `git bisect` with a flaky repro: automate with retries in the test
  script and require 3 consecutive passes to call a commit good.
- Core dump not written: check `ulimit -c`, core_pattern, disk space,
  and systemd's `DefaultLimitCORE` / per-service `LimitCORE`.
- Optimized-out variables in gdb (`<optimized out>`): rebuild that
  translation unit with `-O0 -g` for the debugging session.

## Escalation

- One layer down did not help: go another layer (syscall -> kernel
  messages -> hardware counters), or one layer up (is the caller
  passing garbage?).
- Suspect the compiler, kernel, or library: build a 20-line reproducer
  and test it on a second machine or container; environment-specific
  bugs are real but rare, so demand strong evidence.
- Distributed bug across services: add a request id through the whole
  chain first; debugging without correlation ids is guessing.
- Out of ideas: rubber-duck the timeline to a colleague, or sleep on
  it; a fresh read of the code you "know" is often where the bug is.
- Still stuck after a day: escalate with the repro script, the
  hypothesis log, and what you ruled out; that package gets help fast.

## Detection and defender view

Debugging tools are dual-use: strace, gdb, and core dumps also read
secrets from process memory. Detect misuse with:

```bash
# Unexpected debuggers attached to production processes
ps aux | grep -E 'strace|gdb |ltrace' | grep -v grep

# Core dumps lying around with possible secrets in them
sudo find /tmp /var/tmp /var/crash -name 'core*' -ls 2>/dev/null

# ptrace scope: who may attach to whom (Yama LSM)
cat /proc/sys/kernel/yama/ptrace_scope
```

Defensive rules: set `kernel.yama.ptrace_scope=1` (only parents may
trace) or `2` (only with CAP_SYS_PTRACE) on production hosts, restrict
core dump paths and scrub them, never leave `PYTHONFAULTHANDLER` dumps
or gdb sessions on shared machines, and treat any unexpected core file
as an incident artifact: it may contain keys and PII. A debugger
attached to a payment or auth process outside a maintenance window is
worth an alert.

## Key references

- GDB 15 manual: https://sourceware.org/gdb/current/onlinedocs/gdb.html
- strace man page: https://man7.org/linux/man-pages/man1/strace.1.html
- Python pdb: https://docs.python.org/3/library/pdb.html
- Python faulthandler: https://docs.python.org/3/library/faulthandler.html
- git-bisect docs: https://git-scm.com/docs/git-bisect
- "Debugging: The 9 Indispensable Rules" (Agans): the hypothesis
  discipline behind this skill.
- CWE-754 (Improper Check for Unusual Conditions): bugs born from
  unhandled edge cases.
