---
name: mobile-frida-scripting
description: Use when you need to write custom Frida instrumentation for
  mobile apps during an authorized test, on Android or iOS. Covers agent
  structure for Java.perform and ObjC bridges, method hooking with
  argument and return value control, Interceptor use on native exports,
  Stalker-based code tracing, SSL pinning bypass patterns, the
  frida-compile TypeScript workflow with Node.js, and debugging agents
  that misbehave. Use when objection one-liners are not enough, when you
  must trace native code, when anti-analysis needs careful hook timing,
  or when static analysis handed you exact methods to instrument.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [mobile-ios-static, android-dynamic, ios-dynamic-analysis]
tools:
  - name: Frida
    version: 16.5
  - name: frida-tools
    version: 12.4
  - name: Python
    version: 3.12
  - name: Node.js
    version: 22.0
  - name: objection
    version: 1.11
---

Frida scripting is writing small JavaScript agents that inject into a
running mobile app and change or observe its behavior: hooking methods,
dumping arguments, forcing return values, and tracing native code. It is
the precision tool beneath objection's convenience commands. This skill
teaches the agent patterns that work reliably on real apps: correct
bridges for each platform, overload handling, safe logging, and the
TypeScript workflow for larger scripts. Everything here assumes an
authorized target: your client's in-scope app, your organization's
build, or a lab target, on a test device you control.

## Quick Workflow

1. Verify the Frida toolchain: workstation and device versions match,
   frida-server or gadget is running.
2. Confirm the target process with frida-ps and attach once with a
   hello-world agent.
3. Identify hook targets from static analysis (class-dump, method
   lists) and note exact signatures including overloads.
4. Write the agent: bridge (Java or ObjC), hook, log, and an RPC export
   for interactive control.
5. Test with spawn and --no-pause, watching for crashes on launch.
6. Iterate: add argument dumping, return value control, and backtraces.
7. For native targets, resolve exports and attach Interceptor with
   onEnter and onLeave handlers.
8. Save the working script with the app version in the filename and
   note what it proved.

## 1. Environment setup and the first attach

```bash
# Install the toolchain (Python 3.12 assumed)
pip install frida-tools==12.4

# Versions must match between workstation and device
frida --version
frida-ps -U | head -5

# Hello world agent, saved as hello.js
cat > hello.js <<'EOF'
console.log('[*] agent loaded, arch: ' + Process.arch);
EOF

# Attach to a running app by name
frida -U -n Target -l hello.js

# Or spawn it fresh (better for early hooks)
frida -U -f com.example.target -l hello.js --no-pause
```

If attach fails, check the three usual suspects in order: version
mismatch, frida-server not running or crashed, and the app refusing to
run on the test device (root or jailbreak detection). The sub-skill on
SSL pinning bypass covers the spawn pattern you will reuse constantly.

## 2. Java bridge: hooking Android methods

```javascript
// hooks-android.js: the Java.perform wrapper is mandatory
Java.perform(function () {
    // Resolve the class; use the exact name from static analysis
    var LoginManager = Java.use('com.example.target.LoginManager');

    // Hook a method and log arguments plus return value
    LoginManager.isAuthenticated.implementation = function () {
        var result = this.isAuthenticated();
        console.log('[*] isAuthenticated() -> ' + result);
        return result;
    };

    // Overloads need explicit signatures
    LoginManager.login.overload('java.lang.String', 'java.lang.String',
        'com.example.target.Callback').implementation = function (u, p, cb) {
        console.log('[*] login called for user: ' + u);
        // Call through normally during observation
        this.login(u, p, cb);
    };

    // Enumerate all methods when static analysis was thin
    var methods = LoginManager.class.getDeclaredMethods();
    methods.forEach(function (m) { console.log('[*] method: ' + m.toString()); });
});
```

Run it:

```bash
frida -U -f com.example.target -l hooks-android.js --no-pause
```

Example output shape:

```
[*] agent loaded
[*] method: public boolean com.example.target.LoginManager.isAuthenticated()
[*] login called for user: test@example.com
[*] isAuthenticated() -> false
```

Forcing a return value during an authorized test (for example, to see
what the app does after login without valid credentials) is one line:
replace `return result;` with `return true;`. Keep such modifications
clearly labeled in your notes, since they change app behavior.

## 3. ObjC bridge: hooking iOS methods

```javascript
// hooks-ios.js: ObjC.choose finds live instances, Interceptor hooks IMPs
if (ObjC.available) {
    // Hook by class and selector using the ObjC bridge
    var LoginManager = ObjC.classes.LoginManager;
    Interceptor.attach(LoginManager['- isAuthenticated'].implementation, {
        onEnter: function (args) {
            console.log('[*] isAuthenticated called on ' + args[0]);
        },
        onLeave: function (retval) {
            console.log('[*] isAuthenticated returned ' + retval);
        }
    });

    // Enumerate methods of a class (mirrors the Android example)
    var methods = Object.getOwnPropertyNames(LoginManager)
        .filter(function (m) { return m.indexOf('- ') === 0 || m.indexOf('+ ') === 0; });
    console.log('[*] methods: ' + JSON.stringify(methods.slice(0, 10)));
}
```

Note the selector syntax: `- isAuthenticated` for instance methods,
`+ sharedManager` for class methods. Arguments arrive in `args[0]`
(self), `args[1]` (selector), `args[2]` onward. Convert NSString
arguments for readable logs:

```javascript
onEnter: function (args) {
    var str = ObjC.Object(args[2]).toString();
    console.log('[*] got string arg: ' + str);
}
```

## 4. Interceptor on native exports

When the interesting logic lives in a `.so` or dylib, hook the native
function directly.

```javascript
// Wait for the library, then hook by export name
function hookNative() {
    var lib = Process.findModuleByName('libtarget.so');
    if (!lib) { console.log('[-] lib not loaded yet'); return; }
    var check = lib.getExportByName('Java_com_example_target_Native_check');
    Interceptor.attach(check, {
        onEnter: function (args) {
            console.log('[*] native check called');
            // Dump a byte buffer argument
            console.log(hexdump(args[1], { length: 32 }));
        },
        onLeave: function (retval) {
            console.log('[*] native check returned ' + retval);
            // Force pass during authorized testing
            retval.replace(1);
        }
    });
}
Java.perform(hookNative);  // run after the runtime is ready
```

For iOS dylibs the pattern is identical with `Process.findModuleByName`
and the C function name. When the export name is unknown, enumerate:

```javascript
Process.findModuleByName('libtarget.so').enumerateExports()
    .filter(function (e) { return e.name.indexOf('check') !== -1; })
    .forEach(function (e) { console.log(e.name + ' @ ' + e.address); });
```

## 5. Tracing with Stalker

Stalker follows code execution at the instruction level. Use it to find
which code runs during a feature, or to trace through obfuscated native
code.

```javascript
// Trace a single function with Stalker and log basic blocks
var target = Module.getExportByName('libtarget.so', 'check_license');
Stalker.follow(Process.getCurrentThreadId(), {
    events: { compile: true },
    onReceive: function (events) {
        var parsed = Stalker.parse(events);
        console.log('[*] executed ' + parsed.length + ' basic blocks');
    }
});
Interceptor.attach(target, {
    onEnter: function () { /* stalker already following */ },
    onLeave: function () { Stalker.unfollow(Process.getCurrentThreadId()); }
});
```

Stalker output is voluminous; always scope it to one thread and one
function, and unfollow promptly. For call-graph questions, combine with
backtraces instead:

```javascript
console.log(Thread.backtrace(this.context, Backtracer.ACCURATE)
    .map(DebugSymbol.fromAddress).join('\n'));
```

## 6. The TypeScript workflow with frida-compile

Scripts beyond a hundred lines deserve modules and types.

```bash
npm install -g frida-compile
mkdir agent && cd agent && npm init -y && npm install frida-compile

# agent.ts
cat > agent.ts <<'EOF'
import { log } from "./util.js";
Java.perform(() => {
    const LoginManager = Java.use('com.example.target.LoginManager');
    LoginManager.isAuthenticated.implementation = function () {
        const r: boolean = this.isAuthenticated();
        log(`isAuthenticated -> ${r}`);
        return r;
    };
});
EOF

frida-compile agent.ts -o _agent.js
frida -U -f com.example.target -l _agent.js --no-pause
```

TypeScript catches signature mistakes at compile time instead of as
silent runtime no-ops, which is the most common Frida debugging trap:
a hook that never fires usually has a wrong class name, wrong overload,
or a bridge entered before the runtime was ready.

## 7. RPC exports for interactive control

Expose functions to the Python side so you can call into the app
interactively.

```javascript
// rpc-agent.js
rpc.exports = {
    dumpToken: function () {
        var token = null;
        Java.perform(function () {
            var mgr = Java.use('com.example.target.LoginManager');
            // call a getter on a live instance via Java.choose
            Java.choose('com.example.target.LoginManager', {
                onMatch: function (instance) { token = instance.getToken(); },
                onComplete: function () {}
            });
        });
        return token;
    }
};
```

```python
# driver.py
import frida
session = frida.get_usb_device().attach('Target')
script = session.create_script(open('rpc-agent.js').read())
script.load()
print(script.exports_sync.dump_token())
```

This pattern turns Frida into a scripting API for the app: dump state,
invoke methods, and feed results into the rest of your test harness.

## Edge cases

- The hook never fires and there is no error. The class name is wrong,
  the overload signature is wrong, or the code path never runs. Log
  `Java.enumerateLoadedClasses` filtered by your target substring to
  confirm the class is actually loaded.
- The app crashes on spawn with your agent. Hook later: attach to the
  running app instead of spawning, or delay hooks with setTimeout so
  initialization completes first.
- Anti-Frida code detects the injection (port scan, maps check) and
  kills the app. Rename frida-server, run it on a nonstandard port,
  and inject later in the lifecycle. Document the detection as a
  working resilience control.
- Overload resolution throws "has more than one overload". List
  overloads with `method.overloads.forEach` and pick the exact
  signature; guessing wastes cycles.
- Stalker slows the app to a crawl. Narrow the follow to the target
  thread and function, use `events: { call: true }` instead of full
  compile events, and unfollow as soon as you have the trace.
- TypeScript compile errors reference frida types you never imported.
  The @types/frida-gum package provides them; install it as a
  devDependency.
- iOS selector names contain colons and spaces (`- loginWithUsername:password:`).
  Quote them exactly as `ObjC.classes.Foo['- loginWithUsername:password:']`;
  a missing colon is a silent miss.

## Escalation

- You need a bypass the generic scripts do not cover. Read the
  decompiled check (Ghidra or class-dump output), identify the exact
  method or native function, and write the targeted hook. The pinning
  bypass sub-skill has the platform patterns.
- The app uses heavy obfuscation and method names are meaningless.
  Switch to behavior-led hooking: hook framework APIs (network,
  crypto, storage) instead of app methods, and let the app reveal
  itself.
- Multiple analysts need the same instrumentation. Move the agent to
  the TypeScript workflow, check it into the engagement repo, and
  version it with the app build it targets.
- Frida cannot attach at all (hardened device, no gadget path).
  Escalate to the engagement lead: either the client provides a
  debuggable build or dynamic instrumentation is out of scope, and
  the report says so explicitly.

## Detection and defender view

Apps detect Frida through open port 27042 scans, the frida-server
process name, injected libraries visible in memory maps, and timing
checks around sensitive operations. Defenders should assume a
determined analyst bypasses each of these on a test device; the
durable response is server-side authorization, certificate pinning,
short-lived tokens, and no trust in client-side checks. As the tester,
every bypass you perform is itself evidence about defense depth: note
how long each control resisted and what finally defeated it. Never use
these techniques outside the authorized target and device.

## Key references

- Frida JavaScript API documentation:
  https://frida.re/docs/javascript-api/
- Frida iOS and Android guides:
  https://frida.re/docs/ios/ and https://frida.re/docs/android/
- Frida CodeShare (community scripts, review before use):
  https://codeshare.frida.re/
- objection documentation: https://github.com/sensepost/objection
- OWASP MSTG instrumentation chapters:
  https://mas.owasp.org/MSTG/
- OWASP MASVS resilience requirements:
  https://mas.owasp.org/MASVS/
- frida-compile project:
  https://github.com/frida/frida-compile
