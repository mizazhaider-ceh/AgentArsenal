---
name: recon-subdomain-enumeration-permutation-techniques
parent: recon-subdomain-enumeration
description: Use when passive and brute force enumeration plateau and you need to mutate known names into undiscovered ones on an authorized target domain. Covers alteration wordlists (dnsgen), environment and numbering patterns, hyphen and ordering variants, service-name seeding from the target's tech stack, and validating permutation output without wildcard pollution. Authorized targets only, only enumerate domains you are permitted to test.
version: 1.0.0
domain: recon
lifecycle: stable
last_verified: 2026-10-23
requires: [recon-subdomain-enumeration]
extends: []
relates: [recon-subdomain-enumeration-active-bruteforcing, recon-subdomain-enumeration-passive-sources, recon-active, dns-enumeration]
tools:
  - name: dnsx
    version: 1.2
  - name: dnsgen
    version: 1.1
  - name: Python
    version: 3.12
---

Permutations exploit the target's naming convention: once you know they use `api-prod` and `web-staging`, you generate every combination of their words with every environment, number, and separator they use. This finds names no wordlist contains. This sub-skill covers the permutation layer of recon-subdomain-enumeration. Only enumerate domains you are authorized to test.

## Quick Workflow

1. Take the confirmed subdomain list as seed input.
2. Extract the naming vocabulary: prefixes, suffixes, separators, numbers, service words.
3. Generate alterations with dnsgen from the seed list.
4. Generate pattern-based combinations: environments, numbers, hyphen variants, order swaps.
5. Seed service names from the target's tech stack (job postings, docs, banners).
6. Resolve the permutation list with dnsx, filtering wildcard noise.
7. Merge new hits into the consolidated list.

## 1. Learning the vocabulary

The seed list teaches you the convention. Extract its parts:

```bash
# Second labels and their frequency: learn which words the org reuses
cut -d. -f1 confirmed.txt | sort | uniq -c | sort -rn | head -40
# Example output shape:
#  12 api
#   8 web
#   6 staging
#   5 internal

# Separator style: count hyphens versus plain concatenation
grep -c "-" confirmed.txt
# Numbering style: which names carry digits
grep -E "[0-9]" confirmed.txt | head -20
```

If the output shows `api-prod`, `api-staging`, `web-prod`, the convention is `<service>-<env>`. Your permutations should speak that dialect, not generic wordlist.

## 2. dnsgen alterations

dnsgen mutates each seed name with common alterations (word additions, number insertions, hyphenation):

```bash
pip install dnsgen
dnsgen -l confirmed.txt > dnsgen-perms.txt
wc -l confirmed.txt dnsgen-perms.txt
dnsx -l dnsgen-perms.txt -silent -resp -o dnsgen-hits.txt -t 100 -rl 200
```

dnsgen output is large (tens of thousands per hundred seeds), so resolve it in batches and filter wildcard IPs. Typical hit rate is low but the hits are names no dictionary contains, which makes them high-value: unusual names are often forgotten or staging hosts.

## 3. Pattern-based generation

Hand-built patterns from the learned vocabulary outperform generic alteration:

```bash
# Environments x services, both orders, both separators
services=$(cut -d. -f1 confirmed.txt | sort -u)
for env in dev staging qa uat prod test demo; do
  for s in $services; do
    echo "$s-$env.example.com"; echo "$env-$s.example.com"
    echo "$s$env.example.com";  echo "$env$s.example.com"
  done
done | sort -u > env-perms.txt

# Numbering variants on confirmed names
while read -r n; do
  base="${n%%.*}"; rest="${n#*.}"
  for i in 1 2 3 01 02 v1 v2; do
    echo "$base$i.$rest"; echo "$base-$i.$rest"
  done
done < confirmed.txt | sort -u > number-perms.txt

wc -l env-perms.txt number-perms.txt
dnsx -l <(cat env-perms.txt number-perms.txt) -silent -resp -o pattern-hits.txt
```

Add org-specific environments you discovered (some companies use `ppe`, `int`, `acc`, `pre`). The vocabulary from section 1 tells you which.

## 4. Tech-stack seeding

Internal tooling subdomains follow the stack the company runs. Seed from:

- Job postings and engineering blogs: "we run Kubernetes, Vault, Consul, Grafana" becomes `vault.`, `consul.`, `grafana.`, `k8s.` guesses.
- Banner data from httpx: server headers and tech fingerprints name the stack directly.
- Common combos: `jenkins.`, `gitlab.`, `artifactory.`, `sonar.`, `kibana.`, `prometheus.`, `argocd.`, each with env prefixes from section 3.

```bash
for svc in jenkins gitlab vault consul grafana kibana prometheus argocd; do
  echo "$svc.example.com"
  for env in dev staging prod internal; do
    echo "$svc-$env.example.com"; echo "$env-$svc.example.com"
  done
done | sort -u > stack-perms.txt
dnsx -l stack-perms.txt -silent -resp -o stack-hits.txt
```

## 5. Validation and merging

Permutation lists are noisy by design; validate strictly:

```bash
cat dnsgen-hits.txt pattern-hits.txt stack-hits.txt \
  | grep -v "WILDCARD_IP" | sort -u > perm-validated.txt
# Confirm each resolves and is not already known
comm -23 <(cut -d' ' -f1 perm-validated.txt | sort -u) \
         <(cut -d' ' -f1 resolved-final.txt | sort -u) > perm-new.txt
wc -l perm-new.txt && head -10 perm-new.txt
```

Only genuinely new names proceed to httpx probing. Log the yield per technique; over campaigns you learn which permutation style pays for which kind of target.

## Edge cases

- dnsgen output explodes (millions of candidates): cap it by seeding only the most productive names (services, not every blog subdomain) or it becomes a slow brute force with extra steps.
- Permutations mostly hit the wildcard IP: your filtering is working, but also reconsider; heavy wildcard use means the org provisions names dynamically and permutations have lower value there.
- The convention uses words you cannot guess (project codenames): mine certificate SANs, code repos, and the target's own docs for codenames, then permute those.
- Non-English environments (German `entwicklung`, French `recette`): check the company's locale; environment words follow the team's language.

## Escalation

- Permutations plateau: the naming convention is exhausted. Move to ASN netblock reverse-DNS sweeps and certificate hash pivoting in Shodan for infrastructure the DNS never names.
- One permutation hit reveals a new convention (a codename pattern): immediately generate a second permutation round seeded on the new names. Conventions nest.

## Detection and defender view

- Permutation resolution looks like brute forcing at the DNS layer: high-volume queries for similar names. Same authorization and pacing rules apply.
- Defenders: unusual subdomain names are often the forgotten ones (staging, old projects). Monitor CT logs for new names and audit for stale ones; attackers permute toward exactly these.
- A naming convention is an information leak: `db-backup-prod` tells an attacker what and where. Prefer opaque names for sensitive infrastructure.

## Key references

- dnsgen: https://github.com/lazaruslabs/dnsgen
- dnsx documentation: https://github.com/projectdiscovery/dnsx
- SecLists DNS wordlists: https://github.com/danielmiessler/SecLists
- MITRE ATT&CK T1590.002 DNS: https://attack.mitre.org/techniques/T1590/002/
- OWASP Amass documentation: https://github.com/owasp-amass/amass
