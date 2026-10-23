---
name: osint-image-geolocation-shadow-and-sun-analysis
description: Use when a photo's shadows and sunlight can constrain
  its time and direction during an authorized investigation. Covers
  measuring shadow-to-object ratios in the image, computing solar
  elevation with Python 3.12, determining north from shadow direction
  by hemisphere, cross-checking EXIF timestamps against solar
  position, and using SunCalc for verification. Use when the parent
  osint-image-geolocation workflow needs time-of-day evidence, when
  verifying a claimed capture time, or when shadows are the only
  directional clue in the frame, reconciled with ExifTool timestamps.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-image-geolocation
requires: [osint-image-geolocation]
extends: []
relates: [osint-image-geolocation]
tools:
  - name: Python
    version: 3.12
  - name: ImageMagick
    version: 7.1
  - name: ExifTool
    version: 12.9
---

Shadow and sun analysis turns sunlight into a clock and a compass.
A shadow's direction gives the sun's azimuth; its length relative to
the object gives the sun's elevation; together with a date they
constrain time and latitude. This sub-skill covers the measurements,
the math, and the cross-checks, with worked examples. It assumes an
outdoor daytime photo in an authorized case.

## Quick Workflow

1. Identify a vertical object with a sharp, complete shadow on flat
   ground.
2. Measure the object and shadow lengths in pixels; compute the
   ratio.
3. Convert the ratio to solar elevation with the tangent relation.
4. Read shadow direction for the sun's azimuth and the hemisphere
   rule.
5. Compare with the EXIF timestamp and claimed location using
   SunCalc.
6. Note uncertainties: slope, object lean, measurement error.
7. Write the conclusion with the calculation shown.

## 1. Measuring in the image

```bash
# Crop the shadow region for measurement
convert work.jpg -crop 1200x800+800+1600 shadow.jpg

# Measure pixel lengths along the object and its shadow
# Use any image viewer with a ruler, or measure coordinates and compute:
python3 - <<'EOF'
import math
# Pixel coordinates: object base (x1,y1) to top (x2,y2); shadow tip (x3,y3)
obj_base, obj_top = (400, 700), (400, 300)
shadow_tip = (700, 700)
obj_len = math.dist(obj_base, obj_top)
shad_len = math.dist(obj_base, shadow_tip)
print(f"object {obj_len:.0f}px, shadow {shad_len:.0f}px, ratio {shad_len/obj_len:.2f}")
EOF
```

Example output shape:

```
object 400px, shadow 560px, ratio 1.40
```

Measure on flat ground with the object truly vertical. A leaning
pole or a sloped street biases the ratio; pick the cleanest
object-shadow pair in the frame, and measure two if available to
check agreement.

## 2. Solar elevation from the ratio

The geometry: for a vertical object of height h casting shadow
length s on flat ground, tan(elevation) = h / s.

```python
# elevation.py
import math
ratio = 1.40  # shadow length / object height
elevation = math.degrees(math.atan(1 / ratio))
print(f"solar elevation: {elevation:.1f} degrees")
# solar elevation: 35.5 degrees
```

Interpretation guide:

- Elevation near 90: sun overhead, midday, tropical latitudes.
- Elevation 30-50: mid-morning or mid-afternoon at temperate
  latitudes.
- Elevation under 15: near sunrise or sunset; long dramatic
  shadows.
- Elevation 0 or negative: the photo cannot be sunlit at that
  time; check the timestamp claim.

Uncertainty of a few degrees is normal from pixel measurement; that
translates to roughly 15-30 minutes of time uncertainty, which you
state rather than hide.

## 3. Direction: the hemisphere rule

- Northern hemisphere: at solar noon the sun is due south, so
  shadows point north. Morning shadows point west-ish, evening
  shadows east-ish.
- Southern hemisphere: mirrored; noon shadows point south.
- Equator: near the equinoxes the sun passes nearly overhead and
  shadows are short at noon.

```bash
# Determine the shadow's compass direction from the image if north is known
# (from a map of the confirmed street, or a visible landmark of known bearing)
# Then: sun azimuth = shadow direction + 180 degrees
```

If the visual analysis already fixed the street orientation, the
shadow direction gives the sun's azimuth directly, which pins the
time much tighter than elevation alone.

## 4. Cross-checking with SunCalc and EXIF

```bash
# Get the EXIF timestamp and GPS for the cross-check
exiftool -DateTimeOriginal -GPSPosition -n photo.jpg
# DateTimeOriginal : 2026:10:20 14:32:11+02:00
# GPS Position     : 50.8503, 4.3517
```

Then verify on SunCalc (suncalc.org): enter the coordinates and
date, and read the sun's elevation and azimuth at 14:32 local.
Agreement within a few degrees confirms the timestamp; large
disagreement means the timestamp, the location, or the photo's
authenticity is wrong.

```python
# rough-check.py: approximate solar noon sanity check without external data
# At 50.85 N on Oct 20, solar noon is roughly 12:00 UTC adjusted for longitude:
# solar_noon_utc ≈ 12:00 - lon/15 hours = 12:00 - 0.29h ≈ 11:43 UTC = 13:43 local (+2)
# Photo at 14:32 local is ~50 min after solar noon: sun in the southwest, elevation
# moderate. Shadows should point northeast. Compare with the image.
print("expected: shadows pointing northeast, sun in southwest")
```

This rough check catches gross fabrications (a "noon" photo with
sunset shadows) before you spend time on precision.

## 5. Worked example

Photo: street scene, Brussels, 2026-10-20 14:32 local (+02:00).

1. Lamp post: 400 px tall, shadow 560 px, ratio 1.40, elevation
   35.5 degrees.
2. Street runs east-west (confirmed on the map); shadows fall to
   the north-east side of the posts, so the sun is in the
   south-west.
3. SunCalc for 50.8503 N, 4.3517 E on 2026-10-20 at 14:32 local:
   elevation ~28 degrees, azimuth ~215 degrees (south-west).
4. Measured 35.5 versus computed 28: within rough-measurement
   tolerance given pixel error and possible slight slope.
5. Conclusion: timestamp and location consistent with the shadows.
   Confidence: supporting evidence, not standalone proof.

Write the example in this format in the case file: measurements,
computation, external check, conclusion, tolerance.

## Edge cases

- Overcast sky: no sharp shadows. The method does not apply; note
  it and move on rather than forcing measurements on diffuse
  shading.
- Multiple light sources (street lamps at dusk). Shadows may come
  from artificial light; check for multiple shadow directions,
  which betray mixed lighting.
- The photo is near the equator at noon: shadows vanish and the
  method gives no constraint. Say so.
- Fisheye or wide-angle distortion bends straight shadows. Measure
  near the image center where distortion is minimal, or correct
  the lens profile first.
- The object is not vertical (a leaning sign, a person mid-step).
  Reject the measurement; a bad object is worse than no object.
- Reflections (glass facades, water) create false shadow-like
  features. Verify the shadow connects to the object's base on the
  ground plane.

## Escalation

- Shadows contradict the EXIF timestamp badly (morning shadows on
  an "evening" photo). Treat the timestamp as suspect, re-verify
  the location independently, and flag possible manipulation to the
  case owner.
- The analysis is time-critical to the case (alibi verification).
  Have a second analyst independently measure and compute; do not
  let one person's pixel ruler decide an alibi.
- No usable shadows and the time question matters. Escalate to
  other time clues: shop opening states, traffic density, sky
  color, or clock faces visible in the frame.
- The photo may be synthetic. Impossible sun geometry (two shadow
  directions from one sun, shadows detached from objects) is a
  strong synthetic indicator; escalate to media forensics.

## Detection and defender view

Shadow analysis is hard to defeat deliberately because people do
not think about sun geometry when taking photos, which is exactly
why investigators value it. The defense is the same as for all
geolocation: control backgrounds, strip metadata, and consider what
a photo reveals before publishing. For analysts, the defender view
is a caution about overprecision: pixel measurements have real
error bars, and a geolocation that depends on a two-degree
elevation difference is not a geolocation but a guess with math on
it.

## Key references

- Parent workflow: osint-image-geolocation (this repo)
- SunCalc: https://www.suncalc.org/
- NOAA solar calculator: https://gml.noaa.gov/grad/solcalc/
- Bellingcat shadow analysis references:
  https://www.bellingcat.com/resources/
- ExifTool (for the timestamp side): https://exiftool.org/
