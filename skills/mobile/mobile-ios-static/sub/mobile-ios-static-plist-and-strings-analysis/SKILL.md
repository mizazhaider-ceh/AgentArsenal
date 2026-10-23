---
name: mobile-ios-static-plist-and-strings-analysis
description: Use when you need to squeeze every finding out of an iOS
  app's configuration and readable text without executing it, during an
  authorized static review. Covers Info.plist key-by-key security review
  with plutil and PlistBuddy, entitlement decoding, URL scheme and App
  Transport Security auditing, strings extraction with pattern and entropy
  based secret hunting, and sweeping bundled frameworks. Use when the
  parent mobile-ios-static workflow reaches the configuration and strings
  phases, or when you want fast high-signal findings before heavier
  binary analysis with class-dump or Ghidra, plus Python entropy
  scoring for secret hunting.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
parent: mobile-ios-static
requires: [mobile-ios-static]
extends: []
relates: [mobile-ios-static]
tools:
  - name: Python
    version: 3.12
  - name: Ghidra
    version: 11.2
---

Property lists and strings are the two highest signal-per-minute sources
in iOS static analysis. The plist declares the app's capabilities and
network security posture; the strings reveal its endpoints, SDK keys, and
sometimes its secrets. This sub-skill is the deep method for both: which
keys matter, which patterns catch secrets, and how to separate real
findings from noise. It assumes you already have a decrypted, unpacked
IPA from the parent skill, and that you are authorized to analyze this
build.

## Quick Workflow

1. Convert and pretty-print Info.plist, then walk the security-relevant
   keys one by one.
2. Decode entitlements from the code signature and compare against the
   plist claims.
3. Audit App Transport Security: global flag first, then per-domain
   exceptions.
4. Inventory URL schemes, queried schemes, and background modes as
   attack surface.
5. Extract strings from the main binary with a sane minimum length.
6. Run secret patterns (keys, tokens, endpoints) and an entropy pass.
7. Repeat the strings pass over every bundled framework.
8. Triage hits into findings, leads for dynamic confirmation, and noise.

## 1. Info.plist key-by-key review

Read the plist structurally. Binary plists must go through plutil or
PlistBuddy, never a text editor.

```bash
PLIST=Payload/Target.app/Info.plist

# Full pretty print for the first read
plutil -p "$PLIST" > infoplist.txt
wc -l infoplist.txt

# The security keys, pulled individually for the report
for key in CFBundleIdentifier CFBundleShortVersionString CFBundleVersion \
  NSAppTransportSecurity CFBundleURLTypes LSApplicationQueriesSchemes \
  UIBackgroundModes NSFaceIDUsageDescription NSLocationWhenInUseUsageDescription \
  NSCameraUsageDescription NSMicrophoneUsageDescription \
  ITSAppUsesNonExemptEncryption UIRequiresFullScreen; do
  echo "=== $key ==="
  /usr/libexec/PlistBuddy -c "Print :$key" "$PLIST" 2>&1 | head -12
done
```

Example output shape for the keys that most often produce findings:

```
=== NSAppTransportSecurity ===
Dict {
    NSAllowsArbitraryLoads = true
}
=== CFBundleURLTypes ===
Array {
    Dict {
        CFBundleURLSchemes = Array {
            targetapp
            targetapp-auth
        }
    }
}
=== LSApplicationQueriesSchemes ===
Array {
    twitter
    whatsapp
}
=== UIBackgroundModes ===
Array {
    fetch
    remote-notification
}
```

Read each result with suspicion. `NSAllowsArbitraryLoads = true` is a
finding unless the client justifies it. Each URL scheme is a deeplink
entry point to test later. `LSApplicationQueriesSchemes` reveals which
apps the target can detect, which is minor privacy information. Privacy
usage descriptions (`NSFaceIDUsageDescription` and friends) should
accurately describe why the permission is needed; a copy-pasted or empty
description is a low-severity note.

## 2. Entitlements from the code signature

Entitlements are capabilities granted at signing time. Compare them with
what the plist claims the app does.

```bash
codesign -d --entitlements - Payload/Target.app/Target 2>/dev/null > entitlements.plist
plutil -p entitlements.plist

# The ones to read carefully
/usr/libexec/PlistBuddy -c "Print :get-task-allow" entitlements.plist 2>/dev/null
/usr/libexec/PlistBuddy -c "Print :com.apple.developer.associated-domains" entitlements.plist 2>/dev/null
/usr/libexec/PlistBuddy -c "Print :aps-environment" entitlements.plist 2>/dev/null
/usr/libexec/PlistBuddy -c "Print :keychain-access-groups" entitlements.plist 2>/dev/null
```

`get-task-allow = true` means the binary is debuggable, which should
never ship in a production release. `aps-environment = development`
means push goes through the sandbox gateway, a sign this is not a true
release build, so say so in the report. Associated domains list the
universal link domains; each one is a web-to-app entry point worth
testing. Keychain access groups show which apps share secrets, which
matters when the client has a suite of apps.

## 3. App Transport Security audit

ATS is Apple's TLS policy. Walk it methodically.

```bash
/usr/libexec/PlistBuddy -c "Print :NSAppTransportSecurity" \
  Payload/Target.app/Info.plist
```

Decision tree:

- `NSAllowsArbitraryLoads = true`: finding. Cleartext HTTP allowed
  everywhere. Severity depends on data: a banking app is High, a
  wallpaper app is Low.
- Per-domain `NSExceptionAllowsInsecureHTTPLoads`: note each domain.
  An API domain exception is a finding; a media CDN is usually
  accepted with a note.
- `NSExceptionRequiresForwardSecrecy = false` or minimum TLS version
  overrides: weaker crypto posture, Medium at most, note the domain.
- `NSAllowsLocalNetworking = true`: expected for development and
  local device discovery; flag only if the release build should not
  do local networking.

Also grep the binary for code-level TLS sabotage, since plist ATS can
be undermined by delegate code:

```bash
strings -a Payload/Target.app/Target | grep -E \
  "allowInvalidCertificates|validatesSecureCertificateForHost|continueWithoutCredential" \
  | sort -u
```

A hit here is a lead, not yet a finding: confirm at runtime with the
Frida SSL pinning bypass workflows whether validation is actually
disabled.

## 4. Strings extraction and secret patterns

```bash
BIN=Payload/Target.app/Target
strings -a -n 6 "$BIN" > strings-main.txt
echo "total strings: $(wc -l < strings-main.txt)"

# Endpoints first: they map the backend
grep -Eo 'https?://[A-Za-z0-9._~:/?#@!$&()*+,;=-]+' strings-main.txt \
  | sort -u > endpoints.txt
wc -l endpoints.txt && head -20 endpoints.txt

# Secret-shaped patterns
grep -Eo 'AKIA[0-9A-Z]{16}' strings-main.txt | sort -u
grep -Eo 'xox[bap]-[A-Za-z0-9-]+' strings-main.txt | sort -u
grep -Eo 'ghp_[A-Za-z0-9]{36}' strings-main.txt | sort -u
grep -Eoi '"?(api[_-]?key|client[_-]?secret|auth[_-]?token)"?\s*[:=]\s*"?[A-Za-z0-9_\-]{12,}"?' \
  strings-main.txt | head -20
```

Example output shape:

```
total strings: 48210
https://api.example.com/v2/
https://analytics.example.net/collect
wss://realtime.example.com/socket
```

Endpoints feed the dynamic phase: every API host goes into the proxy
scope. Now the entropy pass for secrets that patterns miss:

```python
import math
from collections import Counter

def entropy(s):
    c = Counter(s)
    n = len(s)
    return -sum(v / n * math.log2(v / n) for v in c.values())

with open('strings-main.txt') as f:
    hits = [(entropy(s), s) for line in f
            for s in [line.strip()]
            if len(s) >= 24 and entropy(s) > 4.6]
for e, s in sorted(hits, reverse=True)[:30]:
    print(f"{e:.2f} {s[:90]}")
```

Triage every high-entropy hit: base64-decode it, check for JWT or PEM
structure, and test whether it is a live credential only with client
approval. Most high-entropy strings are hashes, UUIDs, or compressed
data, which is why this step is triage, not conclusions.

## 5. Framework sweep

Bundled frameworks carry their own secrets, usually SDK keys the main
binary never mentions.

```bash
for fw in Payload/Target.app/Frameworks/*.framework; do
  name=$(basename "$fw" .framework)
  bin="$fw/$name"
  [ -f "$bin" ] || continue
  echo "=== $name ==="
  strings -a -n 6 "$bin" \
    | grep -Eoi '(api[_-]?key|secret|token)[\"'"'"':= ]+[A-Za-z0-9_\-]{10,}' \
    | head -5
done
```

Also check each framework's Info.plist for its version, so the report
can name outdated SDKs with known vulnerabilities:

```bash
for plist in Payload/Target.app/Frameworks/*.framework/Info.plist; do
  echo "=== $plist ==="
  /usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$plist" 2>/dev/null
done
```

An analytics SDK two years out of date with a known data leak is a
worthwhile Medium finding and takes thirty seconds to identify here.

## Edge cases

- The plist is binary and your Linux workstation has no plutil. Use
  Python's plistlib to parse it, or do this phase on a Mac. Never try
  to read binary plists as text.
- strings output is enormous (500k+ lines). Raise the minimum length
  to 8 or 10, and lean on the endpoint and secret greps rather than
  reading it linearly.
- The binary is Swift-heavy, so class names are mangled and strings
  are fragmented. The endpoint and secret greps still work; symbol
  based triage just gets harder.
- A secret-shaped string turns out to be a format example from an SDK
  ("sk_test_..."). Check SDK documentation for known test fixtures
  before reporting, and note test versus live in the evidence.
- ATS exceptions exist for domains the app no longer contacts. Stale
  exceptions are still findings, since they weaken policy for no
  benefit, but mark them as hygiene rather than active risk.
- Info.plist contains `ITSAppUsesNonExemptEncryption = false` while
  the app clearly implements custom crypto. That is an export
  compliance question for the client's legal team, not a security
  finding, but worth one line in the report.

## Escalation

- You found a live production credential (verified with client
  approval). Report it immediately through the agreed channel, do not
  keep testing with it, and recommend rotation in the same message.
- Endpoints in the binary point at hosts outside the agreed scope.
  Confirm scope before any active probing; static observation is
  fine, but connecting is testing.
- The plist declares URL schemes that look like they belong to a
  different app (sso, oauth callbacks for third parties). These are
  often the most attackable surface; flag them for priority dynamic
  testing.
- A framework version has a published CVE with a public exploit.
  Confirm the vulnerable code path is reachable before rating it
  above Low, and cite the CVE in the finding.

## Detection and defender view

Nothing here touches the running app, so there is nothing to detect.
The defender view is about making this phase boring: keep secrets out
of the binary entirely, enforce ATS with no exceptions, use explicit
App IDs and minimal entitlements, and keep SDKs updated. When the
strings pass comes back clean and the plist is tight, say so plainly;
a clean static configuration section builds credibility for the
findings that follow.

## Key references

- Apple Information Property List documentation:
  https://developer.apple.com/documentation/bundleresources/information_property_list
- Apple App Transport Security documentation:
  https://developer.apple.com/documentation/security/preventing_insecure_network_connections
- Apple entitlements documentation:
  https://developer.apple.com/documentation/bundleresources/entitlements
- OWASP MASVS storage and network chapters:
  https://mas.owasp.org/MASVS/
- OWASP MSTG iOS static analysis:
  https://mas.owasp.org/MSTG/
- ExifTool-style plist parsing alternative, Python plistlib docs:
  https://docs.python.org/3/library/plistlib.html
