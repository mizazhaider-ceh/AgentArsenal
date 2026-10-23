---
name: mobile-ios-static
description: Use when you need to statically analyze an iOS application
  during an authorized engagement, such as a client mobile app pentest or a
  review of your own organization's App Store build. Covers IPA acquisition
  and decryption on authorized test devices, IPA layout and code signature
  review, Info.plist and entitlement analysis with plutil, strings and
  hardcoded secret hunting, Objective-C interface recovery with class-dump
  and Ghidra, data protection flags, and App Transport Security review. Use
  when Frida and objection are not yet attached, when you need a full
  inventory of attack surface before dynamic testing, or when the app resists
  runtime instrumentation.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ios-basics, ios-dynamic-analysis, mobile-frida-scripting]
tools:
  - name: Frida
    version: 16.5
  - name: objection
    version: 1.11
  - name: Python
    version: 3.12
  - name: Ghidra
    version: 11.2
  - name: class-dump
    version: 3.5
---

iOS static analysis is the examination of an app's package, binaries, and
configuration without executing it. You extract the IPA, map its layout,
read its property lists and entitlements, hunt for hardcoded secrets, and
recover class interfaces from the Mach-O binary. Static work gives you the
attack surface inventory that dynamic testing then confirms: every URL
scheme, every network security exception, every embedded key. This skill
covers the authorized workflow end to end. Only analyze apps you are
permitted to assess: a client's in-scope build, your own organization's
App Store binary, or a lab target. Never pull apart someone else's
commercial app to steal logic or keys.

## Quick Workflow

1. Acquire the IPA through an authorized channel: a test build from the
   client, Apple Configurator for your own organization's app, or
   decryption on your jailbroken test device with frida-ios-dump.
2. Verify integrity: hash the IPA, note the version, and record where it
   came from.
3. Unzip and map the layout: Payload, the .app bundle, Frameworks,
   embedded.mobileprovision.
4. Review Info.plist and entitlements for URL schemes, ATS exceptions,
   background modes, and privacy permissions.
5. Run strings and secret-hunting patterns over the binary and resources.
6. Run class-dump to recover the Objective-C interface, and load the
   binary in Ghidra for deeper review.
7. Check data protection flags, keychain accessibility classes, and
   transport security settings.
8. Write findings with evidence: file, offset or key, value redacted, and
   severity tied to OWASP MASVS.

## 1. Acquiring the IPA on authorized terms

The cleanest source is the client: an ad-hoc or enterprise-signed build,
or TestFlight access for the exact version in scope. For your own
organization's published app, Apple Configurator on a Mac can download the
IPA to your workstation. On a jailbroken test device that you own, the app
must be decrypted first because App Store binaries are FairPlay encrypted.

```bash
# Hash and record the IPA before you touch it
shasum -a 256 target.ipa
unzip -l target.ipa | head -30

# Decrypt on your own jailbroken test device (authorized target only)
# frida-ios-dump needs frida-server running on the device
python3 dump.py -u <device-udid> com.example.target
# Produces ./target-1.2.3.ipa, decrypted and ready for analysis
```

Record the bundle version from the filename or Info.plist and keep the
original IPA untouched. Every finding later references this exact build.

Example layout listing you should see:

```
Archive:  target.ipa
  Length      Date    Time    Name
---------  ---------- -----   ----
        0  2026-10-01 10:00   Payload/
        0  2026-10-01 10:00   Payload/Target.app/
  1843200  2026-10-01 10:00   Payload/Target.app/Target
     4821  2026-10-01 10:00   Payload/Target.app/Info.plist
     9102  2026-10-01 10:00   Payload/Target.app/embedded.mobileprovision
        0  2026-10-01 10:00   Payload/Target.app/Frameworks/
```

If unzip shows an encrypted binary (class-dump fails with a cryptid
error), the IPA is still FairPlay encrypted and must be decrypted on a
device you own before analysis continues.

## 2. IPA layout: what lives where

Unzip into a working directory and learn the bundle structure. Each
location answers different questions.

```bash
mkdir -p analysis && cd analysis
unzip -q ../target.ipa
find Payload -maxdepth 2 | sort | head -40

# The main binary shares the app's name
ls -la Payload/Target.app/Target

# Check the binary is arm64 Mach-O and whether it is encrypted
file Payload/Target.app/Target
otool -l Payload/Target.app/Target | grep -A4 LC_ENCRYPTION_INFO
```

Key locations and what to look for in each:

- `Payload/Target.app/Target`: the main Mach-O binary, class-dump and
  strings target.
- `Payload/Target.app/Info.plist`: bundle config, URL schemes, ATS.
- `Payload/Target.app/embedded.mobileprovision`: provisioning profile,
  decode it for entitlements and device allowances.
- `Payload/Target.app/Frameworks/`: bundled third-party frameworks,
  each worth its own strings pass for SDK keys.
- `Payload/Target.app/*.lproj/`: localization strings, sometimes
  containing debug text or internal labels.
- `Payload/SwiftSupport/` (if present): Swift standard libraries,
  useful for version fingerprinting.

Decode the provisioning profile to confirm the signing identity matches
what the client claims:

```bash
security cms -D -i Payload/Target.app/embedded.mobileprovision \
  | plutil -p - | grep -E "Name|TeamName|Entitlements" | head -20
```

## 3. Info.plist and entitlements review

The Info.plist is the app's configuration surface. Read it as a plist,
not as text, so binary plists parse correctly.

```bash
# Pretty-print the whole plist
plutil -p Payload/Target.app/Info.plist | head -80

# Pull the keys that matter most for security review
/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" Payload/Target.app/Info.plist
/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" Payload/Target.app/Info.plist
/usr/libexec/PlistBuddy -c "Print :NSAppTransportSecurity" Payload/Target.app/Info.plist
/usr/libexec/PlistBuddy -c "Print :CFBundleURLTypes" Payload/Target.app/Info.plist
/usr/libexec/PlistBuddy -c "Print :LSApplicationQueriesSchemes" Payload/Target.app/Info.plist
/usr/libexec/PlistBuddy -c "Print :UIBackgroundModes" Payload/Target.app/Info.plist
```

Example output shape for a transport security review:

```
NSAppTransportSecurity => {
  NSAllowsArbitraryLoads => true
  NSExceptionDomains => {
    api.example.com => {
      NSExceptionAllowsInsecureHTTPLoads => true
    }
  }
}
```

`NSAllowsArbitraryLoads = true` disables App Transport Security globally
and is a finding on its own. Per-domain exceptions need justification:
a media CDN exception differs from an API exception. `NSAllowsLocalNetworking`
is normal for development but should not ship in production builds.

URL schemes (`CFBundleURLTypes`) are entry points: any app on the device
can open them. Note every scheme and test it later with objection or
Frida during dynamic analysis. Background modes (`audio`, `fetch`,
`remote-notification`) widen what the app can do unattended.

Entitlements come from the code signature, not the plist:

```bash
codesign -d --entitlements - Payload/Target.app/Target 2>/dev/null
```

Look for `get-task-allow` (debuggable build, should be false in
production), `com.apple.developer.associated-domains` (universal links),
keychain access groups, and push notification environment
(`development` versus `production`).

## 4. Strings, secrets, and entropy hunting

The fastest wins in iOS static analysis come from strings. Run a broad
pass, then targeted patterns for secrets.

```bash
BIN=Payload/Target.app/Target

# Baseline strings, minimum length 6 to cut noise
strings -a -n 6 "$BIN" > strings.txt
wc -l strings.txt

# URLs and endpoints
grep -Eo 'https?://[^"'"'"' ]+' strings.txt | sort -u | head -30

# Candidate secrets: AWS keys, generic API keys, tokens
grep -Eo 'AKIA[0-9A-Z]{16}' strings.txt | sort -u
grep -Eoi '(api[_-]?key|secret|token|passwd|password)[\"'"'"':= ]+[A-Za-z0-9_\-]{8,}' strings.txt | head -20

# Firebase, analytics, and SDK configuration endpoints
grep -Eo '[a-z0-9-]+\.firebaseio\.com' strings.txt | sort -u
grep -Eo 'sk_(live|test)_[A-Za-z0-9]+' strings.txt | sort -u
```

High-entropy strings often hide keys that pattern matching misses. A
small Python pass scores them:

```python
import math, re
from collections import Counter

def entropy(s):
    counts = Counter(s)
    return -sum(c / len(s) * math.log2(c / len(s)) for c in counts.values())

with open('strings.txt') as f:
    for line in f:
        s = line.strip()
        if len(s) >= 20 and entropy(s) > 4.5:
            print(f"{entropy(s):.2f}  {s[:80]}")
```

Example output shape:

```
5.12  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6...
4.87  9f2c4a7e1b3d5f608a2c4e6b8d0a2f4c6e8b0d2a4f6c8e0b2d4f6a8c0e2b4d6
```

Base64 blobs that decode to JSON with `alg` and `typ` fields are JWT
secrets or test tokens. Verify whether they are live credentials before
reporting severity: a test key in a debug build is a note, a production
API secret in a release build is a finding.

Also sweep the Frameworks directory, since SDK keys usually live in
bundled libraries rather than the main binary:

```bash
for f in Payload/Target.app/Frameworks/*.framework/*; do
  [ -f "$f" ] && strings -a -n 6 "$f" | grep -Eoi '(api[_-]?key|secret)[\"'"'"':= ]+[A-Za-z0-9_\-]{8,}' | head -3
done
```

## 5. Class-dump: recovering the Objective-C interface

class-dump reads the Objective-C runtime metadata in the Mach-O binary
and reconstructs headers: classes, methods, properties, protocols. This
is your map for Frida hooking later.

```bash
# Dump headers for the main binary
class-dump -H Payload/Target.app/Target -o headers/

# Count what you got
find headers -name '*.h' | wc -l
grep -rl "password\|token\|secret\|keychain" headers/ | head -10

# Dump a bundled framework too
class-dump -H Payload/Target.app/Frameworks/Analytics.framework/Analytics -o headers-analytics/
```

Example header fragment you should expect:

```objc
@interface LoginManager : NSObject
{
    NSString *_authToken;
    NSURLSession *_session;
}
- (void)loginWithUsername:(id)arg1 password:(id)arg2 completion:(id)arg3;
- (BOOL)isAuthenticated;
- (_Bool)validatePIN:(id)arg1;
@end
```

Method names like `validatePIN:` or `isAuthenticated` are direct hooks
targets for the mobile-frida-scripting skill. Ivar names like
`_authToken` tell you what to search memory for at runtime. Protocols
reveal delegate callbacks that handle sensitive flows.

class-dump only works on Objective-C metadata. Pure Swift classes appear
as mangled symbols; for those, the mangled names still leak structure:

```bash
# Swift symbols keep readable fragments after demangling
nm Payload/Target.app/Target | grep -i "login" | head -10
xcrun swift-demangle <<< "_\$s6Target12LoginManagerC5login8username8password10completionySS_SSySo13NSError_pCSgtF"
```

## 6. Mach-O and Swift notes for the static analyst

When class-dump output is thin, the binary may be Swift-heavy or
stripped. Check what the toolchain left behind.

```bash
# Linked libraries: which security frameworks are actually used
otool -L Payload/Target.app/Target | head -30

# Look for Security.framework (keychain, cert handling) and LocalAuthentication (biometrics)
otool -L Payload/Target.app/Target | grep -E "Security|LocalAuthentication|CryptoKit"

# PIE, stack canaries, ARC: hardening flags
otool -hv Payload/Target.app/Target | head -5

# Bitcode and Swift version markers
strings -a Payload/Target.app/Target | grep -m2 "swiftlang"
```

In Ghidra, import the binary, let auto-analysis finish, and start from
the strings window: cross-reference an interesting string (an endpoint,
an error message) to the function that uses it. That function is usually
the network client or the validation routine you will hook later.

Swift binaries resist class-dump, but the method dispatch tables and
protocol witness tables still name types. Search Ghidra's symbol tree
for fragments like `Token`, `Auth`, `Crypto`, `PIN`, and `Biometric`.

## 7. Data protection and transport security flags

Two plist-level checks close out the static pass: how files are
protected at rest, and how traffic is protected in flight.

```bash
# Data protection entitlement on the binary
codesign -d --entitlements - Payload/Target.app/Target 2>/dev/null \
  | grep -A2 "DataProtection"

# Search code and config for explicit file protection classes
grep -rn "NSFileProtection" Payload/ --include="*.plist" | head
strings -a Payload/Target.app/Target | grep -E "NSFileProtection[A-Za-z]+" | sort -u
```

`NSFileProtectionComplete` is the strongest class; anything weaker for
sensitive files is a finding. The absence of any data protection class
means files default to the device default, which is weaker than
Complete.

For transport security, combine the ATS plist review from section 3
with a code-level check for disabled certificate validation:

```bash
# Code signs of disabled TLS validation (confirm at runtime before reporting)
strings -a Payload/Target.app/Target | grep -E "allowInvalidCertificates|validatesSecureCertificate|canAuthenticateAgainstProtectionSpace" | sort -u
```

`allowInvalidCertificates = YES` in shipped code breaks certificate
validation entirely. Treat a strings hit as a lead, then confirm with
the Frida SSL pinning bypass skill whether traffic is actually
interceptable.

## 8. Turning findings into report entries

Every static finding needs four things: location, evidence, impact, and
severity anchored to OWASP MASVS. A finding without a file path and a
redacted evidence snippet is a rumor.

Template:

```
Finding: Hardcoded API secret in main binary
Location: Payload/Target.app/Target (strings offset, build 1.2.3)
Evidence: key prefix "sk_live_..." (full value redacted, verified live via
  test request with client approval)
Impact: anyone extracting the IPA can call the payment API as the app
Severity: High (MASVS-STORAGE-1, MSTG-STORAGE-3)
Fix: move the secret server-side or scope it to a publishable key
```

Severity guidance: hardcoded production credentials are High;
ATS disabled globally is Medium to High depending on data handled;
verbose logging strings are Low unless they log PII; debug endpoints
left in release builds are Medium. Always state whether you verified
the finding at runtime or whether it still needs dynamic confirmation.

## Edge cases

- The IPA is FairPlay encrypted and you have no jailbroken test device.
  You cannot statically analyze the binary. Ask the client for an
  unencrypted test build, which is standard practice on authorized
  iOS engagements.
- class-dump returns almost nothing. The app is likely Swift-only or
  the Objective-C metadata was stripped. Pivot to Ghidra and to
  strings-led analysis, and plan heavier Frida instrumentation.
- The binary is packed or uses a commercial obfuscator. Strings are
  garbage and class names are randomized. Document the obfuscation as
  a resilience control, then move to dynamic analysis where the code
  must decrypt itself to run.
- Info.plist keys are present but the features seem unused. Plist
  entries can be stale. Confirm at runtime whether the URL scheme or
  background mode is actually registered before reporting it as live
  attack surface.
- Secrets found in strings belong to third-party SDKs (analytics keys,
  crash reporting tokens). These are usually low severity by design,
  but check the SDK's docs: some keys are publishable, some are not.
  Report the distinction.
- Multiple app targets or app extensions live in the same IPA
  (watchOS app, widgets, share extension). Each extension is its own
  binary with its own Info.plist and entitlements. Sweep them all;
  extensions are frequently less hardened than the main app.
- The provisioning profile shows a wildcard App ID. Fine for
  development, but production apps handling sensitive data should use
  explicit App IDs so keychain access groups stay scoped.

## Escalation

- You found what looks like a production credential in the binary.
  Stop and verify with the client before testing it. Do not call
  third-party APIs with extracted secrets without written approval,
  and rotate the finding into the report immediately rather than
  sitting on it.
- The app uses certificate pinning plus jailbreak detection and you
  cannot get runtime confirmation of a static lead. Document the lead
  as unverified, note the controls that blocked confirmation, and
  hand the exact hook points to the dynamic phase.
- Static analysis suggests the app talks to undocumented backend
  endpoints. Confirm scope with the client before probing them: an
  endpoint in the binary is not automatically in scope.
- The binary contains signs of malware-like behavior (SMS interception
  strings, overlay permissions) in a client app. Escalate to the
  engagement lead before writing it up; it may be a compromised SDK
  or a misattributed binary.
- Time is short and the IPA is large. Prioritize Info.plist review,
  strings secret hunting, and class-dump of classes with security
  relevant names. Those three produce most findings per hour.

## Detection and defender view

Static analysis leaves no trace on the app itself, since you never run
it. Defenders counter static analysis with the controls you are
assessing: Swift and symbol stripping to shrink class-dump output,
commercial obfuscators to randomize names and encrypt strings,
server-side secrets instead of embedded keys, ATS enforcement with no
exceptions, and complete data protection classes. When you write the
report, credit the controls that worked: an app with no hardcoded
secrets, strict ATS, and complete file protection has a solid static
posture, and saying so makes the real findings land harder. Note that
obfuscation slows analysis but does not stop it; the durable defenses
are architectural, moving secrets and decisions server-side.

## Key references

- OWASP MASVS (Mobile Application Security Verification Standard):
  storage, cryptography, and network requirements to anchor severity.
  https://mas.owasp.org/MASVS/
- OWASP MSTG iOS testing guide: static analysis procedures for iOS.
  https://mas.owasp.org/MSTG/
- Apple developer docs on Info.plist keys and ATS:
  https://developer.apple.com/documentation/bundleresources/information_property_list
- Apple docs on data protection and keychain:
  https://developer.apple.com/documentation/security/
- Frida documentation (for the dynamic follow-up):
  https://frida.re/docs/home/
- objection documentation (iOS runtime exploration):
  https://github.com/sensepost/objection
- class-dump project page: http://stevenygard.com/projects/class-dump/
