---
name: osint-username-enumeration
description: Use when you need to find accounts and profiles tied to a
  username or handle across the internet during an authorized
  investigation. Covers handle normalization and variant generation,
  large-scale site checking with Sherlock and Maigret, manual
  verification to kill false positives, cross-platform correlation via
  avatars, bios, and timestamps, handle history through archives, and
  documentation standards. Use when an investigation starts from a
  screen name, when you must attribute accounts to the same operator,
  or when mapping a subject's public footprint. Public information
  only, within your authorized scope.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [username-osint, osint-methodology, threat-intel]
tools:
  - name: Python
    version: 3.12
  - name: Sherlock
    version: 0.14.0
  - name: Maigret
    version: 0.4.2
  - name: curl
    version: 8.5
---

Username enumeration finds where a handle exists across platforms: the
forums, code hosts, gaming profiles, and social accounts tied to one
screen name. People reuse handles for years, and each account adds
context: bios, avatars, timestamps, linked profiles. This skill covers
the authorized workflow from handle normalization through automated
checking, verification, correlation, and documentation. It covers only
publicly available information gathered within an authorized
investigation, such as a corporate due-diligence check, a threat
intel assignment, or your own handle audit. Do not use these
techniques to stalk, harass, or dox private individuals.

## Quick Workflow

1. Confirm authorization and scope: whose handle, why, and what you
   may do with the results.
2. Normalize the handle: strip decorations, generate likely variants
   (underscores, dots, numbers, leetspeak).
3. Run Sherlock across its site list; save JSON output.
4. Run Maigret for deeper per-site checks on the same variants.
5. Verify every hit manually: open the profile, confirm it is the
   same operator, discard lookalikes.
6. Correlate: compare avatars, bios, writing style, and activity
   timestamps across confirmed accounts.
7. Check handle history: archives and name-change traces for prior
   identities.
8. Document: profile URLs, screenshots, timestamps, and a confidence
   rating per account.

## 1. Handle normalization and variants

```bash
# Normalize: lowercase, strip common decorations
HANDLE="xX_DarkCoder_Xx"
echo "$HANDLE" | tr '[:upper:]' '[:lower:]' | sed 's/^x*//; s/x*$//; s/_//g'
# darkcoder

# Generate variants systematically
python3 - <<'EOF'
base = "darkcoder"
variants = {base}
for v in [base, base + "1", base + "123", base + "_", "_" + base,
          base.replace("o", "0"), base + ".dev", "the" + base, base + "x"]:
    variants.add(v)
print("\n".join(sorted(variants)))
EOF
```

Example output shape:

```
darkcoder
darkcoder123
darkcoderx
thedarkcoder
_darkcoder
d4rkcoder
```

Keep the variant list in the case file; it shows the search was
systematic rather than cherry-picked. Note platform-specific rules:
some sites forbid leading underscores or dots, so a variant missing
on one platform may simply be invalid there.

## 2. Sherlock: broad site checking

```bash
# Install (Python 3.12)
pip install sherlock-project
# Or from source for the latest site list
git clone https://github.com/sherlock-project/sherlock.git

# Basic run with JSON output for the case file
sherlock darkcoder --json --output ./sherlock-darkcoder.json --timeout 15

# Check several variants in one run
sherlock darkcoder darkcoder123 d4rkcoder --json --output ./sherlock-variants.json

# Respectful rate limiting on large runs
sherlock darkcoder --timeout 20 --proxy socks5://127.0.0.1:9050
```

Example output shape:

```
[*] Checking username darkcoder on:
[+] GitHub: https://github.com/darkcoder
[+] Reddit: https://www.reddit.com/user/darkcoder
[+] Twitter: https://twitter.com/darkcoder
[-] Instagram: Not Found!
[-] TikTok: Not Found!
[*] Search completed with 14 results
```

Sherlock checks hundreds of sites; expect false positives on sites
where the username is taken by someone else. The `[+]` marks a hit,
not a confirmed attribution. Every hit needs section 4 verification.

Site list maintenance matters: platforms change their URL schemes and
Sherlock's data file tracks that. Update before an investigation and
note the Sherlock version in the case file so results are
reproducible.

## 3. Maigret: deeper per-site checks

Maigret checks more sites than Sherlock and extracts profile metadata
(ids, bios, avatars) where available.

```bash
pip install maigret

# Run with HTML and JSON reports
maigret darkcoder --html --json simple --timeout 20

# Focus on high-value site groups
maigret darkcoder --top-sites 200

# Parse the JSON for confirmed-profile triage
python3 - <<'EOF'
import json
with open('report.json') as f:
    data = json.load(f)
for site, info in data.items():
    if info.get('status', {}).get('claimed') == 'Claimed':
        print(site, '->', info.get('url'))
EOF
```

Use Maigillt and Sherlock together: Sherlock for breadth, Maigret for
depth and metadata. When they disagree on a site, the manual check in
section 4 decides.

## 4. Manual verification: killing false positives

Automation finds candidates; only a human confirms attribution. For
each hit, open the profile and check:

1. Avatar: same image as other confirmed accounts (reverse image
   search it).
2. Bio: same links, same phrasing, same contact details.
3. Content: same topics, same writing style, cross-references
   between accounts ("my GitHub is...").
4. Timestamps: account creation dates that cluster, activity in the
   same timezone window.
5. Explicit links: profile A links to profile B.

```bash
# Fetch a profile page for the record (public page only)
curl -sL "https://github.com/darkcoder" -o github-darkcoder.html
# Screenshot the rendered profile for the case file; HTML alone misses JS content
```

Rate each account: confirmed (multiple independent links), likely
(one strong link), or unrelated (name collision). Name collisions
are common for short handles; a GitHub `darkcoder` from 2015 and a
TikTok `darkcoder` from 2024 with different avatars and topics are
different people until proven otherwise.

## 5. Cross-platform correlation

```bash
# Compare avatar hashes across downloaded profile images
python3 - <<'EOF'
from PIL import Image
import imagehash
imgs = ['avatar-github.png', 'avatar-reddit.png', 'avatar-forum.png']
hashes = {p: str(imagehash.average_hash(Image.open(p))) for p in imgs}
for p, h in hashes.items():
    print(p, h)
# Identical or near-identical hashes strongly suggest the same operator
EOF
```

Beyond avatars, correlate: bio text reused verbatim (search a
distinctive phrase in quotes), PGP keys or donation addresses shared
across profiles, and timezone inference from posting times. Each
independent correlation raises confidence; document each one, since
"same avatar" alone has fooled investigators before (default avatars,
stolen images).

## 6. Handle history and prior identities

People change handles. Find the old ones:

- Web archives of the profile page show previous usernames and bios.
- Forum posts quoting the old handle ("formerly known as...").
- Git commit history under the old name still attached to the
  account.
- Gaming profiles often show name-change history publicly.

```bash
# Check archive snapshots of a profile (public archive services)
curl -s "https://archive.org/wayback/available?url=github.com/darkcoder" | python3 -m json.tool
```

A prior handle restarts the whole workflow: enumerate the old handle
too, since its accounts may still be live and linked.

## 7. Documentation standard

Each confirmed account gets one record:

```
Handle: darkcoder
Platform: GitHub
URL: https://github.com/darkcoder
Confidence: confirmed (avatar match + bio links to confirmed Twitter)
First seen: 2026-10-23
Screenshot: case/github-darkcoder-20261023.png
Notes: bio links personal site, site links back to Twitter account
```

Store screenshots with dates in filenames. Note negative results too
("checked TikTok, account exists but avatar and content differ:
unrelated"); negative results prevent someone re-doing the work or
misattributing later.

## Edge cases

- The handle is extremely common (e.g. "shadow"). Automated tools
  return hundreds of hits, mostly collisions. Narrow by correlating
  with a second known data point (location, interest, avatar) before
  expanding.
- The subject uses different handles per platform by design.
  Username enumeration alone fails; pivot from a confirmed account's
  bio links, avatar, or writing style instead.
- Profiles are private or deleted. Respect that boundary; do not use
  leaked databases or unauthorized access to view them. Note the
  existence of the private account and move on.
- Sherlock reports a site as "not found" but manual browsing finds
  the profile. Site URL schemes change; verify manually and note the
  tool gap rather than trusting the negative.
- Rate limiting or CAPTCHAs block the run. Slow down, use the proxy
  option, and split runs across time. Aggressive scanning can get
  your IP blocked and, worse, alert the subject.
- The investigation is about your own handle (audit). Same workflow,
  and it is the best way to see your public footprint before someone
  else maps it.

## Escalation

- You find accounts suggesting the subject is engaged in wrongdoing
  within your authorized scope (threat intel, corporate
  investigation). Preserve evidence with timestamps and escalate to
  the case owner; do not contact the subject.
- Correlation points at a private individual's non-public data
  (address, family). Stop expanding in that direction unless the
  authorization explicitly covers it, and flag the boundary to the
  case owner.
- The handle belongs to a minor. Apply extra care: stick to the
  authorized scope, minimize collection, and escalate any concern
  through proper channels rather than investigating further alone.
- Results will be used in legal or employment proceedings. Raise the
  evidence bar: screenshots with timestamps, archived copies, and a
  written methodology the case owner can defend.

## Detection and defender view

From the defender side, handle reuse is the vulnerability: one
compromised or exposed account links to all the others. Defenses are
operational: separate handles for separate contexts, no cross-links
in bios between identities you want apart, unique avatars per
context, and periodic audits of your own footprint using this exact
workflow. For investigators, remember the subject may be doing the
same mapping on you; use dedicated research accounts and VPN
separation for sensitive cases, per your organization's policy.

## Key references

- Sherlock project: https://github.com/sherlock-project/sherlock
- Maigret project: https://github.com/soxoj/maigret
- OSINT methodology skill (this repo): osint-methodology
- NIST SP 800-61 for investigation handling context
- Bellingcat's online investigation toolkit (verification methods):
  https://www.bellingcat.com/resources/
- Web Archive: https://web.archive.org/
- Username OSINT references in the threat-intel skill (this repo)
