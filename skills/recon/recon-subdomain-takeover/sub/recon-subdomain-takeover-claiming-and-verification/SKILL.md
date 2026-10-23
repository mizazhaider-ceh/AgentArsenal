---
name: recon-subdomain-takeover-claiming-and-verification
parent: recon-subdomain-takeover
description: Use when a takeover candidate is fingerprinted as claimable on an in-scope target and the program permits verification. Covers the permission check before any claiming, the least-invasive claiming procedure (benign proof file only, never defacement), evidence to capture at each step, releasing or handing over the resource promptly, and how to report when the program forbids claiming. Authorized targets only, claim only with explicit program permission.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-subdomain-takeover]
extends: []
relates: [recon-subdomain-takeover-cloud-service-fingerprints, recon-subdomain-takeover-dns-record-analysis, bugbounty-report-writing]
tools:
  - name: curl
    version: 8.5
  - name: Python
    version: 3.12
---

Claiming is the proof step of a takeover finding, and it is the step with the most rules. Claim only with the program's explicit permission, only the exact in-scope name, only a benign proof, and release it promptly. Many programs accept fingerprint plus DNS evidence without any claiming; prefer that whenever it is offered. This sub-skill covers safe verification for recon-subdomain-takeover. Never claim a resource outside explicit program permission.

## Quick Workflow

1. Check permission: does the program allow takeover claiming, and under what conditions. Get it in writing if ambiguous.
2. If claiming is forbidden: submit with DNS plus fingerprint evidence. Done; skip the rest.
3. If allowed: claim the exact endpoint name from the dangling record, nothing broader.
4. Place one benign proof file: your handle, the date, and a note that it is a security research proof. No other content.
5. Capture evidence: the claimed resource, the proof file served on the organization's subdomain, timestamps.
6. Release the resource immediately after evidence capture, or hand it over per the program's instructions.
7. Write the report with the full evidence chain and the release confirmation.

## 1. The permission check

Before touching any claim flow, confirm all three:

- The name is in scope: the exact subdomain from your candidate list, verified against the program's scope.
- The program permits takeover verification: check the policy's takeover section. Some programs say "proof via screenshot of the service dashboard is enough"; some say "do not claim, report the dangling record." Follow the stricter reading when ambiguous, and ask in writing when silent.
- You can release what you claim: if the service has no clean deletion or transfer path, do not claim. An unreleasable claim is a liability, not a proof.

Log the permission basis in your notes: policy quote plus date, or the program's message. This is your authorization record for the most sensitive step of the finding.

## 2. Least-invasive claiming

The claim itself is service-specific (create the Heroku app with the exact name, create the S3 bucket, claim the GitHub Pages repo), but the discipline is universal:

- Claim the exact endpoint name from the dangling record. Not a variant, not a broader resource.
- Use an account clearly tied to your researcher identity, not an anonymous throwaway. Programs need to know who held their subdomain.
- The moment the claim succeeds, deploy the single proof file. Example content:

```
Subdomain takeover proof of concept
Researcher: <your handle>
Date: 2026-10-23
Program: <program name>
This is a benign security research proof. No other content was served.
Contact: <your program contact or email>
```

- Nothing else goes on the resource: no analytics, no redirects, no JavaScript, no branding. A proof file is a proof file.

## 3. Evidence capture

Capture in order, with timestamps:

1. The DNS record as found (dig output showing the dangling CNAME).
2. The fingerprint match (the unclaimed error page body before claiming).
3. The service dashboard or API response confirming your claim of the exact name.
4. The proof file served on the organization's subdomain: `curl -s https://blog.example.com/proof.txt` output plus a screenshot.
5. The release: dashboard showing deletion, or the transfer confirmation, with timestamp.

```bash
# Evidence commands, run in sequence and saved to the finding folder
dig +short blog.example.com CNAME @1.1.1.1 | tee evidence/1-dns.txt
curl -sk -m 15 https://blog.example.com/ -o evidence/2-before.html
# ... claim via the service ...
curl -s https://blog.example.com/proof.txt | tee evidence/4-proof.txt
date -u | tee evidence/5-released.txt
```

This chain, DNS to fingerprint to claim to proof to release, is what makes the report unambiguous.

## 4. Release and handover

Release immediately after evidence capture; do not hold the subdomain "in case." If the service supports transfer, offer the program the transfer instead of deletion, per their preference. Confirm the release served: after deletion, the subdomain should return to the unclaimed fingerprint or NXDOMAIN, proving you no longer control it. Screenshot that final state too. Never hand the claimed resource to anyone except the program.

## 5. Reporting without claiming

When the program forbids claiming, the report is still complete with:

- The DNS record evidence (dangling CNAME with NXDOMAIN target, or equivalent).
- The fingerprint match (unclaimed error page body).
- The service-side availability signal where one exists (NoSuchBucket, NXDOMAIN).
- A clear statement: "Claiming was not performed per program policy; the DNS and fingerprint evidence above demonstrates the endpoint is unclaimed."

Programs that forbid claiming accept this routinely. Do not treat "no claim" as a weaker report; it is the policy-compliant report.

## Edge cases

- Someone else claimed it first (squatter): do not contest it. Document the dangling record and the squatter's content with a timestamp, report it as a suspicious takeover-in-progress, and let the program handle it.
- The claim flow requires a paid tier or identity verification you do not have: stop. Report with DNS plus fingerprint evidence instead of working around the barrier.
- The proof file does not serve (caching, propagation delay): wait for DNS and CDN propagation, verify with curl bypassing cache, and only then conclude. Do not deploy workarounds that expand the footprint.
- The program asks you to hold the claim during triage: get the request in writing, set a calendar reminder to follow up, and release the moment they confirm or go quiet past the agreed window.

## Escalation

- Claiming reveals a deeper issue (the service account or bucket contains the organization's leftover data): stop, do not read further than needed to characterize it, and report immediately with minimal detail. Leftover data in a claimable resource is a separate, sensitive finding.
- The release fails (service will not delete): contact the program urgently with the claim details so they can intervene with the provider. Document every attempt.

## Detection and defender view

- Require researcher identity on claims: anonymous takeovers of your subdomains are indistinguishable from attacks. Programs should state the claiming rules explicitly.
- Monitor CT logs for your subdomains: a certificate issued to someone else for your dangling name means the takeover completed without you knowing.
- Build the release into your process: when a hunter reports a takeover, the fix is DNS cleanup first, then verifying no squatter holds the endpoint name at the provider.
- Time-box researcher holds: agree the hold duration up front so subdomains do not sit claimed indefinitely.

## Key references

- Can I take over XYZ: https://github.com/EdOverflow/can-i-take-over-xyz
- HackerOne takeover guidance: https://docs.hackerone.com
- Bugcrowd researcher documentation: https://docs.bugcrowd.com
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
- MITRE ATT&CK T1590.002 DNS: https://attack.mitre.org/techniques/T1590/002/
