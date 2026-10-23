---
name: ios-dynamic-analysis
description: Use when dynamically analyzing iOS apps on an authorized
  engagement with a test device you own. Covers jailbreak lab setup,
  Frida instrumentation, traffic interception, and runtime data
  inspection. Also use when static analysis of an iOS app needs runtime
  confirmation.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [ios-basics, android-dynamic, api-security-testing]
tools:
  - name: Python
    version: 3.12
  - name: Burp Suite
    version: 2026.2
---

iOS dynamic analysis watches the app run: intercept its traffic,
hook its methods, and inspect what it stores. This skill covers the
authorized lab method on a test device you own: setup, Frida hooks,
traffic capture, and data inspection. Test only apps you are
authorized to assess, on devices you own.

## Quick Workflow

1. Prepare the test device: jailbroken lab device, your test Apple
   ID, no personal data.
2. Install the target app build you are authorized to test.
3. Set up traffic interception: proxy with a trusted CA on the
   device.
4. Attach Frida and hook the interesting classes: crypto, network,
   and storage.
5. Exercise the app: login, payments, and sensitive features, while
   capturing.
6. Inspect runtime storage: keychain, files, and caches.
7. Test the findings: replay, tamper, and bypass where authorized.
8. Clean the device between apps; never mix test data.

## 1. Lab setup and traffic

```bash
# Frida server on the jailbroken device (your lab device)
# scp frida-server to the device, run it, then from your workstation:
frida-ps -U | head -20
# Confirm the target app process is listed
```

```bash
# Traffic: install the Burp CA on the device, set the proxy
# Then exercise the app and watch for:
# - certificate pinning (connection fails -> note it, then bypass in lab)
# - plaintext PII in requests
# - weak token handling
echo "pinning bypass in the lab: Frida script hooking the pinning check"
```

## 2. Frida hooks

```javascript
// Hook example: log the arguments of a crypto method (lab, authorized app)
// frida -U -f com.target.app -l hook.js
console.log("hooking...");
/* ObjC.choose or method swizzle pattern per the app's classes:
   - hook NSURLSession methods to log URLs and bodies
   - hook Keychain wrappers to log stored items
   - hook jailbreak detection to return false (lab only) */
```

```bash
# Runtime storage inspection (jailbroken device shell)
# Keychain dump for the app (lab tooling), file inspection:
find /var/mobile/Containers/Data/Application -maxdepth 2 -name "*.sqlite" 2>/dev/null | head
# Check: tokens in plaintext files, cached responses with PII
```

## Edge cases

- The app detects the jailbreak and refuses to run. Bypass in the
  lab for testing, and report the detection as a (weak) control.
- Certificate pinning blocks the proxy. Bypass with Frida in the
  lab; report pinning as present but bypassable.
- The app is a TestFlight or enterprise build. Confirm it matches
  the production build under assessment.

## Escalation

- Traffic shows API flaws: hand the endpoints to api-security-testing.
- Crypto issues found at runtime: confirm statically and report
  with both evidences.

## Detection and defender view

App defenders use jailbreak detection, pinning, and anti tamper,
all of which slow but do not stop lab analysis. They detect abuse
through device attestation (App Attest) and server side anomaly
detection. The durable defense is server side: never trust the
client, validate everything, and treat the app as compromised by
design.

## Key references

- OWASP MASVS: dynamic analysis requirements.
- Frida documentation: iOS instrumentation.
- Related skills: ios-basics, android-dynamic.
