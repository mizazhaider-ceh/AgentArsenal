#!/usr/bin/env python3
"""Test every tool under tools/<tool-name>/<tool-name>.py.

For each tool file it:
  1. Checks the file compiles (py_compile).
  2. Runs it with --help and requires exit code 0 within 15 seconds.

Prints failures and exits non-zero when any tool fails. Stdlib only.

Usage:
    scripts/test_tools.py
    scripts/test_tools.py --quiet
"""

import argparse
import glob
import os
import py_compile
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
TIMEOUT = 15


def find_tools():
    pattern = os.path.join(TOOLS_DIR, "*", "*.py")
    return sorted(glob.glob(pattern))


def check_tool(path):
    """Return a list of failure strings (empty means the tool passed)."""
    failures = []
    name = os.path.basename(path)

    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as exc:
        failures.append("compile failed: %s" % exc)
        return failures

    try:
        proc = subprocess.run(
            [sys.executable, path, "--help"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        failures.append("--help timed out after %d seconds" % TIMEOUT)
        return failures
    except OSError as exc:
        failures.append("--help could not run: %s" % exc)
        return failures

    if proc.returncode != 0:
        failures.append("--help exited with code %d (stderr: %s)" % (
            proc.returncode, proc.stderr.strip()[:200]))
    if not proc.stdout.strip():
        failures.append("--help printed no output")
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile-check and --help-check every tool in tools/.")
    parser.add_argument("--quiet", action="store_true",
                        help="only print failures and the summary")
    args = parser.parse_args(argv)

    tools = find_tools()
    if not tools:
        print("Error: no tools found under %s" % TOOLS_DIR, file=sys.stderr)
        return 2

    failed = {}
    for path in tools:
        rel = os.path.relpath(path, REPO_ROOT)
        problems = check_tool(path)
        if problems:
            failed[rel] = problems
        elif not args.quiet:
            print("PASS  %s" % rel)

    print("")
    print("Checked %d tool(s): %d passed, %d failed"
          % (len(tools), len(tools) - len(failed), len(failed)))
    for rel, problems in sorted(failed.items()):
        print("FAIL  %s" % rel)
        for problem in problems:
            print("      - %s" % problem)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
