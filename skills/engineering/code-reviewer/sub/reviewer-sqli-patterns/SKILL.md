---
name: reviewer-sqli-patterns
description: Use when reviewing code for SQL injection vulnerabilities.
  Covers spotting string-concatenated queries, verifying parameterized
  usage, ORM unsafe patterns, and stored procedure risks. Use when
  reviewing data access code, when auditing a new codebase, when the
  scanner flags a possible injection, or when teaching the team what SQLi
  looks like in code.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
parent: code-reviewer
requires: [code-reviewer]
extends: []
relates: [secure-coding, web-sqli]
tools:
  - name: Python
    version: 3.12
  - name: Bandit
    version: 1.7
---

Code review finds SQL injection before it ships: the reviewer reads the
data access code and checks that untrusted input never becomes query
syntax. This skill covers the review patterns: what vulnerable code
looks like in several languages, how to verify parameterization is real,
and the ORM and procedure edge cases reviewers miss. Review the sink,
not just the source.

## Quick Workflow

1. Find every place the code builds or runs SQL: search for query,
   execute, raw, and SQL keywords.
2. For each, trace whether any part of the query string comes from
   untrusted input.
3. Verify parameterization: placeholders used for VALUES, never for
   identifiers or keywords.
4. Check ORM raw query escapes and stored procedure construction.
5. Flag second-order flows: stored input used in later queries.
6. Write the finding with the file, line, and the safe pattern.

## 1. Vulnerable patterns by language

```python
# PYTHON: string formatting into SQL is the classic
cursor.execute("SELECT * FROM users WHERE name = '%s'" % username)  # VULN
cursor.execute(f"SELECT * FROM users WHERE name = '{username}'")     # VULN
cursor.execute("SELECT * FROM users WHERE name = %s", (username,))   # SAFE

# What to grep for in review:
# execute(.*%.*) | execute(f".*") | ".format(.*" near SQL
```

```javascript
// NODE: template literals and concatenation
db.query(`SELECT * FROM users WHERE id = ${req.params.id}`);  // VULN
db.query("SELECT * FROM users WHERE id = " + id);             // VULN
db.query("SELECT * FROM users WHERE id = ?", [id]);           // SAFE
```

```php
// PHP: the old world, still common
$result = mysqli_query($conn, "SELECT * FROM users WHERE id = " . $_GET['id']);  // VULN
$stmt = $conn->prepare("SELECT * FROM users WHERE id = ?");                     // SAFE
```

The review question is always the same: does any untrusted value become
part of the query TEXT. Placeholders keep values as values; everything
else is suspect until proven otherwise.

## 2. Parameterization done wrong

```python
# Placeholders do not cover everything: identifiers and keywords
# cannot be parameterized in most drivers
table = request.args["table"]
cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (user_id,))  # VULN: table is syntax

# Reviewer check: is the interpolated part a VALUE or SYNTAX?
# Values -> must be placeholders. Syntax (table/column names, ORDER BY
# direction) -> must be allow-listed, never raw input.

ALLOWED_TABLES = {"users", "orders"}
if table not in ALLOWED_TABLES:
    raise ValueError("bad table")
cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (user_id,))  # SAFE
```

Also check: placeholder style matches the driver (`%s` versus `?`
versus `:name`); mixing styles silently breaks parameterization in some
drivers. And stored procedures that build dynamic SQL inside are just
SQLi one layer down; read the procedure body.

## 3. ORM and query builder traps

```python
# Django: raw() and extra() are the escape hatches
User.objects.raw("SELECT * FROM users WHERE name = '%s'" % name)  # VULN
User.objects.filter(name=name)                                    # SAFE
User.objects.extra(where=["name = '%s'" % name])                  # VULN

# SQLAlchemy: text() with bound parameters is safe, f-strings are not
db.session.execute(text(f"SELECT * FROM users WHERE name='{n}'"))  # VULN
db.session.execute(text("SELECT * FROM users WHERE name=:n"), {"n": n})  # SAFE

# Reviewer grep list: raw(, extra(, text(, execute(, order_by( with input
```

ORMs are safe until the developer reaches for raw SQL "just this once."
Review every raw escape hatch as if it were handwritten SQL, because it
is.

## Edge cases

- The query is built in one file and executed in another. Trace across
  the call chain; the sink is where the finding lives, the builder is
  where the fix goes.
- Input is "validated" before the query. Validation is not
  parameterization; review the validation's strength separately and
  still require placeholders.
- Second-order: the value was safe at input, stored, and used in a
  query later. Follow stored data to its query uses, not just its input
  validation.
- The scanner flags a safe query. Verify by reading the code; scanners
  flag patterns, reviewers verify data flow. False positives get noted
  so the next review is faster.

## Escalation

- You find systemic string-built SQL: recommend the parameterized
  pattern once, list every instance, and propose the migration order
  (auth and user-input queries first).
- The team disputes the finding: demonstrate with the test input in a
  safe environment; a working proof ends the debate.
- The codebase needs continuous protection: add the SAST rule for
  string-formatted SQL to CI so the pattern cannot return.

## Detection and defender view

For defenders, code review is the cheapest SQLi defense: every hour of
review prevents incidents that cost weeks. Complement review with SAST
in CI (pattern matching for the vulnerable forms above) and DAST
against staging. The defender's metric is time from code written to
injection found; review moves it left of deployment, scanners move it
left of production.

## Key references

- CWE-89 (SQL Injection).
- OWASP SQL Injection Prevention Cheat Sheet.
- OWASP Code Review Guide: SQL injection sections.
