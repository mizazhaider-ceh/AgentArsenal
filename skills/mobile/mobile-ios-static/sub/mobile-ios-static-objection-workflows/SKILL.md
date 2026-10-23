---
name: mobile-ios-static-objection-workflows
description: Use when you want fast read-oriented runtime inspection of
  an iOS app on an authorized test device without writing Frida scripts.
  Covers objection 1.11 iOS commands for dumping keychain items,
  NSUserDefaults, plist files, and bundle metadata, listing classes and
  methods, searching memory for secrets found during static analysis, and
  disabling SSL pinning for traffic review. Use when the parent
  mobile-ios-static findings need runtime confirmation, when you want to
  check what the app actually stores on disk, or as the quick first pass
  before custom Frida instrumentation.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
parent: mobile-ios-static
requires: [mobile-ios-static]
extends: []
relates: [mobile-ios-static]
tools:
  - name: objection
    version: 1.11
  - name: Frida
    version: 16.5
  - name: Python
    version: 3.12
---

objection is a runtime exploration toolkit built on Frida that gives you
a REPL over a running iOS app with no scripting required. For static
analysts it is the bridge to runtime truth: the plist said the app stores
a token, objection shows you the actual keychain item. This sub-skill
covers the read-oriented iOS workflows: storage dumps, bundle inspection,
and memory search. All commands run against an app on a test device you
own, for a target you are authorized to assess.

## Quick Workflow

1. Confirm frida-server is running on the test device and the versions
   match your workstation.
2. Attach objection to the running app or spawn it.
3. Dump the bundle metadata and environment for orientation.
4. Dump keychain, NSUserDefaults, and plist files; compare against the
   static findings.
5. Search memory for the secret-shaped strings found in the static pass.
6. Disable SSL pinning and confirm traffic in your proxy.
7. Save every dump with the build version in the filename.

## 1. Attaching and orienting

```bash
# Attach to the running app (find the name with frida-ps first)
frida-ps -U | grep -i target
objection --gadget com.example.target explore

# Or spawn it fresh, useful when you need early lifecycle behavior
objection --gadget com.example.target explore --startup-command "ios keychain dump"
```

Inside the REPL, orient yourself:

```
# Show the app environment: bundle id, paths, versions
env

# Example output shape
# Name               Path
# -----------------  ------------------------------------------------
# Bundle identifier  com.example.target
# Bundle path        /var/containers/Bundle/Application/<UUID>/Target.app
# Data path          /var/mobile/Containers/Data/Application/<UUID>/
```

The data path is where the app's documents, library, and caches live.
Every storage dump below reads from there.

## 2. Keychain dump

The keychain is where secrets should live. Dump it and check the
protection classes.

```
ios keychain dump

# Example output shape
# Account        Service              Data                      Accessible
# -------------  ------------------- -------------------------  --------------------------
# user@example   com.example.target  s3cr3t-t0k3n...            AfterFirstUnlock
# device-id      com.example.target  9F2C...                   Always
```

`kSecAttrAccessibleAlways` is deprecated and weak; `AfterFirstUnlock`
is common but weaker than `WhenUnlocked` or `WhenPasscodeSetThisDeviceOnly`.
Cross-check: the static pass may have found the token in strings, which
means it was also compiled into the binary, a double finding. Note
which items the app actually creates versus what the code suggests.

Export for the report:

```
ios keychain dump --json keychain-dump.json
```

## 3. NSUserDefaults and plist inspection

NSUserDefaults is a plist on disk and frequently contains more than
preferences.

```
# Dump all defaults
ios nsuserdefaults get

# Example output shape
# {
#   "authToken": "eyJhbGciOi...",
#   "lastSyncDate": "2026-10-20T...",
#   "userEmail": "user@example.com"
# }

# List plist files in the app sandbox
ios plist list
ios plist cat /var/mobile/Containers/Data/Application/<UUID>/Library/Preferences/com.example.target.plist
```

An auth token in NSUserDefaults is a finding: defaults are stored
unencrypted in the app sandbox and included in backups. Compare with the
keychain dump; tokens should be in the keychain, not here.

## 4. Bundle and class inspection

```
# Bundle info: versions, frameworks, URL schemes as the runtime sees them
ios bundles list_bundles
ios bundles list_frameworks

# List loaded classes, filtered to the app's own prefix
ios hooking list_classes | grep -i target | head -20

# List methods of an interesting class found via class-dump
ios hooking list_methods com.example.target.LoginManager --include-parents
```

Example output shape:

```
# com.example.target.LoginManager methods
# - loginWithUsername:password:completion:
# - isAuthenticated
# - validatePIN:
# - refreshTokenWithCompletion:
```

These method names become the hook targets for the
mobile-frida-scripting skill. The static class-dump and this runtime
listing should agree; if a method appears in headers but not at
runtime, it may be stripped or in an unloaded bundle.

## 5. Memory search for static leads

Take each secret-shaped string from the static pass and search the
app's memory for live copies.

```
# Search all of the app's memory for a token fragment
memory search "eyJhbGciOi" --string

# Example output shape
# 0x105a4b000  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Dump the region around a hit for context
memory dump 0x105a4b000 256 --output /tmp/token-mem.bin
```

Live copies of hardcoded secrets in memory confirm they are actually
used, which raises severity. Also search for the plist-declared URL
schemes and any PIN or password field contents while the relevant
screen is open.

## 6. SSL pinning disable for traffic confirmation

```
# Inside the objection REPL
ios sslpinning disable --quiet
```

Then exercise the app and watch your proxy (Burp or similar). If
decrypted HTTPS appears, the static ATS review from the parent skill
gains its runtime verdict. If traffic stays encrypted, the app pins in
native code or uses a custom trust evaluation, and you escalate to the
Frida pinning bypass sub-skill.

## Edge cases

- objection fails to attach with a Frida version mismatch error. The
  gadget or server version must match the workstation Frida 16.5
  exactly; this is the most common objection failure.
- The app detects the jailbreak and refuses to launch, so there is
  nothing to attach to. Use the client-supplied build path, or accept
  that runtime confirmation is blocked and mark findings accordingly.
- `ios keychain dump` returns empty on a fresh install. Interact with
  the app first (log in, enable biometrics) so it actually writes
  keychain items, then re-dump.
- Memory search finds thousands of hits for a short string. Lengthen
  the search token to something distinctive, or narrow with
  `--offsets-only` and sample.
- The app uses an app group container outside its own data path.
  Check `env` for group container paths and dump those plists too;
  shared containers are a common place for tokens to leak between a
  main app and its extensions.
- objection commands hang on apps with heavy anti-tamper. Fall back
  to plain Frida scripts, which let you control hook timing more
  precisely.

## Escalation

- The keychain contains credentials for third-party services that look
  live. Treat like any extracted secret: verify only with client
  approval, report immediately, recommend rotation.
- Storage dumps reveal other users' data on a shared test device.
  Stop, wipe the device, and note the finding without retaining the
  data; you do not need to keep PII to prove the point.
- Pinning disable does not work and the static pass flagged
  `allowInvalidCertificates`. That combination means custom trust
  code; hand the exact class and method names to the Frida
  function-hooking sub-skill for a targeted bypass.
- You need to modify app behavior, not just read it. objection's
  `ios hooking set_return_value` covers simple cases; anything
  complex belongs in a custom Frida script.

## Detection and defender view

objection injects the Frida gadget, which a defending app can detect:
open Frida port, gadget library in memory maps, modified code
signature. Jailbreak detection blocks the whole workflow. From the
defender side, the durable controls are the same as ever: sensitive
data in the keychain with strong accessibility classes, nothing
sensitive in NSUserDefaults, certificate pinning that survives the
generic bypass, and server-side authorization so that even a fully
instrumented client yields little. When you report, distinguish
between "objection read it trivially" (weak client posture) and
"objection was blocked by X" (control working as designed).

## Key references

- objection documentation and iOS command reference:
  https://github.com/sensepost/objection
- Frida iOS specifics: https://frida.re/docs/ios/
- Apple keychain services documentation:
  https://developer.apple.com/documentation/security/keychain_services
- Apple NSUserDefaults documentation:
  https://developer.apple.com/documentation/foundation/userdefaults
- OWASP MSTG iOS dynamic analysis:
  https://mas.owasp.org/MSTG/
- OWASP MASVS storage requirements:
  https://mas.owasp.org/MASVS/
