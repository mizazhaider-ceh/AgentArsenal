---
name: osint-image-geolocation-landmark-recognition
description: Use when a photo contains visible features that can
  identify its location during an authorized investigation, without
  relying on metadata. Covers systematic visual reading with
  ImageMagick 7.1 crops, signage and language analysis, architecture
  and street furniture identification, license plate and vehicle
  formats, vegetation and terrain clues, reverse image searching, and
  confirming candidates against street-level imagery. Use when the
  parent osint-image-geolocation workflow has no usable EXIF, when
  verifying a claimed location from visual evidence, or when
  narrowing a region from cultural and physical clues, cross-checked
  against ExifTool metadata where available.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-image-geolocation
requires: [osint-image-geolocation]
extends: []
relates: [osint-image-geolocation]
tools:
  - name: ImageMagick
    version: 7.1
  - name: Python
    version: 3.12
  - name: ExifTool
    version: 12.9
---

Landmark recognition is reading a photo like a detective reads a
room: every sign, building style, plate format, and tree species is a
clue that narrows the map. It works when metadata is stripped, which
is most of the time on real cases. This sub-skill teaches the
systematic visual scan, the clue categories that discriminate best,
and how to confirm a candidate location so the geolocation holds up.
Authorized investigations only.

## Quick Workflow

1. Work on a copy; crop regions of interest with ImageMagick for
   close inspection.
2. Read signage: language, script, phone formats, brand names.
3. Read the built environment: architecture, road markings, traffic
   signs, street furniture.
4. Read vehicles: plate formats and colors, driving side, models.
5. Read nature: vegetation, terrain, sky and light quality.
6. Combine clues into a region hypothesis, then a candidate list.
7. Confirm the best candidate against street-level imagery with
   multiple matching features.
8. Write the evidence chain: clue, crop, conclusion, confidence.

## 1. Cropping for inspection

```bash
# Work on a copy; crop regions without touching the original
cp photo.jpg work.jpg
identify work.jpg
# Example: work.jpg JPEG 4032x3024

# Crop the sign (x, y, width, height tuned per image)
convert work.jpg -crop 1400x500+1800+900 sign.jpg
convert work.jpg -crop 1600x900+200+1500 street.jpg
convert work.jpg -crop 1000x800+2500+100 skyline.jpg

# Enhance a dark or distant crop for reading
convert sign.jpg -modulate 110,30 -sharpen 0x1 sign-enhanced.jpg
```

Keep every crop with a descriptive filename; the report references
them as figures. Never upscale beyond readability; enhancement helps
reading, it does not create detail.

## 2. Signage and language

Signage is the highest-discrimination clue category:

- Script and language: Cyrillic narrows enormously, as do Arabic,
  CJK scripts, or distinctive combinations (Dutch plus French
  suggests Belgium).
- Phone number formats: country codes (+32), grouping, and trunk
  prefixes.
- Brand names: chains are regional (a specific supermarket brand
  may exist in three countries).
- Regulatory signs: parking, no-entry, and warning sign designs are
  national standards.

```bash
# Record observations in a structured note as you read
cat > clues.md <<'EOF'
## Signage
- Shop sign: Dutch text "Bakkerij" (crop sign.jpg)
- Phone on van: +32 2 ... (Belgian country code, Brussels area code)
- Parking sign: Belgian design (blue P, white on blue)
EOF
```

Search distinctive business names directly: a quoted shop name in a
web search often returns the address, which becomes candidate one.

## 3. Built environment

- Architecture: brick terraces versus Haussmann blocks versus
  Soviet prefabs each suggest regions; roof shapes and window
  styles refine further.
- Road markings: center line color (yellow in the US, white in
  much of Europe), crosswalk styles (zebra versus continental).
- Traffic signs: shape and color conventions are national (US
  yellow diamonds, European red-bordered triangles).
- Street furniture: lamp post designs, bollards, bins, and bus
  stops are often municipal standards.
- Infrastructure: power line styles, tram tracks, curb heights.

No single feature proves a location; the combination does. "Brick
terraces plus red phone box plus left-hand traffic" is England in
three clues.

## 4. Vehicles and plates

```bash
# Crop and read plates where visible (follow case privacy policy on retention)
convert work.jpg -crop 600x200+1500+2000 plate.jpg
```

Plate knowledge that discriminates fast:

- Plate color schemes: yellow rear plates (UK, Netherlands),
  blue EU band on the left (most of Europe), white on green
  (some regions).
- Plate format: letter and digit groupings are national.
- Driving side: which side of the road vehicles use, visible from
  parked cars or traffic flow.
- Vehicle models: some models are region-specific (kei cars in
  Japan, utes in Australia).

A plate gives country; the format plus a city code on the plate can
give the region. Never run a plate through unauthorized lookup
services; the visual format analysis is the authorized technique.

## 5. Vegetation, terrain, and sky

- Trees: palms versus pines versus deciduous; eucalyptus suggests
  Australia or California; olive suggests the Mediterranean.
- Terrain: flat polder versus hills versus mountains in the
  background.
- Sky and light: quality of light suggests latitude, though this
  is weak alone; combine with the shadow analysis sub-skill for
  real constraint.

These clues are coarse but they kill wrong hypotheses fast: palms
eliminate Scandinavia no matter what the sign says (unless it is a
botanical garden, which is why clues combine).

## 6. Reverse image search

```bash
# Upload the crop (not the full image if people are visible) to reverse image search
# Engines index landmarks, business fronts, and tourist photos well
# Use the sign or skyline crop for distinctive features
```

Reverse search works best on: famous landmarks, hotel fronts,
restaurant signs, and street art. It works poorly on: generic
residential streets, interiors, and night shots. When it hits, the
result still needs confirmation against street-level imagery; search
results mislabel locations routinely.

## 7. Confirming against street-level imagery

The candidate from clues must survive contact with street-level
imagery. Match at least three independent features:

```bash
cat > confirmation.md <<'EOF'
## Candidate: Rue des Bouchers 12, Brussels
Feature 1: bakery sign "Bakkerij" matches facade (crop sign.jpg vs sv-1.png)
Feature 2: lamp post design matches (crop street.jpg vs sv-2.png)
Feature 3: road curve and crosswalk position match (overview vs map)
Imagery date: 2025-06 (facade may have changed since)
Verdict: CONFIRMED at street level
EOF
```

If the imagery is newer than the photo, expect changes and weight
structural features (road layout, building massing) over cosmetic
ones (paint, signage). If imagery is unavailable for the area,
state the confirmation gap honestly.

## Edge cases

- The photo is indoors. Landmark recognition may only reach the
  building or the city (outlet styles, language on fire exit
  signs). State the limit.
- Tourist landmarks are easy; residential streets are hard. Budget
  effort accordingly and say so in the case plan.
- The image is heavily filtered (color shifts). Do not trust color
  clues (plate colors, vegetation tone); rely on shapes and text.
- Multiple locations share the chain store or franchise look.
  Franchises are weak locators; the street around them is the
  locator.
- The photo mixes locations (a collage or a composite). Analyze
  each panel separately; composites are common in disinformation
  cases.
- Night or bad weather hides most clues. Note what is unusable
  and lean on signage and artificial landmarks.

## Escalation

- Visual clues point to a private residence and the case does not
  authorize locating individuals. Stop and escalate the scope
  question before refining further.
- The location is critical and confidence is stuck at medium. Bring
  in a second analyst for an independent read; fresh eyes catch
  clues the first reader normalized.
- The image appears staged or AI-generated (impossible shadows,
  garbled text). Escalate to a media-forensics review; geolocating
  a synthetic image wastes the case and risks a false attribution.
- Clues contradict each other (Arabic sign, Scandinavian
  architecture). Treat the contradiction as the finding: the photo
  may be misattributed, edited, or from a diaspora neighborhood,
  and each hypothesis needs testing.

## Detection and defender view

Landmark recognition is defeated by awareness: photograph against
nondescript backgrounds, avoid signage and distinctive buildings,
and remember that even a bus stop design can place you. Platforms
stripping EXIF does not strip the pixels, so visual hygiene is the
real defense. For investigators, the defender view is a privacy
discipline: the sharper your visual reading gets, the more careful
you must be about whose location you are determining and why the
authorization covers it.

## Key references

- Parent workflow: osint-image-geolocation (this repo)
- Bellingcat geolocation guides:
  https://www.bellingcat.com/resources/
- Mapillary: https://www.mapillary.com/
- OpenStreetMap: https://www.openstreetmap.org/
- License plate format references (country standards)
- Google Earth and street-level imagery documentation
