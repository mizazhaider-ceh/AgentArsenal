# Command reference

Every command in this repo, with only flags that really exist
(verified against `--help` output). Run everything from the repo
root unless noted.

## install.sh

The sparse installer. Copies chosen skill folders into a platform's
skills directory, resolving `requires`/`extends` dependency chains
from `arsenal-manifest.json`. Backs up the target before touching
it.

### Flags

`--all`
: Install every skill in the manifest.
: `bash ./install.sh --all --dry-run`

`--category <name>`
: Install one domain (category). Lists available categories with `--list`.
: `bash ./install.sh --category web --dry-run`

`--list`
: Print domains with skill counts, then exit. No changes made.
: `bash ./install.sh --list`

`--version <skill@ver>`
: Install one skill at a pinned version. Fails on a version mismatch.
: `bash ./install.sh --version web-sqli@1.0.0 --dry-run`

`--target <dir>`
: Install target. Default: `~/.claude/skills/agent-arsenal`.
: `bash ./install.sh --category soc --target /tmp/my-skills`

`--dry-run`
: Print what would be copied, change nothing. Combine with any install mode.
: `bash ./install.sh --all --dry-run`

`--rollback`
: Restore the most recent backup of the target, then exit.
: `bash ./install.sh --rollback`

`--platform <name>`
: Set the install target for a platform's skills folder, e.g.
  `--platform opencode` targets
  `~/.config/opencode/skills/agent-arsenal`. Overrides `--target`.
  Combine with `--all`, `--category`, or `--version`. See
  [platforms/PLATFORM_SUPPORT.md](platforms/PLATFORM_SUPPORT.md) for
  the full table. `--platform aider` does not copy skills (Aider has
  no skills support); it prints an `AGENTS.md` pointer snippet.
: `bash ./install.sh --platform codex-cli --category recon --dry-run`

`--list-platforms`
: Print the supported platform table, then exit. No changes made.
: `bash ./install.sh --list-platforms`

`-h`, `--help`
: Print the flag summary, then exit.
: `bash ./install.sh --help`

No flags at all opens an interactive category picker.

### Common recipes

Install everything for OpenCode, for real:

```bash
bash ./install.sh --platform opencode --all
```

One domain for Claude Code, previewed first:

```bash
bash ./install.sh --platform claude-code --category incident --dry-run
bash ./install.sh --platform claude-code --category incident
```

One pinned skill into a custom folder:

```bash
bash ./install.sh --version nmap-methodology@1.0.0 --target ~/.agents/skills/agent-arsenal
```

## scripts/

CI and repo tooling. All stdlib-only Python 3.

### `scripts/validate.py`

Runs the full validation harness and exits non-zero on ANY failure:
frontmatter standard, naming rules, dependency resolution and
acyclicity, agent and brain bindings, playbook bindings, workflow
structure, manifest sha256 match, install.sh platform check, and a
repo-wide no-em-dash scan. Takes no flags.

```bash
python3 scripts/validate.py
```

### `scripts/score.py`

Grades every skill, agent, and brain 0 to 100 (merge requires 70+)
and writes `scores.json`. Takes no flags.

```bash
python3 scripts/score.py
```

### `scripts/new_skill.py`

Scaffolds `skills/<domain>/<skill-slug>/SKILL.md` with the
frontmatter template.

```
usage: new_skill.py [-h] [--name NAME] [--domain DOMAIN]
                    [--description DESCRIPTION] [--root ROOT]
```

```bash
python3 scripts/new_skill.py --name my-skill --domain web \
  --description "Use when testing web apps for ... (trigger-dense)"
```

### `scripts/derive_manifest.py`

Regenerates `arsenal-manifest.json` from the repo tree.

```
usage: derive_manifest.py [-h] [--check] [--json]
```

```bash
python3 scripts/derive_manifest.py --check   # fail if the manifest on disk differs
python3 scripts/derive_manifest.py --json    # print counters as JSON
```

### `scripts/gen_marketplace.py`

Builds the Claude Code marketplace manifest (`.claude-plugin/marketplace.json`).
Takes no flags.

```bash
python3 scripts/gen_marketplace.py
```

### `scripts/gen_readme_catalog.py`

Regenerates the skill catalog table in README.md from
`arsenal-manifest.json`. Takes no flags.

```bash
python3 scripts/gen_readme_catalog.py
```

### `scripts/generate_docs.py`

Builds the static docs site under `docs/` from the skills tree.

```
usage: generate_docs.py [-h] [--root ROOT]
```

```bash
python3 scripts/generate_docs.py
```

### `scripts/test_tools.py`

Compile-checks and `--help`-checks every tool in `tools/`.

```
usage: test_tools.py [-h] [--quiet]
```

```bash
python3 scripts/test_tools.py
python3 scripts/test_tools.py --quiet   # only failures and the summary
```

## tools/

One self-contained CLI per folder at `tools/<name>/<name>.py`.
Stdlib only, each accepts `--help` and exits 0 on success. Run
with `python3 tools/<name>/<name>.py ...` from the repo root.
Each entry shows the real usage line and one example taken from the
tool's own help text.
### `banner-grabber`

Grab the banner a TCP service sends when you connect. Only probe hosts you own or have permission to test.

```
banner-grabber.py [-h] [--probe PROBE] [--timeout TIMEOUT] host port
```

Example:

```bash
banner-grabber.py 192.168.1.10 22
```

### `base64-codec`

Encode text to base64 or decode base64 back to text.

```
base64-codec.py [-h] [--urlsafe] {encode,decode} [data]
```

Example:

```bash
base64-codec.py encode "hello world"
```

### `caesar-cipher`

Encode or decode text with the Caesar cipher (letter shift).

```
caesar-cipher.py [-h] [-s SHIFT] {encode,decode,brute} [text]
```

Example:

```bash
caesar-cipher.py encode "hello" --shift 3
```

### `checksum-verifier`

[--from-stdin]

```
checksum-verifier.py [-h] [--algo {md5,sha1,sha256,sha512}]
```

Example:

```bash
checksum-verifier.py file.iso 5d41402abc4b2a76b9719d911017c592
```

### `cidr-merger`

Collapse overlapping or adjacent CIDR ranges into the minimal set.

```
cidr-merger.py [-h] [--file FILE] [--count] [networks ...]
```

Example:

```bash
cidr-merger.py 192.168.1.0/24 192.168.2.0/24
```

### `color-converter`

Convert a color between HEX, RGB, and HSL.

```
color-converter.py [-h] [--no-preview] color
```

Example:

```bash
color-converter.py "#ff8800"
```

### `cron-explainer`

Explain a cron schedule (five fields) in plain English.

```
cron-explainer.py [-h] schedule
```

Example:

```bash
cron-explainer.py "*/15 * * * *"
```

### `crontab-validator`

Validate crontab files: time fields, @specials, and commands.

```
crontab-validator.py [-h] [--line LINE] [--stdin] [file]
```

Example:

```bash
crontab-validator.py mycron
```

### `csv-column-extractor`

[--no-header] [--unique] [--count] [--top TOP]

```
csv-column-extractor.py [-h] -c COLUMNS [--delimiter DELIMITER]
```

Example:

```bash
csv-column-extractor.py users.csv --columns name,email
```

### `diceware-generator`

[--wordlist WORDLIST] [--capitalize]

```
diceware-generator.py [-h] [-w WORDS] [--separator SEPARATOR]
```

Example:

```bash
diceware-generator.py
```

### `diff-word`

Word-level diff of two text files.

```
diff-word.py [-h] [--context CONTEXT] [--side-by-side] file_a file_b
```

Example:

```bash
diff-word.py old.txt new.txt
```

### `dns-resolver`

Resolve DNS records for a hostname or IP using the system resolver.

```
dns-resolver.py [-h] [--reverse] [--all] target
```

Example:

```bash
dns-resolver.py example.com
```

### `email-header-analyzer`

Parse email headers: addresses, dates, Received hops, spoofing signs.

```
email-header-analyzer.py [-h] [file]
```

Example:

```bash
email-header-analyzer.py message.eml
```

### `entropy-checker`

Measure Shannon entropy of text or a file (bits per byte).

```
entropy-checker.py [-h] [--file] [text]
```

Example:

```bash
entropy-checker.py "hello world"
```

### `file-hasher`

Compute MD5, SHA-1, and SHA-256 hashes for files (chunked reads).

```
file-hasher.py [-h] [--sha256-only] [--md5-only] files [files ...]
```

Example:

```bash
file-hasher.py document.pdf
```

### `hash-identifier`

Guess the type of a hash from its format. This only identifies the format, it does not crack the hash.

```
hash-identifier.py [-h] [hash]
```

Example:

```bash
hash-identifier.py 5d41402abc4b2a76b9719d911017c592
```

### `hex-codec`

Encode text to hex, decode hex to text, or hex-dump a file.

```
hex-codec.py [-h] [--upper] {encode,decode,dump} [data]
```

Example:

```bash
hex-codec.py encode "hello"
```

### `http-header-checker`

Fetch a URL and print its HTTP response headers plus a security-header checklist.

```
http-header-checker.py [-h] [--timeout TIMEOUT] [--no-checklist] url
```

Example:

```bash
http-header-checker.py https://example.com
```

### `http-status-lookup`

Look up the meaning of an HTTP status code.

```
http-status-lookup.py [-h] codes [codes ...]
```

Example:

```bash
http-status-lookup.py 404
```

### `iban-validator`

Validate IBANs: format check plus mod-97 checksum.

```
iban-validator.py [-h] ibans [ibans ...]
```

Example:

```bash
iban-validator.py DE89370400440532013000
```

### `json-formatter`

[source]

```
json-formatter.py [-h] [--indent INDENT] [--sort] [--compact] [--check]
```

Example:

```bash
json-formatter.py data.json
```

### `jwt-decoder`

Decode a JWT header and payload (decode only, no signature check).

```
jwt-decoder.py [-h] [--payload-only] [token]
```

Example:

```bash
jwt-decoder.py <token>
```

### `log-grep-analyzer`

[--context CONTEXT] [--no-lines] [--errors ERRORS]

```
log-grep-analyzer.py [-h] -p PATTERN [-i] [--top TOP]
```

Example:

```bash
log-grep-analyzer.py /var/log/auth.log -p "Failed password"
```

### `luhn-checker`

Validate numbers with the Luhn checksum (cards, IMEI, etc).

```
luhn-checker.py [-h] [--complete] numbers [numbers ...]
```

Example:

```bash
luhn-checker.py 4532015112830366
```

### `markdown-toc`

Generate a table of contents from Markdown headings.

```
markdown-toc.py [-h] [--min MIN] [--max MAX] [--insert] file
```

Example:

```bash
markdown-toc.py README.md
```

### `morse-codec`

Encode text to Morse code or decode Morse code to text.

```
morse-codec.py [-h] {encode,decode} [data]
```

Example:

```bash
morse-codec.py encode "HELLO WORLD"
```

### `password-generator`

[--no-upper] [--no-digits] [--no-symbols]

```
password-generator.py [-h] [-l LENGTH] [-n NUMBER] [--no-lower]
```

Example:

```bash
password-generator.py
```

### `phone-parser-basic`

Normalize and inspect a phone number (basic heuristic parser).

```
phone-parser-basic.py [-h] [--default-cc DEFAULT_CC] number
```

Example:

```bash
phone-parser-basic.py "+32 470 12 34 56"
```

### `port-list-expander`

Expand a port range spec (80,443,8000-8005) into a full port list.

```
port-list-expander.py [-h] [--compact] [--count-only] spec
```

Example:

```bash
port-list-expander.py "80,443,8000-8005"
```

### `port-scanner`

Scan a host for open TCP ports (connect scan). Only scan hosts you own or have permission to test.

```
port-scanner.py [-h] [-p PORTS] [-t TIMEOUT] [-w WORKERS] host
```

Example:

```bash
port-scanner.py scanme.example.com -p 1-1000
```

### `random-sample-picker`

[--seed SEED]

```
random-sample-picker.py [-h] [--file FILE] [-n NUMBER] [--replace]
```

Example:

```bash
random-sample-picker.py alice bob carol dave -n 2
```

### `regex-tester`

pattern [text]

```
regex-tester.py [-h] [--file] [-i] [--validate-only] [--findall]
```

Example:

```bash
regex-tester.py "^\\d{3}-\\d{4}$" "555-1234"
```

### `rot13-codec`

Apply ROT13 to text (encoding and decoding are identical).

```
rot13-codec.py [-h] [text]
```

Example:

```bash
rot13-codec.py "hello world"
```

### `semver-compare`

version [other]

```
semver-compare.py [-h] [--gte VERSION] [--satisfies RANGE]
```

Example:

```bash
semver-compare.py 1.2.3 1.10.0
```

### `ssl-cert-checker`

Show the TLS certificate details for a host (subject, issuer, dates, SANs, days left).

```
ssl-cert-checker.py [-h] [--timeout TIMEOUT] target
```

Example:

```bash
ssl-cert-checker.py example.com
```

### `string-extractor`

Extract printable strings from a binary file (a simple `strings` clone).

```
string-extractor.py [-h] [-n MIN_LENGTH] [--offset] [--wide] file
```

Example:

```bash
string-extractor.py firmware.bin
```

### `subnet-calculator`

Show subnet details for an IPv4 address in CIDR notation.

```
subnet-calculator.py [-h] [--binary] network
```

Example:

```bash
subnet-calculator.py 192.168.1.0/24
```

### `text-stats`

Text statistics: lines, words, chars, top words.

```
text-stats.py [-h] [--top TOP] [file]
```

Example:

```bash
text-stats.py essay.txt
```

### `timestamp-converter`

Convert Unix timestamps to dates and dates to Unix timestamps.

```
timestamp-converter.py [-h] value
```

Example:

```bash
timestamp-converter.py 1700000000
```

### `totp-generator`

[--algo {sha1,sha256,sha512}] [--issuer ISSUER]

```
totp-generator.py [-h] [--verify CODE] [--digits {6,8}] [--step STEP]
```

Example:

```bash
totp-generator.py JBSWY3DPEHPK3PXP
```

### `unicode-inspector`

Inspect Unicode characters: codepoint, name, category, UTF-8 bytes.

```
unicode-inspector.py [-h] [--confusables] [text]
```

Example:

```bash
unicode-inspector.py "café"
```

### `unit-converter`

Convert between units (length, mass, temperature, data, time).

```
unit-converter.py [-h] value from_unit to_unit
```

Example:

```bash
unit-converter.py 100 km mi
```

### `url-encoder`

URL-encode or URL-decode text, or parse a query string.

```
url-encoder.py [-h] [--plus] {encode,decode,parse} [data]
```

Example:

```bash
url-encoder.py encode "hello world & more"
```

### `url-parser`

Break a URL into its parts and flag suspicious traits.

```
url-parser.py [-h] [url]
```

Example:

```bash
url-parser.py "https://example.com/path?a=1&b=2#frag"
```

### `uuid-generator`

[--namespace {dns,oid,url,x500}] [--name NAME]

```
uuid-generator.py [-h] [-n NUMBER] [-v {1,3,4,5}]
```

Example:

```bash
uuid-generator.py
```

### `wordlist-mutator`

[--symbols] [--numbers] [--all]

```
wordlist-mutator.py [-h] [--word WORD] [--case] [--leet] [--years]
```

Example:

```bash
wordlist-mutator.py words.txt
```

### `memory-store`

A small SQLite memory store for agents: episodic (what happened), semantic (facts that stay true), procedural (how-to knowledge). Implements `memory/LIFECYCLE.md` (capture, consolidate, recall, forget) and `memory/HYGIENE.md` (dedup, redaction, TTL expiry, audit log). The database path comes from `MEMORY_STORE_DB`, defaulting to `~/.memory-store/memory.db`.

```
usage:
    memory-store.py store --kind episodic --agent NAME --text "..." [--confidence 0-1] [--ttl-days N] [--tags a,b]
    memory-store.py recall --query "..." [--kind K] [--limit N] [--agent NAME] [--tags a,b]
    memory-store.py consolidate [--dry-run]
    memory-store.py forget --id ID [--id ID ...] | --expired
    memory-store.py stats
```

Example:

```bash
python3 tools/memory-store/memory-store.py store --kind semantic --agent soc-analyst-agent --text "SSH brute force seen from 203.0.113.7" --tags ssh,brute-force
```

```bash
python3 tools/memory-store/memory-store.py recall --query "brute force" --limit 5
```
