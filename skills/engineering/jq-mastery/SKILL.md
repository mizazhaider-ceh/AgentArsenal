---
name: jq-mastery
description: Use when processing JSON on the command line with jq 1.7.1:
  selecting and filtering fields, transforming API responses, building JSON
  objects, aggregating with map/select/reduce, converting JSON to CSV or
  TSV, handling raw text input with slurp mode, parsing logs that contain
  JSON, or debugging why a filter returns null. Use when the task mentions
  jq, JSON filtering, API response parsing, or reshaping JSON data in
  shell pipelines.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [bash-advanced, python-cli-tooling]
tools:
  - name: jq
    version: 1.7.1
---

jq is sed for JSON: a small language of filters that select, transform,
and reshape JSON in pipelines. The mental model is a pipeline of filters
where `.` is the current input, `|` feeds one filter into the next, and
every filter produces a stream of values. This skill covers jq 1.7.1 from
field selection to reduce, real API and log recipes, output formats, and
the quoting and null-handling traps.

## Quick Workflow

1. Pretty-print first (`jq .`) to see the shape of the data.
2. Select fields with `.field` and `.field.nested`; use `.[]` to
   iterate arrays.
3. Filter with `select(...)`, transform with `map(...)`.
4. Build new objects with `{key: .path}` syntax.
5. Aggregate with `group_by`, `unique`, `length`, `add`, `reduce`.
6. Choose the output: raw strings (`-r`), CSV (`@csv`), TSV (`@tsv`).
7. Handle missing fields with `?`, `//`, and `try/catch`.
8. Test the filter against a saved sample before wiring it into a
   script.

## 1. Selection basics

```bash
# Pretty-print (your first move on any unknown JSON)
curl -s https://api.example.com/v1/users/42 | jq .

# Field access, nested access
echo '{"user":{"name":"Izaz","tags":["a","b"]}}' | jq '.user.name'
echo '{"user":{"name":"Izaz","tags":["a","b"]}}' | jq '.user.tags[0]'

# Iterate an array: one output per element
echo '{"users":[{"n":"a"},{"n":"b"}]}' | jq '.users[].n'

# Optional access: null instead of an error on missing keys
echo '{"a":1}' | jq '.b.c?'

# Keys with dashes or spaces need brackets
echo '{"x-y": 5}' | jq '."x-y"'
echo '{"a":1}' | jq '.["a"]'

# All keys / values of an object
echo '{"a":1,"b":2}' | jq 'keys'
echo '{"a":1,"b":2}' | jq 'to_entries[] | "\(.key)=\(.value)"'
```

## 2. Filtering with select

```bash
# Keep array elements matching a condition
echo '[{"n":"a","ok":true},{"n":"b","ok":false}]' \
  | jq '[.[] | select(.ok == true)]'

# String matching: contains, startswith, test (regex)
curl -s https://api.example.com/v1/users | jq \
  '[.data[] | select(.name | test("izaz"; "i"))]'

# Numeric comparisons and compound conditions
echo '[{"p":5},{"p":15},{"p":25}]' | jq \
  '[.[] | select(.p > 10 and .p < 30)]'

# Filter objects by key existence
echo '[{"a":1},{"b":2}]' | jq '[.[] | select(has("a"))]'
```

## 3. Transforming: map and object construction

```bash
# map over an array, build a new shape
curl -s https://api.example.com/v1/users | jq \
  '[.data[] | {id, name, email: .contact.email}]'

# Rename and compute fields
echo '{"price":100,"qty":3}' | jq '{total: (.price * .qty), currency: "EUR"}'

# String interpolation
echo '{"name":"Izaz","role":"student"}' | jq -r '"\(.name) is a \(.role)"'

# Flatten nested arrays, then reshape
echo '{"groups":[{"members":["a","b"]},{"members":["c"]}]}' | jq \
  '[.groups[].members[]]'

# Split and join strings
echo '{"csv":"a,b,c"}' | jq '.csv | split(",")'
echo '["a","b"]' | jq 'join("; ")'
```

## 4. Aggregation

```bash
# Count, sum, group
echo '[1,2,3,4]' | jq 'add'          # 10
echo '[1,2,3,4]' | jq 'length'      # 4

# Group log entries by level and count
cat app.jsonl | jq -s 'group_by(.level) | map({level: .[0].level, count: length})'

# Unique sorted values
echo '["b","a","b"]' | jq 'unique'

# reduce: the general aggregator (sum of totals here)
echo '[{"t":5},{"t":7}]' | jq 'reduce .[] as $x (0; . + $x.t)'

# Max by a field
echo '[{"n":"a","s":3},{"n":"b","s":9}]' | jq 'max_by(.s).n'
```

## 5. Output formats

```bash
# Raw strings: no JSON quotes (essential for shell variables)
echo '{"token":"abc123"}' | jq -r '.token'
TOKEN=$(curl -s https://api.example.com/auth | jq -r '.token')

# TSV for awk/cut pipelines
curl -s https://api.example.com/v1/users | jq -r \
  '.data[] | [.id, .name, .email] | @tsv' | cut -f1,2

# CSV with headers
curl -s https://api.example.com/v1/users | jq -r \
  '["id","name","email"], (.data[] | [.id, .name, .email]) | @csv'

# Compact single-line output for logs
cat app.jsonl | jq -c '{t: .time, lvl: .level, msg: .msg}'

# Colored pretty output even when piped
jq -C . file.json | less -R
```

## 6. Input modes: slurp, raw, null

```bash
# Slurp: read a JSONL stream into one array
cat app.jsonl | jq -s 'length'

# Raw input: process plain text lines as strings
printf 'a\nb\n' | jq -R '{line: .}'

# Split raw lines into fields
printf 'izaz:admin\nbob:user\n' | jq -R 'split(":") | {user: .[0], role: .[1]}'

# Null input: generate JSON from scratch (with --arg values)
jq -n --arg name "Izaz" --argjson age 25 \
  '{user: $name, age: $age, created: now | strftime("%Y-%m-%d")}'

# Read a file into a variable
jq --slurpfile users users.json -n '$users[0] | length'
```

## 7. Real-world recipes

```bash
# GitHub API: repo names and stars, sorted
curl -s 'https://api.github.com/users/mizazhaider-ceh/repos?per_page=100' | jq -r \
  'sort_by(-.stargazers_count) | .[] | "\(.stargazers_count)\t\(.name)"' | head

# journalctl JSON: error messages in the last hour
journalctl -o json --since "1 hour ago" | jq -r \
  'select(.PRIORITY | tonumber <= 3) | "\(.SYSLOG_IDENTIFIER): \(.MESSAGE)"' | head -20

# AWS-style: instance ids of running instances
aws ec2 describe-instances | jq -r \
  '.Reservations[].Instances[] | select(.State.Name=="running") | .InstanceId'

# Kubernetes: pods not running, with node
kubectl get pods -A -o json | jq -r \
  '.items[] | select(.status.phase != "Running") | "\(.metadata.namespace)/\(.metadata.name) \(.status.phase)"'

# Package.json: list dependencies
jq -r '.dependencies // {} | to_entries[] | "\(.key)@\(.value)"' package.json

# Merge two JSON files (second wins on conflicts)
jq -s '.[0] * .[1]' base.json override.json

# Delete keys recursively (strip secrets before sharing)
jq 'walk(if type == "object" then del(.password, .token, .secret) else . end)' config.json
```

## 8. Nulls, errors, and debugging

```bash
# Default operator: replace null/missing with a fallback
echo '{"a":1}' | jq '.b // "missing"'

# Alternative operator //= assigns the fallback
echo '{"a":null}' | jq '.a //= "default"'

# try/catch around risky filters
echo '{"n":"x"}' | jq 'try (.n | tonumber) catch "not a number"'

# Debug: print intermediate values to stderr without breaking the pipe
echo '{"users":[{"n":"a"}]}' | jq '.users[] | debug | .n'

# Why null? Check the path exists step by step
echo '{"a":{"b":1}}' | jq '.a'        # {"b":1}
echo '{"a":{"b":1}}' | jq '.a.b'      # 1
echo '{"a":{"b":1}}' | jq '.a.c'      # null (key missing, not an error)
```

## Edge cases

- `jq '.[]'` on an object iterates its values; on null it errors;
  guard with `?` (`.[]?`) in heterogeneous data.
- Shell quoting: always single-quote the filter; double quotes let
  the shell eat `$` and backticks. Pass shell values with `--arg`,
  never by interpolating into the filter (injection risk).
- Large files: jq loads the whole input; for multi-GB JSONL use
  `--stream` or process line by line with `jq -c` per line.
- Numbers lose precision past 2^53 (IEEE double); use `--raw-output`
  string handling or Python for 64-bit ids.
- `empty` inside a pipe deletes the value silently; a filter that
  "returns nothing" usually has an `empty` or a failed `select`.
- Unicode: jq handles it correctly, but `length` counts codepoints;
  byte length needs `tostring | length` on the UTF-8 encoding via
  other tools.
- `test()` uses Oniguruma-ish regex; escape backslashes twice in
  shell single quotes is unnecessary, once is enough.

## Escalation

- Filter works on sample, fails in production: the real data has a
  different shape (null where you expected an object); dump one real
  record with `jq -c` and diff the structure.
- "Cannot index string with string": you are deeper than you think;
  print each level (`.a`, `.a.b`) to find where the shape changes.
- Performance on huge inputs: add `-c` and filter early
  (`select` before building objects), or switch to `--stream`.
- Need logic jq cannot express (joins across files, date math):
  `--slurpfile` covers small joins; beyond that use Python (see
  python-cli-tooling).
- Still stuck: `jq --help` lists every builtin; the manual's builtin
  index answers "does jq have X" in seconds.

## Detection and defender view

jq is the analyst's best friend and occasionally the attacker's: it
extracts secrets from JSON configs and API dumps just as easily as it
parses logs. Detect misuse with:

```bash
# jq reading sensitive files (history / process list review)
grep -h "jq" ~/.bash_history | grep -E 'id_rsa|shadow|secret|token' | head

# Pipelines exfiltrating parsed secrets
ps aux | grep -E 'jq.*token|curl.*jq.*secret' | grep -v grep
```

Defensive rules: never paste jq output containing secrets into chats,
tickets, or docs; use `walk(del(...))` to strip secrets before sharing
API dumps; prefer `--arg` over interpolation so values never land in
process lists via the filter string; and remember shell history stores
the whole pipeline including any embedded token, so use env vars and
`HISTCONTROL=ignorespace` for sensitive one-liners.

## Key references

- jq 1.7.1 manual: https://jqlang.github.io/jq/manual/
- jq tutorial: https://jqlang.github.io/jq/tutorial/
- JSONPath vs jq discussion in the manual's FAQ.
- CWE-20 (Improper Input Validation): parsing untrusted JSON without
  schema checks.
