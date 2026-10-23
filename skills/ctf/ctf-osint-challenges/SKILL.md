---
name: ctf-osint-challenges
description: Use when competing in a CTF OSINT challenge, practicing in a
  lab, or researching information you are authorized to collect. Covers the
  OSINT workflow for competitions, hunting usernames across platforms,
  geolocating images from visual clues, extracting metadata from files,
  using public records and archives, verifying findings before submitting,
  and staying within the challenge rules and the law. Use when given a
  username, photo, or vague clue, when the flag hides in public data, or
  when you need to attribute an online persona in an authorized setting.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [osint-methodology, ctf-competition-playbook]
tools:
  - name: Python
    version: 3.12
  - name: ExifTool
    version: 12.90
  - name: curl
    version: 8.5
  - name: CyberChef
    version: latest
---

OSINT challenges hide flags in public information: social profiles,
photos with location clues, file metadata, archived pages, and public
records. The winning pattern is breadth first (enumerate every source
the clue could live in), then depth on the promising lead, then
verification (two independent sources before submitting). This skill
covers the authorized competition methodology with concrete tools and
search techniques. Scope is CTF competitions, lab exercises, and
information you are authorized to collect; it never covers private data,
unauthorized access, or harassment.

## Quick Workflow

1. Read the challenge text precisely; every word is a potential
   search term, username, or coordinate hint.
2. Classify the artifact: username, image, document, URL, or vague
   description, and pick the matching sub-skill path.
3. Enumerate broadly: search engines (with operators), platform
   searches, archives (Wayback Machine), and metadata.
4. Follow the strongest lead: one confirmed profile or location beats
   ten maybes.
5. Pivot: usernames repeat across platforms, photos contain landmarks,
   documents contain authors.
6. Verify with a second independent source before submitting (two
   sources or it did not happen).
7. Respect the rules: no interacting with real people (no DMs, no
   friend requests), no attempting logins, public data only.
8. Record sources and queries for the writeup; OSINT writeups need
   reproducibility.

## 1. Search engine operators for CTF OSINT

```bash
# Google/Bing dorks that solve CTF OSINT fast
# site:github.com "<username>"
# site:linkedin.com/in "<full name>"
# "<username>" -site:twitter.com      # exclude noisy domains
# filetype:pdf "<event name>"         # documents
# inurl:profile "<username>"

# Automate multi-engine username checks (see username-hunting sub-skill)
# and archive lookups:
curl -s "http://archive.org/wayback/available?url=example.com/page" | python3 -m json.tool
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com/*&output=json&limit=20" | head -30
```

Search the exact challenge strings in quotes first; CTF authors reuse
handles and phrases across events, and quoted search finds the original.

## 2. Image triage for location and identity

```bash
# Metadata first: GPS coordinates end many challenges immediately
exiftool photo.jpg | grep -i -E "gps|create date|camera|software|comment|author"

# Reverse image search: upload to the major engines and compare results
# (Google Lens, Bing Visual Search, TinEye, Yandex Images)
# Yandex is notably strong on faces and Eastern European locations;
# use it for person-identification style challenges within the rules.

# If no metadata: note landmarks, signs, license plates, vegetation,
# architecture style, and language on signage; feed these to the
# image-geolocation sub-skill workflow.
```

Never enhance or identify real private individuals beyond the challenge
scope; CTF OSINT targets fictional or consenting personas, and the
rules usually forbid contacting anyone.

## 3. Document and file metadata

```bash
exiftool -a -u document.pdf | head -60
# Author, Creator, Producer, CreateDate, GPS, embedded thumbnails

# Office documents: unzip and read the XML
unzip -p doc.docx docProps/core.xml
unzip -p doc.docx docProps/app.xml

# PDF: check for hidden layers and embedded files
pdfinfo document.pdf
strings document.pdf | grep -i -E "author|flag" | head

# Audio/video: same exiftool pass; check encoder strings for usernames
exiftool video.mp4 | grep -i -E "encoder|author|comment|gps"
```

Metadata often contains the author's handle, software usernames, or GPS;
each is a pivot into the username-hunting or geolocation workflows.

## 4. Public records and archives

- Wayback Machine: past versions of challenge-linked pages often
  contain the flag or the clue that was later removed.
- GitHub: search code and commits for the username; commit emails
  leak real names, and old commits contain removed secrets.
- Certificate transparency (crt.sh): subdomains of challenge domains
  reveal staging or admin hosts.
- DNS history and WHOIS: creation dates and registrant handles for
  attribution-style challenges.

```bash
# crt.sh subdomain enumeration for a challenge domain
curl -s "https://crt.sh/?q=%25.example-ctf.com&output=json" | \
  python3 -c "import json,sys; [print(r['name_value']) for r in json.load(sys.stdin)]" | sort -u | head -20
```

## 5. Verification before submission

OSINT answers feel certain and are often wrong. Require:

- Two independent sources agreeing (e.g. EXIF GPS plus a matching
  Street View landmark).
- The flag format matches the event's pattern.
- No contradiction from a source you already checked (a profile
  saying "moved to Berlin in 2020" kills a 2024 Paris geolocation).

When sources conflict, trust primary artifacts (metadata, archived
pages) over secondary claims (bios, comments).

## Edge cases

- The challenge persona is fictional: in-event OSINT uses planted
  profiles; treat them like real OSINT but expect the trail to be
  short and deliberate.
- Search engines return nothing: try alternative spellings,
  leetspeak variants, and other languages; also check platform
  internal search, which indexes what Google does not.
- The image has no EXIF and no landmarks: look at shadows (sun
  angle gives latitude hints), license plates, and tiny text;
  enhance carefully without inventing details.
- Rate limits on APIs (GitHub, social platforms): use authenticated
  tokens where allowed and cache results; do not hammer endpoints.
- The challenge mixes OSINT with another category (a hash in a profile
  bio): solve each half with its own skill and keep the pivots labeled
  by source.

## Escalation

- Every lead dead-ends: re-read the challenge text for the clue you
  skimmed (a date, a version number, a misspelling); CTF OSINT always
  has a planted starting thread.
- The trail points at a real person: stop and check the rules; most
  events forbid real-person targeting, and the intended path is
  elsewhere.
- Attribution is ambiguous between two candidates: look for the
  discriminator (a unique photo, a specific date) rather than
  collecting more weak matches.
- Time is short: prioritize metadata and archives; they are the two
  fastest high-yield sources in CTF OSINT.

## Detection and defender view

Defenders practice OSINT defensively: auditing what public data exposes
about their organization (employee handles, photo metadata, document
authors, exposed subdomains) and removing it. Detection of hostile
OSINT is hard because it uses public sources, so defense focuses on
reducing the attack surface: strip metadata before publishing, use
separate professional and personal handles, and monitor certificate
transparency for lookalike domains. For individuals: review photo
backgrounds, disable geotagging, and audit old profiles.

## Key references

- MITRE ATT&CK T1593 (Search Open Websites/Domains) and T1598
  (Phishing for Information)-adjacent search techniques; the
  reconnaissance tactics family (TA0043).
- OSINT Framework: https://osintframework.com/
- Bellingcat's open source investigation toolkit:
  https://www.bellingcat.com/resources/
- Wayback Machine: https://web.archive.org/
- ExifTool: https://exiftool.org/
