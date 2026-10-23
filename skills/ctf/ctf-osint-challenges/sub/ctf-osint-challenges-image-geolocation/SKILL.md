---
name: ctf-osint-challenges-image-geolocation
description: Use when a CTF OSINT challenge provides a photo that must be
  located, or when geolocating imagery you are authorized to analyze.
  Covers the visual clue checklist (signage, architecture, vegetation,
  license plates, sun shadows), reverse image search across engines,
  Street View and satellite verification, using maps and terrain features,
  and confirming a location with two independent signals. Use when handed
  a photo with no metadata, when EXIF GPS is stripped, or when the flag
  is the place itself (coordinates, venue name, street address).
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-osint-challenges
requires: [ctf-osint-challenges]
extends: []
relates: [osint-methodology, ctf-osint-challenges]
tools:
  - name: Python
    version: 3.12
  - name: ExifTool
    version: 12.90
---

Image geolocation is identifying where a photo was taken from visual
evidence alone. CTF challenges strip EXIF GPS and expect you to read the
scene: text on signs, architectural styles, vegetation, license plates,
and sun angles. This sub-skill covers the authorized competition
workflow: systematic clue extraction, search strategies, and verification
discipline. Scope is CTF competitions and imagery you are authorized to
analyze.

## Quick Workflow

1. Check EXIF anyway (`exiftool`); stripped GPS is the norm but
   thumbnails and software tags sometimes survive.
2. Extract every readable clue: text on signs, shop names, license
   plates, flags, phone number formats, language.
3. Note environmental clues: vegetation, terrain, architecture style,
   road markings, vehicle models, sun direction and shadow length.
4. Reverse image search the photo (Google Lens, Bing, Yandex, TinEye)
   to check whether it is a stock or previously published image.
5. Search distinctive text clues in quotes plus candidate regions.
6. Verify on Street View or satellite imagery: match 3+ independent
   details (a sign, a building shape, a road layout).
7. Produce the answer in the required format (coordinates, address,
   venue name) with the verification trail.
8. Never submit a guess from one clue; geolocation needs
   corroboration.

## 1. The visual clue checklist

Work through this list on every photo before searching:

- Text: shop signs, street signs, billboards, license plates, menus,
  posters. Transcribe exactly, including language and script.
- Numbers: phone country codes (+32 Belgium, +33 France), postal
  codes, license plate formats and colors.
- Architecture: roof shapes, window styles, building materials,
  church or mosque silhouettes, construction style.
- Nature: tree species (palms vs pines), terrain (flat vs hills),
  sky and light quality.
- Infrastructure: road marking colors, sidewalk style, power line
  design, traffic sign shapes (EU round vs US diamond).
- People and vehicles: license plates, taxi colors, bus liveries,
  clothing styles.
- Sun: shadow direction gives hemisphere and rough time; long
  shadows mean morning or evening.

Write clues down; the list becomes your search query set.

## 2. Reverse image search strategy

```bash
# No CLI does this well; use the web UIs and compare:
# - Google Lens: best for landmarks and text in image
# - Bing Visual Search: strong on similar scenes
# - Yandex Images: strong on faces and Eastern Europe / Central Asia
# - TinEye: best for finding the earliest publication (original source)
```

If the image is a cropped stock photo, TinEye finds the original with
its caption and location. If it is AI-generated or a composite, reverse
search fails and the challenge expects pure clue reading; look for
inconsistencies (impossible shadows, garbled text) as the hint.

## 3. Searching from text clues

```bash
# Quoted distinctive phrases plus region guesses
# "Café de la Poste" brussels
# "Pizzeria Napoli" "via Roma" street view
# license plate format: search "<format description> license plate country"
```

Search the transcribed sign text in quotes; small businesses have
unique names that resolve to an address instantly. For non-Latin
scripts, use Lens to transcribe, then search the transcription. When a
phone number is visible, the country code narrows the search to one
country immediately.

## 4. Verification with maps

1. Drop the candidate address into Street View; walk virtually to the
   photo's viewpoint.
2. Match at least three details: a distinctive sign, a building
   facade, the road curve, a lamppost style.
3. Cross-check with satellite view: roof shapes and parking lots
   should match the photo's background.
4. Check the sun: does the shadow direction in Street View imagery
   (noting its capture date) roughly agree with the photo?

A single matching sign is not enough; signs move. Three independent
static features (building, road layout, permanent fixture) is the
standard.

## 5. Coordinates from shadows (rough)

When the challenge wants coordinates and clues are thin:

- Hemisphere: shadows point away from the equator at noon; in the
  northern hemisphere, noon shadows point north.
- Shadow length vs object height gives sun elevation; with a known
  date (event posters, EXIF CreateDate), solar calculators estimate
  latitude within a few degrees.
- This is a corroboration technique, not a primary one; use it to
  choose between two candidate cities, not to derive coordinates
  from scratch.

## Edge cases

- Indoor photo: geolocate via distinctive interiors (chain
  restaurants, hotel lobbies, venue stages); search the visible
  branding, not the architecture.
- Night photo: fewer clues; rely on lit signage and light pole
  designs, plus any visible text.
- Heavily cropped photo: reverse search the crop anyway (engines
  handle crops well); the original may be wider and more revealing.
- The location is fictional or a game map: recognize the style
  (game UI elements, impossible geography) and switch to
  game-community wikis rather than real maps.
- The photo is a screenshot (maps app, game, video): geolocate the
  depicted content, not the screenshot chrome; UI elements date the
  capture but not the place.

## Escalation

- No readable text and generic scenery: look at the smallest
  details (a power outlet shape, a manhole cover design, a
  distinctive tree); CTF photos always contain one deliberate clue.
- Reverse search finds nothing and clues are ambiguous: widen the
  region search with the strongest single clue (a unique shop name
  beats ten generic ones).
- Two candidate locations both match: find the discriminator (a
  second sign, a license plate, a phone code) rather than guessing.
- Time is short: prioritize quoted text search; it resolves faster
  than visual comparison in most CTF geolocation challenges.

## Detection and defender view

Defenders use geolocation awareness to protect people and operations:
training staff that photos leak locations, stripping EXIF before
publishing, and reviewing backgrounds in shared images. For
investigators, the same skills verify the provenance of viral images
and detect misattributed locations. Organizations monitor for exposed
imagery of sensitive sites (data centers, executive homes) and request
takedowns. The durable lesson: every photo is a potential location
disclosure; treat publication as intentional disclosure.

## Key references

- MITRE ATT&CK T1593 (Search Open Websites/Domains).
- Bellingcat geolocation guides: https://www.bellingcat.com/resources/
- Google Earth / Street View and Bing Maps (verification tools).
- SunCalc (shadow and sun position): https://www.suncalc.org/
- GeoGuessr community guides (visual clue reading techniques).
