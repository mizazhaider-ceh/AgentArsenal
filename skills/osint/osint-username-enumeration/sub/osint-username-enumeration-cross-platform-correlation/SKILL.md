---
name: osint-username-enumeration-cross-platform-correlation
description: Use when automated username checks return candidate
  profiles and you must prove they belong to the same operator during
  an authorized investigation. Covers avatar comparison with perceptual
  hashing in Python 3.12, bio and writing-style pivots, timezone
  inference from activity timestamps, linked-account graphs, and
  confidence rating per account. Use when the parent
  osint-username-enumeration workflow has unverified hits, when name
  collisions make automation unreliable, or when building a defensible
  attribution for a report, fetching public profiles with curl for
  the case file.
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
  - name: curl
    version: 8.5
---

Cross-platform correlation turns a pile of same-name profiles into an
attributed footprint, or into a set of unrelated collisions. One data
point never proves identity; independent points that agree do. This
sub-skill covers the independent pivots: avatars, bios, timestamps,
links, and style, plus how to combine them into a confidence rating
that survives scrutiny. Public information only, authorized
investigations only.

## Quick Workflow

1. Collect the candidate profiles from the parent workflow into one
   working set with URLs and screenshots.
2. Download avatars and compare with perceptual hashing.
3. Extract bios and search distinctive phrases across the web.
4. Pull activity timestamps and infer the operator's timezone.
5. Map explicit links between profiles (bio links, cross-posts).
6. Compare writing style markers on long-form content.
7. Score each account: confirmed, likely, or unrelated, with reasons.
8. Write the attribution memo with evidence per account.

## 1. Avatar comparison

```bash
mkdir -p avatars && cd avatars
# Download public avatars (public profile images only)
curl -sL "https://github.com/darkcoder.png" -o avatar-github.png
curl -sL "https://example-forum.com/avatar/darkcoder.png" -o avatar-forum.png
```

```python
# avatar-compare.py: perceptual hash comparison
from PIL import Image
import imagehash
import itertools

hashes = {}
for name in ['avatar-github.png', 'avatar-forum.png', 'avatar-reddit.png']:
    try:
        hashes[name] = imagehash.phash(Image.open(name))
    except FileNotFoundError:
        print(f"missing {name}, skipping")

for a, b in itertools.combinations(hashes, 2):
    dist = hashes[a] - hashes[b]
    verdict = "SAME" if dist <= 5 else "different"
    print(f"{a} vs {b}: distance {dist} -> {verdict}")
```

Example output shape:

```
avatar-github.png vs avatar-forum.png: distance 2 -> SAME
avatar-github.png vs avatar-reddit.png: distance 28 -> different
```

A distance under 5 on pHash means near-identical images despite
resizing or recompression. Caveat: default avatars and popular
meme images produce false matches, so an avatar match is one vote,
not a verdict. Always pair it with another pivot.

## 2. Bio and phrase pivots

```bash
# Save each bio verbatim in the case file, then search distinctive phrases
# A unique phrase in quotes is the strongest text pivot
curl -sL "https://api.github.com/users/darkcoder" | python3 -c \
  "import json,sys; print(json.load(sys.stdin).get('bio'))"
# Example: "Embedded systems. I break UARTs for fun. No DMs."
```

Search the exact distinctive phrase in a web search engine, quoted.
If the same unusual sentence appears on three profiles, that is a
strong link, stronger than a shared common phrase like "software
developer". Also pivot on:

- Personal site domains listed in bios (then check the domain's
  other references).
- Contact emails or handles in bios ("tg: darkcoder_ops").
- PGP keys, crypto donation addresses, or sponsor links shared
  across profiles.

```bash
# Check whether a personal site links back to the other profiles
curl -sL "https://darkcoder.dev" | grep -oiE "(github|twitter|reddit)\.com/[a-z0-9_]+" | sort -u
```

A bio link from A to B plus a bio link from B to A is mutual
confirmation, the gold standard of this technique.

## 3. Timezone inference from timestamps

```python
# tz-infer.py: histogram of posting hours across profiles
from datetime import datetime
from collections import Counter

# Collect UTC timestamps of public posts per profile (from APIs or page data)
posts = {
    'github': ['2026-10-20T14:03:00Z', '2026-10-21T09:15:00Z'],
    'forum': ['2026-10-20T15:40:00Z', '2026-10-22T10:02:00Z'],
}
hours = Counter()
for profile, stamps in posts.items():
    for s in stamps:
        hours[datetime.fromisoformat(s.replace('Z', '+00:00')).hour] += 1

for h in sorted(hours):
    print(f"{h:02d}:00 UTC  {'#' * hours[h]}")
```

Example output shape:

```
09:00 UTC  ##
10:00 UTC  #
14:00 UTC  #
15:00 UTC  #
```

Activity concentrated in 08:00-18:00 UTC suggests a European operator;
a matching quiet window across profiles supports same-operator
attribution, while wildly different active windows weakens it. This
is a supporting pivot, never a primary one, since schedulers and
travel distort it.

## 4. Link graph

Build the explicit connection map:

```bash
# For each confirmed or candidate profile, record outbound identity links
# Store as a simple edge list in the case file
cat > links.csv <<'EOF'
from,to,evidence
github:darkcoder,twitter:darkcoder_ops,"bio links twitter"
twitter:darkcoder_ops,github:darkcoder,"bio links github, pinned tweet"
forum:darkcoder,github:darkcoder,"signature links github"
EOF
column -t -s, links.csv
```

Mutual links (A links B and B links A) are the strongest structural
evidence. One-way links are weaker but still useful. A profile with
no links to any other candidate stays at "likely" at best.

## 5. Writing style markers

For long-form content (forum posts, blog, READMEs), compare stable
markers: distinctive misspellings, punctuation habits (double spaces,
em dash usage), greeting and sign-off formulas, and jargon choices.
This is manual, qualitative work; do it on samples of at least a few
hundred words per profile.

```bash
# Pull a sample of public posts for side-by-side reading
curl -s "https://example-forum.com/user/darkcoder/posts" -o forum-posts.html
# Extract text and read, do not automate authorship attribution claims
```

Never present style similarity as proof on its own. It corroborates;
it does not convict.

## 6. Confidence rating

| Rating | Requirement |
|---|---|
| Confirmed | Two or more independent pivots agree (for example, avatar match plus mutual bio links), no contradictions |
| Likely | One strong pivot (mutual link, identical rare phrase) with no contradictions |
| Unrelated | Contradicting pivots (different faces in photos, disjoint timezones, different topics over years) |
| Unknown | Insufficient data; do not guess |

Write one paragraph per account stating the rating and the pivots
behind it. The memo should let a reviewer reach the same conclusion
from the same evidence.

## Edge cases

- The operator deliberately separates identities (work versus
  personal). Respect the separation in your analysis unless the
  authorization explicitly asks to test the boundary; linking them
  in a report has real consequences for the subject.
- Avatars are AI-generated or stock images reused by many people.
  Reverse image search the avatar first; if it appears on dozens of
  unrelated profiles, discard the avatar pivot entirely.
- Timestamps are sparse (a handful of posts). Do not infer
  timezones from fewer than twenty data points; note insufficient
  data instead.
- Bios are empty on most profiles. Fall back to content topics and
  link graphs; empty bios are common and prove nothing either way.
- The subject reuses a handle but the accounts are clearly different
  people (name collision). Document the collision explicitly so no
  one later treats the set as one person.
- One profile is private. You cannot use its content; note its
  existence and the public metadata only (username, avatar if
  public, follower counts where visible).

## Escalation

- Correlation suggests the accounts belong to someone other than the
  investigation subject (wrong-person risk). Stop, re-verify the
  seed data with the case owner, and do not publish the attribution
  until resolved.
- You uncover non-public personal data during correlation (address,
  workplace, family). Minimize collection, note it only if the
  authorization covers it, and escalate handling to the case owner.
- The attribution will be used in proceedings. Raise the bar to
  "confirmed" on at least two pivots per account, archive every
  source page, and have a second reviewer check the memo.
- Evidence points to coordinated inauthentic behavior (many linked
  accounts acting together). This outgrows username enumeration;
  escalate to the threat-intel workflow for network analysis.

## Detection and defender view

Correlation is how investigators defeat identity separation, so the
defense is genuine separation: distinct handles, distinct avatars,
no cross-links, separate posting patterns per context, and awareness
that distinctive phrases are fingerprints. For investigation teams,
the defender view cuts both ways: run this workflow on your own
public footprint to find the links you did not know you left, and
use dedicated research accounts so your correlations do not leak
back to you.

## Key references

- Parent methodology: osint-username-enumeration (this repo)
- OSINT methodology: osint-methodology (this repo)
- Bellingcat verification and geolocation guides:
  https://www.bellingcat.com/resources/
- ImageHash (perceptual hashing library):
  https://github.com/JohannesBuchner/imagehash
- Web Archive for historical bios:
  https://web.archive.org/
