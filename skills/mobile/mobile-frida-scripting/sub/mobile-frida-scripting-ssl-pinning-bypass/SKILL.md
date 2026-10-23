---
name: mobile-frida-scripting-ssl-pinning-bypass
description: Use when a mobile app's HTTPS traffic stays encrypted in
  your proxy during an authorized test because of certificate pinning.
  Covers pinning bypass agents for Android (OkHttp CertificatePinner,
  TrustManager, network security config) and iOS (NSURLSession delegate,
  SecTrustEvaluate, Alamofire ServerTrustPolicy) with Frida 16.5, the
  objection one-command bypasses, verifying decrypted traffic in Burp
  Suite, and handling native-code pinning. Use when the parent
  mobile-frida-scripting workflow or objection hits encrypted tunnels,
  when static analysis flagged pinning libraries, or when you need the
  app's real API traffic for further testing.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
parent: mobile-frida-scripting
requires: [mobile-frida-scripting]
extends: []
relates: [mobile-frida-scripting]
tools:
  - name: Frida
    version: 16.5
  - name: objection
    version: 1.11
  - name: Burp Suite
    version: 2024.12
---

Certificate pinning hardcodes which server certificates an app trusts,
so your proxy's CA is rejected even when installed on the device. The
bypass replaces the app's trust decision at runtime with "accept", which
lets the proxy decrypt traffic for analysis. This sub-skill gives you
the platform patterns that cover most apps, the objection shortcuts,
and the verification loop. Only bypass pinning on apps and devices you
are authorized to test; the technique itself is dual-use, so scope
discipline is the whole game.

## Quick Workflow

1. Confirm the symptom: proxy shows CONNECT tunnels or TLS alerts, no
   decrypted HTTPS.
2. Identify the pinning implementation from static analysis (OkHttp,
   TrustKit, network security config, NSURLSession, Alamofire).
3. Try the objection one-command bypass first; it covers the common
   cases in seconds.
4. If objection fails, run the platform Frida agent below matching the
   library in use.
5. Verify: repeat an in-app action and confirm decrypted HTTPS in the
   proxy.
6. If still encrypted, check for native-code pinning and escalate to a
   targeted hook.
7. Record which bypass worked and what it proves about the app's
   transport defenses.

## 1. Android: OkHttp and TrustManager bypass

```javascript
// pinning-android.js: covers OkHttp, TrustManagerFactory, HostnameVerifier
Java.perform(function () {
    // OkHttp3 CertificatePinner.check(String, List)
    try {
        var Pinner = Java.use('okhttp3.CertificatePinner');
        Pinner.check.overload('java.lang.String', 'java.util.List')
            .implementation = function (host, pins) {
                console.log('[*] OkHttp pinning bypassed for ' + host);
                return;
            };
        // Newer overload with Call parameter
        Pinner.check.overload('java.lang.String', 'java.util.List').implementation = function () { return; };
    } catch (e) { console.log('[-] OkHttp CertificatePinner not found'); }

    // TrustManager: replace checkServerTrusted with a no-op
    try {
        var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
        var TrustManager = Java.registerClass({
            name: 'com.example.PermissiveTrustManager',
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function (chain, authType) {},
                checkServerTrusted: function (chain, authType) {},
                getAcceptedIssuers: function () { return []; }
            }
        });
        var SSLContext = Java.use('javax.net.ssl.SSLContext');
        SSLContext.init.overload('[Ljavax.net.ssl.KeyManager;',
            '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom')
            .implementation = function (km, tm, sr) {
                console.log('[*] SSLContext.init hooked, injecting permissive TrustManager');
                var permissive = TrustManager.$new();
                this.init(km, [permissive], sr);
            };
    } catch (e) { console.log('[-] TrustManager hook failed: ' + e); }

    // HostnameVerifier: accept everything
    try {
        var HostnameVerifier = Java.use('javax.net.ssl.HostnameVerifier');
        // Hook the default verifier used by HttpsURLConnection
        var HttpsURLConnection = Java.use('javax.net.ssl.HttpsURLConnection');
        HttpsURLConnection.setDefaultHostnameVerifier.implementation = function (v) {
            console.log('[*] setDefaultHostnameVerifier called, keeping permissive');
        };
    } catch (e) { console.log('[-] HostnameVerifier hook skipped'); }
});
```

Run against the spawned app:

```bash
frida -U -f com.example.target -l pinning-android.js --no-pause
```

## 2. Android: network security config and TrustKit

Apps using `network_security_config.xml` with `<pin-set>` do not call
OkHttp's pinner; the platform validates pins. Hook at the
X509TrustManager level as above, which still applies, or patch the
config in a repackaged test build (authorized target only):

```bash
# Inspect the config to know what you are bypassing
# (from the APK: res/xml/network_security_config.xml)
grep -A8 "pin-set" res/xml/network_security_config.xml
```

TrustKit and Appcelerator pin through their own validators. The
community bypass scripts bundle hooks for these; when hand-rolling,
find the validator class from static analysis (search for TrustKit in
the decompiled sources) and no-op its verification method the same
way as the OkHttp pinner.

## 3. iOS: NSURLSession and SecTrustEvaluate bypass

```javascript
// pinning-ios.js: covers NSURLSession delegates and Security.framework
if (ObjC.available) {
    // Hook NSURLSession delegate authentication challenges is complex;
    // the reliable chokepoint is SecTrustEvaluateWithError / SecTrustEvaluate
    var SecTrustEvaluateWithError = Module.getExportByName('Security', 'SecTrustEvaluateWithError');
    Interceptor.attach(SecTrustEvaluateWithError, {
        onEnter: function (args) {
            console.log('[*] SecTrustEvaluateWithError called');
        },
        onLeave: function (retval) {
            // BOOL return: force true (1)
            retval.replace(1);
            console.log('[*] forced trust evaluation to pass');
        }
    });

    // Alamofire ServerTrustPolicy.evaluate: force success
    try {
        var ServerTrustPolicy = ObjC.classes.AFServerTrustPolicy;
        if (ServerTrustPolicy) {
            Interceptor.attach(ServerTrustPolicy['- evaluateServerTrust:forDomain:'].implementation, {
                onLeave: function (retval) { retval.replace(1); }
            });
            console.log('[*] Alamofire trust policy hooked');
        }
    } catch (e) { console.log('[-] Alamofire not present'); }
}
```

```bash
frida -U -f com.example.target -l pinning-ios.js --no-pause
```

For Swift-only networking stacks, the symbol names are mangled; use
the native export enumeration from the parent skill to find the trust
evaluation function, or fall back to the objection bypass which
handles several Swift stacks.

## 4. The objection shortcuts

Before hand-rolling, try the built-ins. They encode the same patterns
above and take seconds:

```
# Android
android sslpinning disable
android sslpinning disable --quiet

# iOS
ios sslpinning disable --quiet
```

objection prints which hooks it installed. If it reports hooks
installed but traffic stays encrypted, the pinning lives somewhere
objection does not cover (native code, custom validator), and you move
to section 5.

## 5. Native-code pinning

When Java and ObjC hooks do nothing, the check is in native code:
OpenSSL or BoringSSL verification, or a custom C validator. Strategy:

```javascript
// Find TLS verification functions in native libraries
Process.enumerateModules().forEach(function (m) {
    m.enumerateExports().forEach(function (e) {
        if (/SSL_get_verify_result|verify_callback|X509_verify/i.test(e.name)) {
            console.log(m.name + '!' + e.name + ' @ ' + e.address);
        }
    });
});
```

Hook `SSL_get_verify_result` to return `X509_V_OK` (0):

```javascript
var f = Module.getExportByName('libssl.so', 'SSL_get_verify_result');
Interceptor.attach(f, {
    onLeave: function (retval) {
        console.log('[*] forcing verify result to X509_V_OK');
        retval.replace(0);
    }
});
```

On iOS the equivalent chokepoint is often `SSLHandshake` in
Security.framework or BoringSSL symbols inside the app binary. This is
the escalation point: identify the exact function from Ghidra, then
write the targeted hook.

## 6. Verification loop

A bypass is only done when the proxy shows plaintext:

1. In the app, perform a network action (login, refresh, search).
2. In Burp, confirm the request and response bodies are readable.
3. Check the TLS handshake in Burp's dashboard: it should show Burp's
   CA as the issuer, proving traffic flows through the proxy.
4. Note any endpoints that still fail: some apps pin only the
   authentication host and leave analytics unpinned, or vice versa.

```bash
# Sanity: confirm the device proxy is actually set
adb shell settings get global http_proxy
# Should show your Burp host:port, e.g. 10.0.2.2:8080
```

If some hosts decrypt and others do not, the app uses different trust
configurations per host. That is worth a report line: inconsistent
pinning coverage.

## Edge cases

- The bypass works but the app then fails server-side attestation
  (Play Integrity, app attestation). Traffic decrypts, but the API
  rejects requests. Document the attestation as an effective
  additional control; you have still proven the pinning bypass.
- Multiple pinning libraries in one app (OkHttp plus TrustKit). One
  bypass is not enough; hook each validator, and verify host by host.
- The app uses certificate transparency enforcement on top of
  pinning. Generic bypasses ignore SCT checks; you need the specific
  transparency validator hook, or test the API directly.
- QUIC or HTTP/3 traffic bypasses the proxy entirely. Force HTTP/1.1
  or HTTP/2 via proxy settings, or hook the socket layer to capture
  plaintext before encryption.
- WebViews pin independently of the native stack. Hook the WebView's
  `onReceivedSslError` (Android) or `WKNavigationDelegate`
  (iOS) in addition to the native bypass.
- The app pins a backup pin and rotates. Your bypass does not care
  about pin values since it no-ops the check, but note rotation
  behavior for the report's accuracy.

## Escalation

- Every known bypass fails. Decompile the exact trust evaluation
  (search the binary for the pinned hash strings from static
  analysis), find the function that compares them, and hook it
  directly. This is normal on hardened banking apps.
- Pinning is enforced in a server-driven config fetched at runtime.
  Hook the config parser or the network client that applies it; the
  check still executes client-side and is still hookable.
- You cannot get any traffic decrypted and the engagement needs API
  coverage. Ask the client for a build with pinning disabled or with
  a debug flag; this is a standard ask on authorized tests.
- Time is short: at minimum, run the objection bypass and document
  the result. "Pinning resisted generic bypass" is itself a useful
  report statement with the right evidence.

## Detection and defender view

Pinning bypass is exactly what the control is meant to resist, so a
bypass that takes one objection command is a finding about defense
depth, not a clever hack. Stronger defenses layer attestation (Play
Integrity, App Attest) and anomaly detection on top of pinning, so
that even decrypted traffic cannot be replayed usefully. Report the
full chain: pinning bypassed in N minutes with tool X, then attestation
accepted or rejected the proxied traffic. Defenders should also know
that pinning without server-side authorization is theater against an
instrumented client.

## Key references

- Frida CodeShare pinning bypass scripts (review before use):
  https://codeshare.frida.re/
- objection SSL pinning commands:
  https://github.com/sensepost/objection
- OWASP MSTG network communication testing:
  https://mas.owasp.org/MSTG/
- OWASP MASVS network requirements:
  https://mas.owasp.org/MASVS/
- Android network security configuration docs:
  https://developer.android.com/training/articles/security-config
- Apple ATS and TLS documentation:
  https://developer.apple.com/documentation/security/preventing_insecure_network_connections
