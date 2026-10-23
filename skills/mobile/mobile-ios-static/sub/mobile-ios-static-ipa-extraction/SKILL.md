---
name: mobile-ios-static-ipa-extraction
description: Use when you need to obtain an analyzable IPA file for iOS
  static analysis on an authorized engagement. Covers the authorized
  acquisition paths (client-supplied test builds, Apple Configurator
  downloads of your own organization's app, TestFlight builds in scope),
  decrypting FairPlay-encrypted App Store binaries on your own jailbroken
  test device with frida-ios-dump and Frida 16.5, verifying integrity with
  hashes, and unpacking the bundle layout for analysis. Use when the parent
  mobile-ios-static workflow is blocked at step one because no IPA is
  available, or when you must confirm the binary is decrypted before
  class-dump and strings work, using Python helpers to verify the
  cryptid flag on every binary.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
parent: mobile-ios-static
requires: [mobile-ios-static]
extends: []
relates: [mobile-ios-static]
tools:
  - name: Frida
    version: 16.5
  - name: Python
    version: 3.12
  - name: unzip
    version: 6.0
---

IPA extraction is getting the app package onto your workstation in a form
you can analyze. App Store binaries are FairPlay encrypted and useless for
static analysis until decrypted, which requires running code on a device
you own. This sub-skill covers the three authorized acquisition paths and
the verification steps that prove the IPA is intact and decrypted. Only
extract apps you are authorized to assess. Decrypting someone else's paid
app to pirate or redistribute it is not authorized testing.

## Quick Workflow

1. Ask the client for a test build first; it is the fastest authorized
   path and usually unencrypted.
2. If the client points at the App Store, check whether the app is your
   organization's (Apple Configurator path) or needs device decryption.
3. Prepare your jailbroken test device: install the target app version,
   run frida-server, verify Frida connectivity.
4. Decrypt with frida-ios-dump and pull the IPA to your workstation.
5. Hash the IPA and confirm the main binary is decrypted (cryptid check).
6. Unzip into a working directory and confirm the expected bundle layout.
7. Record build, version, source, and hash in your notes before analysis.

## 1. Client-supplied builds

Always ask first. A client can usually provide an ad-hoc, enterprise, or
TestFlight build of the exact version in scope, signed for your test
device's UDID. These builds are typically unencrypted and sometimes even
include debug symbols, which makes static analysis dramatically easier.

```bash
# What to request from the client
# - IPA for the exact build in scope (bundle version, e.g. 2.4.1 build 88)
# - Signed for your test device UDID, or an enterprise distribution cert
# - Note whether it is a release or debug configuration

# When you receive it, hash immediately and check the signature
shasum -a 256 client-build.ipa
unzip -l client-build.ipa | grep -E "Payload/.*\.app/$|Info.plist"
```

If the client only offers TestFlight, install it on your test device and
use the device decryption path below; TestFlight binaries are still
FairPlay encrypted.

## 2. Apple Configurator path (your organization's app)

For an app your organization publishes, Apple Configurator on a Mac can
download the IPA to your workstation without touching a device.

```bash
# Steps in Apple Configurator (GUI, summarized for the runbook):
# 1. Sign in with an Apple ID in your organization
# 2. Add the device or use "Add Apps" for the target Apple ID
# 3. Select the app and choose Add; Configurator downloads the .ipa
# 4. Find it under ~/Library/Group Containers/*.com.apple.configurator/Library/Caches/
# 5. Copy it out before Configurator cleans the cache

cp ~/Library/Group\ Containers/K36BKF7T3D.group.com.apple.configurator/Library/Caches/Assets/TemporaryItems/*.ipa ./target.ipa
shasum -a 256 target.ipa
```

This IPA is still FairPlay encrypted, so it goes through the decryption
step below on your own device. The advantage is a clean, official copy
tied to your organization's account.

## 3. Decrypting on your jailbroken test device

FairPlay decryption happens at load time on the device, so the standard
technique dumps the decrypted binary from memory while the app runs.
frida-ios-dump automates this over Frida.

```bash
# On the device: app installed from the App Store, frida-server running
frida-ps -U | grep -i target

# Dump (run from your frida-ios-dump checkout)
python3 dump.py -u <device-udid> com.example.target

# Expected output shape
# [dump.py] start dump
# [dump.py] app: Target (com.example.target)
# [dump.py] dumping /var/containers/Bundle/Application/<UUID>/Target.app/Target ...
# [dump.py] done, output: ./com.example.target-2.4.1.ipa
```

The tool repackages the decrypted binary into a fresh IPA. Keep the
original App Store install on the device untouched so you can re-dump if
the app updates.

Requirements that commonly bite: the device must be jailbroken (palera1n
or Dopamine on a test device you own), frida-server version must match
your workstation Frida 16.5, and the app must actually launch (apps with
aggressive jailbreak detection may refuse, in which case you need the
client build path instead).

## 4. Verifying the binary is decrypted

Before any analysis, prove the Mach-O load commands show no encryption.
An encrypted binary wastes hours of confusing tool failures.

```bash
# The definitive check: cryptid must be 0
otool -l Payload/Target.app/Target | grep -B2 -A2 cryptid
# LC_ENCRYPTION_INFO
#    cryptoff 16384
#   cryptsize 131072
#    cryptid 0        <-- 0 means decrypted, 1 means still encrypted

# Quick heuristic if otool is unavailable
file Payload/Target.app/Target
```

If cryptid is 1, the dump failed silently or you grabbed the wrong file.
Re-run the dump while the app is foregrounded, and confirm frida-server
did not crash mid-dump (large binaries sometimes need two attempts).

## 5. Unpacking and layout verification

```bash
mkdir -p work && cd work
unzip -q ../com.example.target-2.4.1.ipa

# Sanity checks on the unpacked bundle
ls Payload/
codesign -dvv Payload/Target.app/Target 2>&1 | head -8
plutil -p Payload/Target.app/Info.plist | grep -E "CFBundleIdentifier|CFBundleShortVersionString|CFBundleVersion"
```

Example output shape for the version check:

```
CFBundleIdentifier => "com.example.target"
CFBundleShortVersionString => "2.4.1"
CFBundleVersion => "88"
```

The version here must match the version in scope for the engagement.
If the App Store updated the app between scoping and testing, re-dump
or note the drift in your report. Hand the verified, unpacked directory
to the parent skill's workflow at step 3.

## Edge cases

- The app refuses to launch on the jailbroken device because of
  jailbreak detection. You cannot dump what will not run. Fall back to
  asking the client for an unencrypted test build, which is the normal
  authorized path anyway.
- frida-ios-dump crashes partway through a large binary. Re-run it;
  partial dumps are common on the first attempt for apps over 100 MB.
  Make sure the device has free disk space for the repackaged IPA.
- The dump succeeds but class-dump still fails. Recheck cryptid; some
  apps ship multiple binaries (app extensions, watch app) and only the
  main binary got dumped. Dump each extension bundle separately.
- Apple Configurator no longer shows the cached IPA. Newer Configurator
  versions clean the cache aggressively. Copy the file during the
  download, or use the device dump path instead.
- The client build and the App Store build differ in version. Analyze
  the version in scope. If the client wants the store build assessed,
  say so explicitly and re-acquire; do not silently substitute builds.
- You only have a Mac without jailbreak tooling for the device's iOS
  version. Check current jailbreak support for the exact iOS version
  before promising the device path; otherwise commit to the
  client-build path from the start.

## Escalation

- No authorized acquisition path exists: the client will not provide a
  build and you have no jailbreakable test device. Stop. Static
  analysis of an App Store binary you cannot decrypt is not possible,
  and sideloading cracks from the internet is never authorized.
- The dumped IPA's signing identity does not match the client's
  claimed identity. Treat the binary as untrusted, confirm the source
  with the engagement lead, and do not base findings on it.
- Decryption works but the app phones home with device attestation on
  launch. Note it, keep the device offline during dumps if the client
  approves, and document any attestation behavior for the dynamic
  phase.
- Time is short: skip the Configurator path and go straight to asking
  the client for a build. It is the fastest route in nearly every
  engagement.

## Detection and defender view

IPA extraction is an analyst-side activity; the app cannot detect being
unzipped on your workstation. On the device, jailbreak detection and
Frida detection are the app's defenses against the dump step itself:
an app that refuses to run on a jailbroken device denies you the
decrypted binary, which is a legitimate resilience control. From the
defender side, the durable protections are not stopping the dump but
making it worthless: no hardcoded secrets, certificate pinning, and
server-side authorization mean a decrypted IPA yields little. Report
which of those held.

## Key references

- Frida documentation on iOS deployment:
  https://frida.re/docs/ios/
- frida-ios-dump project:
  https://github.com/AloneMonkey/frida-ios-dump
- Apple Platform Security guide (FairPlay and code signing):
  https://support.apple.com/guide/security/welcome/web
- OWASP MSTG iOS anti-reversing and static analysis notes:
  https://mas.owasp.org/MSTG/
- Apple Configurator documentation:
  https://support.apple.com/apple-configurator
