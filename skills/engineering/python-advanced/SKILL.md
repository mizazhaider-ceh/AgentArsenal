---
name: python-advanced
description: Use when writing or reviewing advanced Python code on an
  authorized engineering task. Covers type hints and mypy 1.13 strictness,
  dataclasses and Pydantic-style validation patterns, context managers,
  generators and iterators, asyncio concurrency, multiprocessing, packaging
  with pyproject.toml and venv, profiling with cProfile and tracemalloc,
  and debugging with pdb and faulthandler. Use when a Python CLI, service,
  or script needs structure, speed, or safer concurrency.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [python-cli-tooling, code-reviewer, secure-coding]
tools:
  - name: Python
    version: 3.12
  - name: pytest
    version: 8.3
  - name: mypy
    version: 1.13
---

This skill covers Python at the professional level: typing that catches
bugs before runtime, data modeling, resource-safe patterns, concurrency
that does not corrupt state, packaging that installs cleanly, and
profiling that tells you where the time and memory really go. It builds
on the basics of small scripts and CLIs and focuses on code that must be
correct, fast, and maintainable in production. All examples use Python
3.12 and stdlib unless a tool is named.

## Quick Workflow

1. Create an isolated environment with `venv` and pin dependencies in
   `requirements.txt` or `pyproject.toml`.
2. Write typed code from the start and check it with `mypy --strict`.
3. Model data with `dataclasses` or typed containers, never with loose
   dicts that grow undocumented keys.
4. Wrap every external resource (files, sockets, locks) in a context
   manager so cleanup happens even on exceptions.
5. Choose the right concurrency model: asyncio for I/O bound work,
   multiprocessing for CPU bound work, threads only with locks you can
   explain.
6. Profile before optimizing: `cProfile` for time, `tracemalloc` for
   memory, `py-spy` style sampling for production.
7. Write tests with `pytest` for the paths that handle money, auth, or
   data loss.
8. Package with `pyproject.toml` so the project installs with one
   command and ships metadata.

## 1. Environments and packaging

Never install project dependencies into the system Python. Use a virtual
environment per project and record exact pins.

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# Pin what you have today, review what you add later
pip install requests pytest mypy
pip freeze > requirements.txt

# Check which interpreter and packages are active
which python
pip list | head -20
```

A minimal `pyproject.toml` makes the project installable and declares
metadata in one place:

```bash
cat > pyproject.toml <<'EOF'
[project]
name = "mytool"
version = "0.1.0"
description = "Internal helper tool"
requires-python = ">=3.12"
dependencies = ["requests>=2.31"]

[project.scripts]
mytool = "mytool.cli:main"

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
EOF

pip install -e .
mytool --help
```

## 2. Type hints and mypy

Type hints document intent and let mypy catch an entire class of bugs
before the code ever runs. Start strict on new code; add types to old
code file by file.

```bash
# Install and run mypy in strict mode
pip install mypy==1.13
mypy --strict src/
```

```python
from __future__ import annotations

def fetch_user(user_id: int) -> dict[str, str] | None:
    """Return the user record, or None when the id is unknown."""
    row = db_lookup(user_id)  # assume this returns dict or None
    if row is None:
        return None
    return {"name": row["name"], "email": row["email"]}

def notify(users: list[int], message: str) -> int:
    sent = 0
    for uid in users:
        if send_message(uid, message):
            sent += 1
    return sent
```

Common mypy findings to fix, not silence: returning `None` where a
value is promised, mutating a `tuple` like a list, and passing
`str` where `int` is expected. Use `cast()` only when you can prove
the type and the checker cannot; every cast is a bet you should be
able to explain.

## 3. Dataclasses for structured data

Dataclasses replace dicts that grow mystery keys and tuples whose field
order nobody remembers.

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)
class ScanResult:
    """Immutable result: safe to share across threads and tasks."""
    host: str
    port: int
    open: bool
    banner: str = ""
    scanned_at: datetime = field(default_factory=datetime.now)

@dataclass
class ScanJob:
    targets: list[str]
    ports: list[int] = field(default_factory=lambda: [80, 443])
    timeout: float = 5.0
    results: list[ScanResult] = field(default_factory=list)

    def add(self, result: ScanResult) -> None:
        self.results.append(result)
```

Use `frozen=True` for value objects that must not change after
creation. Use `field(default_factory=...)` for mutable defaults; a
bare `[]` default is a shared mutable object and a classic bug.

## 4. Context managers for safe resources

Files, locks, database connections, and temporary directories must be
released even when code raises. The `with` statement plus a custom
context manager guarantees it.

```python
from contextlib import contextmanager
import time

@contextmanager
def timed_section(label: str):
    """Context manager that logs how long a block took."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"{label} took {elapsed:.2f}s")

with timed_section("database scan"):
    run_scan()
```

```bash
# Verify a file handle closes even on exception
python3 - <<'EOF'
f = open("/tmp/demo.txt", "w")
try:
    f.write("data")
    raise RuntimeError("boom")
except RuntimeError:
    pass
finally:
    f.close()
print("closed:", f.closed)
EOF
```

## 5. Generators and iterators

Generators process one item at a time, so a 10 GB log file never sits
in memory.

```python
def read_lines(path: str):
    """Yield lines lazily; the file closes when the loop ends."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            yield line.rstrip("\n")

def failed_logins(path: str):
    for line in read_lines(path):
        if "Failed password" in line:
            yield line

# Count without loading the file
count = sum(1 for _ in failed_logins("/var/log/auth.log"))
print("failed logins:", count)
```

Generator expressions (`sum(1 for ...)`) beat list comprehensions when
you only need one pass. Chain generators into pipelines instead of
building intermediate lists.

## 6. asyncio for I/O bound concurrency

When the program waits on the network, asyncio runs hundreds of
operations in one thread instead of blocking on each.

```python
import asyncio

async def check_port(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout
        )
        writer.close()
        return True
    except (OSError, asyncio.TimeoutError):
        return False

async def scan(host: str, ports: list[int]) -> list[int]:
    results = await asyncio.gather(
        *(check_port(host, p) for p in ports)
    )
    return [p for p, is_open in zip(ports, results) if is_open]

open_ports = asyncio.run(scan("127.0.0.1", [22, 80, 443, 8080]))
print("open:", open_ports)
```

Limit concurrency with a semaphore so you do not open 10,000
connections at once:

```python
sem = asyncio.Semaphore(100)

async def checked(host: str, port: int) -> bool:
    async with sem:
        return await check_port(host, port)
```

Never mix blocking calls (like `time.sleep` or `requests.get`) inside
async functions; they freeze the whole event loop. Use `await
asyncio.sleep()` and async HTTP clients instead.

## 7. multiprocessing for CPU bound work

The GIL stops threads from using multiple cores for pure computation.
Use processes when the bottleneck is CPU, not waiting.

```bash
python3 - <<'EOF'
import multiprocessing as mp
import hashlib, os

def hash_chunk(n: int) -> str:
    h = hashlib.sha256()
    for i in range(n):
        h.update(f"block-{i}".encode())
    return h.hexdigest()[:16]

if __name__ == "__main__":
    print("cpus:", os.cpu_count())
    with mp.Pool(processes=os.cpu_count()) as pool:
        results = pool.map(hash_chunk, [200_000] * os.cpu_count())
    print("done:", len(results))
EOF
```

Guard process-spawning code with `if __name__ == "__main__":` or child
processes will re-run your top-level code. Prefer `pool.map` over
manual process management; pass plain data (numbers, strings) between
processes, not open sockets or locks.

## 8. Profiling and debugging

Optimize with measurements, never with guesses.

```bash
# CPU profile: which functions burn time
python3 -m cProfile -s cumulative myscript.py | head -25

# Memory: where allocations come from
python3 - <<'EOF'
import tracemalloc
tracemalloc.start()
data = [bytearray(10_000) for _ in range(1_000)]
current, peak = tracemalloc.get_traced_memory()
print(f"current={current/1e6:.1f}MB peak={peak/1e6:.1f}MB")
tracemalloc.stop()
EOF

# Post-mortem debugging: drop into pdb on unhandled exception
python3 - <<'EOF'
import pdb, traceback, sys

def buggy():
    items = [1, 2, 3]
    return items[10]

try:
    buggy()
except Exception:
    traceback.print_exc()
    # pdb.post_mortem()  # uncomment for interactive inspection
EOF
```

`faulthandler` dumps a traceback when a hung process gets SIGABRT,
which is invaluable for deadlocks in production:

```bash
# In code: faulthandler.enable() at startup
# Then send SIGABRT to a stuck process to get a thread dump
kill -ABRT <pid>
```

## 9. pytest patterns that survive

```bash
pip install pytest==8.3
mkdir -p tests && cat > tests/test_scan.py <<'EOF'
import pytest
from mytool.scan import ScanResult

def test_scan_result_defaults():
    r = ScanResult(host="h", port=80, open=True)
    assert r.banner == ""
    assert r.scanned_at is not None

@pytest.mark.parametrize("port,expected", [(80, True), (0, False), (70000, False)])
def test_port_valid(port, expected):
    assert (1 <= port <= 65535) == expected
EOF

pytest -q
pytest -q --tb=short -x   # stop at first failure, short tracebacks
```

Fixtures isolate setup; parametrize covers the boundary table in one
test instead of ten copies.

## Edge cases

- mypy strict on legacy code produces hundreds of errors. Adopt it
  module by module: add one clean module to the checked list at a
  time instead of fighting the whole codebase at once.
- asyncio code calls a blocking library and the loop stalls. Symptom:
  all coroutines pause together. Fix: run the blocking call in a
  thread with `asyncio.to_thread()`, or switch to an async library.
- Multiprocessing passes huge objects and startup crawls. Data is
  pickled to each child; pass small arguments and load shared data
  once per worker with an initializer.
- Generators are single-use. Iterating a generator twice silently
  yields nothing the second time; convert to a list if you need two
  passes, or rebuild the generator.
- `pip install` fails inside containers without network. Build a
  wheelhouse on a connected machine (`pip download -r
  requirements.txt -d wheels`) and install offline with
  `--no-index --find-links wheels`.
- Memory grows without bound on long runs. Check for unbounded caches
  (`functools.lru_cache` without `maxsize`), appended lists that are
  never drained, and reference cycles holding file handles.
- `python` points to Python 2 or the wrong 3.x on old systems. Always
  invoke `python3 -m venv` and activate explicitly; never trust a bare
  `python` on a machine you did not set up.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. A Python service is misconfigured when it runs as
root, when `pip install` pulls unsigned packages from a public index
on a production host, or when `eval()` and `pickle.loads()` touch
untrusted input (both execute arbitrary code). Detect misuse by
auditing imports of `subprocess`, `os.system`, `pickle`, and `eval`
in code that handles external data, and by checking that services run
under dedicated users with read-only code directories. Dependency
confusion and typosquatting are caught by pinning hashes
(`pip install --require-hashes`) and by using a private index for
internal packages. Slowloris-style resource exhaustion from unbounded
asyncio tasks shows up as one process holding thousands of sockets;
cap concurrency with semaphores and set timeouts on every network
call.

## Key references

- Python 3.12 documentation: https://docs.python.org/3.12/
- mypy 1.13 documentation: https://mypy.readthedocs.io/
- pytest 8.3 documentation: https://docs.pytest.org/
- asyncio documentation: https://docs.python.org/3/library/asyncio.html
- packaging with pyproject.toml: https://packaging.python.org/
- CWE-20 (Improper Input Validation): applies to untrusted data
  handled by Python services.
- CWE-502 (Deserialization of Untrusted Data): `pickle.loads` on
  untrusted input.
- CWE-78 (OS Command Injection): `os.system` and unsanitized
  `subprocess` calls.
