---
name: mobile-frida-scripting-native-code-tracing
description: Use when the security logic you need to understand lives in
  native code (C, C++, Rust) inside a mobile app during an authorized
  test. Covers resolving native exports with Frida 16.5, Interceptor
  tracing of JNI and C functions, Stalker-based instruction tracing for
  obfuscated routines, reading ARM64 registers and memory, dumping
  buffers with hexdump, and tracing from a managed hook into the native
  layer. Use when the parent mobile-frida-scripting hooks stop at a
  native boundary, when crypto or license checks live in a .so or dylib,
  or when static analysis of the native library needs runtime
  confirmation, mapped back to Ghidra disassembly.
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
  - name: Ghidra
    version: 11.2
---

Native code tracing follows execution into compiled libraries where
Java and Objective-C hooks cannot reach: JNI bridges, bundled crypto,
license validators, and obfuscated routines. Frida's Interceptor and
Stalker give you breakpoints and instruction traces without a
debugger. This sub-skill covers resolving native targets, reading
registers and memory at hook points, and scoping Stalker traces so they
stay usable. Authorized targets only, on test devices you control.

## Quick Workflow

1. Identify the native library and function from static analysis
   (Ghidra, strings, JNI name mangling).
2. Confirm the library is loaded at runtime and resolve the export
   address.
3. Attach a minimal Interceptor hook that logs entry and the return
   value.
4. Add register and memory reads for the arguments you care about.
5. For control-flow questions, run a scoped Stalker trace on one
   thread and one function.
6. Correlate the trace with the Ghidra disassembly to name the basic
   blocks that executed.
7. Dump interesting buffers to files for offline analysis.
8. Record addresses as offsets from the module base, since ASLR moves
   them every launch.

## 1. Resolving native targets

```javascript
// Find the library and list candidate exports
var lib = Process.findModuleByName('libtarget.so');
if (lib === null) {
    console.log('[-] libtarget.so not loaded yet');
} else {
    console.log('[*] base: ' + lib.base + ' size: ' + lib.size);
    lib.enumerateExports().forEach(function (e) {
        if (/check|verify|decrypt|license/i.test(e.name)) {
            console.log('[*] ' + e.type + ' ' + e.name + ' @ ' +
                e.address.sub(lib.base) + ' (offset)');
        }
    });
}

// JNI functions follow a mangled naming convention you can predict
// Java_com_example_target_Native_check -> search directly:
var check = lib.getExportByName('Java_com_example_target_Native_check');
console.log('[*] check @ offset ' + check.sub(lib.base));
```

Always record offsets, not absolute addresses: ASLR randomizes the
base every launch, but the offset is stable per build. Your report and
your Ghidra annotations should use offsets.

If the export is not listed, the function may be static (local) inside
the library. Find it by pattern: hook the JNI entry point and Stalker
trace into the library, or search memory for a known constant the
function references.

## 2. Interceptor on native functions with register reads

```javascript
// Trace a native check function: arguments are in registers on ARM64
Interceptor.attach(check, {
    onEnter: function (args) {
        // JNI signature: (JNIEnv* env, jobject thiz, ...) so real args start at args[2]
        console.log('[*] native check entered');
        console.log('    arg0 (env):  ' + args[0]);
        console.log('    arg1 (thiz): ' + args[1]);
        // Dump the first 64 bytes of the buffer argument
        console.log(hexdump(args[2], { length: 64, header: true, ansi: false }));
        // Save registers for the onLeave handler
        this.bufArg = args[2];
    },
    onLeave: function (retval) {
        console.log('[*] native check returned: ' + retval);
        // Force pass during authorized testing
        // retval.replace(1);
    }
});
```

On ARM64, integer and pointer arguments arrive in x0-x7, which Frida
exposes as `args[0]` through `args[7]`. Floating point arguments use
separate registers and need `this.context.d0` style reads via the
`this.context` object available in the handlers.

Example output shape:

```
[*] native check entered
    arg0 (env):  0x7b8c2a1000
    arg1 (thiz): 0x12c080060
              0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
00000000  7b 22 74 6f 6b 65 6e 22 3a 22 65 79 4a 68 62 47  {"token":"eyJhbG
[*] native check returned: 0x0
```

The hexdump shows the plaintext token entering native code, which
answers "what does the native layer actually receive" definitively.

## 3. Reading memory safely

```javascript
// Guard every read: native pointers can be null or garbage
function safeReadString(ptr) {
    try {
        if (ptr.isNull()) return '<null>';
        return Memory.readUtf8String(ptr, 256);
    } catch (e) {
        return '<unreadable: ' + e.message + '>';
    }
}

function safeReadBytes(ptr, len) {
    try {
        return Memory.readByteArray(ptr, len);
    } catch (e) {
        console.log('[-] read failed: ' + e.message);
        return null;
    }
}
```

Wrap reads in try/catch as a habit. A crashing agent on a hooked
hot path can destabilize the app and cost you the test session.
Prefer `Memory.readByteArray` plus offline analysis over huge
console dumps.

## 4. Scoped Stalker tracing

```javascript
// Trace one function on the current thread, then stop
var target = lib.getExportByName('verify_license');

Interceptor.attach(target, {
    onEnter: function (args) {
        console.log('[*] starting Stalker on thread ' + Process.getCurrentThreadId());
        Stalker.follow(Process.getCurrentThreadId(), {
            events: {
                call: true,   // log calls, cheaper than full compile events
                ret: false,
                exec: false,
                block: false,
                compile: false
            },
            onReceive: function (events) {
                var calls = Stalker.parse(events, { annotate: true });
                calls.forEach(function (c) {
                    console.log('[*] call -> ' + DebugSymbol.fromAddress(c[1]));
                });
            }
        });
        this.tracing = true;
    },
    onLeave: function (retval) {
        if (this.tracing) {
            Stalker.unfollow(Process.getCurrentThreadId());
            Stalker.flush();
            console.log('[*] trace complete, return: ' + retval);
        }
    }
});
```

Rules for usable traces: one thread only, one function scope, call
events instead of compile events unless you need basic blocks, and
always unfollow. An unbounded Stalker trace on a busy app produces
gigabytes and teaches nothing.

To map the trace back to Ghidra, convert each logged address to a
module offset (`address.sub(lib.base)`) and look it up in the
disassembly. The executed call targets name the real control flow
through obfuscated dispatchers.

## 5. Tracing JNI boundaries

```javascript
// Hook RegisterNatives to learn dynamic JNI mappings
var RegisterNatives = Module.getExportByName('libart.so', '_ZN3art3JNI15RegisterNativesEP7_JNIEnvP7_jclassPK15JNINativeMethodi');
Interceptor.attach(RegisterNatives, {
    onEnter: function (args) {
        var methods = args[2];
        var count = args[3].toInt32();
        console.log('[*] RegisterNatives, ' + count + ' methods');
        for (var i = 0; i < count; i++) {
            var entry = methods.add(i * Process.pointerSize * 3);
            var name = Memory.readUtf8String(Memory.readPointer(entry));
            var sig = Memory.readUtf8String(Memory.readPointer(entry.add(Process.pointerSize)));
            var fn = Memory.readPointer(entry.add(Process.pointerSize * 2));
            console.log('    ' + name + sig + ' -> ' + fn);
        }
    }
});
```

Apps that register JNI methods dynamically defeat static name-based
lookup. This hook reveals the true name-to-address mapping at
runtime, and every address it prints becomes a hook target for
section 2.

## 6. Dumping buffers to files

```javascript
// Write a captured buffer to the device, then pull it
Interceptor.attach(check, {
    onLeave: function (retval) {
        var out = safeReadBytes(this.bufArg, 256);
        if (out) {
            var path = '/data/local/tmp/native-dump.bin';
            var f = new File(path, 'wb');
            f.write(out);
            f.close();
            console.log('[*] dumped 256 bytes to ' + path);
        }
    }
});
```

```bash
adb pull /data/local/tmp/native-dump.bin ./
xxd native-dump.bin | head -20
```

Offline analysis of the dump (entropy check, structure parsing)
complements the live trace and keeps the agent lightweight.

## Edge cases

- The library is not loaded when your agent runs. Defer hooking:
  watch `dlopen` or `android_dlopen_ext` and install hooks when the
  target module appears, or trigger the feature that loads it first.
- The function is stripped and has no export name. Work from offsets
  found in Ghidra, resolved as `lib.base.add(0x1234)`, and verify with
  a logging-only hook before adding logic.
- Stalker output is empty. The thread id may be wrong (hooks run on
  the calling thread, so capture it in onEnter), or the function
  returned before Stalker attached. Start the follow inside onEnter
  as shown.
- The app uses multiple threads for the sensitive operation. Trace
  each thread separately, or hook the thread creation point and
  follow the new thread from there.
- Reading a register gives garbage. Confirm the calling convention:
  ARM64 passes the first eight arguments in x0-x7, but variadic or
  large struct arguments behave differently. Check the Ghidra
  decompilation for the true signature.
- The native code detects the hook via integrity checks. This is the
  escalation point: hook the integrity check first, or trace without
  patching by using Stalker alone.

## Escalation

- You need instruction-level detail through an obfuscated routine.
  Enable compile events in Stalker for that one function, accept the
  slowdown, and map executed blocks back to Ghidra. Keep the window
  as short as possible.
- The target uses anti-debugging (ptrace, timing checks) that also
  trips on Frida. Hook the anti-debug functions to no-op them before
  installing your real hooks; the parent skill covers hook ordering.
- The crypto is custom and you need the algorithm, not just the key.
  Trace with Stalker, extract the executed basic blocks, and
  reconstruct the round function in Ghidra or Python offline.
- The engagement needs this trace repeatable. Save the agent with
  module offsets (not absolute addresses) and the exact build
  version, and note the Ghidra addresses they correspond to.

## Detection and defender view

Native hooks are harder for an app to detect than managed hooks, but
not invisible: timing checks around crypto operations, integrity
verification of code pages, and detection of Stalker's code cache can
all fire. Defenders layer these with server-side checks so that even
a fully traced client cannot mint valid tokens. Your report should
describe what the native layer actually did with the data you traced
(key usage, validation logic) and whether defeating it changed any
server-side outcome. A native check that the server re-verifies is
defense in depth working as intended.

## Key references

- Frida Stalker documentation:
  https://frida.re/docs/stalker/
- Frida JavaScript API (Interceptor, Memory, Stalker):
  https://frida.re/docs/javascript-api/
- ARM64 procedure call standard (register usage):
  https://developer.arm.com/documentation/ihi0055/latest
- Android JNI tips and RegisterNatives:
  https://developer.android.com/training/articles/perf-jni
- Ghidra documentation:
  https://ghidra-sre.org/
- OWASP MSTG reverse engineering chapters:
  https://mas.owasp.org/MSTG/
