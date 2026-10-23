---
name: mobile-frida-scripting-function-hooking
description: Use when you need precise control over individual methods
  in a mobile app during an authorized test, on Android or iOS. Covers
  resolving exact overloads on Android with Java.use, hooking Objective-C
  selectors with the ObjC bridge and Interceptor, dumping and modifying
  arguments, forcing return values, reading and writing instance fields,
  calling methods on live instances with Java.choose and ObjC.choose, and
  chaining hooks across a call flow. Use when static analysis or the
  parent mobile-frida-scripting workflow gives you exact method names to
  instrument, when you must observe or alter one security check, or when
  objection cannot reach the logic you need, using Frida 16.5 agents
  driven by Python harnesses.
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
  - name: frida-tools
    version: 12.4
  - name: Python
    version: 3.12
---

Function hooking is the core Frida operation: intercept one method,
see what goes in, decide what comes out. Done well, it turns a black
box security check into a readable log line. This sub-skill is the
reference for doing it precisely: exact signatures, argument handling
on both platforms, return value control, and field access. All examples
assume an authorized target on a test device you control. Forcing
return values changes app behavior; label such hooks clearly in your
notes so observation and modification never get confused.

## Quick Workflow

1. Get the exact method signature from static analysis or runtime
   enumeration (class name, method name, parameter types).
2. Write a minimal hook that only logs entry, and confirm it fires.
3. Add argument dumping with proper type conversion for readability.
4. Add return value logging with a backtrace to see the caller.
5. If the test needs it, add return value forcing or argument
   modification, clearly labeled.
6. For state inspection, read instance fields or call getters on live
   instances.
7. Chain hooks across the call flow (caller and callee) to confirm
   the full path.
8. Save the script with the app version and a note of what it proved.

## 1. Android: exact overload resolution

```javascript
Java.perform(function () {
    var Target = Java.use('com.example.target.CryptoUtil');

    // List overloads when you are unsure of the signature
    Target.encrypt.overloads.forEach(function (o, i) {
        console.log('[*] overload ' + i + ': ' + o.methodName + o.argumentTypes.join(','));
    });

    // Hook the exact overload: encrypt(byte[], byte[])
    Target.encrypt.overload('[B', '[B').implementation = function (data, key) {
        console.log('[*] encrypt called');
        console.log('    key (' + key.length + ' bytes): ' + bytesToHex(key));
        console.log('    plaintext (' + data.length + ' bytes): ' + bytesToHex(data.slice(0, 64)));
        var out = this.encrypt(data, key);
        console.log('    ciphertext (' + out.length + ' bytes): ' + bytesToHex(out.slice(0, 64)));
        return out;
    };

    function bytesToHex(arr) {
        var hex = [];
        for (var i = 0; i < arr.length; i++) {
            hex.push(('0' + (arr[i] & 0xff).toString(16)).slice(-2));
        }
        return hex.join('');
    }
});
```

Example output shape:

```
[*] overload 0: encrypt[B,[B
[*] encrypt called
    key (32 bytes): 9f2c4a7e1b3d5f608a2c4e6b8d0a2f4c6e...
    plaintext (48 bytes): 7b22757365726e616d65223a22616c69636522...
    ciphertext (64 bytes): a41f09c2...
```

A 32-byte key logged here is the app's encryption key in the clear.
That is the finding; the hook is just how you proved it.

## 2. Android: forcing return values and modifying arguments

```javascript
Java.perform(function () {
    var Checker = Java.use('com.example.target.RootChecker');

    // Force the check to report "not rooted" during authorized testing
    Checker.isDeviceRooted.implementation = function () {
        console.log('[*] isDeviceRooted() forced to false');
        return false;
    };

    // Modify an argument: rewrite the API base URL to your test server
    var Api = Java.use('com.example.target.ApiClient');
    Api.setBaseUrl.overload('java.lang.String').implementation = function (url) {
        var testUrl = 'https://test-api.example.local/';
        console.log('[*] rewriting base URL ' + url + ' -> ' + testUrl);
        this.setBaseUrl(testUrl);
    };
});
```

Label every behavior-changing hook in the script header with
`MODIFIES BEHAVIOR` so a later reader never mistakes forced values
for observed ones.

## 3. Android: fields and live instances

```javascript
Java.perform(function () {
    // Read and write an instance field
    var Session = Java.use('com.example.target.Session');
    var field = Session.class.getDeclaredField('authToken');
    field.setAccessible(true);

    // Find live instances and dump the field
    Java.choose('com.example.target.Session', {
        onMatch: function (instance) {
            var token = field.get(instance);
            console.log('[*] live session token: ' + token);
        },
        onComplete: function () { console.log('[*] instance scan complete'); }
    });

    // Call a method on the live instance
    Java.choose('com.example.target.Session', {
        onMatch: function (instance) {
            console.log('[*] isExpired: ' + instance.isExpired());
        },
        onComplete: function () {}
    });
});
```

`Java.choose` only finds instances the garbage collector has not
collected; trigger the relevant screen first so the instance exists.

## 4. iOS: hooking selectors precisely

```javascript
if (ObjC.available) {
    var LoginManager = ObjC.classes.LoginManager;

    // Instance method with arguments: - loginWithUsername:password:completion:
    Interceptor.attach(LoginManager['- loginWithUsername:password:completion:'].implementation, {
        onEnter: function (args) {
            // args[0] self, args[1] selector, args[2..] real arguments
            var username = ObjC.Object(args[2]).toString();
            var password = ObjC.Object(args[3]).toString();
            console.log('[*] login attempt for: ' + username);
            console.log('[*] password length: ' + password.length);
            // Never log the password value itself in saved output
        },
        onLeave: function (retval) {
            console.log('[*] login returned, backtrace:');
            console.log(Thread.backtrace(this.context, Backtracer.ACCURATE)
                .map(DebugSymbol.fromAddress).join('\n'));
        }
    });

    // Class method: + sharedManager
    Interceptor.attach(LoginManager['+ sharedManager'].implementation, {
        onLeave: function (retval) {
            console.log('[*] sharedManager -> ' + retval);
        }
    });
}
```

Note the discipline: log that a password was passed and its length,
not its value, in any artifact you keep. Your working notes are still
part of the engagement record.

## 5. iOS: properties, ivars, and live instances

```javascript
if (ObjC.available) {
    // Find live instances of a view controller or manager
    ObjC.choose(ObjC.classes.LoginViewController, {
        onMatch: function (vc) {
            console.log('[*] found LoginViewController: ' + vc);
            // Read an ivar by name
            var token = vc.$ivars._authToken;
            if (token) console.log('[*] _authToken: ' + token.toString().slice(0, 20) + '...');
        },
        onComplete: function () {}
    });

    // Swizzle via method_setImplementation for persistent replacement
    var orig = LoginManager['- isAuthenticated'].implementation;
    Interceptor.attach(orig, {
        onLeave: function (retval) {
            console.log('[*] isAuthenticated intercepted, forcing true for test flow');
            retval.replace(1);
        }
    });
}
```

`$ivars` access is the fastest way to read object state without
calling getters that might have side effects.

## 6. Chaining hooks across a call flow

One hook shows a point; chained hooks show the flow. Hook the caller
and the callee together to confirm data actually travels between
them:

```javascript
Java.perform(function () {
    var Ui = Java.use('com.example.target.LoginActivity');
    var Net = Java.use('com.example.target.ApiClient');

    Ui.onLoginClicked.implementation = function (view) {
        console.log('[*] FLOW: login button clicked');
        this.onLoginClicked(view);
    };
    Net.postCredentials.overload('java.lang.String', 'java.lang.String')
        .implementation = function (u, p) {
            console.log('[*] FLOW: credentials posted for ' + u);
            return this.postCredentials(u, p);
        };
});
```

If the first hook fires but the second never does, the credentials
take a different path than static analysis suggested, and you have
just found the real one by elimination.

## Edge cases

- The method is overloaded and your signature is slightly wrong. The
  hook silently never fires. Always enumerate overloads first when
  the signature comes from a decompiler rather than headers.
- The class is loaded by a custom classloader (common in packed or
  plugin apps). `Java.use` fails; enumerate classloaders with
  `Java.enumerateClassLoaders` and use `Java.ClassFactory` on the
  right one.
- The method is inlined or the call goes through reflection. Hook the
  reflective call (`Method.invoke`) instead, and log which method it
  dispatches to.
- iOS selector lookup returns undefined. The class may be Swift-only
  (no ObjC metadata) or the method may be stripped. Check
  `ObjC.classes` for the class first, then fall back to native
  hooking of the mangled symbol.
- Hooking a hot method (called thousands of times per second) floods
  the log and slows the app. Add a counter and log every Nth call,
  or hook only while a flag set via RPC is true.
- Forcing a return value crashes the app later. The app may depend
  on side effects of the real method. Force values only for the
  narrow test, then restore the original implementation.
- Arguments are encrypted or encoded before your hook point. Move the
  hook earlier in the call chain, or hook the encode function itself.

## Escalation

- The security check you need to observe is split across native code.
  Hand the Java or ObjC hook points to the native-code-tracing
  sub-skill and trace from the managed hook into the native layer.
- The app detects hooks on its security methods (integrity checks
  over its own code). Hook the integrity check itself first, or
  attach later in the lifecycle after the check has run.
- You need to hook a method that only exists in a dynamically loaded
  module. Use `Module.load` callbacks or hook `dlopen`/`System.loadLibrary`
  and install your hooks when the module appears.
- The engagement needs repeatable instrumentation. Promote the script
  to the TypeScript workflow from the parent skill and check it into
  the engagement repo with the target build version.

## Detection and defender view

Method hooks are invisible to the app unless it looks for them:
integrity checks over method implementations, timing anomalies, and
Frida artifact detection. A defender-grade app combines these with
server-side verification so that a forced `isAuthenticated = true`
still cannot reach protected data. Your report should state exactly
which client-side checks fell to hooking and whether the server
stopped the forced flow anyway. That distinction is the difference
between a critical finding and an informative one.

## Key references

- Frida JavaScript API (Java and ObjC bridges):
  https://frida.re/docs/javascript-api/
- Frida CodeShare hooking examples:
  https://codeshare.frida.re/
- objection memory and hooking commands:
  https://github.com/sensepost/objection
- OWASP MSTG reverse engineering chapters:
  https://mas.owasp.org/MSTG/
- Apple Objective-C runtime reference:
  https://developer.apple.com/documentation/objectivec
- Android ART runtime method resolution notes:
  https://source.android.com/docs/core/dalvik
