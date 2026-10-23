---
name: bugbounty-scope-recon-out-of-scope-avoidance
parent: bugbounty-scope-recon
description: Use when testing is underway on an in-scope bug bounty program and you need mechanical guarantees that no packet leaves the authorized scope. Covers enforcing the target list in scanners (exclusion flags), Burp target scope with out-of-scope dropping, pre-flight scope checks before active tools run, handling redirects and pivots that lead outside scope, and the honest disclosure procedure when you touch out-of-scope by accident. Authorized targets only.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-scope-recon]
extends: []
relates: [bugbounty-scope-recon-scope-boundary-mapping, bugbounty-scope-recon-asset-discovery, bug-bounty-workflow]
tools:
  - name: Burp Suite
    version: 2026.2
  - name: nmap
    version: 7.98
  - name: Python
    version: 3.12
  - name: ffuf
    version: 2.1
---

Out-of-scope avoidance is mechanical, not willpower. Memory fails during a long hunt; configuration does not. This sub-skill sets up the enforcement layer: exclusion lists in every scanner, Burp dropping out-of-scope traffic, pre-flight checks before active tools run, and rules for redirects and pivots that try to lead you outside. It also covers what to do when avoidance fails. Only test targets with an in-scope verdict.

## Quick Workflow

1. Build exclude.txt from the boundary mapping verdicts and keep it next to targets-in-scope.txt.
2. Pass the exclusion list to every scanner that supports one; verify the flag actually filters.
3. Configure Burp target scope from the in-scope list and enable dropping out-of-scope requests.
4. Add a pre-flight scope check script in front of ad-hoc active commands.
5. Define the redirect and pivot rule: never follow a lead from in-scope to out-of-scope.
6. Re-check scope on every program policy update; move newly excluded assets to exclude.txt immediately.
7. If out-of-scope gets touched anyway: stop, document, disclose honestly to the program.

## 1. Scanner-level exclusions

Every scanner gets the exclusion list. Verify the flag works with a dry run before the real run:

```bash
# nmap: exclude file (verify with --excludefile, test on one host first)
nmap -sV --top-ports 100 -T3 --excludefile exclude.txt -iL targets-in-scope.txt -oA nmap-scoped

# ffuf: single host from the in-scope list only, never a bare wordlist run
ffuf -u https://api.example.com/FUZZ -w wordlist.txt -mc 200,301,302,403 -o ffuf-api.json

# nuclei: run against the in-scope URL list, not a discovered-everywhere list
nuclei -l in-scope-urls.txt -t ~/nuclei-templates/http/misconfiguration/ -o nuclei.txt
```

The pattern: tools read from `targets-in-scope.txt` and exclude `exclude.txt`. Never point a scanner at a raw discovery file that has not been through boundary verdicts.

## 2. Burp target scope enforcement

In Burp Suite, define the target scope from your in-scope list, then turn on enforcement:

- Target > Scope: add each in-scope domain (use suffix match for `example.com` to cover subdomains) and each in-scope IP or range.
- Proxy > Options (or the equivalent in 2026.x): enable dropping or flagging out-of-scope requests so a stray click in the browser does not generate unauthorized traffic.
- Spider and Scanner: set to only crawl in-scope targets.

Test the enforcement: browse to an excluded host through the proxy and confirm the request is dropped or flagged before it leaves. A scope rule you never tested is a hope, not a control.

## 3. Pre-flight scope check script

For ad-hoc commands, a tiny check beats memory:

```bash
#!/usr/bin/env bash
# scope-check.sh: usage: scope-check.sh <target>
target="$1"
if grep -qxF "$target" targets-in-scope.txt; then
  echo "IN SCOPE: $target"
elif grep -qxF "$target" exclude.txt; then
  echo "OUT OF SCOPE: $target, refusing"; exit 1
else
  echo "NO VERDICT for $target, refusing (ask the program first)"; exit 1
fi
```

```bash
./scope-check.sh api.example.com && nmap -sV api.example.com
```

Anything without a verdict refuses. This is deliberately strict: the failure mode of strictness is a missed test, while the failure mode of laxity is a ban.

## 4. Redirects, pivots, and third-party boundaries

The two most common accidental crossings:

- Redirects: an in-scope app redirects to an out-of-scope domain (SSO provider, payment processor, partner site). Do not follow it with testing intent. Note the redirect and move on.
- Pivots: a finding on an in-scope host suggests an attack against a connected out-of-scope host (a database on a partner network, an internal host named in an error). The vulnerability does not transfer scope. Report what you found on the in-scope asset; do not pivot.

For SSRF testing specifically, this matters most: collaborator callbacks are fine, but directing the server at out-of-scope internal or partner addresses from an SSRF is still out-of-scope testing. Keep SSRF proof inside clearly authorized space (your collaborator, the program's own hosts).

## Edge cases

- A scan is already running when the policy updates with new exclusions: kill the scan, update exclude.txt, and restart against the new list. Do not let it finish "since it already started."
- Burp's scope uses suffix matching and you fat-fingered the domain: review the scope entries character by character after configuring. `exampl.com` matching nothing is a silent failure.
- The target resolves to different IPs per region and one is out-of-scope: pin your testing to the in-scope resolution or ask the program which endpoint to use.
- You discover the program's own scanner or canary in your logs: do not test it back. Note it and continue with your scope.
- Shared tooling (a team wordlist server, a shared collaborator): ensure shared infrastructure cannot cause your traffic to hit out-of-scope targets on your behalf.

## Escalation

- You touched out-of-scope: stop immediately, record exactly what was sent (timestamps, requests, responses), and disclose it to the program honestly with the explanation of how it happened. Then fix the control that failed.
- The program disputes whether an asset was in scope: your decisions.md and SCOPE.txt are the evidence. Walk them through the verdict calmly.
- Repeated near-misses: your enforcement layer has a gap. Audit which tool or habit bypassed the checks and close it before the next session.

## Detection and defender view

- Out-of-scope probing from an otherwise careful hunter usually means an ambiguous policy line or a tooling gap, not malice. Clarify the line; the hunter's decision log will show good faith.
- Defenders: publish exclusions as explicitly as inclusions. "Everything except X" is clearer than implying X is excluded.
- Rate and scope alerts on your side should distinguish in-scope hunter traffic (expected, welcome) from out-of-scope traffic (investigate, then clarify).
- Safe harbor language should state plainly that good-faith, in-policy testing is authorized and how to report accidental crossings; hunters who can disclose safely will disclose.

## Key references

- HackerOne safe harbor documentation: https://docs.hackerone.com
- Bugcrowd safe harbor docs: https://docs.bugcrowd.com
- Burp Suite target scope documentation: https://portswigger.net/burp/documentation
- nmap documentation: https://nmap.org/book/man.html
- MITRE ATT&CK T1595 Active Scanning: https://attack.mitre.org/techniques/T1595/
