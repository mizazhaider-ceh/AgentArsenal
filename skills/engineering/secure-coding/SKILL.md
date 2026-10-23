---
name: secure-coding
description: Use when writing or fixing code that handles untrusted input, when choosing safe APIs for SQL, shell, and file access, when implementing password hashing, session tokens, and output encoding, when managing secrets and dependencies, and when you need each practice mapped to its CWE so findings line up with code review and web testing.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [code-reviewer, web-sqli, web-xss]
tools:
  - name: python
    version: "3.12"
  - name: git
    version: "2.43"
---

This skill covers defensive coding practices for everyday development: validating input, encoding output, using safe APIs, handling authentication and sessions, managing secrets, and keeping dependencies healthy. Every practice is mapped to its CWE identifier so findings line up with the code-reviewer skill and with web testing skills like web-sqli and web-xss. The scope is language-agnostic principles with concrete Python 3.12 examples, because examples are what survive into real code. It does not cover designing new cryptographic protocols; use vetted primitives and call in a specialist for anything custom.

## Quick Workflow

1. List every input to the component and mark the trust boundary: what is attacker-controlled?
2. Validate at the boundary: type, allowlist, length, and range. Reject, do not sanitize, when possible.
3. Choose safe APIs: parameterized queries, argument lists instead of shells, safe path joins.
4. Encode output for its context: HTML, JavaScript, URL, shell, and log contexts all differ.
5. Centralize authentication: memory-hard password hashing, random session tokens, secure cookies.
6. Keep secrets out of code, logs, and error messages. Load from the environment or a secret store.
7. Pin and audit dependencies. Fewer dependencies, reviewed updates, no unmaintained packages.
8. Fail closed: deny by default, log the event without the secret, and show users a generic error.

## Phase 1: Input validation

Validate where untrusted data enters, not where it is used. An allowlist (what is permitted) beats a denylist (what is blocked), because attackers are creative and your denylist is finite. CWE-20.

```python
import re

USERNAME_RE = re.compile(r"[a-z0-9_]{3,20}")

def valid_username(value: str) -> bool:
    return USERNAME_RE.fullmatch(value) is not None

def parse_page(value: str) -> int:
    page = int(value)          # raises ValueError on garbage: good
    if not 1 <= page <= 1000:
        raise ValueError("page out of range")
    return page
```

Rules: check type first, then format, then length, then range. Set explicit maximum lengths on every string input; unbounded input is a denial-of-service vector. Normalize Unicode (NFKC) before validation when the input feeds comparisons or filesystem paths. Never trust client-side validation; it is UX, not security.

## Phase 2: Output encoding

Encoding depends on context. HTML-escaping a value placed inside a `<script>` block does not protect it. Encode at the last moment, for the exact context. CWE-79.

```python
import html
import urllib.parse

def render_profile(name: str) -> str:
    return f"<p>Hello, {html.escape(name)}</p>"   # HTML body context

def build_link(query: str) -> str:
    return "/search?q=" + urllib.parse.quote(query, safe="")  # URL context

def safe_log(value: str) -> str:
    return value.replace("\n", " ").replace("\r", " ")  # log context: no newlines
```

Log injection (CWE-117): a newline in logged user input lets an attacker forge log lines. Strip or replace `\r` and `\n` in anything written to logs. In templates, use the framework's autoescaping and never mark user data as safe. In JavaScript contexts, prefer `textContent` over `innerHTML`, and JSON-encode server data instead of interpolating it into scripts.

## Phase 3: Safe data access

Use APIs that separate code from data. String-building SQL, shell commands, or file paths from user input is the single most common source of critical findings.

SQL, parameterized (CWE-89):

```python
import sqlite3

db = sqlite3.connect("app.db")
cur = db.cursor()
cur.execute("SELECT * FROM users WHERE name = ?", (name,))  # data stays data
```

Bad pattern for comparison: `f"SELECT * FROM users WHERE name = '{name}'"`. One quote character ends the string and the rest becomes SQL.

Shell, argument list form (CWE-78):

```python
import subprocess

subprocess.run(["convert", filename, "out.png"], shell=False, check=True)
```

Bad pattern: `subprocess.run("convert " + filename + " out.png", shell=True)`. A filename of `x.png; rm -rf ~` becomes two commands. Rule: never use `shell=True` with any part of the command derived from input. If you must build complex pipelines, use `shlex.quote` on each argument, but prefer the list form.

File paths, no traversal (CWE-22):

```python
import pathlib

BASE = pathlib.Path("/srv/uploads").resolve()

def safe_path(name: str) -> pathlib.Path:
    candidate = (BASE / name).resolve()
    if BASE not in candidate.parents and candidate != BASE:
        raise ValueError("path escapes upload directory")
    return candidate
```

Bad pattern: `open("/srv/uploads/" + name)` with `name = "../../etc/passwd"`. Resolve symlinks with `.resolve()` and verify the result stays under the base directory.

## Phase 4: Authentication and sessions

Get this wrong and nothing else matters. Centralize auth logic in one module; scattered auth checks drift out of sync.

Password hashing (CWE-916): use a memory-hard, salted KDF. Never MD5, SHA1, or plain SHA256 for passwords; they are too fast and fall to GPUs.

```python
import hashlib, os

def hash_password(password: str) -> bytes:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return salt + dk

def verify_password(password: str, stored: bytes) -> bool:
    salt, dk = stored[:16], stored[16:]
    check = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(check, dk)
```

Session tokens (CWE-330): generate with a cryptographic random source, with at least 128 bits of entropy.

```python
import secrets, hmac

session_id = secrets.token_urlsafe(32)   # 256 bits, URL-safe
```

Compare secrets with `hmac.compare_digest`, never `==`, to avoid timing attacks. Cookies holding sessions get `HttpOnly`, `Secure`, and `SameSite=Lax` (or `Strict`). Enforce rate limiting and lockout on login endpoints to blunt brute force, and never reveal whether the username or the password was wrong.

## Phase 5: Secrets management

Secrets in code are compromised code. Treat every committed secret as public. CWE-798, CWE-259.

```python
import os

def get_secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required secret: {name}")
    return value

API_KEY = get_secret("APP_API_KEY")   # fails fast at startup, never defaults
```

Rules: load secrets from environment variables or a secret store (never from the repo, never from client-side code). Fail fast at startup when a required secret is missing; do not fall back to a default. Rotate on a schedule and immediately after any suspected exposure. Redact secrets in logs and error messages with a helper, and scan the repo history for past leaks:

```bash
git log --all -S 'BEGIN PRIVATE KEY' --oneline
rg -n -i "(password|secret|api[_-]?key)\s*[:=]\s*['\"][^'\"]{4,}['\"]" .
```

Sensitive data in logs (CWE-532): no passwords, tokens, session IDs, or full card numbers in application logs. Log the event ("login failed for user X"), not the credential.

## Phase 6: Dependency hygiene

Every dependency is code you did not write but now ship. CWE-1104, CWE-829.

```bash
python3 -m pip install --dry-run -r requirements.txt   # preview before installing
python3 -m pip freeze | sort > requirements.lock        # pin what you tested
```

Rules: pin versions and test what you pin. Prefer well-maintained packages with a real release history over abandoned ones. Review what a new dependency pulls in transitively; a tiny utility package with thirty transitive deps is a supply-chain risk. Subscribe to security advisories for your stack and update on a cadence, not only during incidents. Remove dependencies you no longer use; dead deps still get exploited.

## Edge cases

- Unicode attacks: normalize with NFKC before validation; watch homoglyphs (lookalike characters) in usernames and domains.
- Time-of-check to time-of-use: validating a path and then opening it can race. Where it matters, operate on open file descriptors rather than re-resolving paths.
- Timing attacks: any comparison of secrets, tokens, or hashes must use constant-time compare.
- SSRF in URL validation: parse the URL, resolve the host, and check it against an allowlist. Block private ranges, link-local addresses (like cloud metadata endpoints), and redirects to unlisted hosts. A regex on the URL string is not enough.
- Error messages: generic to the user ("login failed"), detailed to the server log. Never echo SQL, stack traces, file paths, or framework versions to clients.
- Deserialization: never unpickle, unserialize, or eval untrusted data. Use JSON with explicit schema checks.

## Escalation

- No safe API exists for what you need: write one thin wrapper module that the whole codebase must use, and review that wrapper once, carefully. One reviewed choke point beats fifty ad-hoc fixes.
- Legacy code cannot be fixed now: add a compensating control (strict allowlist at the edge, a WAF rule), file it as tracked tech debt with an owner and a deadline, and do not let the deadline slide silently.
- The problem is cryptographic protocol design, novel token schemes, or custom key management: stop and bring in a specialist. Do not invent ciphers, modes, or protocols.

## Detection and defender view

For engineering skills this section covers detecting insecure-coding misuse and pipeline misconfiguration.

- Misuse: validation disabled "temporarily for testing" and never re-enabled, debug mode on in production, secrets committed to env files in the repo, installs without pinned versions.
- Detect in CI: run a SAST scanner on every diff, run a secret scanner on every push, run a dependency audit on a schedule. Gate merges on the results; advisory-only scanners get ignored.
- Detect in production: alert on authentication anomalies (spikes in failed logins, logins from new geographies), on unexpected 500s that may indicate probing, and on processes spawning shells from web handlers.
- Misconfiguration: verbose error pages in production, directory listing enabled, default credentials on deployed services, TLS verification disabled to "fix" a cert error.

## Key references

- CWE-20 Improper Input Validation, CWE-22 Path Traversal, CWE-78 OS Command Injection, CWE-79 Cross-site Scripting, CWE-89 SQL Injection, CWE-117 Log Injection, CWE-259 Hard-coded Password, CWE-330 Insufficient Randomness, CWE-532 Sensitive Information in Logs, CWE-798 Hard-coded Credentials, CWE-829 Untrusted Inclusion, CWE-916 Weak Password Hashing, CWE-1104 Unmaintained Third-Party Components (cwe.mitre.org)
- OWASP Secure Coding Practices and Cheat Sheet Series: Input Validation, Authentication, Session Management, Cryptographic Storage (cheatsheetseries.owasp.org)
- Python 3.12 docs: secrets, hashlib, html, subprocess, pathlib (docs.python.org/3/library/)
