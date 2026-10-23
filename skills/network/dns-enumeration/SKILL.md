---
name: dns-enumeration
description: Use when enumerating DNS on authorized engagements, internal or
  external. Covers forward and reverse lookups, record harvesting (A, MX,
  TXT, SRV, NS, SOA), zone transfer (AXFR) attempts, DNSSEC NSEC zone
  walking, subdomain brute forcing with curated wordlists, and wildcard
  detection with dig, host, dnsrecon, and nmap. Use when the target owns a
  domain, when you need hostnames to feed port scanning, or when a
  misconfigured nameserver may leak the whole zone.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [recon-passive, recon-active]
tools:
  - name: BIND
    version: 9.20
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
---

DNS turns names into addresses, and misconfigured DNS turns one known domain
into a full map of the target's infrastructure. This skill covers authorized
DNS enumeration: identifying authoritative nameservers, harvesting records,
attempting zone transfers, walking DNSSEC-signed zones, brute forcing
subdomains, and doing reverse lookups over IP ranges. It pairs naturally with
recon-passive (which gathers names without touching the target) and feeds
host lists into recon-active and nmap-methodology. All testing targets
systems you have written permission to test.

## Quick Workflow

1. Identify the authoritative nameservers for the target domain.
2. Harvest all standard records (SOA, NS, MX, TXT, SRV) from a resolver.
3. Attempt a zone transfer (AXFR) against every authoritative server.
4. If the zone is DNSSEC signed, attempt NSEC zone walking.
5. Brute force subdomains with a curated wordlist, with wildcard detection.
6. Reverse lookup every in-scope IP range to find more names.
7. Merge all names into one de-duplicated host list for scanning.

## 1. Find the authoritative nameservers

Start from the domain and work down to the servers that actually hold the
zone. Query the authoritative servers directly later so cached or filtered
resolver answers do not mislead you.

```bash
# NS records and SOA (start of authority) for the domain
dig +short NS example.com
dig +short SOA example.com

# Full answer with the server that responded
dig NS example.com +noall +answer +comments

# Ask each authoritative server directly from here on
NS=$(dig +short NS example.com | head -1)
echo "Using authoritative server: $NS"
dig @$NS example.com SOA +short
```

```bash
# host and nslookup equivalents when dig is missing
host -t NS example.com
nslookup -type=SOA example.com
```

## 2. Harvest standard records

Pull every record type that commonly leaks infrastructure details. TXT
records often contain SPF data (which names mail servers), verification
tokens, and sometimes secrets someone pasted by accident.

```bash
# Common record types in one pass
for t in A AAAA MX TXT NS SOA SRV CAA; do
  echo "=== $t ==="
  dig +short $t example.com @$NS
done | tee /tmp/dns-records.txt

# SRV records reveal services: sip, xmpp, ldap, kerberos
dig +short SRV _sip._tcp.example.com @$NS
dig +short SRV _ldap._tcp.example.com @$NS
dig +short SRV _kerberos._tcp.example.com @$NS

# TXT records, one per line, check for pasted secrets
dig +short TXT example.com @$NS | tr ' ' '\n' | sort -u
```

```bash
# nmap DNS enumeration scripts as a cross-check
nmap --script dns-brute,dns-srv-enum -p 53 $NS
```

## 3. Attempt zone transfers (AXFR)

A zone transfer asks the nameserver for every record in the zone at once.
It is almost always denied, but when it works it hands you the entire
infrastructure map in one response, so always test it.

```bash
# Try AXFR against every authoritative nameserver
for ns in $(dig +short NS example.com); do
  echo "=== AXFR via $ns ==="
  dig AXFR example.com @$ns +noall +answer | head -40
done | tee /tmp/axfr.txt

# host syntax for the same test
host -l example.com $NS
```

A successful transfer prints dozens or hundreds of records. A refused one
prints `Transfer failed` or returns nothing. Test every NS host, because
administrators sometimes lock down the primary and forget a secondary.
Also try the transfer over TCP explicitly (AXFR only works over TCP, but
forcing it rules out UDP weirdness):

```bash
dig +tcp AXFR example.com @$NS +noall +answer | wc -l
```

If the transfer succeeds, parse it immediately into A records and hostnames
for the scanning phase.

```bash
# Extract hostnames and addresses from a successful transfer
grep -E '^[^ ;]' /tmp/axfr.txt | awk '{print $1, $NF}' | sort -u > /tmp/zone-hosts.txt
```

## 4. DNSSEC NSEC zone walking

DNSSEC-signed zones that use NSEC (not NSEC3) records can be walked: each
NSEC record names the next existing name in the zone, so you can enumerate
every name without brute force. NSEC3 uses hashes and resists this.

```bash
# Check whether the zone is signed and which NSEC flavor it uses
dig +short DNSKEY example.com @$NS | head -2
dig example.com @$NS +dnssec +noall +answer | grep -E 'NSEC3?PARAM|RRSIG'

# Walk the zone with nmap's dns-nsec-enum script
nmap --script dns-nsec-enum --script-args dns-nsec-enum.domains=example.com \
  -p 53 $NS -oN /tmp/nsec-walk.txt
```

If `dns-nsec-enum` is unavailable, walk manually: query a nonexistent name,
read the NSEC record in the authority section for the next name, query that
name, repeat. A small Python loop using only the standard library and raw
`dig` calls automates this:

```python
#!/usr/bin/env python3
"""Walk an NSEC-signed zone by following 'next name' pointers with dig."""
import subprocess, re

DOMAIN = "example.com"
NS = "ns1.example.com"  # authoritative server from step 1

def nsec_next(name):
    out = subprocess.run(
        ["dig", f"nonexistent-{name}.{DOMAIN}", f"@{NS}", "+noall", "+authority"],
        capture_output=True, text=True, timeout=10).stdout
    m = re.search(r"(\S+)\s+\d+\s+IN\s+NSEC\s+(\S+)", out)
    return m.group(2).rstrip(".") if m else None

seen, cur = set(), f"0.{DOMAIN}"
while True:
    nxt = nsec_next(cur)
    if not nxt or nxt in seen or not nxt.endswith(DOMAIN):
        break
    seen.add(nxt)
    print(nxt)
    cur = nxt.split(".")[0]
print(f"[*] walked {len(seen)} names")
```

## 5. Brute force subdomains

When AXFR and NSEC fail, brute force with a wordlist. The critical step is
wildcard detection: some domains answer every name with the same address,
which makes naive brute force report thousands of false positives.

```bash
# Wildcard check: query a random name that cannot exist
dig +short thisnamecannotexist12345.example.com @$NS

# If that returns an address, the zone is wildcarded. Note the wildcard IP:
WILD=$(dig +short thisnamecannotexist12345.example.com @$NS | head -1)
echo "Wildcard IP: $WILD"
```

```bash
# Brute force with dnsrecon, filtering the wildcard IP
dnsrecon -d example.com -t brt -D /usr/share/wordlists/dnsmap.txt \
  --wildcards -f | tee /tmp/dnsrecon-brt.txt

# nmap dns-brute as an alternative (slower, noisier)
nmap --script dns-brute --script-args dns-brute.domain=example.com \
  -p 53 $NS -oN /tmp/dns-brute.txt
```

Filter results against the wildcard IP before trusting them: any answer
matching the wildcard address is a false positive. Keep wordlists
curated (a few thousand entries beats a million-entry list that takes all
night and trips rate limits).

```bash
# Quick stdlib Python brute forcer with wildcard filtering
python3 - <<'EOF'
import subprocess
DOMAIN = "example.com"
NS = "ns1.example.com"
WILD = "93.184.216.34"  # from the wildcard check, or "" if none
words = [w.strip() for w in open("/usr/share/wordlists/dnsmap.txt")]
found = []
for w in words:
    try:
        out = subprocess.run(["dig", "+short", f"{w}.{DOMAIN}", f"@{NS}"],
                             capture_output=True, text=True, timeout=5).stdout
        ips = [l for l in out.splitlines() if l and not l.endswith(".")]
        ips = [ip for ip in ips if ip != WILD]
        if ips:
            found.append((w, ips)); print(f"{w}.{DOMAIN} -> {','.join(ips)}")
    except Exception:
        pass
print(f"[*] {len(found)} real subdomains")
EOF
```

## 6. Reverse lookups over IP ranges

PTR records map addresses back to names and often reveal naming conventions
(`vpn-01`, `mail-02`, `dc1`) that suggest more targets.

```bash
# Reverse lookup one address
dig +short -x 192.168.1.10 @$NS

# Sweep a /24 with nmap (fast, one query per host)
nmap -sn -PR --dns-servers $NS 192.168.1.0/24 -oG /tmp/rev.gnmap
grep -oP 'Host: \S+ \(\K[^)]+' /tmp/rev.gnmap | sort -u | tee /tmp/ptr-names.txt
```

```bash
# dnsrecon reverse sweep alternative
dnsrecon -d example.com -t rvl -r 192.168.1.0/24
```

## 7. Merge everything into a scan target list

Combine zone data, brute force hits, and PTR names into one clean list for
the scanning phase.

```bash
cat /tmp/zone-hosts.txt /tmp/dnsrecon-brt.txt /tmp/ptr-names.txt 2>/dev/null \
  | grep -oE '[a-z0-9.-]+\.example\.com' | sort -u > /tmp/targets.txt
wc -l /tmp/targets.txt && head -20 /tmp/targets.txt
```

Resolve every name to an address and drop anything outside the authorized
scope before scanning.

```bash
# Resolve and keep only in-scope addresses (example: 203.0.113.0/24)
while read -r h; do dig +short "$h" A @$NS; done < /tmp/targets.txt \
  | grep -E '^203\.0\.113\.' | sort -u > /tmp/inscope-ips.txt
```

## Edge cases

- The resolver rate limits you. Slow the brute force (add sleep between
  queries), split the wordlist, or ask the client for a dedicated resolver.
- Wildcard DNS poisons every result. Always run the wildcard check first
  and filter its IP; otherwise the whole brute force is garbage.
- Split horizon DNS: internal nameservers answer differently from external
  ones. Enumerate from the network position the scope describes, and note
  which view you tested.
- AXFR over UDP silently fails. AXFR requires TCP; use `+tcp` and test
  every authoritative server, including secondaries.
- NSEC3 zones resist walking. Fall back to brute force; do not waste time
  trying to reverse the hashes during the engagement.
- `dig` returns SERVFAIL for everything. The nameserver may block your IP
  or the domain may use DNS filtering. Try a different source address or
  confirm with the client that testing is expected.
- CNAME chains hide the real address. Follow them with `dig +short` until
  you reach A records, and record the full chain.
- Huge zones time out the transfer. Page through with `dig AXFR` and save
  raw output to a file instead of the terminal.

## Escalation

- Standard records are clean and AXFR is denied. Move to brute force with
  a larger wordlist and to certificate transparency logs via recon-passive
  for names the DNS servers will not give you.
- Brute force finds nothing new. Try common service prefixes manually
  (`vpn`, `owa`, `autodiscover`, `sip`, `test`, `dev`, `staging`) and
  check SRV records again for service-specific names.
- The target uses a DNS firewall that lies. Compare answers from the
  authoritative server, a public resolver, and the internal resolver; the
  differences themselves are findings.
- You suspect subdomain takeover on a dangling CNAME. That is a web finding;
  hand the CNAME target to the web team (see webapp-pentest-methodology).
- Reverse lookups reveal a naming convention. Generate candidates from the
  pattern (`db01`, `db02`, `db03`) and test them directly.

## Detection and defender view

Defenders see DNS enumeration as high volumes of NXDOMAIN responses from
one source (brute force), AXFR attempts in nameserver logs (almost always
malicious or audit related), and NSEC walking as sequential queries for
nonexistent names. DNS query logging at the resolver or passive DNS
sensors catch all of it. The durable fixes: deny zone transfers to
unauthorized clients (`allow-transfer { trusted; };` in BIND), prefer
NSEC3 over NSEC for signed zones, avoid wildcard records where possible,
keep TXT records free of secrets, and monitor for NXDOMAIN spikes. Rate
limiting at the authoritative server blunts brute force without breaking
legitimate use.

## Key references

- MITRE ATT&CK T1590.002 (Gather Victim Network Information, DNS):
  record harvesting and zone data.
- MITRE ATT&CK T1046 (Network Service Discovery): DNS-driven host
  discovery.
- CWE-200 (Exposure of Sensitive Information): zone data and TXT secrets.
- CWE-749 (Exposed Dangerous Method or Function): open AXFR.
- IETF RFC 1035 (DNS), RFC 5936 (AXFR), RFC 5155 (NSEC3).
- BIND 9 Administrator Reference: allow-transfer configuration.
- dnsrecon documentation: https://github.com/darkoperator/dnsrecon
- nmap dns NSE scripts: https://nmap.org/nsedoc/scripts/dns-brute.html
