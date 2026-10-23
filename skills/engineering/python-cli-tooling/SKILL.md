---
name: python-cli-tooling
description: Use when building command-line tools in Python using only the standard library, when designing an argparse interface with subcommands, when adding --help, --version, --sample, and --output json conventions to a script, when defining typed exit codes for CI pipelines, and when packaging a tool as a single file or zipapp archive with no pip dependencies.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: []
tools:
  - name: python
    version: "3.12"
---

This skill covers building dependable command-line tools in Python 3.12 with zero third-party dependencies. The scope is the full contract of a good CLI: an argparse interface with subcommands, consistent `--help`, `--version`, `--sample`, and `--output` conventions, typed exit codes that CI pipelines can branch on, clean separation of human output (stdout) and diagnostics (stderr), and single-file distribution via zipapp. Everything here uses the standard library only, so the tool runs on any machine with a bare Python 3.12 interpreter.

## Quick Workflow

1. Define the command surface: verbs (subcommands), options, inputs, and outputs.
2. Scaffold argparse with subparsers and a shared parent parser for common flags.
3. Wire `--help`, `--version`, and a `--sample` command that prints example input.
4. Add `--output {text,json}` and emit one structured record per result.
5. Define typed exit codes as an IntEnum and use them on every exit path.
6. Add `-v`/`-q` logging to stderr. Never mix logs into stdout data.
7. Handle stdin, files, and encodings explicitly (UTF-8, streaming line by line).
8. Package as a single file or zipapp archive with a shebang.
9. Contract-test: `--help` exits 0, `--sample` output parses, `--output json` validates, bad input exits non-zero.

## Phase 1: argparse skeleton with subcommands

One file, subcommands as verbs, common flags on a parent parser so they stay consistent.

```python
#!/usr/bin/env python3
"""logfilter: filter JSON log lines by level."""
import argparse
import sys

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="count", default=0,
                        help="increase log verbosity (repeatable)")
    common.add_argument("-q", "--quiet", action="store_true",
                        help="suppress non-essential output")
    common.add_argument("--output", choices=["text", "json"], default="text",
                        help="output format (default: text)")

    parser = argparse.ArgumentParser(
        prog="logfilter",
        description="Filter JSON log lines by severity level.")
    parser.add_argument("--version", action="version", version="logfilter 1.0.0")
    sub = parser.add_subparsers(dest="command", required=True,
                                metavar="command")

    p_filter = sub.add_parser("filter", parents=[common],
                              help="keep lines at or above a level")
    p_filter.add_argument("--level", default="INFO",
                          choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                          help="minimum level to keep")
    p_filter.add_argument("input", nargs="?", default="-",
                          help="input file, or - for stdin (default: -)")
    p_filter.set_defaults(func=cmd_filter)

    p_sample = sub.add_parser("sample", parents=[common],
                              help="print example input and exit")
    p_sample.set_defaults(func=cmd_sample)
    return parser

def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
```

Key points: `required=True` on subparsers makes a bare invocation print help and exit 2 instead of crashing with AttributeError. `set_defaults(func=...)` dispatches cleanly. `nargs="?"` with default `"-"` gives the Unix stdin convention.

## Phase 2: The --help, --sample, and --output conventions

`--help` and `--version` come free from argparse. `--sample` is the convention this skill adds: it prints valid example input so users and tests can exercise the tool without fixtures.

```python
import json

SAMPLE_LINES = [
    {"ts": "2026-10-23T04:00:00Z", "level": "INFO", "msg": "started"},
    {"ts": "2026-10-23T04:00:01Z", "level": "ERROR", "msg": "disk full"},
]

def cmd_sample(args) -> int:
    for record in SAMPLE_LINES:
        print(json.dumps(record))
    return 0

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}

def cmd_filter(args) -> int:
    threshold = LEVELS[args.level]
    stream = sys.stdin if args.input == "-" else open(args.input, encoding="utf-8")
    with stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                log(args, f"skipping bad line: {exc}")
                continue
            if LEVELS.get(record.get("level", ""), 0) >= threshold:
                emit(args, record)
    return 0

def emit(args, record: dict) -> None:
    if args.output == "json":
        print(json.dumps(record))
    else:
        print(f"{record.get('ts', '?')} [{record.get('level', '?')}] {record.get('msg', '')}")
```

Try it:

```bash
python3 logfilter.py sample | python3 logfilter.py filter --level WARNING --output json
python3 logfilter.py filter --help
python3 logfilter.py --help
```

`--output json` must always be machine-parseable: one JSON object per line (JSONL) or a single JSON array. Never print log lines, progress bars, or warnings to stdout when `--output json` is set.

## Phase 3: Typed exit codes

Define every exit code in one place as an IntEnum. CI pipelines branch on these, so they are part of the tool's public contract and must not change meaning between versions.

```python
import enum

class Exit(enum.IntEnum):
    OK = 0
    ERROR = 1          # unexpected runtime failure
    USAGE = 2          # bad arguments (argparse uses this too)
    INPUT = 3          # input missing or unreadable
    VALIDATION = 4     # input failed validation
    OUTPUT = 5         # could not write output
    INTERRUPTED = 130  # SIGINT, the shell convention

def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"logfilter: {exc}", file=sys.stderr)
        return Exit.INPUT
    except BrokenPipeError:
        # downstream closed the pipe (e.g. | head); exit quietly
        return Exit.OK
    except KeyboardInterrupt:
        return Exit.INTERRUPTED
```

| Code | Meaning | When to use |
|---|---|---|
| 0 | Success | normal completion, including "no matches found" for a filter |
| 1 | General error | unexpected exception, keep for truly unexpected cases |
| 2 | Usage error | bad flags or missing required args (argparse default, do not override) |
| 3 | Input problem | file not found, unreadable stdin, bad encoding |
| 4 | Validation failed | input parsed but is semantically invalid |
| 5 | Output problem | cannot write the output file or stream |
| 130 | Interrupted | user pressed Ctrl-C |

Note: exit 0 on "no results" for a filter or search tool. Reserve non-zero for actual failure, or `grep`-style pipelines become unusable.

## Phase 4: Logging and I/O discipline

Logs go to stderr. Data goes to stdout. This is what makes `--output json | jq` pipelines work.

```python
import logging

def setup_logging(args) -> None:
    level = logging.WARNING
    if args.verbose == 1:
        level = logging.INFO
    elif args.verbose >= 2:
        level = logging.DEBUG
    if args.quiet:
        level = logging.ERROR
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s",
                        stream=sys.stderr)

def log(args, message: str) -> None:
    if not args.quiet:
        print(f"logfilter: {message}", file=sys.stderr)
```

File handling rules: always open text files with `encoding="utf-8"`. Stream line by line instead of `read()` when the input can be large. If stdin is a TTY and the tool expects piped input, print a hint to stderr and exit 2 rather than hanging forever:

```python
if args.input == "-" and sys.stdin.isatty():
    print("logfilter: no input: pipe data in or pass a file", file=sys.stderr)
    return Exit.USAGE
```

## Phase 5: Packaging with no dependencies

Check the file compiles, then ship it as a single executable zipapp archive or a plain script with a shebang.

```bash
python3 -m py_compile logfilter.py && echo "compiles clean"
chmod +x logfilter.py
./logfilter.py --help
```

For a multi-module tool, keep the zipapp path working:

```bash
mkdir -p mytool
cp logfilter.py mytool/__main__.py
python3 -m zipapp mytool -p "/usr/bin/env python3" -o logfilter.pyz
./logfilter.pyz sample | ./logfilter.pyz filter --level ERROR
```

Optional config files without dependencies: use `tomllib` (standard library since Python 3.11). Convention: CLI flags override config file values, which override built-in defaults.

```python
import tomllib, pathlib

def load_config(path: str) -> dict:
    p = pathlib.Path(path).expanduser()
    if not p.exists():
        return {}
    with p.open("rb") as fh:
        return tomllib.load(fh)
```

## Phase 6: Contract tests

A five-minute test script that guards the CLI contract:

```bash
./logfilter.py --help >/dev/null            || echo "FAIL: --help"
./logfilter.py --version                    || echo "FAIL: --version"
./logfilter.py bogus-command 2>/dev/null   && echo "FAIL: bad command should exit non-zero"
./logfilter.py sample | python3 -m json.tool >/dev/null || echo "FAIL: sample is not valid JSON"
./logfilter.py sample | ./logfilter.py filter --level ERROR --output json | python3 -c "import json,sys; [json.loads(l) for l in sys.stdin]" || echo "FAIL: json output invalid"
echo '{"level":"INFO"}' | ./logfilter.py filter --level ERROR; test $? -eq 0 || echo "FAIL: no-match filter should exit 0"
```

## Edge cases

- Broken pipe (`| head`): catch `BrokenPipeError` and exit 0. Also set `SIGPIPE` to default on platforms where Python ignores it, or the tool prints a traceback on every truncated pipe.
- `--help` exits 0 and `--version` exits 0. Tests and users rely on this.
- Flags after the subcommand belong to the subcommand; flags before it belong to the top parser. Document the order in `--help` examples.
- `argparse` with `nargs="*"` and a file argument: an empty list is fine, do not crash on it.
- Unicode filenames and content: open with `encoding="utf-8"` and decide on `errors="replace"` for hostile input versus strict for validated input.
- Long-running tools: flush stdout periodically or use `print(..., flush=True)` so pipelines see progress.
- Do not call `sys.exit()` deep inside helper functions. Return exit codes up to `main()` so the tool stays importable and testable.

## Escalation

- The tool outgrows one file: convert to a package directory with `__main__.py`, keep the zipapp build step, and keep the CLI surface identical.
- You need config files: use `tomllib` with the flag-overrides-file-overrides-defaults layering. Do not invent a custom config format.
- You need speed: stream instead of loading whole files, avoid per-line regex recompilation, profile with `cProfile` before rewriting anything.
- You genuinely need a third-party dependency: stop and reconsider scope. This skill's contract is stdlib-only; adding a dependency changes installation, packaging, and the security review surface.

## Detection and defender view

For engineering skills this section covers detecting CLI misuse and interface misconfiguration.

- Misuse: a tool that exits 0 on failure breaks every pipeline silently. Detect with the contract tests in Phase 6 run in CI.
- Misconfiguration: logs printed to stdout corrupt `--output json` for downstream parsers. Detect by piping JSON output through `python3 -m json.tool` in CI; any failure is a bug.
- Security-relevant misuse: building shell commands with `shell=True` from CLI arguments reintroduces command injection (see secure-coding). Grep the tool's own source for `shell=True`, `eval(`, and `os.system` before release.
- Convention drift across a team's tools (one uses `--json`, another `--output json`): pick one convention, document it, and lint for it.

## Key references

- Python 3.12 docs: argparse (docs.python.org/3/library/argparse.html), logging, sys, tomllib, zipapp, enum (docs.python.org/3/library/)
- Exit status conventions: sysexits.h and the POSIX shell convention for 130 on SIGINT
- zipapp: python -m zipapp --help and docs.python.org/3/library/zipapp.html
