---
name: ctf-osint-challenges-metadata-analysis
description: Use when a CTF OSINT or forensics challenge provides files
  whose metadata may hide the flag, or when analyzing files you are
  authorized to examine. Covers ExifTool deep dives on images, documents,
  audio, and video, extracting GPS coordinates and author fields, reading
  Office document XML internals, PDF metadata and embedded objects,
  thumbnail recovery, and pivoting from metadata (usernames, software,
  locations) into wider OSINT. Use when handed any file with possible
  hidden properties, when a photo's location is the question, or when
  document authorship is the lead.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-osint-challenges
requires: [ctf-osint-challenges]
extends: []
relates: [osint-methodology, forensics-fundamentals]
tools:
  - name: ExifTool
    version: 12.90
  - name: Python
    version: 3.12
---

Metadata is data about the file: who made it, when, where, and with what.
CTF authors plant flags in EXIF comments, GPS tags, document authors,
and software version strings because most players never look there.
This sub-skill covers the authorized metadata workflow: extracting
everything, interpreting the fields that matter, and pivoting from each
finding. Scope is CTF competitions, lab files, and files you are
authorized to analyze.

## Quick Workflow

1. Run `exiftool` with all tags (`-a -u`) on every file in the
   challenge bundle; do not assume which file hides the metadata.
2. Prioritize high-value fields: GPS coordinates, Comment,
   Description, Author, Creator, Software, CreateDate.
3. Convert GPS to a map location and verify it matches the challenge
   context.
4. Pivot on usernames found in Author/Creator/Software into the
   username-hunting workflow.
5. For Office docs, unzip and read the XML properties directly;
   for PDFs, check info dict plus embedded files.
6. Extract embedded thumbnails; they sometimes differ from the main
   image and contain the hidden content.
7. Check for metadata in container formats (video encoder strings,
   audio tags) with the same exiftool pass.
8. Record the exact tags and values; metadata writeups need the
   field names, not just the conclusions.

## 1. ExifTool deep dive

```bash
# Everything, including duplicates and unknown tags
exiftool -a -u -G1 photo.jpg | head -80
# -G1 shows the group (EXIF, XMP, IPTC, MakerNotes) per tag

# GPS specifically, in decimal degrees
exiftool -gpslatitude -gpslongitude -n photo.jpg
# 50.8503 4.3517  -> paste into a map

# Common flag fields, one pass over a directory
exiftool -r -Comment -Description -Artist -Author -Creator -Software \
  -CreateDate -GPSLatitude -GPSLongitude ./challenge_files/ | head -60

# Write a clean report of all metadata to a file for notes
exiftool -a -u photo.jpg > /tmp/meta.txt
```

MakerNotes (camera-specific) sometimes contain serial numbers and
owner names; XMP can carry editing history with usernames. Do not stop
at the first screen of output.

## 2. GPS coordinates: extraction and verification

```bash
# Decimal output for direct map use
exiftool -n -gpslatitude -gpslongitude photo.jpg

# Full GPS block (altitude, timestamp, processing method)
exiftool -gps:all photo.jpg
```

Verify the coordinates make sense: a CTF photo "taken in Brussels"
with GPS in the ocean means spoofed metadata (which is itself the
challenge: the real location comes from visual clues, or the spoofed
coordinates spell something). Check GPSDateStamp vs CreateDate
mismatches; they reveal edited metadata.

## 3. Office document internals

```bash
# .docx/.xlsx/.pptx are zips; the properties are XML
unzip -p report.docx docProps/core.xml | python3 -c "
import sys, xml.dom.minidom
print(xml.dom.minidom.parseString(sys.stdin.read()).toprettyxml())"
# dc:creator, dc:title, dcterms:created, cp:revision

unzip -p report.docx docProps/app.xml      # application, company
unzip -l report.docx | head -30            # embedded objects and images

# Tracked changes and comments can hold deleted flag text
unzip -p report.docx word/comments.xml
```

Also check: `docProps/custom.xml` for custom properties, embedded
files in `word/embeddings/`, and revision history showing removed
content. A "clean" document with 40 revisions is hiding something.

## 4. PDF metadata and embedded objects

```bash
pdfinfo document.pdf
# Title, Author, Creator, Producer, CreationDate

exiftool -a -u document.pdf | grep -i -E "author|creator|title|subject|keyword"

# Embedded files (flags hide as attachments)
pdfdetach -list document.pdf
pdfdetach -saveall -o /tmp/pdf_embedded document.pdf

# Incremental updates: previous versions of the PDF may contain removed text
# (check with pdfinfo Pages vs actual content, or carve with binwalk)
```

## 5. Thumbnail and preview recovery

```bash
# Extract the embedded thumbnail (may differ from the displayed image)
exiftool -b -ThumbnailImage photo.jpg > /tmp/thumb.jpg
file /tmp/thumb.jpg && exiftool /tmp/thumb.jpg | head -10

# Some formats store multiple previews
exiftool -b -PreviewImage photo.jpg > /tmp/preview.jpg
exiftool -b -JpgFromRaw photo.dng > /tmp/fromraw.jpg
```

CTF authors sometimes put the flag only in the thumbnail: the main
image looks clean, the 160px preview contains text. Always extract and
view thumbnails.

## 6. Pivoting from metadata

Each metadata value is a new OSINT seed:

- Author/Creator username -> username-hunting workflow.
- GPS coordinates -> image-geolocation verification workflow.
- Software string with a username (`Adobe Photoshop, registered to
  johndoe`) -> username search.
- CreateDate anomalies -> timeline questions (why was this edited
  at 3am? what version came before?).
- Serial numbers -> usually dead ends in CTFs, but note them.

## Edge cases

- Metadata is entirely stripped: the challenge expects visual or
  content analysis instead; do not keep digging an empty hole.
- Timestamps are uniform or zeroed: treat as anti-forensics signal
  and pivot to content.
- The file has metadata for a different file (copy-paste artifact):
  note the mismatch; CTF authors sometimes plant the flag in the
  inconsistency itself.
- Video files: check all streams (`exiftool -a` shows per-stream
  tags); encoder strings like `Lavf` plus a username are the usual
  plant.
- The metadata contains deliberately false GPS: treat it as a clue
  about the author's intent (a joke location, a previous challenge)
  rather than discarding it outright.

## Escalation

- exiftool shows nothing but the file feels planted: run `strings`
  on the raw file; some challenges hide fake "metadata" as plain
  text near the header.
- GPS points nowhere sensible: convert manually (degrees, minutes,
  seconds fields may be split across tags) before concluding it is
  spoofed.
- The document properties are all default: check the binary XML
  for custom parts (`unzip -l` full listing); defaults in the UI
  do not mean empty internals.
- Two files claim contradictory authorship: check CreateDate ordering
  and editing software; the later editor usually overwrote the original
  author field.

## Detection and defender view

Defenders strip metadata as a matter of policy: publishing pipelines
remove EXIF GPS, document properties get scrubbed, and video gets
re-encoded. Detection of metadata leakage is by audit: sample public
files and check what they expose. DLP tools can flag GPS-tagged
uploads from corporate devices. For individuals, the lesson is the
CTF lesson: every file you share carries its history unless you
actively remove it; check before publishing, not after.

## Key references

- MITRE ATT&CK T1593 (Search Open Websites/Domains).
- ExifTool documentation: https://exiftool.org/
- OSINT Framework: https://osintframework.com/
- Bellingcat metadata guides: https://www.bellingcat.com/resources/
- NIST SP 800-86 (media metadata in forensic examination).
