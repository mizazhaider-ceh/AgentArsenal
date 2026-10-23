---
name: android-hardening
description: Use when hardening Android apps you build or review.
  Covers network security config, root and tamper detection, secure
  storage, and anti reverse engineering appropriate to the risk.
  Also use when an assessment found client side weaknesses to fix.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [android-static, android-dynamic, secure-coding]
tools:
  - name: Python
    version: 3.12
---

Android hardening raises the cost of attacking the app: it does not
make the client trusted, but it slows attackers and stops the easy
wins. This skill covers the practical controls for apps you build:
network config, storage, tamper detection, and what not to rely on.
Every control here assumes a motivated lab attacker can still bypass
it; the server stays the real boundary.

## Quick Workflow

1. Set the network security config: cleartext off, pinning on for
   your domains.
2. Store secrets properly: Android Keystore, never SharedPreferences
   or strings.
3. Add root and tamper detection appropriate to the risk, wired to
   server side responses.
4. Obfuscate and shrink the release build; keep the mapping for
   crash reports.
5. Protect the debug surface: no debuggable releases, no verbose
   logs.
6. Review IPC: exported components minimized and permission
   protected.
7. Test the hardening on a rooted lab device: what actually holds.
8. Document the residual risk honestly for the threat model.

## 1. Network and storage

```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
  <domain-config cleartextTrafficPermitted="false">
    <domain includeSubdomains="true">api.example.com</domain>
    <pin-set>
      <!-- pin your SPKI hashes; include a backup pin -->
      <pin digest="SHA-256">REPLACE_WITH_PIN</pin>
    </pin-set>
  </domain-config>
</network-security-config>
```

```bash
# Storage review: find insecure patterns
grep -rn "SharedPreferences\|MODE_WORLD\|getExternalStorage" \
  --include="*.java" --include="*.kt" app/src/ | head -20
# Secrets in BuildConfig or strings.xml: move to Keystore or fetch at runtime
grep -rn "api_key\|secret" app/src/main/res/values/ 2>/dev/null | head -10
```

## 2. Build and tamper controls

```bash
# Release build: minify, shrink, obfuscate (R8)
# android { buildTypes { release { minifyEnabled true; shrinkResources true } } }
# Verify the release APK is not debuggable:
aapt dump badging app-release.apk | grep -i debuggable
# Must be absent; debuggable=true in release is a critical finding
```

```bash
# Root/tamper detection points (implement, then test bypass in the lab):
# - SafetyNet/Play Integrity attestation, verified server side
# - signature check of the running APK
# - debugger and emulator detection for high risk flows
echo "each check must change server behavior, not just show a dialog"
```

## Edge cases

- Pinning breaks with certificate rotation. Keep a backup pin and
  a tested rotation runbook.
- Obfuscation breaks crash reporting. Upload the mapping file to
  your crash service.
- Hardening annoys legitimate power users (rooted devices). Tier
  the response: warn, limit, or block per the risk.

## Escalation

- Assessment found client side secrets: move them server side;
  no obfuscation fixes a hardcoded key.
- Need the attacker's view: hand to android-dynamic for the
  bypass testing.

## Detection and defender view

Hardening is detected working when lab bypass takes real effort
and automated attacks fail. Server side, monitor for attestation
failures, rooted device rates, and API abuse from modified apps.
The durable principle: harden the client to raise cost, enforce
security on the server to provide it.

## Key references

- OWASP MASVS: hardening requirements.
- Android developer security documentation.
- Related skills: android-static, secure-coding.
