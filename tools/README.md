# Operator Tools

Small, single-purpose Python CLI tools for operators. Every tool uses the
Python standard library only, no third-party packages. Each tool accepts
`--help` with a description and usage examples, exits 0 on success, and
exits 2 on usage errors.

Usage:

    python3 tools/<tool-name>/<tool-name>.py --help

For example:

    python3 tools/port-scanner/port-scanner.py scanme.example.com -p 1-1024
    python3 tools/file-hasher/file-hasher.py document.pdf

| Tool | What it does |
| ---- | ------------ |
| port-scanner | TCP connect scan of a host for open ports (scan only what you may test) |
| banner-grabber | Connect to a TCP port and read the service banner |
| hash-identifier | Guess a hash type from its format (never cracks it) |
| subnet-calculator | Show network, broadcast, mask, and host range for a CIDR |
| password-generator | Generate random passwords with the secrets module |
| base64-codec | Encode text to base64 or decode base64 to text |
| hex-codec | Encode text to hex, decode hex, or hex-dump a file |
| log-grep-analyzer | Search a log with regex and summarize the matches |
| json-formatter | Pretty-print, minify, and validate JSON |
| url-encoder | URL-encode, URL-decode, or parse a query string |
| jwt-decoder | Decode a JWT header and payload (does NOT verify the signature) |
| dns-resolver | Resolve A/AAAA records or do a reverse lookup with the system resolver |
| http-header-checker | Fetch a URL and report response headers plus a security checklist |
| ssl-cert-checker | Show the TLS certificate of a host: subject, issuer, dates, SANs |
| file-hasher | Hash files with MD5, SHA-1, and SHA-256 using chunked reads |
| string-extractor | Pull printable strings out of a binary file (a simple strings clone) |
| cron-explainer | Explain a five-field cron schedule in plain English |
| regex-tester | Test a regex against text and show matches and named groups |
| caesar-cipher | Encode, decode, or brute-force the Caesar letter-shift cipher |
| rot13-codec | Apply ROT13 to text (encoding and decoding are the same) |
| morse-codec | Encode text to Morse code or decode Morse code to text |
| uuid-generator | Generate UUIDs (versions 1, 3, 4, 5) |
| timestamp-converter | Convert Unix timestamps to dates and dates to timestamps |
| entropy-checker | Measure Shannon entropy of text or a file in bits per byte |
| csv-column-extractor | Extract CSV columns by name or index, with dedupe and counts |
| cidr-merger | Collapse overlapping or adjacent CIDR ranges into the minimal set |
| port-list-expander | Expand a port spec like 80,443,8000-8005 into a full list |
| http-status-lookup | Look up the meaning of HTTP status codes |
| unicode-inspector | Show codepoint, name, category, and UTF-8 bytes per character |
| checksum-verifier | Verify a file against an expected checksum (auto-detects the algo) |
| diceware-generator | Build a passphrase from random words with the secrets module |
| totp-generator | Generate or verify TOTP codes (RFC 6238) from a base32 secret |
| email-header-analyzer | Parse email headers: addresses, Received hops, spoofing signs |
| iban-validator | Validate IBANs with a format check and the mod-97 checksum |
| luhn-checker | Validate numbers with the Luhn checksum or compute a check digit |
| semver-compare | Compare semantic versions and test simple version ranges |
| crontab-validator | Validate crontab files: time fields, @specials, and commands |
| markdown-toc | Generate a table of contents from Markdown headings |
| wordlist-mutator | Mutate wordlist entries: case, leet, years, symbols, numbers |
| url-parser | Break a URL into parts and flag suspicious traits |
| phone-parser-basic | Normalize and inspect a phone number (basic heuristic parser) |
| color-converter | Convert a color between HEX, RGB, and HSL |
| unit-converter | Convert length, mass, temperature, data size, and time units |
| random-sample-picker | Pick N random items from a list, with or without replacement |
| text-stats | Count lines, words, characters, and top words in text |
| diff-word | Show a word-level diff of two text files |
