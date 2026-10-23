---
name: bash-advanced
description: Use when writing production-grade Bash 5.2 scripts: strict mode
  (set -euo pipefail), safe quoting and word splitting, arrays and
  associative arrays, parameter expansion, traps and cleanup handlers,
  getopts argument parsing, process substitution, functions with local
  variables, debugging with set -x and PS4, or fixing a fragile script that
  fails silently. Use when the task mentions shell scripting, bash
  automation, cron wrappers, or making an existing script robust and
  maintainable.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [python-cli-tooling, git-workflows]
tools:
  - name: Bash
    version: 5.2
  - name: ShellCheck
    version: 0.10
---

Bash is the default automation language on Linux servers, but casual Bash
fails silently: unset variables expand to empty strings, failed commands in
pipelines go unnoticed, and unquoted variables split on spaces. This skill
covers writing Bash 5.2 scripts that fail loudly and early: strict mode,
quoting discipline, data structures, error handling, argument parsing, and
debugging. Scope is scripting technique; interactive shell customization is
out of scope.

## Quick Workflow

1. Start every script with a shebang, `set -euo pipefail`, and a sane IFS.
2. Quote every variable expansion; use arrays instead of space-separated
   strings.
3. Validate inputs and required commands up front; fail with a clear usage
   message.
4. Install a trap that cleans up temp files on any exit path.
5. Write functions with `local` variables and explicit return codes.
6. Parse arguments with getopts; never hand-roll `$1` shifting for more
   than one flag.
7. Run ShellCheck on the script and fix every warning.
8. Test the failure paths: missing args, missing files, failing commands.

## 1. The strict header

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# -e: exit on any command failure
# -u: exit on use of an unset variable
# -o pipefail: a pipeline fails if ANY stage fails (not just the last)
# IFS narrowed so word splitting only breaks on newline/tab

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
```

Pipefail example of why it matters:

```bash
# Without pipefail this "succeeds" even if the download fails
set -o pipefail
curl -fsSL https://example.com/data.tar.gz | tar -xz -C /opt/data
```

## 2. Quoting and word splitting

```bash
name="backup dir"
# WRONG: splits into two arguments
# rm -rf $name
# RIGHT: one argument
rm -rf "$name"

# Arrays: the only safe way to build command lines dynamically
args=(-name "*.log" -mtime +30)
find /var/log "${args[@]}" -delete

# "$@" preserves each argument exactly (use in wrappers)
#!/usr/bin/env bash
set -euo pipefail
exec /usr/local/bin/real-tool "$@"
```

## 3. Parameter expansion (the built-in string toolkit)

```bash
file="/var/log/nginx/access.log"
echo "${file##*/}"      # basename: access.log
echo "${file%/*}"       # dirname:  /var/log/nginx
echo "${file%.log}"     # strip suffix: /var/log/nginx/access

# Defaults and mandatory values
: "${PORT:=8080}"                 # default if unset or empty
: "${API_KEY:?API_KEY must be set}"  # fatal error if unset

# String ops
s="  Hello World  "
echo "${s^^}"           # HELLO WORLD (uppercase)
echo "${s,,}"           # hello world (lowercase)
echo "${s// /_}"        # replace all spaces: __Hello_World__
echo "${#s}"            # length
echo "${s:2:5}"         # substring: Hello
```

## 4. Arrays and associative arrays

```bash
# Indexed arrays
hosts=(web1 web2 web3)
hosts+=(db1)
echo "${hosts[0]}"          # web1
echo "${#hosts[@]}"         # 4 (count)
for h in "${hosts[@]}"; do  # safe iteration
  echo "deploying to $h"
done

# Associative arrays (Bash 4+)
declare -A ports=([http]=80 [https]=443 [ssh]=22)
ports[metrics]=9090
echo "${ports[https]}"
for svc in "${!ports[@]}"; do
  echo "$svc -> ${ports[$svc]}"
done

# Read lines into an array without word splitting issues
mapfile -t lines < /etc/hosts
```

## 5. Error handling, traps, and cleanup

```bash
#!/usr/bin/env bash
set -euo pipefail

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT            # always clean up
trap 'echo "Interrupted"; exit 130' INT TERM

# Central error reporter with line number
err() { echo "ERROR: $*" >&2; }
trap 'err "failed at line $LINENO (exit $?)"' ERR

# Check prerequisites up front
need() { command -v "$1" >/dev/null 2>&1 || { err "missing: $1"; exit 1; }; }
need curl
need jq
```

Expected failures need explicit handling so `-e` does not kill the
script:

```bash
# grep returns 1 when nothing matches: that is not an error here
if grep -q "pattern" file.log; then
  echo "found"
fi

# Or neutralize with || true when the status is intentionally ignored
count=$(grep -c "x" file.log || true)
```

## 6. Functions with local scope

```bash
#!/usr/bin/env bash
set -euo pipefail

log()  { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die()  { log "FATAL: $*" >&2; exit 1; }

fetch() {
  local url="$1"
  local dest="$2"
  local retries="${3:-3}"
  local attempt=1
  while (( attempt <= retries )); do
    if curl -fsSL --retry 2 -o "$dest" "$url"; then
      return 0
    fi
    log "attempt $attempt/$retries failed for $url"
    (( attempt++ ))
    sleep 2
  done
  die "could not fetch $url after $retries attempts"
}

fetch "https://example.com/app.tar.gz" "/tmp/app.tar.gz"
```

## 7. Argument parsing with getopts

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() { echo "usage: $0 [-e env] [-v] [-n] <target>"; exit 2; }

env="prod"; verbose=0; dry_run=0
while getopts ":e:vn" opt; do
  case "$opt" in
    e) env="$OPTARG" ;;
    v) verbose=1 ;;
    n) dry_run=1 ;;
    :) echo "option -$OPTARG needs a value" >&2; usage ;;
    \?) echo "unknown option -$OPTARG" >&2; usage ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -eq 1 ]] || usage
target="$1"

(( verbose )) && echo "env=$env target=$target dry_run=$dry_run"
```

## 8. Process substitution and redirection tricks

```bash
# Diff command outputs without temp files
diff <(ls /backup/a) <(ls /backup/b)

# Feed a loop without a subshell (variables survive the loop)
while IFS= read -r line; do
  (( count++ ))
done < input.txt
echo "lines: $count"

# Never pipe INTO a while loop if you need the variables after:
# cat file | while read ... (WRONG: loop runs in a subshell)

# Timestamped logging of a whole script section
{
  echo "starting deploy"
  ./deploy.sh
} 2>&1 | ts '[%Y-%m-%d %H:%M:%S]' | tee /var/log/deploy.log

# Here-doc for multi-line files (quoted delimiter = no expansion)
cat > /etc/myapp/config.yaml <<'EOF'
server:
  port: 8080
EOF
```

## 9. Debugging

```bash
# Trace execution: shows each command before it runs
bash -x script.sh
# Or toggle inside the script
set -x   # tracing on
./risky-part.sh
set +x   # tracing off

# Richer trace prompt with line numbers (put in the script)
export PS4='+ ${BASH_SOURCE}:${LINENO}: '
set -x
```

ShellCheck catches the bugs tracing cannot:

```bash
shellcheck -S warning deploy.sh
# Fix everything it reports; aim for zero warnings
```

## Edge cases

- `set -e` is ignored in some contexts: commands in `if` conditions,
  `while` conditions, `&&`/`||` lists, and the last command of a
  function called in a condition. Do not rely on `-e` inside those;
  check statuses explicitly.
- `set -u` breaks `${arr[@]}` on empty arrays in Bash versions before
  4.4. Guard with `${arr[@]:-}` or check `${#arr[@]}` first.
- Command substitution strips trailing newlines: `x=$(cmd)` loses them.
  Append a sentinel character and strip it if trailing newlines matter.
- `read` without `-r` mangles backslashes; always use `read -r`.
- Filenames starting with `-` are parsed as flags: use `--` before paths
  (`rm -- "$file"`) or prefix with `./`.
- Cron runs scripts with a minimal environment: always set PATH
  explicitly and use absolute paths in cron-called scripts.
- `local` outside a function is a syntax error; keep declarations inside
  functions.

## Escalation

- Script dies silently under `-e`: rerun with `bash -x` and PS4 line
  numbers to find the exact failing command.
- Works interactively but fails from cron/systemd: environment issue;
  log `env | sort` at script start and compare, or source the needed
  profile explicitly.
- Intermittent failures: add retries with backoff (the fetch pattern
  above), log attempts, and make operations idempotent so reruns are
  safe.
- ShellCheck warning you do not understand: read its wiki page
  (`shellcheck -W 2086` prints the code); the wiki explains the exact
  failure mode.
- Logic too complex for Bash (nested JSON, date math, real data
  structures): that is the signal to rewrite in Python; see
  python-cli-tooling.

## Detection and defender view

Bash is also the attacker's favorite: malicious scripts use the same
constructs (curl pipes, base64 decoding, traps for persistence). Detect
misuse and risky scripting with:

```bash
# Suspicious one-liners in process lists and history
ps aux | grep -E 'curl.*\|\s*(ba)?sh|wget.*\|\s*(ba)?sh' | grep -v grep

# Scripts with dangerous patterns in common drop zones
sudo grep -rIlE 'curl.*\|.*sh|base64 --?decode.*\|.*sh|/dev/tcp/' \
  /tmp /var/tmp /dev/shm 2>/dev/null

# Recently modified scripts in system paths
sudo find /usr/local/bin /opt -name '*.sh' -mtime -7 -ls

# Cron and systemd timers calling shell scripts (persistence check)
sudo grep -r "sh$" /etc/cron* /var/spool/cron/ 2>/dev/null
systemctl list-timers --all
```

Defensive scripting habits: never `curl | bash` from untrusted sources,
pin checksums for downloaded scripts, run automation with least-privilege
users, and keep scripts in version control so unexpected changes stand
out. A script that phones home, decodes blobs, or touches
`/etc/cron.d` deserves investigation.

## Key references

- Bash 5.2 manual: https://www.gnu.org/software/bash/manual/bash.html
- BashFAQ (common pitfalls): https://mywiki.wooledge.org/BashFAQ
- Bash Pitfalls list: https://mywiki.wooledge.org/BashPitfalls
- ShellCheck wiki: https://www.shellcheck.net/wiki/
- Google Shell Style Guide: https://google.github.io/styleguide/shellguide.html
- CWE-78 (OS Command Injection): unquoted variables passed to shells.
- CWE-88 (Argument Injection): filenames starting with dash.
