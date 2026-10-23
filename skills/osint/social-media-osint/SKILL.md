---
name: social-media-osint
description: Use when researching publicly visible social media content
  on an authorized engagement. Covers profile analysis and attribution,
  timeline and network mapping, image and video metadata, geolocation
  from public posts, sock puppet OPSEC, and lawful limits. Use when the
  task needs background on a threat actor's public persona, brand
  monitoring, or verifying claims, always on public posts only and
  within platform terms of service and privacy law.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [osint-methodology]
tools:
  - name: Python
    version: 3.12
  - name: curl
    version: 8.x
---

Social media holds a large share of public human intelligence: who
people claim to be, who they know, where they have been, and what they
care about. This skill covers researching publicly visible social
content for authorized purposes: profile analysis, network mapping,
media forensics, and geolocation, with strict limits. Only public
posts, no bypassing privacy controls, no interaction with subjects,
respect platform terms of service and privacy law.

## Quick Workflow

1. Define the question and confirm the authorization covers social
   media research on public content only.
2. Prepare the research profile: clean browser, VPN, sock puppet with
   no real identity links, no interaction with targets.
3. Identify candidate profiles from the seed data (name, handle,
   email, photo).
4. Verify identity: corroborate across platforms with photos, dates,
   and connections before treating a profile as the subject.
5. Map the network: followers, interactions, and tagged content.
6. Extract media and metadata; geolocate where posts allow it.
7. Timeline the findings and assign confidence levels.
8. Archive everything with timestamps and write the report.

## 1. Research setup and OPSEC

```bash
# Dedicated browser profile for research (example: Chromium)
/usr/bin/chromium --user-data-dir=/cases/acme/soc-profile --incognito &

# Never reuse: one sock puppet per engagement, created with a case email
# No personal photos, no phone numbers tied to you, no real friends

# Keep a research log from the first search
echo "$(date -u +%FT%TZ) start: seed handle @example" >> /cases/acme/log.md
```

Rules that keep you lawful and safe:

- View public content only. If a profile is private, it is out of
  scope unless the authorization explicitly covers it (it usually
  does not).
- Never send follows, friend requests, messages, likes, or comments
  to subjects. Observation only.
- Do not use scraping tools that violate the platform's terms of
  service. Manual review and official APIs or export features are the
  safe path.
- Separate research activity from personal accounts completely.

## 2. Profile identification and verification

Start from seeds: a handle, an email, a phone number, or a photo.
Find candidate profiles, then verify before analysis.

Verification checklist:

- Photo match across two or more platforms (same face, same
  distinctive background).
- Date consistency: account creation, employment dates, life events
  that align.
- Network overlap: mutual connections who are plausibly real.
- Content consistency: writing style, locations, interests match.

```bash
# Reverse image search starting points (manual, in the research browser):
# - Google Images / Lens upload of the profile photo
# - TinEye for older copies of the same image
# Note where else the photo appears and the earliest date found
```

A profile that fails verification is not the subject. Report it as
unverified rather than building analysis on it.

## 3. Timeline and network mapping

Build a timeline of public posts: dates, locations mentioned,
employment changes, travel. Clusters reveal routines and time zones.

Network mapping, manually:

- List public followers and followees; note which look like real
  people vs bots (no photo, no posts, following thousands).
- Record interactions: who comments regularly, who is tagged in
  photos, who appears across platforms.
- Draw the graph on paper or in a link analysis tool; shared
  connections between two identities suggest they are the same person
  or close associates.

```bash
# Simple interaction log format (TSV, UTC dates)
# date        platform  actor       action    target      url
printf '2026-10-20\tinstagram\t@seed\tpost\t-\thttps://...\n' \
  >> /cases/acme/interactions.tsv
```

## 4. Image and video forensics

Downloaded media carries evidence. Work on copies, keep originals
hashed.

```bash
# Inspect EXIF metadata (install exiftool in your environment)
exiftool -a -G1 photo.jpg | grep -iE "gps|create date|make|model|software"

# GPS coordinates to a map link (verify they are plausible, not spoofed)
# Check CreateDate vs the post date: mismatches suggest recycled images

# Hash everything for the evidence log
sha256sum evidence/* > evidence/hashes.txt
```

What to extract: embedded GPS, device model, timestamps, software
traces (edited in Photoshop vs straight from a phone), and thumbnails
that differ from the main image (a sign of editing). Many platforms
strip EXIF on upload; absence of metadata is normal, presence is a
bonus. Never rely on a single GPS tag for a location conclusion.

## 5. Geolocation from public posts

Geolocate using visible clues, corroborated:

- Landmarks, street signs, shop names, license plates (region).
- Vegetation, architecture, and language on signage.
- Shadows and sun angle for rough time of day (supporting, not
  primary, evidence).
- Check-ins, tagged locations, and event posts the subject made
  public.

```bash
# Keep a geolocation worksheet per assessed location
# location | clue | source URL | archive URL | confidence
printf 'Brussels\tGrand Place in background\thttps://...\tarchive/...\tprobable\n' \
  >> /cases/acme/geolocation.tsv
```

Confirm with at least two independent clues before reporting a
location. One photo of a famous landmark proves a visit, not a home
address.

## 6. Brand and threat monitoring uses

Defensive applications that stay clearly lawful:

- Monitor public mentions of your brand for phishing kits, fake
  support accounts, and scam ads impersonating the company.
- Track ransomware groups' public leak sites for your organization
  name (this is public threat intel collection).
- Verify breach claims: a claimed leak gets checked against what is
  actually posted before anyone reacts.
- Executive exposure review: what public posts reveal travel plans,
  family details, or security answers, reported back for reduction.

## 7. Cross-platform handle correlation

Subjects reuse handles, emails, and usernames across platforms. Use
that to link identities, carefully.

```bash
# Check a handle across platforms with a lightweight Python prober
# (HEAD requests only, respects rate limits, no scraping of content)
python3 << 'EOF'
import urllib.request
handle = "example_handle"
sites = {
    "github": f"https://github.com/{handle}",
    "reddit": f"https://www.reddit.com/user/{handle}/",
    "telegram": f"https://t.me/{handle}",
    "medium": f"https://medium.com/@{handle}",
}
for name, url in sites.items():
    try:
        req = urllib.request.Request(url, method="HEAD",
            headers={"User-Agent": "Mozilla/5.0"})
        code = urllib.request.urlopen(req, timeout=10).status
        print(name, "exists:", code == 200)
    except Exception as e:
        print(name, "no match or blocked")
EOF
```

Correlation rules: an exact handle match on two platforms is a lead,
not proof. Confirm with photo, dates, or network overlap before
merging identities in your analysis. Common handles collide; check
the account creation dates and content themes. Record every match
with its URL and your confidence, and keep unverified matches in a
separate "unconfirmed" list so they never leak into the report as
fact.

## Edge cases

- The subject deletes content mid-investigation. Your archive is the
  record; note the deletion date and keep the archived copy.
- Deepfakes and AI-generated profile photos. Check for artifacts,
  reverse image search, and treat single-photo identities as
  unverified.
- Platform changes break your workflow (API closed, layout changed).
  Fall back to manual review; do not deploy scrapers against the new
  terms.
- You are blocked or rate-limited. Stop, note the limitation, and
  use other platforms or sources. Do not evade with new accounts.
- Content in another language. Machine translate and flag quotes as
  translations; verify names and places with a second tool.
- Minors appear in the material. Minimize collection, do not store
  more than the task needs, and escalate handling to the case lead.

## Escalation

- You find credible threats of violence or ongoing crime: follow the
  engagement's reporting chain and local legal obligations; do not
  investigate alone.
- A subject contacts you or detects the research: disengage
  immediately, document the contact, and inform the case lead. Never
  engage in conversation.
- The task needs private content or interaction: stop and get
  explicit written authorization; this usually changes the legal
  basis of the work.
- You accidentally access non-public data: do not copy or use it,
  document the incident, and inform the case lead at once.
- Platform legal threat: cease that collection, preserve your
  authorization, and route through legal.

## Detection and defender view

Social media OSINT defends as well as it exposes:

- Attackers build target profiles from public posts for spear
  phishing (T1598, T1593). Reduce the raw material: review what
  employees post about projects, travel, and org charts.
- Fake executive and support accounts run scams. Monitor for them
  and publish a verified-accounts page so customers can check.
- Attackers verify phishing lures with public details ("your boss
  is traveling"). Train staff that public details prove nothing.
- Defenders can spot pre-attack chatter and infrastructure bragging
  on public channels; treat it as a lead, verify before acting.
- Your own team's OPSEC matters: researchers who slip and interact
  from real accounts burn the operation and create liability.

## Key references

- MITRE ATT&CK T1593 (Search Open Websites/Domains), T1598 (Phishing
  for Information), T1591 (Gather Victim Org Information).
- Platform terms of service for each network researched (read before
  collecting).
- ExifTool documentation: https://exiftool.org/
- Bellingcat's open source investigation guides (methodology
  reference for geolocation and verification).
