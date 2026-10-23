---
name: ctf-forensics-challenges-steganography
description: Use when a CTF forensics challenge hides data inside images,
  audio, video, or text files, or when analyzing media you are authorized
  to examine. Covers PNG LSB analysis with zsteg, steghide extraction and
  stegseek brute forcing, appended archive detection with binwalk, EXIF
  and metadata inspection, audio spectrogram analysis for hidden images,
  whitespace and unicode text steganography, and layered hiding where one
  method conceals another. Use when an image looks normal but must hide
  something, when audio sounds odd, or when file sizes do not match their
  visible content.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-forensics-challenges
requires: [ctf-forensics-challenges]
extends: []
relates: [forensics-fundamentals, ctf-forensics-challenges]
tools:
  - name: Python
    version: 3.12
  - name: ExifTool
    version: 12.90
  - name: binwalk
    version: 2.3
  - name: CyberChef
    version: latest
---

Steganography hides data inside ordinary-looking files: flags in image
pixels, audio frequencies, or invisible text characters. CTF stego
challenges are solved with a standard tool ladder run in order, because
each layer is designed to be found by one specific tool. This sub-skill
covers the authorized methodology: the ordered tool sequence, what each
tool's output means, manual LSB inspection when tools fail, audio visual
analysis, text stego decoding, and handling layered challenges. Scope is
CTF competitions, lab media, and files you are authorized to analyze.

## Quick Workflow

1. Run the cheap checks first: `file`, `exiftool`, `binwalk`, and a
   flag-shaped grep over the raw bytes.
2. Check the file size against expectations; appended data after the
   logical end (JPEG EOI, PNG IEND) is the most common hiding spot.
3. For PNG: run `zsteg -a` (all channels, all bit orders).
4. For JPEG/BMP/WAV/AU with a passphrase hint: try `steghide extract`
   with empty, then challenge-themed passphrases, then `stegseek`.
5. For audio: view the spectrogram; listen for SSTV warbles or DTMF.
6. For text: check trailing whitespace and zero-width unicode with
   `cat -A` and a Python scan.
7. If one layer yields an archive or another image, recurse the whole
   ladder on the extracted file.
8. Decode the final payload (base64, hex, reversed, XOR) and verify
   the flag format.

## 1. The ordered tool ladder

Run in this order; stop at the first hit, then recurse on any extracted
file.

```bash
f="$1"  # the challenge file

# 1. metadata and magic
file "$f"
exiftool "$f" | head -40        # Comment, Description, Artist fields often hold flags

# 2. appended data
binwalk "$f"                   # archives glued after IEND/EOI
tail -c 200 "$f" | xxd         # eyeball the tail

# 3. raw flag grep (catches plaintext and base64-ish hiding)
grep -a -o -E "flag\{[^}]+\}" "$f" | head -3
strings -n 10 "$f" | grep -i -E "flag|ctf" | head -10

# 4. PNG LSB
zsteg -a "$f" 2>/dev/null | head -40

# 5. steghide (needs a passphrase guess)
steghide info "$f" -p ""       # test empty passphrase
echo "test" | steghide extract -sf "$f" -p "" -xf /tmp/out.bin -f 2>&1 | head -3
```

`zsteg -a` output shape: lines like `b1,rgb,lsb,xy .. text: "flag{...}"`
where b1 is bit plane 1, rgb the channel, lsb the order. Copy the
extracted text directly; when it says `file: ...` it wrote an embedded
file to disk.

## 2. steghide and stegseek

```bash
# Try the challenge's obvious passphrases first (theme words, "password", "")
for pw in "" "password" "ctf" "flag" "stego"; do
  echo "== passphrase: '$pw'"
  steghide extract -sf image.jpg -p "$pw" -xf /tmp/out_$RANDOM.bin -f 2>&1 | head -2
done

# Brute force with rockyou when hints suggest a real passphrase
stegseek image.jpg /usr/share/wordlists/rockyou.txt
# [i] Found passphrase: "sunshine"  -> writes image.jpg.out
file image.jpg.out && head -c 200 image.jpg.out
```

`stegseek` is fast because it exploits steghide's format; use it before
manual guessing marathons. If the challenge gives no passphrase hint at
all, the intended tool is probably zsteg or appended data, not steghide.

## 3. Manual LSB inspection

When tools find nothing but the image still feels wrong (file too large,
visual noise), inspect bit planes manually.

```python
#!/usr/bin/env python3
"""Dump LSB planes of a PNG for manual inspection."""
from PIL import Image

img = Image.open("image.png").convert("RGB")
w, h = img.size
px = img.load()

for plane in (0, 1):          # bit planes 0 and 1
    bits = []
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            bits.append(str((r >> plane) & 1))
            bits.append(str((g >> plane) & 1))
            bits.append(str((b >> plane) & 1))
    raw = bytes(int("".join(bits[i:i+8]), 2) for i in range(0, len(bits) - 7, 8))
    open(f"/tmp/plane{plane}.bin", "wb").write(raw)
    print(f"plane {plane}: {len(raw)} bytes, printable ratio:",
          sum(32 <= c < 127 for c in raw) / max(len(raw), 1))
```

Check each plane file: high printable ratio means text is hidden there.
Also try MSB-to-LSB and reversed bit orders (`zsteg --order` variants)
before concluding the image is clean.

## 4. Audio steganography

```bash
# Spectrogram: flags are often drawn as text in the frequency domain
sox audio.wav -n spectrogram -o /tmp/spec.png
# open /tmp/spec.png and read it like an image

# Metadata and appended data first (same ladder as images)
exiftool audio.wav | head -20
binwalk audio.wav

# SSTV: the warbling robot sound encodes an image
# record or convert to wav, then decode with robot36 / QSSTV

# DTMF tones: decode dial sequences
# multimon-ng -a DTMF -t wav audio.wav

# LSB in WAV: same Python approach as images, on 16-bit samples
python3 - <<'EOF'
import wave
w = wave.open("audio.wav")
frames = w.readframes(w.getnframes())
lsb = bytes(b & 1 for b in frames)
text = bytes(int("".join(map(str, lsb[i:i+8])), 2) for i in range(0, len(lsb) - 7, 8))
print(text[:200])
EOF
```

Listen to the audio once: morse code beeps, dial tones, and SSTV warbles
are recognizable by ear and each maps to a specific decoder.

## 5. Text steganography

```bash
# Trailing whitespace: spaces and tabs encode binary
cat -A note.txt | head -20
# "hello world   $"  -> trailing spaces before $ are data

# Zero-width unicode: invisible characters encode bits
python3 - <<'EOF'
data = open("note.txt", encoding="utf-8").read()
mapping = {"\u200b": "0", "\u200c": "1", "\u200d": "", "\ufeff": ""}
bits = "".join(mapping.get(c, "") for c in data)
if bits:
    raw = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits) - 7, 8))
    print(raw[:300])
else:
    print("no zero-width characters found")
EOF

# Whitespace decode: space=0, tab=1 on trailing runs
python3 - <<'EOF'
bits = ""
for line in open("note.txt"):
    stripped = line.rstrip("\n")
    trail = stripped[len(stripped.rstrip(" \t")):]
    bits += trail.replace(" ", "0").replace("\t", "1")
raw = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits) - 7, 8))
print(raw[:300])
EOF
```

## 6. Layered challenges

CTF authors chain methods: a PNG with LSB text pointing to a steghide
passphrase, whose extracted zip contains audio with a spectrogram flag.
Handle layers strictly in order:

1. Solve the outermost layer completely before theorizing about inner
   ones.
2. Extracted files go through the full ladder again (binwalk, zsteg,
   exiftool, grep).
3. Keep every intermediate file; a wrong turn is cheap to retry if you
   kept the inputs.
4. Read ALL text zsteg/steghide output; passphrases and next-step hints
   hide in tool output the solver skims past.

## Edge cases

- The image is a valid photo with no hidden data: the challenge may be
  about metadata only (GPS coordinates, camera serial); exiftool is the
  whole solve.
- zsteg reports data but it is garbage: try `--order` variations and
  different channels; some challenges use MSB-first or inverted bits.
- The audio spectrogram shows nothing: check the phase or stereo
  difference (flag in L-R channel), or slow the audio down (hidden
  voice at 0.25x speed).
- Video files: extract frames (`ffmpeg -i vid.mp4 frame%03d.png`)
  and run the image ladder on each; also check audio track separately.
- The file extension lies (a PNG renamed to .jpg or vice versa): trust
  `file` output over the name; run the ladder for the real format.

## Escalation

- Full ladder finds nothing: verify the file is not corrupt or a
  decoy; check the challenge description for hints you dismissed
  (numbers that are bit planes, color names that are channels).
- The passphrase is not in rockyou: derive candidates from the
  challenge theme, author handle, and event name before wider brute
  force.
- Custom LSB scheme (every 3rd pixel, alpha channel only): read the
  challenge source or binary when provided; custom schemes are always
  documented in the challenge materials.
- Time is short: prioritize appended data and zsteg; they solve the
  majority of CTF image challenges in under five minutes combined.

## Detection and defender view

Defenders encounter steganography in data exfiltration and malware C2:
payloads hidden in images on public sites, DNS TXT records, and social
media uploads. Detection uses statistical steganalysis (LSB plane
randomness tests, file size anomalies, format inconsistencies) rather
than per-file inspection. Durable defenses: egress content inspection,
blocking unknown outbound protocols, and data classification so
sensitive files are tracked regardless of container. For analysts, the
CTF ladder transfers directly: metadata, appended data, LSB, then
targeted tools.

## Key references

- MITRE ATT&CK T1027 (Obfuscated Files or Information) and T1002
  (Data Compressed) for exfil-adjacent hiding.
- zsteg: https://github.com/zed-0xff/zsteg
- steghide docs: http://steghide.sourceforge.net/documentation.html
- ExifTool: https://exiftool.org/
- "Steganography in depth" references via HackTricks forensics section.
