---
name: osint-image-geolocation
description: Use when you need to determine where a photograph was
  taken during an authorized investigation, using only the image and
  public sources. Covers preserving the original file, EXIF and GPS
  metadata extraction with ExifTool 12.9, visual landmark and
  vegetation analysis, sun and shadow analysis for time and direction,
  cross-checking against maps and street-level imagery, and writing a
  confidence-rated geolocation report. Use when an investigation
  provides photos of unknown provenance, when verifying a claimed
  location, or when corroborating other evidence. Authorized cases
  only, with care for pictured individuals' privacy, cropping regions
  of interest with ImageMagick.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [image-osint, osint-methodology, osint-username-enumeration]
tools:
  - name: ExifTool
    version: 12.9
  - name: Python
    version: 3.12
  - name: ImageMagick
    version: 7.1
---

Image geolocation determines where a photo was taken from its pixels
and metadata: GPS tags, landmarks, signage language, vegetation, sun
angle, and street furniture. Investigators use it to verify claimed
locations and to place events. This skill covers the method from file
preservation through metadata, visual analysis, solar analysis, and
the confidence-rated report. It applies only to authorized
investigations and respects privacy: geolocating a photo of a private
individual without authorization is not in scope, and faces and
plates get handled per your case policy.

## Quick Workflow

1. Confirm authorization and the question: exact location, or
   verification of a claimed one.
2. Preserve the original: hash it, work on copies, never re-encode
   the original.
3. Extract EXIF with ExifTool; check for GPS tags, timestamps, and
   device info.
4. Do the visual read: landmarks, signage, language, vegetation,
   vehicles, street furniture.
5. Run sun and shadow analysis for direction and time of day.
6. Cross-check candidate locations against maps and street-level
   imagery.
7. Score confidence and write the report with evidence per claim.
8. Handle privacy: minimize retention of images with identifiable
   people.

## 1. Preservation

```bash
# Hash the original immediately; every later step works on copies
sha256sum photo.jpg | tee photo.sha256
cp photo.jpg work-photo.jpg

# Confirm it is what it claims to be
file photo.jpg
identify -verbose work-photo.jpg | grep -E "Geometry|Format|Colorspace"
```

Example output shape:

```
photo.jpg: JPEG image data, Exif, 4032x3024
  Geometry: 4032x3024
  Format: JPEG
```

If the file was re-encoded by a messaging app or social platform,
EXIF is likely stripped and resolution reduced; note the provenance
chain, since each re-encode destroys evidence.

## 2. EXIF extraction

```bash
# Full EXIF dump
exiftool photo.jpg > exif.txt
wc -l exif.txt

# The fields that matter for geolocation
exiftool -GPSPosition -GPSLatitude -GPSLongitude -GPSAltitude \
  -CreateDate -DateTimeOriginal -Make -Model -Software photo.jpg

# Extract the embedded thumbnail (sometimes it differs from the main image)
exiftool -b -ThumbnailImage photo.jpg > thumb.jpg
```

Example output shape:

```
GPS Position                    : 50.8503 N, 4.3517 E
Create Date                     : 2026:10:20 14:32:11+02:00
Make                            : Google
Model                           : Pixel 8
Software                        : HDR+ 1.0
```

A GPS position is the fastest answer, but verify it: check that the
timestamp, the visible landmarks, and the sun angle agree with the
coordinates. Spoofed or stale GPS tags happen, especially in
screenshots of maps rather than true photos. No GPS data is normal
for images from messaging apps; proceed to visual analysis.

## 3. Visual read: the systematic scan

Work through the image in layers, nearest to farthest:

1. Foreground: signage text and language, license plates (country
   format), shop names, phone number formats.
2. Midground: architecture style, road markings, traffic signs,
   vehicle models, street furniture (lamp posts, bins).
3. Background: skyline, mountains, distinctive buildings, church
   spires, construction cranes.
4. People and vehicles: uniforms, license plate colors, driving
   side (left or right).
5. Vegetation and terrain: palm versus pine, arid versus green.

```bash
# Crop regions for closer inspection without touching the original
convert work-photo.jpg -crop 1200x800+2000+400 sign-crop.jpg
convert work-photo.jpg -crop 1000x700+500+1800 skyline-crop.jpg
```

Record each observation as a separate line with the crop filename.
"The sign is in Dutch" narrows to a few countries; "the license
plate is yellow rear, white front" narrows to one.

## 4. Sun and shadow analysis

Shadows give direction and time. The sub-skill
osint-image-geolocation-shadow-and-sun-analysis covers the full
method; the essentials:

- In the northern hemisphere at midday, shadows point north; in the
  southern hemisphere, south.
- Shadow length versus object height gives the sun's elevation,
  which maps to time of day for a known date and latitude.
- The visible sun position plus the EXIF timestamp cross-checks the
  claimed timezone.

```bash
# Measure in the image: pick a vertical object with a clear shadow
# Record pixel lengths; the ratio is what matters, not absolute size
# shadow_pixels / object_pixels = 1 / tan(elevation)
python3 - <<'EOF'
import math
ratio = 1.4  # shadow is 1.4x the object height
elevation = math.degrees(math.atan(1 / ratio))
print(f"sun elevation ~{elevation:.1f} degrees")
EOF
```

## 5. Cross-checking with maps

Take the candidate from visual analysis and verify against
street-level imagery: match the building facades, the road layout,
the lamp post style, the shopfronts. A geolocation is confirmed when
multiple independent features match the same spot: the sign text,
the building across the street, and the road curve all agree.

```bash
# Keep a verification log per candidate
cat > candidates.md <<'EOF'
## Candidate 1: Grand Place area, Brussels
- Sign language Dutch/French: consistent
- Facade match on street view: YES (screenshot sv-1.png)
- Shadow direction vs EXIF time: consistent (north, midday)
- Confidence: high
EOF
```

One matching feature is a lead; three independent matches are a
geolocation. If street-level imagery is outdated, note the imagery
date; facades change.

## 6. Confidence-rated reporting

```
Claim: photo taken at Grand Place, Brussels (50.8467 N, 4.3525 E)
Confidence: high
Evidence:
- EXIF GPS 50.8503 N, 4.3517 E (400 m from claim, consistent)
- Signage in Dutch and French (crop sign-crop.jpg)
- Facade match on street-level imagery (sv-1.png, imagery dated 2025-06)
- Shadow analysis: sun elevation ~35 deg, consistent with 14:32 local in October
Limitations: no distinctive landmark in frame; location is street-level, not building-level
```

Always state the precision honestly: city-level, street-level, or
building-level. Overclaiming precision is the classic geolocation
failure.

## Edge cases

- EXIF is stripped (social media, messaging apps). Proceed with
  visual and solar analysis; note the provenance loss.
- The image is a screenshot, not a photo. GPS tags may show the
  screenshot location, not the depicted location; treat metadata as
  suspect and rely on visual content.
- Night photo: no shadows, limited color. Lean on signage,
  architecture, and any visible skyline; artificial lighting color
  temperature is a weak clue at best.
- Indoor photo: geolocation may be impossible beyond the building
  if identifiable. State that plainly rather than guessing.
- The photo is old and the location has changed. Historical
  street-level imagery and archives help; note the imagery dates.
- Multiple plausible candidates. Rank them with evidence for each
  and pick the best-supported; do not force a single answer.
- Faces or plates are visible. Follow your case policy: blur in
  working copies if required, minimize retention, and never publish
  identifiable images without authorization.

## Escalation

- The geolocation would identify a private individual's home or
  routine. Stop and check authorization: locating private persons
  is outside most OSINT scopes and may be unlawful.
- The image appears to depict wrongdoing within your authorized
  scope. Preserve the original with hashes, document the chain of
  custody, and escalate to the case owner before further analysis.
- Confidence stays low after full analysis. Report "unresolved"
  with the evidence gathered; a wrong geolocation is worse than
  none, especially if operational decisions depend on it.
- The photo is one of a series. Geolocate the easiest first; a
  confirmed location for one image constrains the others.

## Detection and defender view

Geolocation is defeated by stripping metadata (which most platforms
do automatically), avoiding distinctive backgrounds, and being aware
of what signage and landmarks reveal. For investigators, the
defender view is a reminder of privacy impact: the same techniques
that verify a news photo can locate a person, so authorization and
minimization are not bureaucracy but the ethical core of the work.
When publishing geolocation results, consider whether the location
detail serves the investigation or merely exposes someone.

## Key references

- ExifTool documentation: https://exiftool.org/
- Bellingcat geolocation guides:
  https://www.bellingcat.com/resources/
- SunCalc (sun position for any location and time):
  https://www.suncalc.org/
- Shadow analysis methodology (sub-skill):
  osint-image-geolocation-shadow-and-sun-analysis (this repo)
- Mapillary street-level imagery: https://www.mapillary.com/
- OpenStreetMap: https://www.openstreetmap.org/
- Image OSINT references: image-osint (this repo)
