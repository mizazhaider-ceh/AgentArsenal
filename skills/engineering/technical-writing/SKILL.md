---
name: technical-writing
description: "Use when writing documentation people actually read: planning a doc for its audience, structuring tutorials, how-to guides, reference, and explanations (Diataxis), writing clear plain-English procedures with verifiable steps, documenting APIs and CLIs, reviewing docs for accuracy, linting prose with Vale and pandoc 3.4, or turning rough notes into a polished README or runbook. Use when the task mentions documentation, README, runbook, API docs, style guide, or editing technical prose."
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [git-workflows]
tools:
  - name: pandoc
    version: 3.4
  - name: Vale
    version: 3.9
---
Technical writing is engineering with words: the doc is a product with
users, requirements, and bugs. Good docs get read because they respect the
reader's goal; bad docs get skimmed because they serve the writer's ego.
This skill covers writing docs that work: audience analysis, the Diataxis
structure (tutorial, how-to, reference, explanation), plain-language style,
verifiable procedures, API and CLI documentation, review and linting with
Vale and pandoc, and keeping docs alive in version control.

## Quick Workflow

1. Name the reader and their goal in one sentence before writing a word.
2. Pick the doc type: tutorial (learning), how-to (task), reference
   (lookup), explanation (understanding). One doc, one type.
3. Outline with the reader's questions, not the system's components.
4. Draft fast in plain language; short sentences, verbs up front.
5. Make every procedure verifiable: each step ends with how to confirm
   it worked.
6. Add examples that run: copy-pasteable commands with expected output.
7. Review for accuracy by following the doc yourself on a clean machine.
8. Lint the prose (Vale) and build the output (pandoc); fix what they
   flag.
9. Keep the doc next to the code, reviewed in the same pull request.

## 1. Know the reader

```text
Bad:  "This document describes the backup system."
Good: "After this guide, you can restore the database from last night's
       backup in under 10 minutes."
```

Write the reader contract at the top of every doc:

```markdown
# Restoring the database

**For:** on-call engineers. **You need:** SSH access to db-1, the backup
bucket credentials. **Time:** 10 minutes. **Result:** a running database
with last night's data.
```

If you cannot fill in those four lines, you do not know the reader yet.

## 2. Diataxis: the four doc types

| Type | Goal | Reader question | Shape |
|---|---|---|---|
| Tutorial | Learning | "Teach me" | Lesson with guaranteed outcome |
| How-to guide | Task | "How do I...?" | Steps to a goal |
| Reference | Lookup | "What does X do?" | Dry, complete, structured |
| Explanation | Understanding | "Why is it like this?" | Concept discussion |

```bash
# Docs layout that mirrors the four types
mkdir -p docs/{tutorials,how-to,reference,explanation}
ls docs/
```

Rules: never mix types in one page (a tutorial that detours into
reference material loses the learner); link between them instead.
Tutorials must work end to end or they teach distrust; how-tos assume
competence and skip teaching; reference must be complete, not chatty;
explanations give the why behind the what.

## 3. Procedures that verify themselves

Every step: imperative verb first, exact command or click path, then the
check.

```markdown
## Rotate the API key

1. Generate a new key (keep the old one active for now):
   `vault write -f auth/approle/role/api/secret-id`
   You should see: a JSON block with `secret_id` and `secret_id_ttl`.

2. Deploy the new key to the app servers:
   `ansible-playbook rotate-key.yml`
   You should see: `PLAY RECAP ... failed=0` for all hosts.

3. Confirm the app serves traffic with the new key:
   `curl -H "Authorization: Bearer $NEW_KEY" https://api.example.com/v1/health`
   You should see: `HTTP 200` and `{"status":"ok"}`.

4. Revoke the old key only after step 3 passes on every host.
```

Anti-patterns: steps without checks ("configure the thing"), screenshots
of text that should be copyable, "simply" and "just" (if it were simple
the reader would not be reading), and pronouns without antecedents.

## 4. Style: plain, direct, scannable

```text
Prefer:  "Restart the service. Confirm it is active."
Avoid:   "The service should then be restarted by the operator, at which
          point its active status can be confirmed."

Prefer:  "The backup fails if the disk is full."
Avoid:   "In the event of insufficient disk capacity, backup failure may
          occur."
```

House rules that fix 80 percent of bad prose:

- One idea per sentence; average under 20 words.
- Active voice, present tense, second person ("you").
- Headings are the table of contents; make them task-shaped ("Rotate
  the API key", not "Key rotation considerations").
- Lists for anything with more than two items; tables for comparisons.
- Define jargon on first use, then use it consistently (pick one term
  per concept: "key", not "key/token/secret" at random).
- Numbers, versions, and commands are exact; never "the latest" or
  "recently".

## 5. Documenting APIs and CLIs

For each endpoint or command: purpose in one line, exact syntax,
parameters with types and defaults, one real example with real-looking
output, and the error cases.

````markdown
## `GET /v1/users/{id}`

Returns one user. Requires the `users:read` scope.

**Example:**

```bash
curl -s https://api.example.com/v1/users/42 \
  -H "Authorization: Bearer $TOKEN"
```

```json
{ "data": { "id": 42, "name": "Izaz", "role": "student" } }
```

**Errors:** `401` bad token, `403` missing scope, `404` unknown id.
````

For CLIs, document `--help` output as the contract and test it:

```bash
# The help text IS documentation; keep it accurate
mytool deploy --help
# Every flag in --help appears in the docs, and vice versa
diff <(mytool deploy --help) <(sed -n '/## deploy/,/^## /p' docs/reference/cli.md)
```

## 6. Review: the accuracy pass

Docs rot. The review that matters is not copy-editing, it is execution:

```bash
# Follow your own doc on a clean machine or container and fix every
# step that lies, assumes, or skips
docker run --rm -it ubuntu:24.04 bash
# ... perform the procedure exactly as written ...
```

Review checklist: every command runs as written; expected outputs match
reality; prerequisites are listed and sufficient; links resolve;
versions mentioned still exist; screenshots match the current UI;
"you should see" checks actually appear. Assign every doc an owner and
a review date; undated docs are assumed stale.

## 7. Linting prose with Vale and building with pandoc

```bash
# Vale: prose linter with a style guide (install from GitHub releases)
vale --version
vale docs/how-to/restore-database.md

# Example .vale.ini enforcing plain language
cat > .vale.ini <<'EOF'
StylesPath = styles
MinAlertLevel = suggestion
[*.md]
BasedOnStyles = write-good, Vale
EOF
```

```bash
# pandoc: build one source into HTML and PDF
pandoc docs/how-to/restore-database.md \
  -o /tmp/restore-database.html --standalone --toc
pandoc docs/how-to/restore-database.md \
  -o /tmp/restore-database.pdf --pdf-engine=xelatex

# Check for common doc bugs mechanically
grep -rn "TODO\|FIXME\|XXX" docs/ | head          # unfinished sections
grep -rn "http://" docs/ | grep -v localhost     # insecure links
```

Vale catches passive voice, weasel words, and overlong sentences; it
does not catch lies, so the execution review in section 6 stays
mandatory.

## 8. READMEs that work

```markdown
# Project name

One paragraph: what it does and who it is for.

## Quick start (under 5 minutes, copy-paste)

## Installation

## Usage (the 3 most common tasks)

## Configuration

## Troubleshooting (the 5 errors everyone hits)

## Contributing / License
```

README rules: quick start first, never marketing fluff; every claim
links to the doc that proves it; badges only for signals that matter
(build status, not vanity). A README longer than two screens needs the
docs/ directory treatment.

## 9. Keeping docs alive

```bash
# Docs live next to the code and ship in the same PR
git log --oneline -5 -- docs/how-to/restore-database.md

# Find docs nobody updated in a year (staleness candidates)
find docs -name '*.md' -mtime +365 | head -20

# Link check in CI (example with lychee)
lychee --no-progress docs/**/*.md
```

Process rules: doc changes ride with code changes in the same PR;
"docs later" means docs never; every incident postmortem asks "what
doc would have prevented this"; changelogs note behavior changes so
docs authors know what to update.

## Edge cases

- The procedure works for you but not the reader: you have tribal
  knowledge (env vars, VPN, permissions); list every prerequisite
  explicitly, including the embarrassing ones.
- Screenshots rot fastest: prefer text commands and outputs; screenshot
  only UI that cannot be described in words, and date-stamp them.
- Translating docs: write translation-friendly source first (short
  sentences, no idioms, no jokes); machine translation of idiomatic
  prose is where meaning dies.
- API docs vs code drift: generate reference from the OpenAPI spec or
  docstrings in CI; hand-written reference rots within months.
- Too many audiences in one doc: split it; a doc for beginners and
  experts serves neither.

## Escalation

- Nobody reads the docs: the doc answers the wrong question; interview
  two readers about what they actually needed and restructure around
  that.
- Docs are accurate but unused: discoverability problem; link from the
  README, the error messages, and the places people get stuck.
- Reviewers rubber-stamp doc PRs: require the execution check (section
  6) as a merge requirement for how-to guides.
- Conflicting docs: designate one source of truth per topic and delete
  or redirect the duplicates; two truths is zero truths.

## Detection and defender view

Docs are a security surface: they leak architecture, credentials in
examples, and internal hostnames. Detect misuse and misconfig with:

```bash
# Secrets pasted into docs and examples (the classic leak)
grep -rnE 'AKIA[0-9A-Z]{16}|ghp_[0-9A-Za-z]{36}|password\s*=\s*["'\''][^"'\'']+' \
  docs/ README.md | head

# Internal hostnames or IPs in public docs
grep -rnE '10\.[0-9]+\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+|\.internal\b' \
  docs/ | head

# Example tokens that look real enough to try
grep -rn 'Bearer ey' docs/ | head
```

Defensive rules: examples use obviously fake values (`example.com`,
`AKIAIOSFODNN7EXAMPLE`), never real credentials even redacted-looking
ones; keep internal runbooks in the private repo and public docs in the
public one; scan docs in CI with a secret scanner; treat a leaked
credential in docs as a rotation event, not an edit.

## Key references

- Diataxis framework: https://diataxis.fr/
- Google developer documentation style guide:
  https://developers.google.com/style
- Vale 3.9 docs: https://vale.sh/docs/
- pandoc 3.4 manual: https://pandoc.org/MANUAL.html
- "Docs for Developers" (Wilson): engineering-focused writing guide.
- CWE-200 (Exposure of Sensitive Information): secrets in docs.
- CWE-532 (Insertion of Sensitive Information into Log File): the same
  habit in examples and logs.
