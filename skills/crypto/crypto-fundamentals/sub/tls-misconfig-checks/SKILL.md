---
name: tls-misconfig-checks
description: Use when assessing TLS configuration on servers during an
  authorized engagement. Covers protocol versions, cipher suites,
  certificate validation, and common misconfigurations. Use when testing
  HTTPS endpoints, when the scope includes transport security, when
  reviewing certificate deployments, or when prioritizing TLS findings.
version: 1.0.0
domain: crypto
lifecycle: stable
last_verified: 2026-10-23
parent: crypto-fundamentals
requires: [crypto-fundamentals]
extends: []
relates: [reviewer-crypto-misuse, nmap-scripting]
tools:
  - name: OpenSSL
    version: 3.0
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
---

TLS misconfigurations expose traffic to decryption and tampering: old
protocols, weak ciphers, and broken certificates. This skill covers
checking TLS deployments on authorized engagements: what to test,
how to test it with standard tools, and how to rank the findings. It
is a configuration review done from the network; code-level TLS review
is reviewer-crypto-misuse.

## Quick Workflow

1. List every TLS endpoint in scope.
2. Check protocol versions: TLS 1.2 minimum, 1.3 preferred.
3. Check cipher suites: no NULL, RC4, 3DES, or weak DHE.
4. Validate the certificate chain, expiry, and hostname matching.
5. Test the classic attacks: downgrade, renegotiation, compression.
6. Rank findings by exploitability and write them up.

## 1. Protocols and ciphers

```bash
# Protocol support: try each version explicitly
for v in tls1 tls1_1 tls1_2 tls1_3; do
  echo -n "$v: "
  echo | timeout 5 openssl s_client -connect target.example:443 -$v \
    2>/dev/null | grep -c 'Protocol' || echo "not supported / failed"
done
# Finding: tls1 or tls1_1 accepted

# Cipher enumeration with nmap (fast, structured)
nmap --script ssl-enum-ciphers -p443 target.example -oN /tmp/ciphers.txt
grep -E 'TLSv|SSLv' /tmp/ciphers.txt | head -20

# Flag on sight: RC4, 3DES, NULL, EXPORT, DES, MD5 MAC, anonymous DH
grep -i -E 'RC4|3DES|DES-CBC|NULL|EXPORT|anon' /tmp/ciphers.txt | head -10
```

TLS 1.0 and 1.1 accepted is a finding in every modern review; there is
no legitimate client left that needs them. Weak ciphers are the same:
the list above has no business being negotiable.

## 2. Certificate review

```bash
# Chain, expiry, subject, issuer in one command
echo | timeout 5 openssl s_client -connect target.example:443 \
  -servername target.example 2>/dev/null | openssl x509 -noout \
  -subject -issuer -dates -ext subjectAltName 2>/dev/null | head -20

# Expiry check across endpoints (alert threshold: 30 days)
echo | timeout 5 openssl s_client -connect target.example:443 2>/dev/null \
  | openssl x509 -noout -checkend 2592000
# exit 0 means valid for 30+ days; exit 1 means expiring soon

# Hostname matching: does the cert cover the name you connected to?
# Check subjectAltName for the exact hostname or a proper wildcard
```

Certificate findings that matter: expired, wrong hostname, self-signed
in production, SHA1 signatures, and chains that do not validate. A
cert expiring next week is an availability finding; a wrong-hostname
cert is a trust finding.

## 3. Classic attack checks

```bash
# Compression (CRIME): must be disabled
echo | timeout 5 openssl s_client -connect target.example:443 2>/dev/null \
  | grep -i 'compression:' | head -2
# Expect: Compression: NONE

# Renegotiation: secure renegotiation expected
# (openssl s_client -connect with -msg shows the extension)

# Heartbleed and friends are long dead on patched servers, but the
# nmap vuln scripts still check cheaply on legacy estates:
nmap --script ssl-heartbleed,ssl-poodle,ssl-ccs-injection \
  -p443 target.example -oN /tmp/tls_vuln.txt
```

These are quick wins on legacy estates and usually clean on modern
ones. Run them, note the negatives as positive assurance, and move on;
do not spend the engagement's hours here unless the estate is old.

## Edge cases

- The endpoint is behind a CDN or WAF. You are testing the edge's
  TLS, not the origin's; note the distinction and test the origin
  directly if in scope.
- STARTTLS services (SMTP, IMAP). Test with the protocol's STARTTLS
  command before the TLS handshake; misconfigurations hide there.
- Client certificates required. Note the mutual TLS as a positive;
  test what happens without the client cert (must fail closed).
- Many endpoints, little time. Script the checks across the endpoint
  list and review the consolidated output.

## Escalation

- A critical TLS finding on a production endpoint (expired cert,
  private key exposure): report through the fast channel; some TLS
  findings are outage-adjacent.
- The fleet needs the standard: propose the TLS baseline (1.2+,
  strong ciphers, HSTS) with the finding list as the gap analysis.
- You need continuous assurance: the check commands become the
  scheduled scan.

## Detection and defender view

For defenders, TLS posture is continuously scannable: run these checks
on a schedule and alert on regressions (new weak cipher, expiring
cert). Certificate transparency logs catch misissued certs. The
defender's baseline is the TLS standard document; every deviation is
either a finding or a documented exception with an expiry date.

## Key references

- CWE-327 (Use of a Broken or Risky Cryptographic Algorithm).
- CWE-295 (Improper Certificate Validation).
- NIST SP 800-52r2 (TLS configuration guidelines).
- Mozilla SSL configuration generator (baseline reference).
