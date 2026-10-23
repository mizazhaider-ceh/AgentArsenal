---
name: mobile-android-dynamic-runtime-manipulation
description: Use when you need to change an Android app's behavior at
  runtime during an authorized test, beyond observation. Covers forcing
  method return values with Frida 16.5, modifying arguments and instance
  fields, bypassing client-side checks (login gates, license checks,
  timers) on authorized builds, manipulating activity state with adb and
  am commands, and clearly labeling behavior-changing hooks. Use when
  the parent mobile-android-dynamic workflow needs to test what the app
  does after a check passes, when you must reach authenticated screens
  without valid credentials on a test build, or when server responses
  need client-side simulation.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
parent: mobile-android-dynamic
requires: [mobile-android-dynamic]
extends: []
relates: [mobile-android-dynamic]
tools:
  - name: Frida
    version: 16.5
  - name: adb
    version: 35.0
  - name: objection
    version: 1.11
  - name: Python
    version: 3.12
---

Runtime manipulation changes what the app does instead of just watching
it: forcing a login check to pass, rewriting a server response before
the UI sees it, or skipping a license gate. It answers "what happens
if" questions that observation cannot. This sub-skill covers the
techniques and, just as importantly, the discipline: every
behavior-changing hook is labeled, reversible, and scoped to the
authorized test build. Never manipulate apps or accounts outside the
engagement scope; changing behavior on someone else's production app
is not testing.

## Quick Workflow

1. Define the question: which check, and what should happen after it
   passes.
2. Locate the exact method from static analysis or runtime
   enumeration.
3. Write an observation-only hook first and confirm it fires on the
   real flow.
4. Add the modification (forced return, rewritten argument), labeled
   MODIFIES BEHAVIOR in the script header.
5. Trigger the flow and record what the app does differently.
6. Check whether the server independently validates; note the result.
7. Restore the original behavior (reload the script without the
   modification) and confirm the app returns to normal.
8. Write the finding: what was forced, what it unlocked, and whether
   the server stopped it.

## 1. Forcing return values

```javascript
// manipulate.js: every behavior change labeled at the top
// MODIFIES BEHAVIOR: forces auth and license checks to pass (authorized test build only)
Java.perform(function () {
    // 1. Force login state
    var Session = Java.use('com.example.target.SessionManager');
    Session.isLoggedIn.implementation = function () {
        console.log('[*] isLoggedIn forced -> true');
        return true;
    };

    // 2. Force license validation
    var License = Java.use('com.example.target.LicenseValidator');
    License.validate.overload('java.lang.String').implementation = function (key) {
        console.log('[*] validate("' + key.slice(0, 8) + '...") forced -> true');
        return true;
    };

    // 3. Skip a timed gate (e.g. trial countdown)
    var Trial = Java.use('com.example.target.TrialManager');
    Trial.getDaysRemaining.implementation = function () {
        return 999;
    };
});
```

```bash
frida -U -f com.example.target -l manipulate.js --no-pause
```

After forcing, navigate the app and record which screens and API calls
become reachable. The security question is always what the server
does next: if the API serves premium data to a forced client, the
authorization flaw is server-side and critical.

## 2. Rewriting arguments and responses

```javascript
Java.perform(function () {
    // Rewrite the user id sent to the API (test horizontal access control)
    var Api = Java.use('com.example.target.ApiClient');
    Api.getProfile.overload('java.lang.String').implementation = function (userId) {
        var target = 'user-1337';  // second test account provided by the client
        console.log('[*] getProfile: ' + userId + ' -> ' + target);
        return this.getProfile(target);
    };

    // Rewrite a server response before the app parses it
    var Parser = Java.use('com.example.target.ResponseParser');
    Parser.parse.overload('java.lang.String').implementation = function (json) {
        console.log('[*] original response: ' + json.slice(0, 120));
        var modified = json.replace('"isAdmin":false', '"isAdmin":true');
        return this.parse(modified);
    };
});
```

Use client-provided test accounts for IDOR-style checks, never real
user identifiers. The forced `isAdmin` rewrite tests whether the app
trusts the client; the finding lands only if the server also honors
the tampered role.

## 3. Manipulating fields and activity state

```javascript
Java.perform(function () {
    // Flip a boolean field on a live activity
    Java.choose('com.example.target.MainActivity', {
        onMatch: function (activity) {
            var field = activity.class.getDeclaredField('debugMode');
            field.setAccessible(true);
            field.setBoolean(activity, true);
            console.log('[*] debugMode enabled on live activity');
        },
        onComplete: function () {}
    });
});
```

```bash
# Activity-level manipulation without Frida
# Bring any activity to the foreground, including non-exported ones on debug builds
adb shell am start -n com.example.target/.AdminActivity

# Simulate configuration changes the app may handle insecurely
adb shell am broadcast -a android.intent.action.BATTERY_LOW
```

Changing activity state with `am start` on non-exported activities
works on debuggable builds; on release builds the activity manager
enforces the exported flag, which is itself worth verifying.

## 4. Time and trial manipulation

```javascript
Java.perform(function () {
    // Freeze System.currentTimeMillis for trial logic under test
    var System = Java.use('java.lang.System');
    var fixedTime = 1760000000000;  // a fixed instant for the test window
    System.currentTimeMillis.implementation = function () {
        return fixedTime;
    };
});
```

```bash
# Device-level alternative: change the clock (affects everything, use carefully)
adb shell "su -c 'date 101512002026.00'"
```

Clock manipulation tests trial expiry, token lifetimes, and
certificate validity windows. Always restore the clock afterward; a
wrong device clock breaks TLS validation for every subsequent test.

## 5. objection shortcuts for quick manipulation

```
# Force common boolean returns without writing scripts
android hooking set_return_value com.example.target.SessionManager.isLoggedIn true

# List methods first if you are unsure of the name
android hooking list_methods com.example.target.SessionManager
```

objection's one-liner covers simple boolean gates in seconds. For
anything with arguments or object returns, write the Frida script.

## 6. Verifying server-side enforcement

The manipulation is only half the test. After forcing the client:

1. Perform the now-unlocked action (open premium content, call the
   admin API).
2. Watch the proxy: does the server return the data or reject with
   401 or 403.
3. If the server rejects, the client check was defense in depth and
   the server is correctly authoritative. Note it as a positive.
4. If the server complies, you have an authorization finding. Capture
   the request and response as evidence.

```bash
# Example: forced premium screen triggers this API call (from Burp history)
# GET /api/v2/premium/content -> 200 with content  => finding
# GET /api/v2/premium/content -> 403 Forbidden     => server enforces correctly
```

## Edge cases

- Forcing a return value crashes the app later in the flow. The real
  method had side effects (caching, callbacks) that the forced path
  skipped. Hook narrower: force the value only for the specific call
  you are testing, using a counter or a caller check.
- The check runs in native code, so the Java hook never fires. Move
  to the native-code-tracing sub-skill and force the native return
  instead.
- The app re-checks on every screen, not just at login. A single
  forced login is not enough; keep the hook installed for the whole
  session and note the re-check frequency.
- Server-side enforcement makes the manipulation pointless for data
  access but still useful for UI review. Say so explicitly rather
  than claiming a finding the server already prevents.
- Multiple processes (the app uses isolated services). Frida attaches
  to one process; spawn with `--realm` or attach to the specific
  process name shown by frida-ps.
- The modification persists across sessions because you patched the
  APK instead of hooking. Prefer hooks (reversible, in-memory) over
  patches for behavior tests; patches are for persistent lab setups.

## Escalation

- Manipulation reveals that the server trusts client-supplied roles
  or ids. This is the critical finding: stop, capture clean evidence
  with client test accounts, and report promptly rather than
  exploring further.
- The app detects your hooks and wipes local data (some banking apps
  do this). Restore from your baseline snapshot, note the defensive
  behavior as effective, and continue with observation-only hooks.
- You need to simulate a full malicious server, not just rewrite one
  response. Point the app at a test harness with the proxy's
  map-local rules, keeping everything inside the authorized lab
  network.
- The engagement scope is unclear about how far manipulation may go.
  Ask before forcing payment flows, license checks on paid features,
  or anything that could cost the client money.

## Detection and defender view

Runtime manipulation is what client-side defenses exist to slow:
integrity checks, hook detection, and server-side re-validation.
Every forced check that the server then rejects is the architecture
working correctly, and your report should credit it. The durable
defense is never trusting the client: authorize every action
server-side, keep tokens short-lived and bound, and treat any
client-supplied privilege flag as untrusted input. As the tester,
your manipulation log doubles as a map of which client controls
exist and how quickly each fell.

## Key references

- Frida JavaScript API: https://frida.re/docs/javascript-api/
- objection hooking commands:
  https://github.com/sensepost/objection
- OWASP MSTG tampering and reverse engineering:
  https://mas.owasp.org/MSTG/
- OWASP MASVS resilience and authorization:
  https://mas.owasp.org/MASVS/
- Android activity lifecycle and am commands:
  https://developer.android.com/guide/components/activities/activity-lifecycle
- CWE-602 (Client-Side Enforcement of Server-Side Security):
  https://cwe.mitre.org/data/definitions/602.html
