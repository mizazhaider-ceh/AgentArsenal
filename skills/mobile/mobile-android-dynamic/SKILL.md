---
name: mobile-android-dynamic
description: Use when you need to analyze a running Android app during
  an authorized engagement, such as a client mobile pentest or your own
  organization's release candidate. Covers test device and emulator
  setup with adb from platform-tools 35, frida-server deployment,
  objection 1.11 runtime exploration, Burp Suite traffic interception,
  runtime secret extraction, intent and deep link fuzzing, local storage
  and backup review, and handling root detection on authorized builds.
  Use when static analysis produced leads that need runtime proof, when
  the app hides behavior behind obfuscation or server checks, or when
  the assessment requires observing real data flows.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [android-static, android-dynamic, mobile-frida-scripting]
tools:
  - name: adb
    version: 35.0
  - name: Frida
    version: 16.5
  - name: objection
    version: 1.11
  - name: Burp Suite
    version: 2024.12
  - name: Wireshark
    version: 4.2
  - name: Python
    version: 3.12
---

Android dynamic analysis observes the app while it runs: its traffic,
its storage writes, its inter-process messages, and its reactions to
crafted input. Static analysis tells you where the interesting code
is; dynamic analysis proves what it does with real data. This skill is
the full authorized workflow from lab setup through traffic
interception, runtime instrumentation, input fuzzing, and evidence
capture. Test only apps and devices you are authorized to assess: the
client's in-scope build on your test device, your organization's app,
or a lab target.

## Quick Workflow

1. Prepare the test device or emulator: enable USB debugging, verify
   adb access, install the in-scope APK.
2. Deploy the matching frida-server and confirm Frida connectivity.
3. Capture baseline behavior: logcat, a proxy traffic sample, and a
   storage snapshot.
4. Explore with objection: components, storage, keystore, and hooked
   API watches.
5. Route traffic through Burp Suite; bypass pinning if needed.
6. Extract runtime secrets: memory search, SharedPreferences,
   databases, logs.
7. Fuzz exported components, intents, and deep links with crafted
   inputs while watching logcat.
8. Handle root detection and anti-tamper on the authorized build, then
   write findings with reproduction steps.

## 1. Lab setup: device, adb, frida-server

Use a rooted test device or an emulator you control. Root simplifies
everything; without it, use the Frida gadget path.

```bash
# Device visible and authorized
adb devices
# Example output:
# List of devices attached
# emulator-5554    device

# Architecture determines which frida-server binary to use
adb shell getprop ro.product.cpu.abi
# arm64-v8a -> frida-server-16.5-android-arm64

# Deploy and start frida-server
adb push frida-server-16.5-android-arm64 /data/local/tmp/fs
adb shell "chmod 755 /data/local/tmp/fs"
adb shell "su -c '/data/local/tmp/fs &'"
frida-ps -U | head -5

# Install the in-scope APK and confirm the version
adb install target.apk
adb shell dumpsys package com.example.target | grep -E "versionName|versionCode"
```

Example output shape for the version check:

```
versionCode=88 minSdk=26 targetSdk=34
versionName=2.4.1
```

Record the versionName with every finding. If the device is not
rooted, patch the APK with the Frida gadget via objection and install
the patched build:

```bash
objection patchapk --source target.apk
adb install target.apk.objection.apk
```

## 2. Baseline capture

Before changing anything, record normal behavior. Baselines make
anomalies visible and give the report its "expected versus observed"
structure.

```bash
# Clear and capture logcat during a normal app session
adb logcat -c
adb logcat -v threadtime > baseline-logcat.txt &
# ... interact with the app normally for two minutes ...
# Then stop the capture and look for warnings and leaks
grep -iE "token|password|secret|key|auth" baseline-logcat.txt | head -20

# Snapshot the app-private directory listing
adb shell "su -c 'ls -R /data/data/com.example.target/'" > baseline-files.txt
wc -l baseline-files.txt
```

Note which files appear after login versus on a fresh install; files
that appear only after authentication are where session material
lives.

## 3. Runtime exploration with objection

objection gives a REPL over the running app with no scripting. Start
every dynamic session here.

```bash
objection --gadget com.example.target explore
```

Inside the REPL:

```
# Components and current state
android hooking list activities
android hooking list services
android hooking list receivers
android hooking get current_activity
env

# Storage
android shared_prefs list
ls /data/data/com.example.target/files/
ls /data/data/com.example.target/databases/

# Watch security-relevant APIs while you use the app
android hooking watch crypto --dump-args --dump-return
android hooking watch file --dump-args
```

Example output shape:

```
# android hooking list activities
# com.example.target.LoginActivity
# com.example.target.MainActivity
# com.example.target.DebugActivity      <-- investigate this one
```

A `DebugActivity` in a release build is a classic finding: an exported
or reachable debug screen the developers forgot to remove.

## 4. Traffic interception with Burp Suite

```bash
# Point the device at Burp (emulator: 10.0.2.2 is the host loopback)
adb shell settings put global http_proxy 10.0.2.2:8080

# Install the Burp CA into the system trust store (rooted device)
# Convert Burp's DER export and push it with the subject hash as filename
openssl x509 -inform DER -in burp.der -out /tmp/burp.pem
HASH=$(openssl x509 -inform PEM -subject_hash_old -in /tmp/burp.pem | head -1)
adb push /tmp/burp.pem /data/local/tmp/${HASH}.0
adb shell "su -c 'mount -o rw,remount /system'"
adb shell "su -c 'cp /data/local/tmp/${HASH}.0 /system/etc/security/cacerts/'"
adb shell "su -c 'chmod 644 /system/etc/security/cacerts/${HASH}.0'"
adb shell "su -c 'mount -o ro,remount /system'"
```

Exercise the app and confirm decrypted HTTPS in Burp. If you see only
CONNECT tunnels, the app pins certificates; use the
mobile-frida-scripting-ssl-pinning-bypass sub-skill, or the objection
shortcut:

```
android sslpinning disable --quiet
```

Clear the proxy when the session ends:

```bash
adb shell settings put global http_proxy :0
```

## 5. Runtime secret extraction

Static strings show what is compiled in; runtime extraction shows what
is actually used, including values fetched from the server.

```
# In the objection REPL: search memory for a token fragment
memory search "eyJhbGciOi" --string

# Dump SharedPreferences (often holds tokens and flags)
android shared_prefs list
```

```bash
# Pull and inspect databases
adb shell "su -c 'ls /data/data/com.example.target/databases/'"
adb pull /data/data/com.example.target/databases/app.db ./
sqlite3 app.db ".tables"
sqlite3 app.db "SELECT name FROM sqlite_master WHERE type='table';"

# Check the keystore for aliases (keys should live here, not in prefs)
# In objection:
android keystore list
```

A key alias in the keystore with the actual key material in
SharedPreferences is a finding: the keystore is being used as a
label, not as protection.

## 6. Intent and deep link fuzzing

Exported components accept input from any app on the device, including
yours.

```bash
# List exported components from the manifest first (static phase)
# Then start an exported activity directly
adb shell am start -n com.example.target/.DebugActivity

# Fire crafted intents at exported receivers
adb shell am broadcast -a com.example.target.ACTION_SYNC --es token "test'injection"

# Open advertised deep links with hostile parameters
adb shell am start -a android.intent.action.VIEW -d "example://account/transfer?amount=9999"

# Start an exported service with extras
adb shell am startservice -n com.example.target/.SyncService --es url "https://test.example/"
```

Watch logcat during fuzzing:

```bash
adb logcat -v threadtime | grep -iE "com.example.target|exception|caused by" | head -40
```

Example output shape for a crash worth reporting:

```
E/AndroidRuntime: FATAL EXCEPTION: main
E/AndroidRuntime: java.lang.NullPointerException: Attempt to invoke virtual method
E/AndroidRuntime:   at com.example.target.DeepLinkHandler.onCreate(DeepLinkHandler.java:42)
```

A crash from a crafted deep link is at minimum a robustness finding;
the stack trace often reveals the injectable code path for a deeper
issue.

## 7. Handling root detection on authorized builds

Test builds often include root detection that blocks your lab. On an
authorized build you may neutralize it to continue testing; document
exactly what you bypassed.

```javascript
// bypass-root.js: hook common root detection checks
Java.perform(function () {
    var RootBeer = Java.use('com.scottyab.rootbeer.RootBeer');
    RootBeer.isRooted.implementation = function () {
        console.log('[*] RootBeer.isRooted forced to false');
        return false;
    };
    // Generic: apps that check for su binary or test-keys
    var File = Java.use('java.io.File');
    File.exists.implementation = function () {
        var path = this.getAbsolutePath();
        if (path.indexOf('su') !== -1 || path.indexOf('busybox') !== -1) {
            return false;
        }
        return this.exists();
    };
});
```

```bash
frida -U -f com.example.target -l bypass-root.js --no-pause
```

If the app also detects Frida itself, rename the frida-server binary,
run it on a nonstandard port with `-l`, and connect with
`frida -H 127.0.0.1:27043`. Report the detection as a working control
and the bypass as evidence of its depth.

## 8. Evidence capture and reporting

Every dynamic finding needs reproduction steps precise enough that the
client can replay them:

```
Finding: Debug activity reachable via intent
Steps:
  1. adb shell am start -n com.example.target/.DebugActivity
  2. Debug screen opens without authentication (screenshot 4)
Impact: exposes internal diagnostics and a log viewer
Severity: Medium (MASVS-PLATFORM-2, MSTG-PLATFORM-4)
```

Save the exact commands, the app version, and the relevant logcat or
proxy excerpts with each finding. The Commands Executed discipline
from the lab guides applies here: no finding without the command
that produced it.

## Edge cases

- The app refuses to run on the emulator (Play Integrity or
  SafetyNet failure). Move to a physical rooted test device, which
  passes more integrity checks than any emulator.
- frida-server dies when the device sleeps. Keep the device awake
  during sessions, or run frida-server under a persistent shell.
- Traffic uses certificate transparency plus pinning. The generic
  bypass decrypts nothing; escalate to a targeted hook or ask the
  client for a debuggable build.
- The app communicates over QUIC, WebSockets, or raw TLS sockets.
  Burp sees handshakes only; hook the socket layer with Frida to
  capture plaintext before encryption.
- Objection cannot start because of anti-tamper. Use plain Frida
  scripts with delayed hooks, which give finer control over timing.
- Logcat is flooded by system noise. Filter by the app PID:
  `adb shell pidof com.example.target`, then
  `adb logcat --pid=<pid>`.
- The patched gadget APK fails to install (signature or split APK
  issues). Ask the client for a debuggable build instead of fighting
  the repackaging.

## Escalation

- Static analysis flagged a method you cannot reach at runtime. It
  may be dead code, reflection-hidden, or in an unloaded module.
  Trigger the feature in the UI with hooks active, or enumerate
  loaded classes and search by name fragment.
- Pinning bypass fails on every known approach. Identify the exact
  library from decompiled code and write the targeted hook, or
  request a build with pinning disabled for the test window.
- You discover the app exfiltrating data beyond its stated purpose
  (contacts, SMS, location without consent). Stop testing that flow,
  document carefully, and escalate to the engagement lead before
  writing it up; this may be a compromised SDK.
- The assessment needs persistent behavior changes. Patch with
  apktool, rebuild, and re-sign with your own debug key on the
  authorized test build.

## Detection and defender view

On your test device, detection does not apply. In production,
defenders detect this whole workflow through root detection, Frida
artifact detection, emulator detection, APK signature tampering
checks, and Play Integrity verdicts. The durable defenses are the
ones that survive full instrumentation: server-side authorization on
every API call, certificate pinning plus attestation for high-value
flows, no sensitive data in client storage, and short-lived tokens.
Report which of these the app actually has; a pinning bypass that
took ten seconds is itself a finding about defense depth.

## Key references

- OWASP MSTG Android dynamic testing:
  https://mas.owasp.org/MSTG/
- OWASP MASVS: https://mas.owasp.org/MASVS/
- Frida Android guide: https://frida.re/docs/android/
- objection documentation:
  https://github.com/sensepost/objection
- Android developer docs on intents and intent filters:
  https://developer.android.com/guide/components/intents-filters
- Android network security configuration:
  https://developer.android.com/training/articles/security-config
- Burp Suite mobile testing docs:
  https://portswigger.net/burp/documentation
