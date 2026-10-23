---
name: osint-username-enumeration-handle-enumeration
description: Use when a subject's primary handle is known but their
  other accounts use variations, and you must systematically discover
  them during an authorized investigation. Covers building variant
  lists (typos, leetspeak, affixes, platform conventions) with Python
  3.12, checking platform username policies to prune impossible
  variants, searching handle fragments in web search engines, and
  tracking renamed or deleted accounts through archives. Use when the
  parent osint-username-enumeration workflow stalls on the primary
  handle, when the subject is known to rotate handles, or when mapping
  a full historical footprint, checking top variants with Sherlock.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-username-enumeration
requires: [osint-username-enumeration]
extends: []
relates: [osint-username-enumeration]
tools:
  - name: Python
    version: 3.12
  - name: Sherlock
    version: 0.14.0
  - name: curl
    version: 8.5
---

Handle enumeration is the systematic generation and testing of
username variants: the typos, suffixes, and platform adaptations a
person accumulates over years. Most people do not invent a fresh
identity per site; they mutate one. This sub-skill covers generating
those mutations methodically, pruning the impossible ones with
platform rules, and chasing renamed accounts through history. Public
data only, authorized investigations only.

## Quick Workflow

1. Start from the confirmed primary handle and any known aliases.
2. Generate variants: affixes, separators, leetspeak, truncations,
   and common typos.
3. Prune variants against platform username policies.
4. Check variants with Sherlock and targeted manual searches.
5. Search handle fragments in web search engines for unindexed
   mentions.
6. Chase renames: archives, quotes of old handles, commit history.
7. Verify each discovered variant with the correlation sub-skill.
8. Record the variant map: which handles are live, renamed, or dead.

## 1. Variant generation

```python
# variants.py: systematic handle mutation
import itertools

base = "darkcoder"
variants = set()

# Affixes and separators
for affix in ["", "_", ".", "-", "x", "the", "real", "official"]:
    variants.add(affix + base)
    variants.add(base + affix)
for num in ["1", "12", "123", "007", "69", "2000"]:
    variants.add(base + num)

# Leetspeak substitutions
leet = str.maketrans({"a": "4", "e": "3", "i": "1", "o": "0", "s": "5"})
variants.add(base.translate(leet))

# Truncations (platform length limits force these)
for n in [8, 10, 12]:
    variants.add(base[:n])

# Common typos: doubled letters, adjacent key swaps
variants.add(base.replace("oo", "o"))
variants.add("drakcoder")  # transposition

print(f"{len(variants)} variants")
print("\n".join(sorted(variants)[:20]))
```

Example output shape:

```
47 variants
d4rkc0der
darkcode
darkcoder
darkcoder007
darkcoder123
darkcoderx
drakcoder
realdarkcoder
thedarkcoder
```

Prioritize: the subject's own observed patterns beat generic lists.
If their known alias is `darkcoder_dev`, weight the `_dev` and
`.dev` families first.

## 2. Platform policy pruning

```python
# prune.py: drop variants a platform cannot accept
policies = {
    'github':   {'min': 1, 'max': 39, 'allow': set('abcdefghijklmnopqrstuvwxyz0123456789-')},
    'twitter':  {'min': 1, 'max': 15, 'allow': set('abcdefghijklmnopqrstuvwxyz0123456789_')},
    'reddit':   {'min': 3, 'max': 20, 'allow': set('abcdefghijklmnopqrstuvwxyz0123456789-_')},
}

def valid(handle, policy):
    h = handle.lower()
    return (policy['min'] <= len(h) <= policy['max']
            and set(h) <= policy['allow'])

for site, pol in policies.items():
    ok = [v for v in variants if valid(v, pol)]
    print(f"{site}: {len(ok)} plausible variants")
```

Example output shape:

```
github: 41 plausible variants
twitter: 33 plausible variants
reddit: 38 plausible variants
```

Pruning focuses manual effort: a 20-character variant cannot be a
Reddit username, so do not waste verification time there. Keep the
policy table in the case file; platforms change rules and your
pruning must be auditable.

## 3. Checking variants at scale

```bash
# Feed the top variants to Sherlock (keep batches small for rate limits)
head -12 variants.txt | tr '\n' ' ' > batch1.txt
sherlock $(cat batch1.txt) --json --output ./cases/variants-batch1.json --timeout 20

# Triage: which variants claimed anything at all
python3 - <<'EOF'
import json
data = json.load(open('variants-batch1.json'))
# Sherlock multi-user output nests per username; flatten for triage
print(json.dumps({k: v for k, v in list(data.items())[:3]}, indent=1)[:800])
EOF
```

Work in small batches and verify between batches; a confirmed variant
often reveals the subject's mutation pattern, letting you generate
the next batch smarter instead of brute-forcing the whole list.

## 4. Fragment search in web engines

Usernames appear in places Sherlock never checks: paste sites, forum
quotes, commit logs, old bios.

```bash
# Search distinctive fragments (use the engine's web UI or API per your policy)
# Queries to try, quoted for precision:
#   "darkcoder" site:example-forum.com
#   "darkcoder_dev"
#   "darkcoder" "formerly"
```

```bash
# GitHub commit search via the public API (authenticated for better limits)
curl -s -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/commits?q=author:darkcoder" | \
  python3 -c "import json,sys; [print(i['commit']['author']['name'], i['html_url']) for i in json.load(sys.stdin)['items'][:10]]"
```

Commit author names are a rich source of handle variants: people
commit as `DarkCoder`, `darkcoder@laptop`, or an old handle long
after renaming the account.

## 5. Chasing renames and deletions

```bash
# GitHub username history is not public via API, but archives help
curl -s "https://archive.org/wayback/available?url=github.com/darkcoder" | python3 -m json.tool

# Forum quotes preserve old handles: search for the rename announcement pattern
#   "darkcoder" "renamed" / "formerly known as"
```

Also check: gaming platforms that show previous names on the profile,
code hosts where old commit emails persist, and package registries
(npm, PyPI) where the author field rarely gets updated. Each old
handle restarts the parent workflow, since its accounts may still be
live.

## 6. The variant map

```
Primary: darkcoder (confirmed, active)
Variants:
  darkcoder_dev  -> confirmed (GitHub org member, avatar match)
  d4rkcoder      -> likely (forum, same PGP key)
  thedarkcoder   -> unrelated (different avatar, topics, timezone)
Renamed:
  oldcoder99     -> renamed to darkcoder in 2021 (archive snapshot 2021-03-14)
Dead:
  darkcoder123   -> account deleted (profile 404 since 2024)
```

The map is the deliverable: it shows the search was exhaustive,
records negative results, and gives the next investigator a starting
point instead of a mystery.

## Edge cases

- The variant list explodes combinatorially. Cap it: prioritize
  observed patterns, then common mutations, then brute force only
  for the highest-value platforms.
- A variant is claimed but belongs to a different person (collision).
  The correlation sub-skill decides; never assume a variant match is
  the subject.
- The subject uses completely unrelated handles per context. Variant
  enumeration cannot bridge that gap; only correlation pivots
  (avatar, bio, links) from a confirmed account can.
- Platform policies changed since your table was written. Re-check
  the policy before pruning in a new case; a rule change can
  invalidate old pruning.
- Search engines return stale results for renamed accounts. Verify
  the live profile before recording a variant as active.
- The investigation scope covers only the primary handle. Do not
  expand to variants without the case owner's approval; each new
  handle is new collection.

## Escalation

- Variant discovery reveals accounts clearly outside the authorized
  scope (family members, unrelated persons). Exclude them from the
  case file beyond a one-line note, and do not investigate further.
- A discovered variant is actively used for wrongdoing within a
  threat intel scope. Preserve evidence and escalate to the case
  owner immediately.
- The variant map keeps growing without converging. Set a stopping
  rule with the case owner (for example, two batches with no new
  confirmations) to keep the investigation bounded.
- Results feed legal proceedings. Every variant needs the same
  evidence standard as the primary: archived pages, timestamps, and
  correlation notes.

## Detection and defender view

Variant patterns are predictable, which is why investigators exploit
them and why defenders should break them: use unrelated handles per
context, never reuse affix patterns (`_dev`, `_real`) across
identities you want separated, and clean up old accounts instead of
abandoning them (abandoned accounts get hijacked and then attributed
to you). Audit your own variants with this workflow annually; the
typos you would never choose are exactly the ones an investigator
generates first.

## Key references

- Parent workflow: osint-username-enumeration (this repo)
- Correlation method: osint-username-enumeration-cross-platform-correlation (this repo)
- Sherlock: https://github.com/sherlock-project/sherlock
- GitHub REST API docs: https://docs.github.com/en/rest
- Web Archive: https://web.archive.org/
- Bellingcat resources: https://www.bellingcat.com/resources/
