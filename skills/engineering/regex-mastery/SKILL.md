---
name: regex-mastery
description: "Use when writing or debugging regular expressions: choosing between BRE, ERE, and PCRE flavors, crafting grep, sed, and awk patterns, using character classes, anchors, quantifiers, groups, backreferences, and lookarounds, extracting fields from logs with capture groups, validating inputs like IPs and emails, avoiding catastrophic backtracking, or testing patterns quickly with grep -P and Python re. Use when the task mentions regex, pattern matching, log parsing, text extraction, or sed/awk one-liners."
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [python-cli-tooling]
tools:
  - name: GNU grep
    version: 3.11
  - name: PCRE2
    version: 10.44
  - name: Python
    version: 3.12
---
Regular expressions are the shared language of text processing, but three
flavors with different metacharacters cause most of the pain: BRE (basic,
used by default grep and sed), ERE (extended, `grep -E` / `sed -E`), and
PCRE (Perl-compatible, `grep -P`, Python, most modern languages). This skill
covers writing correct patterns in each flavor, the building blocks from
character classes to lookarounds, practical extraction recipes, and the
performance traps that turn a pattern into a denial of service.

## Quick Workflow

1. Pick the flavor first: ERE for grep/sed/awk work, PCRE when you need
   lookarounds or non-greedy matching.
2. Anchor the pattern (`^`, `$`, `\b`) so it matches what you mean and
   runs fast.
3. Build from small pieces: character class, then quantifier, then group.
4. Test against both matching and non-matching samples before using it.
5. Prefer specific classes (`[0-9]`, `[A-Za-z]`) over `.` to avoid
   over-matching.
6. Capture with groups and reference them in replacements.
7. Check for nested quantifiers (`(a+)+`) that cause catastrophic
   backtracking; rewrite with atomic groups or possessive quantifiers in
   PCRE.
8. Document tricky patterns with a comment and example matches.

## 1. Know your flavor

```bash
# BRE (default grep/sed): ( ) { } need backslashes to be special
grep 'foo\(bar\)\+' file.txt        # BRE: matches foobar, foobarbar...

# ERE (grep -E, sed -E, awk): metacharacters work unescaped
grep -E 'foo(bar)+' file.txt
sed -E 's/foo(bar)+/X/' file.txt

# PCRE (grep -P): lookarounds, \d \w \s, non-greedy, atomic groups
grep -P 'foo(?=bar)' file.txt       # foo only when followed by bar
grep -P '\d{1,3}(\.\d{1,3}){3}' file.txt

# Which flavor is your tool? Test quickly:
echo "aab" | grep -E 'a+b'    # ERE ok
echo "aab" | grep -P 'a+?b'   # PCRE non-greedy ok
```

Rule of thumb: use `grep -E` for portable scripts (PCRE in grep is
experimental and absent on some systems); use PCRE in Python/Perl where it
is first-class.

## 2. Building blocks

```bash
# Character classes
grep -E '[0-9]+' file            # digits
grep -E '[A-Za-z_][A-Za-z0-9_]*' # identifier-like words
grep -E '[^0-9]' file            # NOT a digit (^ first = negation)

# Shorthand (PCRE / ERE with grep -P)
grep -P '\d+' file               # digits
grep -P '\w+' file               # word chars [A-Za-z0-9_]
grep -P '\s+' file               # whitespace

# Anchors: ^ start, $ end, \b word boundary
grep -E '^ERROR' app.log         # lines starting with ERROR
grep -E '\.log$' files.txt       # ending in .log
grep -w 'fail' app.log           # whole word only

# Quantifiers: * (0+), + (1+), ? (0/1), {n}, {n,}, {n,m}
grep -E 'colou?r' file           # color or colour
grep -E '[0-9]{4}-[0-9]{2}-[0-9]{2}' file   # YYYY-MM-DD

# Alternation and grouping
grep -E '^(INFO|WARN|ERROR):' app.log
grep -E '(ab){2,3}' file         # abab or ababab
```

Greedy vs non-greedy (PCRE): `.*` grabs as much as possible, `.*?` as
little as possible.

```bash
echo '<a>1</a><b>2</b>' | grep -oP '<.*>'    # <a>1</a><b>2</b> (greedy)
echo '<a>1</a><b>2</b>' | grep -oP '<.*?>'   # <a> then </a>... per tag
```

## 3. Capture groups and replacements

```bash
# sed -E: reorder date from DD/MM/YYYY to YYYY-MM-DD
echo "23/10/2026" | sed -E 's#([0-9]{2})/([0-9]{2})/([0-9]{4})#\3-\2-\1#'

# Extract key=value pairs, print value only
grep -oP '^token=\K.*' config.env        # \K drops the matched prefix

# awk with match() and capture groups (gawk)
echo "user=izaz id=42" | awk 'match($0, /id=([0-9]+)/, m) {print m[1]}'

# Python: named groups make extraction readable
```

```python
import re
log = '2026-10-23 07:12:01 ERROR db connection failed (retry 3)'
m = re.match(
    r'(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}:\d{2}) '
    r'(?P<level>[A-Z]+) (?P<msg>.*)', log)
print(m.groupdict())
# {'date': '2026-10-23', 'time': '07:12:01', 'level': 'ERROR',
#  'msg': 'db connection failed (retry 3)'}
```

## 4. Lookarounds (PCRE only)

Lookarounds assert context without consuming characters:

```bash
# Password with a digit somewhere ahead (validation)
echo "s3cret!" | grep -P '^(?=.*\d).{6,}$' && echo valid

# Find 'error' NOT preceded by 'no '
grep -oP '(?<!no )error' app.log

# Split camelCase: insert space before capitals not at start
echo "camelCaseWord" | grep -oP '(?<!^)(?=[A-Z])|.' | tr -d '\n'
# Simpler with sed:
echo "camelCaseWord" | sed -E 's/([a-z])([A-Z])/\1 \2/g'

# Match a quoted string, allowing escaped quotes inside
grep -oP '"(\\.|[^"\\])*"' code.js
```

## 5. Practical recipes

```bash
# IPv4 addresses (each octet 0-255, strict version)
grep -oP '\b(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}\b' net.log

# Quick-and-dirty IPv4 (fine for log grepping, not validation)
grep -oE '\b[0-9]{1,3}(\.[0-9]{1,3}){3}\b' net.log

# Email-ish (practical, not RFC-perfect)
grep -oiE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' mail.log

# HTTP status codes from an access log, count them
grep -oP '" \K[0-9]{3}(?= )' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# Top 10 client IPs
grep -oP '^\S+' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head

# Strip ANSI color codes from command output
sed -E 's/\x1b\[[0-9;]*m//g' colored.txt

# Validate a semantic version
echo "1.27.0" | grep -qP '^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$' && echo "semver ok"
```

Multiline matching in Python (log entries spanning lines):

```python
import re
text = open('/var/log/app.log').read()
# DOTALL lets . cross newlines; find tracebacks as one match
for tb in re.findall(r'Traceback \(most recent call last\):.*?(?=\n\S|\Z)',
                     text, re.DOTALL):
    print(tb[:200], '\n---')
```

## 6. Performance: catastrophic backtracking

Nested quantifiers make the engine try exponentially many paths:

```bash
# DANGEROUS: (a+)+ on a long string of a's with no match hangs
python3 -c "
import re, time
s = 'a' * 30 + '!'
t = time.time()
try:
    re.match(r'^(a+)+$', s)
except Exception as e:
    print(e)
print('took', round(time.time() - t, 2), 's')
"
```

Fixes: make the inner part specific, use atomic groups `(?>...)` or
possessive quantifiers `++` in PCRE, or anchor and simplify:

```bash
# PCRE atomic group: once a+ matches, never backtrack into it
grep -P '^(?>a+)$' file
# Or just write what you mean
grep -P '^a+$' file
```

Also: prefer `[^"]*` over `.*?` inside quotes (negated class cannot
backtrack across the delimiter), and put the most selective literal first
so the engine skips non-matching positions fast.

## Edge cases

- `.` does not match newline by default; use `[\s\S]` or DOTALL/`-z`
  for multiline.
- In BRE, `+` `?` `|` are literal unless escaped; in ERE they are
  special unless escaped. Mixing flavors is the number one bug source.
- `grep -P` may warn "PCRE support is experimental" or be missing on
  macOS/BSD grep; use `pcre2grep` or Python there.
- Character ranges like `[A-z]` include `[\]^_` between Z and a; always
  write `[A-Za-z]`.
- Locale affects `[a-z]` in some tools (it can match accented chars);
  set `LC_ALL=C` for byte-predictable matching in scripts.
- `$` in the shell: single-quote every pattern or the shell eats `$`,
  backticks, and `!` (history expansion).
- `sed` `&` in the replacement means "the whole match"; escape it as
  `\&` when you want a literal ampersand.

## Escalation

- Pattern matches too much: add anchors and replace `.` with negated
  classes; test against a corpus of must-not-match lines.
- Pattern matches nothing: build it up token by token, testing each
  addition; check flavor (BRE vs ERE) first.
- Works in a tester, fails in the script: quoting issue; echo the exact
  pattern the tool receives, or the shell mangled it.
- Too slow on big files: anchor to line start, use `grep -F` for literal
  pre-filtering before the regex stage, or switch to awk for
  field-based parsing (far faster than regex on structured logs).
- Still stuck: paste the pattern plus three sample lines (one match,
  two non-matches) into a PCRE debugger or Python with
  `re.DEBUG` to see how the engine parses it.

## Detection and defender view

Regex shows up defensively in input validation, WAF rules, and log
detection patterns, and offensively in ReDoS (a malicious input crafted to
hang a vulnerable pattern). Detect misuse and misconfig with:

```bash
# Find nested-quantifier patterns in code (ReDoS candidates)
grep -rnE '\(\.\+\)\+|\(\.\*\)\*|\(\[^\]]+\]\+\)\+' --include='*.py' src/ | head

# Test a suspect pattern against a hostile input with a timeout
timeout 3 python3 -c "import re; re.match(r'^(a+)+\$', 'a'*40+'!')" \
  && echo ok || echo "HANGS or too slow"
```

Defender rules: validate with allowlists (`^[a-z0-9-]+$`) instead of
blocklists, set regex timeouts where the engine supports them (Python
3.11+ has no built-in timeout; use `timeout` wrappers or the `regex`
module), prefer parsers over regex for nested formats (HTML, JSON),
and never let user input become part of a pattern without `re.escape`.

## Key references

- PCRE2 syntax: https://www.pcre.org/current/doc/html/pcre2pattern.html
- Python re module: https://docs.python.org/3/library/re.html
- GNU grep manual: https://www.gnu.org/software/grep/manual/
- GNU sed manual: https://www.gnu.org/software/sed/manual/sed.html
- OWASP Input Validation Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
- CWE-1333 (Inefficient Regular Expression Complexity): ReDoS.
- CWE-20 (Improper Input Validation): validation done with sloppy
  patterns.
