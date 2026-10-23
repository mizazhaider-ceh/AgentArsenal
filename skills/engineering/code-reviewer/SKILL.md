---
name: code-reviewer
description: Use when reviewing code or pull requests for correctness, security, and maintainability, when auditing a codebase for vulnerabilities such as injection, broken authentication, insecure cryptography, and leaked secrets, and when you need a structured security-first checklist with ripgrep pattern sweeps, trust boundary mapping, manual data-flow tracing, and actionable findings that state severity, impact, proof, and a concrete fix.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding]
tools:
  - name: git
    version: "2.43"
  - name: ripgrep
    version: "14.1"
  - name: python
    version: "3.12"
---

This skill covers structured, security-first code review for pull requests and full codebases. It treats the reviewer as the last cheap line of defense: a bug caught in review costs far less than a bug caught in production. The scope is manual review supported by fast automated sweeps (git diff context, ripgrep pattern hunts, language analyzers). It covers the vulnerability patterns a reviewer must recognize per language, a repeatable review workflow, and how to write findings that authors can act on without follow-up questions. It pairs with secure-coding, which holds the fix patterns this skill points to.

## Quick Workflow

1. Size the change: files touched, lines added, and risk areas (auth, crypto, input handling, infrastructure).
2. Read the PR description and linked issue. Know what the change claims to do before reading how.
3. Map trust boundaries: list every source of untrusted input and every sink it can reach.
4. Run the dangerous-API sweep with ripgrep and the language analyzer. Record every hit.
5. Triage hits: confirm or rule out each one by reading the surrounding code.
6. Trace data flow for each candidate: can attacker-controlled data really reach the sink?
7. Review cross-cutting concerns: auth checks, session handling, crypto choices, secrets, logging.
8. Write findings with severity, impact, proof (file and line), and a concrete fix.
9. Verify fixes in a follow-up review and confirm a regression test exists.

## Phase 1: Scope and setup

Start every review by understanding the shape of the change. Review the diff, not the whole file, but pull in enough context to see where inputs come from.

```bash
git diff --stat main...HEAD
git diff --name-only main...HEAD | grep -E '\.(py|js|ts|java|go|sql)$'
git log --oneline -5
git diff main...HEAD -- auth/ crypto/ login/ | head -200
```

Rules of thumb: a PR over about 400 changed lines is hard to review well, send it back to be split. Generated files (migrations, protobuf output, lockfiles) get a skim, not a line review. New dependencies get a version and maintenance check, not a code read.

## Phase 2: Dangerous-API sweep

Run fast pattern searches before reading line by line. These find candidates, not confirmed bugs. Every hit still needs manual tracing in Phase 3.

Python:

```bash
rg -n "subprocess\.(run|call|Popen|check_output).*shell\s*=\s*True" --type py .
rg -n "pickle\.loads|yaml\.load\(|shelve\.open|eval\(|exec\(" --type py .
rg -n "f['\"]SELECT |f['\"]INSERT |%\s*\(.*\)\s*['\"]" --type py . | grep -i "select\|insert\|update\|delete"
rg -n "random\.(random|choice|randint)" --type py . | grep -vi "test"
```

JavaScript and TypeScript:

```bash
rg -n "innerHTML|outerHTML|document\.write|eval\(|new Function\(" -tjs -tts .
rg -n "child_process.*exec\(|execSync\(" -tjs -tts .
rg -n "__proto__|constructor\.prototype" -tjs -tts .
```

Java:

```bash
rg -n "Runtime\.getRuntime\(\)\.exec|ProcessBuilder" --type java .
rg -n "DocumentBuilderFactory|XMLReaderFactory|SAXParserFactory" --type java .
rg -n "readObject\(\)|XMLDecoder" --type java .
rg -n "createStatement\(\)\.execute" --type java .
```

Go:

```bash
rg -n "exec\.Command\(\"sh\", \"-c\"" --type go .
rg -n "fmt\.Sprintf\(.*SELECT|fmt\.Sprintf\(.*INSERT" --type go .
rg -n "math/rand" --type go . | grep -v "crypto/rand"
```

Secrets in any language:

```bash
rg -n -i "(password|passwd|secret|api[_-]?key|aws_secret|private[_-]?key)\s*[:=]\s*['\"][^'\"]{4,}['\"]" .
rg -n "BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY" .
rg -n -i "sk_live|ghp_|xox[bap]-|AKIA[0-9A-Z]{16}" .
```

## Phase 3: Manual data-flow trace

A sink is only a finding if untrusted data can reach it. For each candidate, walk backward from the sink to the source and forward from the source to the sink.

Example trace (Python web app):

```python
# route handler: source is request.args (untrusted)
@app.get("/report")
def report():
    name = request.args.get("name", "")          # SOURCE: attacker controlled
    query = f"SELECT * FROM reports WHERE name = '{name}'"  # string-built SQL
    cur.execute(query)                            # SINK: SQL execution
```

Checklist for the trace:

```bash
# find all callers of the risky function to see what feeds it
rg -n "def run_report|run_report\(" --type py .
# check whether any sanitizer or allowlist sits between source and sink
rg -n "escape|sanitize|allowlist|fullmatch" --type py app/
```

Ask three questions: Is the source attacker-controlled? Is there any validation, encoding, or allowlist between source and sink? Does the sink interpret the data as code? If all three answers are yes, yes is missing, and yes, you have a finding.

## Phase 4: Cross-cutting checks

These apply no matter what the diff touches. Run them on every review.

Authentication and authorization:

```bash
rg -n "login|authenticate|authorize|is_admin|has_role|@login_required" --type py -tjs -tts .
```

Verify: every sensitive route checks auth, authorization is enforced server side (not just hidden in the UI), password comparison uses a constant-time compare, and session tokens come from a cryptographic random source.

Cryptography: flag MD5 or SHA1 for passwords or tokens, ECB mode, hardcoded IVs, custom crypto, `verify=False` on TLS, and JWT code that does not pin the algorithm.

Secrets: no credentials in code, config, or tests committed to the repo. No secrets printed in logs or error messages.

Logging and errors: logs must not contain passwords, tokens, or full PII. Error responses must be generic to the client and detailed only in server logs.

## Phase 5: Writing actionable findings

Every finding needs five parts. If you cannot fill in the fix, you have not understood the bug well enough.

Severity rubric:

| Severity | Meaning | Example |
|---|---|---|
| Critical | Remote code execution, auth bypass, mass data exposure | SQL injection on login, command injection, hardcoded admin creds |
| High | Serious but needs more conditions | Stored XSS, SSRF to internal metadata, private key in repo |
| Medium | Real issue, limited impact or needs user interaction | Reflected XSS needing a click, verbose errors leaking paths |
| Low | Hardening, defense in depth | Missing security headers, weak but non-critical crypto |
| Info | Suggestion, no security impact | Naming, dead code, test coverage |

Finding template:

```text
[High] SQL injection in report search (CWE-89)
File: app/reports.py:42
What: the `name` query parameter is concatenated into a SQL string.
Impact: an attacker can read or modify any table the app user can access.
Proof: GET /report?name=' OR '1'='1 returns all reports.
Fix: use a parameterized query: cur.execute("SELECT * FROM reports WHERE name = ?", (name,)).
```

Rules: one finding per issue, no duplicates. Link the CWE. Propose the fix as code, not as advice. Separate security findings from style nits so the author sees what blocks the merge.

## Phase 6: Fix verification

Re-review the fix diff, not the author's word that it is fixed. Confirm the sink now uses the safe API. Confirm a regression test was added that fails on the old code and passes on the new code. If the fix only narrows the issue (for example, escaping instead of parameterization), say so and keep the finding open at a lower severity.

## Edge cases

- Huge diffs: review commit by commit, or send back with a size limit. Rubber-stamping a 3,000-line PR is worse than not reviewing it.
- Generated code: mark generated directories and skip them in sweeps (`rg --glob '!migrations/**'`).
- Vendored third-party code: do not line-review it. Check the version, check it is maintained, check known CVEs.
- Analyzer false positives: rule out in one line, citing why the sink is unreachable (for example, "input is an integer parsed with int() before use").
- "It is only internal": internal today, exposed tomorrow. Flag it at a lower severity, not zero.
- Time pressure: never skip the auth and input-handling files. Skim UI text changes instead.

## Escalation

- The diff is too large to review well: send it back and ask the author to split it. Suggest a split order.
- You cannot decide exploitability: write the smallest proof of concept that reaches the sink. If it works, it is a finding. If you cannot make it work after a focused attempt, record it as a hardening note.
- A security fix conflicts with a deadline: do not silently accept the risk. Write a risk acceptance with an owner and an expiry date, and track it.
- The code needs domain expertise you lack (custom crypto, auth protocols): request a second reviewer from that area instead of guessing.

## Detection and defender view

For engineering skills this section covers detecting review misuse and review-process misconfiguration.

- Rubber-stamp approvals: detect with metrics. Median time from PR open to approval under a few minutes on large diffs, or zero findings across dozens of PRs, signals review theater.
- Missing gates: no required reviews on the main branch, no CODEOWNERS for auth, crypto, and infrastructure paths, static analysis running but not blocking merges, force-push allowed on protected branches.
- Fix the process: require at least one reviewer, add CODEOWNERS entries for security-sensitive paths, make analyzer results block the merge, and track mean time to fix for security findings the way you track incidents.

## Key references

- CWE-78 OS Command Injection, CWE-79 Cross-site Scripting, CWE-89 SQL Injection, CWE-95 Eval Injection, CWE-502 Deserialization of Untrusted Data, CWE-611 XXE, CWE-798 Hardcoded Credentials, CWE-918 Server-Side Request Forgery, CWE-1321 Prototype Pollution (cwe.mitre.org)
- OWASP Code Review Guide (owasp.org/www-project-code-review-guide)
- git diff documentation (git-scm.com/docs/git-diff)
- ripgrep user guide (github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)
