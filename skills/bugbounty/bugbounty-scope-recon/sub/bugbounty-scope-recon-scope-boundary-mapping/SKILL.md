---
name: bugbounty-scope-recon-scope-boundary-mapping
parent: bugbounty-scope-recon
description: Use when your asset inventory is built and every discovered asset needs a verdict before testing begins. Covers the three-verdict system (in-scope, out-of-scope, gray area), how to judge tricky cases like CNAMEs to third parties, acquired domains, shared staging, and IP reassignments, writing the decision log that protects you, and asking the program precise scope questions that get fast yeses. Authorized targets only, only test assets the program explicitly lists in scope.
version: 1.0.0
domain: bugbounty
lifecycle: stable
last_verified: 2026-10-23
requires: [bugbounty-scope-recon]
extends: []
relates: [bugbounty-scope-recon-asset-discovery, bugbounty-scope-recon-out-of-scope-avoidance, bug-bounty-workflow]
tools:
  - name: dig
    version: 9.18
  - name: whois
    version: 5.5
  - name: Python
    version: 3.12
---

Boundary mapping is the verdict step: every asset in your inventory gets labeled in-scope, out-of-scope, or gray area, with the reasoning written down. Gray areas stay untouched until the program answers in writing. This decision log is what proves your testing stayed authorized. This sub-skill covers only the boundary verdict step of bugbounty-scope-recon. Only test assets with an in-scope verdict.

## Quick Workflow

1. Take the asset inventory from asset discovery as the input list.
2. For each asset, apply the three-verdict test: explicitly listed or clearly covered, explicitly excluded or third-party, or ambiguous.
3. Resolve CNAMEs and check IP ownership for every verdict; the DNS answer often changes the call.
4. Write each verdict plus one line of reasoning into decisions.md.
5. Batch all gray-area assets into one precise question to the program, with evidence per asset.
6. Mark the final in-scope list as the enforced target list for all tooling.
7. Re-run the verdicts whenever the program updates its policy.

## 1. The three-verdict test

For each asset, ask in order:

- In-scope: is the exact name or IP listed, or does a listed wildcard or CIDR plainly cover it. `api.example.com` under `*.example.com`: in-scope.
- Out-of-scope: is it explicitly excluded, does it belong to a third party, or is it outside every listed domain and range. `staging.example.com` when excluded: out-of-scope, no debate.
- Gray area: plausible but not decidable from the policy alone. Acquired company domains not yet listed, subdomains pointing at partners, shared staging environments, app-discovered API hosts on generic cloud domains.

```bash
# decisions.md format: asset | verdict | reasoning | date
# api.example.com | IN | covered by *.example.com | 2026-10-23
# staging.example.com | OUT | explicitly excluded in policy | 2026-10-23
# legacy-acquired.io | GRAY | acquired 2024, not listed; asked program | 2026-10-23
```

Default rule: when you cannot decide between in-scope and gray, it is gray. When you cannot decide between gray and out, it is out. Caution never cost anyone a ban.

## 2. DNS and ownership checks that change verdicts

The DNS answer frequently flips a verdict. Check before finalizing:

```bash
# CNAME to a third party: the name may be in scope, the provider is not
dig +short shop.example.com CNAME @1.1.1.1
# Example output shape: shops.myshopify.com.

# IP ownership for range-scoped assets
whois -h whois.arin.net 203.0.113.45 | grep -iE "orgname|netname" | head -3
```

Verdict rules from these checks:

- In-scope name CNAMEd to a third-party SaaS: test application behavior on the in-scope name only. Do not test the provider's infrastructure; that is someone else's scope.
- IP in a scoped range that whois now shows as reassigned: treat as out-of-scope until the program confirms. Ranges get reallocated and stale scopes are common.
- Subdomain resolving to an IP outside the program's ASN with no CNAME explanation: gray. It may be a partner integration or a misconfiguration; ask.

## 3. Asking the program well

Batch gray areas into one message with evidence per asset. Precise asks get fast answers:

```
Subject: Scope question: 3 assets found during recon

1. legacy-acquired.io - resolves to 198.51.100.23, serves the Example Corp
   login page with your branding. Acquired 2024 per press release.
   Request: confirm in or out of scope.
2. partners.example.com - CNAMEs to partner-cdn.net (third party).
   Request: is testing the application behavior on partners.example.com
   in scope, excluding the CDN infrastructure itself.
3. api-internal.example.com - resolves internally only from my location;
   found in your Android app's strings. Request: confirm in or out.
```

Ask once, with everything, instead of dripping one question a day. Most programs answer scope questions quickly because ambiguity protects neither side.

## 4. The enforced target list

After verdicts, compile the final list that your tooling will enforce:

```bash
grep "| IN |" decisions.md | cut -d'|' -f1 | tr -d ' ' | sort -u > targets-in-scope.txt
grep "| OUT |" decisions.md | cut -d'|' -f1 | tr -d ' ' | sort -u > exclude.txt
wc -l targets-in-scope.txt exclude.txt
```

`targets-in-scope.txt` feeds your scanners and your Burp target scope. `exclude.txt` feeds every exclusion flag. Gray assets appear in neither file until the program answers.

## Edge cases

- The program answers "we'll get back to you" and never does: after their stated SLA, treat the asset as out-of-scope and move on. Silence is not permission.
- A verdict changes mid-hunt (program updates exclusions): move the asset to exclude.txt immediately and stop any running scans against it.
- Two scope lines conflict (a wildcard includes what an exclusion names): the exclusion wins. Specific beats general.
- The asset is the program's but the finding would be in a third-party component: report the application-layer issue on the in-scope name; do not test the component's own infrastructure.
- You inherited someone else's target list: re-verify every verdict yourself. Secondhand scope is how out-of-scope scans happen.

## Escalation

- Gray list keeps growing: your scope reading may be too cautious or the policy too vague. Ask the program for a scope clarification call or an updated policy; many will oblige.
- A critical-looking issue appears on a gray asset: do not probe it. Note its existence with zero exploitation detail and ask the program whether to proceed.
- The program expands scope based on your questions: re-run asset discovery on the new scope lines and re-do verdicts for affected assets.

## Detection and defender view

- A written decision log is the audit trail that separates authorized testing from unauthorized scanning. Keep it per program, per engagement.
- Defenders: ambiguous scopes generate gray-area questions; every vague line costs your team triage time answering hunters. Write scopes like firewall rules: explicit allows, explicit denies.
- Monitor for hunters probing just outside your stated scope: it usually signals an ambiguous policy line, not malice. Clarify the line instead of banning the hunter.
- Safe harbor depends on the boundary: publish the exact scope, keep it current, and hunters will stay inside it.

## Key references

- HackerOne program scope documentation: https://docs.hackerone.com
- Bugcrowd scope and safe harbor docs: https://docs.bugcrowd.com
- dig documentation (BIND 9): https://www.isc.org/bind/
- MITRE ATT&CK T1590 Gather Victim Network Information: https://attack.mitre.org/techniques/T1590/
- OWASP Testing Guide: https://owasp.org/www-project-web-security-testing-guide/
