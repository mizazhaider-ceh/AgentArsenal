---
name: osint-image-geolocation-exif-analysis
description: Use when a photo in an authorized investigation may
  contain embedded metadata worth extracting. Covers reading EXIF,
  IPTC, and XMP with ExifTool 12.9, interpreting GPS tags and
  coordinate formats, checking timestamps and timezone offsets,
  extracting embedded thumbnails, detecting stripped or manipulated
  metadata, and converting coordinates for map use with Python 3.12.
  Use when the parent osint-image-geolocation workflow reaches the
  metadata phase, when verifying whether metadata survived a
  platform upload, or when a timestamp needs timezone reconciliation.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-image-geolocation
requires: [osint-image-geolocation]
extends: []
relates: [osint-image-geolocation]
tools:
  - name: ExifTool
    version: 12.9
  - name: Python
    version: 3.12
  - name: ImageMagick
    version: 7.1
---

EXIF analysis reads the metadata cameras and phones embed in image
files: GPS coordinates, timestamps, device model, and settings. It is
the fastest path to a geolocation when present, and its absence is
itself information about provenance. This sub-skill covers
extraction, interpretation, verification, and the common ways
metadata lies. Authorized investigations only; handle images of
people per your case privacy policy.

## Quick Workflow

1. Hash the original and work on a copy.
2. Dump all metadata with ExifTool and save it to the case file.
3. Read GPS tags first: position, altitude, and GPS timestamp.
4. Read timestamps: creation, modification, and timezone offsets.
5. Read device and software tags for provenance clues.
6. Extract the embedded thumbnail and compare it with the image.
7. Check for signs of stripping or manipulation.
8. Convert coordinates to decimal and verify against visual
   evidence.

## 1. Full metadata dump

```bash
# Everything, grouped and sorted for reading
exiftool -G -s photo.jpg > exif-full.txt
wc -l exif-full.txt

# Human-readable summary of the interesting groups
exiftool -EXIF:all -GPS:all -XMP:all photo.jpg | head -60
```

Example output shape:

```
[EXIF]    Make                            : Google
[EXIF]    Model                           : Pixel 8
[EXIF]    DateTimeOriginal                : 2026:10:20 14:32:11
[EXIF]    CreateDate                      : 2026:10:20 14:32:11
[GPS]     GPSLatitude                     : 50 deg 51' 1.08" N
[GPS]     GPSLongitude                    : 4 deg 21' 6.12" E
[GPS]     GPSAltitude                     : 32 m Above Sea Level
[GPS]     GPSDateStamp                    : 2026:10:20
[GPS]     GPSTimeStamp                    : 12:32:11
[XMP]     Creator                         : darkcoder
```

Note the GPS timestamp is UTC (12:32) while the EXIF time is local
(14:32, UTC+2). That two-hour offset is itself a timezone clue;
mismatched offsets suggest the metadata was edited or the device
clock was wrong.

## 2. GPS tags in depth

```bash
# Decimal coordinates ready for maps
exiftool -GPSPosition -n photo.jpg
# -n prints in decimal: 50.850300, 4.351700

# All GPS fields including accuracy and processing method
exiftool -GPS:all photo.jpg
```

Fields to check beyond the position:

- `GPSAltitude`: inconsistent altitude (say, 3000 m for a street
  photo) suggests spoofing or a stale fix.
- `GPSProcessingMethod`: GPS versus CELLID versus WLAN; cell and
  wifi fixes are coarser.
- `GPSDOP`: dilution of precision; high DOP means a weak fix.
- `GPSDateStamp` versus `DateTimeOriginal`: a photo whose GPS date
  differs from its capture date reused an old location fix.

```python
# coords.py: decimal conversion and a maps link for the case file
lat, lon = 50.850300, 4.351700
print(f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}")
```

## 3. Timestamps and timezones

```bash
# All date fields, with timezone offsets where present
exiftool -time:all -d "%Y-%m-%d %H:%M:%S%z" photo.jpg

# File system dates for comparison (can differ after copying)
exiftool -FileModifyDate -FileCreateDate photo.jpg
```

Interpretation rules:

- `DateTimeOriginal` is the capture moment in the device's local
  time; the offset (`+02:00`) may be present in newer files.
- `GPSDateStamp`/`GPSTimeStamp` are always UTC; the difference to
  `DateTimeOriginal` gives the device's UTC offset at capture.
- `FileModifyDate` newer than the EXIF dates means the file was
  edited or re-saved after capture; treat metadata as less
  trustworthy from that point.
- `CreateDate` differing from `DateTimeOriginal` by seconds is
  normal (shutter versus file write); differing by hours is not.

## 4. Thumbnail extraction and comparison

```bash
# Extract the embedded thumbnail
exiftool -b -ThumbnailImage photo.jpg > thumb.jpg
identify thumb.jpg

# Compare visually: the thumbnail sometimes predates edits to the main image
```

If the thumbnail shows a different scene than the main image, the
photo was edited and the metadata may describe the original. That
mismatch is a finding about provenance, and the thumbnail itself
may be the more truthful artifact.

## 5. Detecting stripped or manipulated metadata

```bash
# What metadata groups exist at all
exiftool -G1 -s photo.jpg | cut -d: -f1 | sort | uniq -c

# Software tag often names the editor
exiftool -Software -CreatorTool -HistorySoftwareAgent photo.jpg

# Check for resave signatures: JPEG quantization tables change on re-encode
exiftool -JPEGDigest photo.jpg
```

Signs of manipulation: EXIF present but GPS selectively removed
(suggests deliberate stripping), `Software: Adobe Photoshop` with
original timestamps intact (edited but honest), quantization tables
indicating multiple re-encodes (provenance chain through platforms),
or metadata that contradicts the pixels (winter clothing with a
July timestamp).

Platform behavior to know: major social networks and messaging apps
strip GPS and most EXIF on upload; some keep basic dimensions and
orientation. An image "from WhatsApp" with full GPS is suspicious,
not lucky.

## 6. Verification against the pixels

Metadata is a claim; the image is the evidence. Cross-check:

1. Plot the GPS point: does the street-level imagery match the
   photo's buildings and signs.
2. Compare the timestamp with the sun angle (shadow sub-skill).
3. Compare the device model with the image characteristics
   (resolution matches the sensor).
4. Check the timezone offset against the claimed location's
   offset on that date (daylight saving transitions catch
   fabrications).

```bash
# Quick consistency summary for the case file
cat > exif-verdict.md <<'EOF'
## EXIF verdict: photo.jpg
GPS: 50.8503 N, 4.3517 E (GPS fix, DOP low)
Time: 2026-10-20 14:32 local (+02:00), GPS UTC 12:32 (consistent)
Device: Pixel 8, resolution matches sensor
Edits: none indicated (no Software tag, single encode)
Pixel cross-check: PENDING (visual analysis)
Trust: high, pending visual confirmation
EOF
```

## Edge cases

- No EXIF at all (stripped by platform). Normal for social media
  images; proceed to visual analysis and note the provenance.
- GPS present but the photo is a screenshot. The coordinates are
  where the screenshot was taken, not what it depicts; verify what
  the image actually shows.
- Timestamps in the future or in 1970. Device clock errors are
  common; do not build a timeline on a single bad timestamp.
- Multiple conflicting date fields. Trust GPSDateStamp (UTC,
  satellite-derived) over device-local fields when they disagree.
- HEIC or RAW formats. ExifTool handles both, but thumbnails and
  GPS placement differ; check the format-specific tags.
- Metadata in a language you cannot read (XMP titles, comments).
  Translate for the record; titles sometimes name the location
  outright.

## Escalation

- Metadata places the photo at a private residence and the case
  does not authorize locating individuals. Stop the geolocation
  and escalate the scope question; do not refine the position.
- Signs of deliberate fabrication (edited GPS, mismatched
  thumbnail). Document the manipulation indicators carefully;
  fabricated metadata is itself evidence in fraud or
  disinformation cases.
- The image is part of a legal case. Preserve the original with
  hashes, keep the ExifTool version on record, and avoid any
  operation that rewrites the file.
- Timestamps are critical and contradictory. Escalate to a
  timeline specialist rather than picking the convenient one;
  choosing wrong corrupts the whole case timeline.

## Detection and defender view

EXIF is trivially stripped, which is why platforms do it by
default, and trivially forged, which is why investigators verify
against pixels. The defender guidance is simple: strip metadata
before publishing any photo, check what your camera embeds by
default, and remember that thumbnails and XMP survive some
"metadata removers" that only clear EXIF. For investigators, the
defender view is humility: metadata is the easiest evidence to
fake, so it starts every analysis and never ends one.

## Key references

- ExifTool documentation and tag names:
  https://exiftool.org/
- EXIF standard reference: https://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf
- Parent workflow: osint-image-geolocation (this repo)
- Bellingcat image verification guides:
  https://www.bellingcat.com/resources/
- OpenStreetMap: https://www.openstreetmap.org/
